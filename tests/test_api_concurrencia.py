"""Tests de concurrencia del endpoint POST /validar (Semana 7, hallazgo B2).

El endpoint es `async def`. Si el motor de reglas o el envío SMTP corren en
el hilo del event loop, la API completa deja de responder mientras dura cada
validación, y hasta TIMEOUT_SEGUNDOS extra por request si el servidor SMTP
está caído.

Contrato fijado aquí: el trabajo bloqueante se despacha al threadpool
(`fastapi.concurrency.run_in_threadpool`) y NUNCA corre en el hilo del
event loop. La verificación es estructural, no de timing: desde un hilo de
trabajo `asyncio.get_running_loop()` lanza RuntimeError; desde el hilo del
loop en ejecución devuelve el loop.
"""

import asyncio
import time

import httpx
from conftest import CLIENTE, MIME_DOCX
from docx_factory import aplicar_mutacion, compilar_docx, configuracion_base

import validator.api
from validator.models import RuleResult, Severity
from validator.notificacion import ResultadoEnvio


def _docx_bytes() -> bytes:
    """Bytes del documento bueno del factory (sin depender de recursos/)."""
    with open(compilar_docx(configuracion_base()), "rb") as f:
        return f.read()


def _docx_rojo_bytes() -> bytes:
    """Bytes de un DOCX con el cuerpo a 15 pt: reporte rojo, misma estructura."""
    config = aplicar_mutacion("tamano_cuerpo", configuracion_base())
    with open(compilar_docx(config), "rb") as f:
        return f.read()


