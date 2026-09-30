"""Tests unitarios del módulo de notificación (validator/notificacion.py).

Cobertura:
- ConfigSMTP: defaults (deshabilitado), activación por entorno, parsing
  defensivo de puerto.
- plantilla_correo: registro formal, escape HTML de contenido adversario,
  inclusión de rule_id/cita/ubicación, versión texto plano, caso defensivo
  verde.
- enviar_notificacion: envío mocked (encabezados Date/Message-ID, From/To,
  STARTTLS/login condicionales), fallo best-effort (nunca lanza, expone
  motivo en detalle), deshabilitado por defecto.
- Guardia de contrato: POST /validar expone el estado de la notificación
  (campo `notificacion` con `estado` y `detalle`).
"""

import html
import smtplib

import pytest
from conftest import CLIENTE, MIME_DOCX
from docx_factory import compilar_docx, configuracion_base

from validator.api_models import ValidarResponse
from validator.notificacion import (
    ConfigSMTP,
    enviar_notificacion,
    plantilla_correo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def dto_rojo() -> ValidarResponse:
    """DTO de ejemplo con 2 reglas fallidas (una con contenido adversario)."""
    return ValidarResponse.model_validate(
        {
            "semaforo": "rojo",
            "resumen": {"total": 47, "fallidos_error": 2, "fallidos_warning": 1},
            "resultados": [
                {
                    "rule_id": "papel_tamano",
                    "paso": False,
                    "severidad": "error",
                    "mensaje": "Tamaño de papel incorrecto <script>alert('xss')</script>",
                    "esperado": "210 x 297 mm",
                    "encontrado": "216 x 279 mm",
                    "ubicacion": 'Sección "Formato general" (párr. 124-125)',
                    "fuente": "MANUAL.docx",
                    "cita": '"Tamaño A4/papel (210x297 cm)"',
                },
                {
                    "rule_id": "fuente_cuerpo",
                    "paso": False,
                    "severidad": "warning",
                    "mensaje": "Fuente del cuerpo distinta a Arial",
                    "esperado": "Arial 12",
                    "encontrado": "Times New Roman 12",
                    "ubicacion": None,
                    "fuente": "",
                    "cita": "",
                },
                {
                    "rule_id": "margen_superior",
                    "paso": True,
                    "severidad": "error",
                    "mensaje": "Margen superior correcto",
                    "esperado": "",
                    "encontrado": "cumple",
                    "ubicacion": None,
                    "fuente": "",
                    "cita": "",
                },
            ],
            "como_preguntar_a_una_ia": [],
            "metadatos": {
                "archivo_nombre": "tesis_prueba.docx",
                "archivo_tamano_bytes": 1024,
                "reglas_evaluadas": 47,
                "version_esquema": "2026-09-01",
            },
        }
    )


def dto_verde() -> ValidarResponse:
    """DTO defensivo: todo pasa (el wiring solo debe enviar en rojo)."""
    return ValidarResponse.model_validate(
        {
            "semaforo": "verde",
            "resumen": {"total": 47, "fallidos_error": 0, "fallidos_warning": 0},
            "resultados": [],
            "como_preguntar_a_una_ia": [],
            "metadatos": {
                "archivo_nombre": "tesis_ok.docx",
                "archivo_tamano_bytes": 1024,
                "reglas_evaluadas": 47,
                "version_esquema": "2026-09-01",
            },
        }
    )


class SMTPFalso:
    """Doble de smtplib.SMTP que registra llamadas sin red."""

    instancias: list[SMTPFalso] = []

    def __init__(self, host: str, port: int, timeout: float | None = None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.llamadas: list = []
        self.mensaje_enviado = None
        SMTPFalso.instancias.append(self)

    def starttls(self) -> None:
        self.llamadas.append("starttls")

    def login(self, usuario: str, clave: str) -> None:
        self.llamadas.append(("login", usuario, clave))

    def send_message(self, msg) -> None:
        self.mensaje_enviado = msg
        self.llamadas.append("send_message")

    def __enter__(self) -> SMTPFalso:
        return self

    def __exit__(self, *exc) -> None:
        return None


@pytest.fixture
def smtp_falso(monkeypatch):
    """Parchea smtplib.SMTP por el doble; expone las instancias creadas."""
    SMTPFalso.instancias = []
    monkeypatch.setattr(smtplib, "SMTP", SMTPFalso)
    return SMTPFalso


# ---------------------------------------------------------------------------
# ConfigSMTP
# ---------------------------------------------------------------------------


class TestConfigSMTP:
    def test_deshabilitado_por_defecto(self, monkeypatch):
        """Sin variables de entorno, el envío queda deshabilitado."""
        for var in (
            "VISTOBUENO_SMTP_HOST",
            "VISTOBUENO_SMTP_PORT",
            "VISTOBUENO_SMTP_USER",
            "VISTOBUENO_SMTP_PASSWORD",
            "VISTOBUENO_SMTP_STARTTLS",
            "VISTOBUENO_CORREO_REMITENTE",
            "VISTOBUENO_NOTIFICACIONES",
        ):
            monkeypatch.delenv(var, raising=False)
        cfg = ConfigSMTP.desde_entorno()
        assert cfg.enabled is False

    def test_habilitado_con_host_y_flag(self, monkeypatch):
        """Flag + host activan; el password no es necesario para 'enabled'."""
        monkeypatch.setenv("VISTOBUENO_SMTP_HOST", "smtp.unitru.edu.pe")
        monkeypatch.setenv("VISTOBUENO_SMTP_PORT", "587")
        monkeypatch.setenv("VISTOBUENO_NOTIFICACIONES", "1")
        cfg = ConfigSMTP.desde_entorno()
        assert cfg.enabled is True
        assert cfg.starttls is True

    def test_flag_sin_host_no_habilita(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_NOTIFICACIONES", "1")
        monkeypatch.delenv("VISTOBUENO_SMTP_HOST", raising=False)
        assert ConfigSMTP.desde_entorno().enabled is False

    def test_puerto_no_numerico_cae_al_default(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_SMTP_PORT", "no-numerico")
        assert ConfigSMTP.desde_entorno().port == 587

    def test_starttls_false_para_sink_local(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("VISTOBUENO_SMTP_STARTTLS", "false")
        monkeypatch.setenv("VISTOBUENO_NOTIFICACIONES", "1")
        cfg = ConfigSMTP.desde_entorno()
        assert cfg.starttls is False
        assert cfg.enabled is True


# ---------------------------------------------------------------------------
# plantilla_correo
# ---------------------------------------------------------------------------


class TestPlantillaCorreo:
    def test_registro_formal_y_nombre(self):
        html_body, texto = plantilla_correo(dto_rojo())
        for cuerpo in (html_body, texto):
            assert "Estimado(a) estudiante" in cuerpo
            assert "tesis_prueba.docx" in cuerpo

    def test_contiene_reglas_fallidas_y_excluye_cumplidas(self):
        html_body, texto = plantilla_correo(dto_rojo())
        assert "papel_tamano" in html_body
        assert "fuente_cuerpo" in html_body
        # La regla que PASA no debe aparecer en la tabla de observaciones
        assert "margen_superior" not in html_body

    def test_escapa_html_adversario(self):
        html_body, texto = plantilla_correo(dto_rojo())
        assert "<script>" not in html_body
        # La forma escapada de "<script>" (html.escape) debe estar presente
        assert html.escape("<script>") in html_body
        # En texto plano el contenido adversario se conserva literal (es texto)
        assert "<script>alert('xss')</script>" in texto

    def test_contiene_valores_referencias_y_citas(self):
        html_body, _ = plantilla_correo(dto_rojo())
        assert "210 x 297 mm" in html_body
        assert "216 x 279 mm" in html_body
        assert "Formato general" in html_body
        assert "210x297 cm" in html_body  # cita
        assert "<strong>error</strong>" in html_body
        assert "<strong>warning</strong>" in html_body

    def test_caso_defensivo_verde(self):
        html_body, texto = plantilla_correo(dto_verde())
        assert "No se detectaron observaciones" in html_body
        assert "No se detectaron observaciones" in texto


# ---------------------------------------------------------------------------
# enviar_notificacion
# ---------------------------------------------------------------------------


class TestEnviarNotificacion:
    def test_deshabilitado_no_toca_smtp(self, smtp_falso):
        """Config sin flag: no envía, explica el motivo y jamás abre conexión."""
        cfg = ConfigSMTP(host="127.0.0.1", notificaciones=False)
        resultado = enviar_notificacion(dto_rojo(), "destino@prueba.local", cfg)
        assert resultado.enviado is False
        assert "deshabilitadas" in resultado.detalle
        assert smtp_falso.instancias == []

    def test_envio_exitoso_arma_encabezados(self, smtp_falso):
        cfg = ConfigSMTP(
            host="127.0.0.1",
            port=8025,
            starttls=False,
            remitente="no-responder@unitru.edu.pe",
            notificaciones=True,
        )
        assert enviar_notificacion(dto_rojo(), "destino@prueba.local", cfg).enviado is True
        (smtp,) = smtp_falso.instancias
        assert (smtp.host, smtp.port) == ("127.0.0.1", 8025)
        assert "send_message" in smtp.llamadas
        msg = smtp.mensaje_enviado
        # Encabezados que smtplib NO agrega y los servidores reales exigen
        assert msg["Date"] is not None
        assert msg["Message-ID"] is not None
        assert str(msg["From"]) == "no-responder@unitru.edu.pe"
        assert str(msg["To"]) == "destino@prueba.local"
        assert "tesis_prueba.docx" in str(msg["Subject"])
        assert msg.is_multipart()  # multipart/alternative (texto + HTML)

    def test_starttls_y_login_condicionales(self, smtp_falso):
        cfg = ConfigSMTP(
            host="smtp.unitru.edu.pe",
            port=587,
            user="vistobueno",
            password="clave-de-prueba",
            starttls=True,
            notificaciones=True,
        )
        assert enviar_notificacion(dto_rojo(), "destino@prueba.local", cfg).enviado is True
        (smtp,) = smtp_falso.instancias
        assert "starttls" in smtp.llamadas
        assert ("login", "vistobueno", "clave-de-prueba") in smtp.llamadas

    def test_sin_starttls_no_lo_negocia(self, smtp_falso):
        cfg = ConfigSMTP(host="127.0.0.1", starttls=False, notificaciones=True)
        enviar_notificacion(dto_rojo(), "destino@prueba.local", cfg)
        (smtp,) = smtp_falso.instancias
        assert "starttls" not in smtp.llamadas
        assert not any(llamada.startswith("login") for llamada in smtp.llamadas)

    def test_fallo_smtp_es_best_effort(self, monkeypatch):
        """Conexión rechazada (OSError): retorna False, nunca lanza."""

        class SMTPRoto:
            def __init__(self, *args, **kwargs):
                raise ConnectionRefusedError("conexion rechazada")

        monkeypatch.setattr(smtplib, "SMTP", SMTPRoto)
        cfg = ConfigSMTP(host="127.0.0.1", notificaciones=True)
        resultado = enviar_notificacion(dto_rojo(), "destino@prueba.local", cfg)
        assert resultado.enviado is False
        # El motivo técnico queda expuesto para el personal del repositorio
        assert "ConnectionRefusedError" in resultado.detalle

    def test_error_smtp_en_login_tambien_es_best_effort(self, monkeypatch):
        class SMTPAuthRoto:
            def __init__(self, *args, **kwargs):
                pass

            def starttls(self):
                pass

            def login(self, u, p):
                raise smtplib.SMTPAuthenticationError(code=535, msg="credenciales rechazadas")

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

        monkeypatch.setattr(smtplib, "SMTP", SMTPAuthRoto)
        cfg = ConfigSMTP(host="smtp.unitru.edu.pe", user="u", password="p", notificaciones=True)
        resultado = enviar_notificacion(dto_rojo(), "destino@prueba.local", cfg)
        assert resultado.enviado is False
        assert "SMTPAuthenticationError" in resultado.detalle


# ---------------------------------------------------------------------------
# Guardia de contrato: la respuesta de /validar expone la notificación
# ---------------------------------------------------------------------------


class TestGuardiaContrato:
    def test_respuesta_expone_estado_de_notificacion(self, monkeypatch):
        """El esquema incluye `notificacion` (estado + detalle)."""
        # Defensivo: si el entorno del desarrollador tiene SMTP configurado,
        # el estado cambiaría. monkeypatch revierte al salir del test.
        for var in (
            "VISTOBUENO_SMTP_HOST",
            "VISTOBUENO_SMTP_PORT",
            "VISTOBUENO_SMTP_USER",
            "VISTOBUENO_SMTP_PASSWORD",
            "VISTOBUENO_SMTP_STARTTLS",
            "VISTOBUENO_NOTIFICACIONES",
        ):
            monkeypatch.delenv(var, raising=False)
        with open(compilar_docx(configuracion_base()), "rb") as f:
            respuesta = CLIENTE.post(
                "/validar",
                files={
                    "archivo": (
                        "tesis.docx",
                        f,
                        MIME_DOCX,
                    )
                },
                data={"correo": "estudiante@unitru.edu.pe"},
            )
        assert respuesta.status_code == 200
        assert set(respuesta.json().keys()) == {
            "semaforo",
            "notificacion",
            "resumen",
            "resultados",
            "como_preguntar_a_una_ia",
            "metadatos",
        }
        # Documento base con rojo + correo válido, pero notificaciones
        # deshabilitadas por defecto en el entorno de tests.
        notificacion = respuesta.json()["notificacion"]
        assert notificacion == {"estado": "deshabilitado", "detalle": None}