def _corrio_en_event_loop() -> bool:
    """True si el hilo actual es el del event loop (donde NO debe correr)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _resultado_rojo() -> list[RuleResult]:
    """Un solo resultado de error: fuerza semáforo rojo en la respuesta."""
    return [
        RuleResult(
            rule_id="margen_superior",
            passed=False,
            severity=Severity.ERROR,
            message="Margen superior incorrecto",
            expected="3 cm",
            found="2.5 cm",
        )
    ]


class TestTrabajoBloqueanteFueraDelEventLoop:
    def test_el_motor_no_corre_en_el_event_loop(self, monkeypatch):
        """validate_docx debe correr en un hilo de trabajo, no en el loop."""
        en_loop: dict = {}

        def validate_docx_sonda(docx_path, rules_data, ficha_data=None):
            en_loop["motor"] = _corrio_en_event_loop()
            return []

        monkeypatch.setattr(validator.api, "validate_docx", validate_docx_sonda)
        respuesta = CLIENTE.post(
            "/validar",
            files={"archivo": ("tesis.docx", _docx_bytes(), MIME_DOCX)},
        )

        assert respuesta.status_code == 200
        assert en_loop.get("motor") is False, (
            "validate_docx corrió en el hilo del event loop: bloquea toda la API mientras valida"
        )

    def test_el_envio_smtp_no_corre_en_el_event_loop(self, monkeypatch):
        """enviar_notificacion (smtplib bloqueante) debe ir al threadpool."""
        en_loop: dict = {}

        def validate_docx_sonda(docx_path, rules_data, ficha_data=None):
            en_loop["motor"] = _corrio_en_event_loop()
            return _resultado_rojo()

        def enviar_sonda(respuesta, destino, config=None):
            en_loop["smtp"] = _corrio_en_event_loop()
            return ResultadoEnvio(enviado=True, detalle=None)

        monkeypatch.setattr(validator.api, "validate_docx", validate_docx_sonda)
        monkeypatch.setattr(validator.api, "enviar_notificacion", enviar_sonda)
        monkeypatch.setenv("VISTOBUENO_NOTIFICACIONES", "1")
        monkeypatch.setenv("VISTOBUENO_SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("VISTOBUENO_SMTP_STARTTLS", "false")

        respuesta = CLIENTE.post(
            "/validar",
            files={"archivo": ("tesis.docx", _docx_bytes(), MIME_DOCX)},
            data={"correo": "estudiante@unitru.edu.pe", "notificar": "true"},
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        # El rojo y el opt-in garantizan que la sonda SMTP se haya invocado
        assert cuerpo["semaforo"] == "rojo"
        assert cuerpo["notificacion"]["estado"] == "enviado"
        assert en_loop.get("smtp") is False, (
            "enviar_notificacion corrió en el hilo del event loop: "
            "un SMTP caído congelaría la API hasta por 10 s por request"
        )


class TestDosTesisSeguidas:
    """RI-01: dos validaciones consecutivas no se bloquean entre sí.

    El cupo es estado del proceso. Estos tests NO lo limpian entre las dos
    cargas: es exactamente la condición que reproducía el 429 de la
    revisión integral. El fixture autouse solo limpia al empezar y al
    terminar cada test.
    """

    @staticmethod
    def _subir(contenido: bytes):
        return CLIENTE.post(
            "/validar",
            files={"archivo": ("tesis.docx", contenido, MIME_DOCX)},
        )

    def test_orden_verde_rojo(self):
        """Tesis conforme y luego tesis con errores: las dos llegan a 200."""
        assert self._subir(_docx_bytes()).status_code == 200
        assert self._subir(_docx_rojo_bytes()).status_code == 200

    def test_orden_rojo_verde(self):
        """El orden inverso tampoco deja la segunda carga fuera."""
        assert self._subir(_docx_rojo_bytes()).status_code == 200
        assert self._subir(_docx_bytes()).status_code == 200

    def test_la_tercera_tesis_espera_el_cupo(self, monkeypatch):
        """Dos tesis de 3.8 s de CPU entran; la tercera recibe 429 coherente.

        El coste se simula con un medidor fijo para no gastar minutos de
        CPU en el test. 3.8 s es el coste medido con las tesis reales del
        corpus después de RI-07.
        """

        class MedidorFijo:
            def __init__(self) -> None:
                self.segundos = 0.0

            def medir(self, fn, *args):
                try:
                    return fn(*args)
                finally:
                    self.segundos += 3.8

        monkeypatch.setattr(validator.api, "_MedidorCPU", MedidorFijo)

        assert self._subir(_docx_bytes()).status_code == 200
        assert self._subir(_docx_rojo_bytes()).status_code == 200

        rebotada = self._subir(_docx_bytes())
        assert rebotada.status_code == 429
        espera = int(rebotada.headers["Retry-After"])
        detalle = rebotada.json()["detail"].lower()
        # 7.6 s de deuda - 5 s de presupuesto = 2.6 s a 5 s/min ≈ 31 s.
        assert 25 <= espera <= 40
        assert f"{espera} segundos" in detalle


class TestRafagaParalela:
    """RI-01: una ráfaga paralela no puede saltarse el cupo.

    El cupo de CPU se consulta antes del trabajo pesado: el coste real
    solo se conoce al terminar. Sin una cota de simultaneidad, varias
    peticiones paralelas entran todas antes de que la primera cobre su
    coste (medido con las tesis reales: 4 en paralelo = 14.2 s de CPU y
    la carga siguiente bloqueada 102 s).
    """

    @staticmethod
    def _subir_async(cliente: httpx.AsyncClient, contenido: bytes):
        return cliente.post(
            "/validar",
            files={"archivo": ("tesis.docx", contenido, MIME_DOCX)},
        )

    @staticmethod
    def _validacion_lenta(docx_path, rules_data, ficha_data=None):
        """Mantiene la validación en curso.

        El trabajo se despacha al threadpool, así que la espera no
        bloquea el event loop: las peticiones se solapan de verdad.
        """
        time.sleep(0.5)
        return []

    @classmethod
    async def _disparar(cls, numero: int, contenido: bytes) -> list[httpx.Response]:
        """Lanza `numero` validaciones a la vez y devuelve las respuestas."""
        transporte = httpx.ASGITransport(app=validator.api.app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(
            transport=transporte, base_url="http://127.0.0.1", timeout=60
        ) as cliente:
            return list(
                await asyncio.gather(*[cls._subir_async(cliente, contenido) for _ in range(numero)])
            )

    def test_la_rafaga_paralela_no_entra_entera(self, monkeypatch):
        """Solo entran las validaciones que caben en la cota; el resto, 429."""
        monkeypatch.setattr(validator.api, "validate_docx", self._validacion_lenta)
        contenido = _docx_bytes()

        respuestas = asyncio.run(self._disparar(6, contenido))
        codigos = [r.status_code for r in respuestas]

        assert codigos.count(200) == validator.api.MAX_VALIDACIONES_CONCURRENTES, codigos
        assert codigos.count(429) == 6 - validator.api.MAX_VALIDACIONES_CONCURRENTES, codigos

    def test_el_429_de_la_cota_dice_cuanto_esperar(self, monkeypatch):
        """La respuesta de la cota trae `Retry-After` y el mismo mensaje."""
        monkeypatch.setattr(validator.api, "validate_docx", self._validacion_lenta)
        contenido = _docx_bytes()

        respuestas = asyncio.run(self._disparar(4, contenido))
        rebotadas = [r for r in respuestas if r.status_code == 429]

        assert rebotadas, [r.status_code for r in respuestas]
        for rebotada in rebotadas:
            espera = int(rebotada.headers["Retry-After"])
            detalle = rebotada.json()["detail"].lower()
            assert espera >= 1
            # El mensaje usa la misma espera que el header (singular o plural).
            assert f"{espera} segundo" in detalle

    def test_el_hueco_se_libera_tras_un_archivo_rechazado(self):
        """Un 415 no deja un hueco cogido: las dos siguientes entran."""
        assert (
            CLIENTE.post(
                "/validar",
                files={"archivo": ("tesis.docx", b"contenido", "text/plain")},
            ).status_code
            == 415
        )
        assert (
            CLIENTE.post(
                "/validar",
                files={"archivo": ("tesis.docx", _docx_bytes(), MIME_DOCX)},
            ).status_code
            == 200
        )
        assert (
            CLIENTE.post(
                "/validar",
                files={"archivo": ("tesis.docx", _docx_bytes(), MIME_DOCX)},
            ).status_code
            == 200
        )

    def test_el_hueco_se_libera_si_el_cuerpo_es_invalido(self):
        """Una petición sin archivo (422) no deja un hueco cogido."""
        assert CLIENTE.post("/validar").status_code == 422
        assert (
            CLIENTE.post(
                "/validar",
                files={"archivo": ("tesis.docx", _docx_bytes(), MIME_DOCX)},
            ).status_code
            == 200
        )
        assert (
            CLIENTE.post(
                "/validar",
                files={"archivo": ("tesis.docx", _docx_bytes(), MIME_DOCX)},
            ).status_code
            == 200
        )

    def test_la_cota_ocupada_devuelve_429(self):
        """Con los huecos ocupados, /validar responde 429 con Retry-After."""
        ocupacion = [
            validator.api._SEMAFORO_VALIDACIONES.acquire(blocking=False)
            for _ in range(validator.api.MAX_VALIDACIONES_CONCURRENTES)
        ]
        try:
            assert all(ocupacion)
            respuesta = CLIENTE.post(
                "/validar",
                files={"archivo": ("tesis.docx", _docx_bytes(), MIME_DOCX)},
            )
            assert respuesta.status_code == 429
            assert int(respuesta.headers["Retry-After"]) >= 1
        finally:
            for tomada in ocupacion:
                if tomada:
                    validator.api._SEMAFORO_VALIDACIONES.release()
