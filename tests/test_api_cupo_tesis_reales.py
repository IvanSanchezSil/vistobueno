"""Prueba del cupo de CPU con las tesis reales del corpus (RI-01).

`recursos/` está en `.gitignore`: en CI este archivo se salta. En la
máquina del operador carga las dos tesis reales y comprueba el criterio
de cierre de RI-01.

El presupuesto es un límite de TRABAJO por minuto, no un contador de
tesis: el coste de una validación varía con el documento y con el estado
del proceso (entre 1.5 y 3.8 s de CPU medidos en este corpus). Por eso
la prueba fija los invariantes que NO dependen de esa variación:

- una tesis real SIEMPRE entra: el operador no queda bloqueado por un
  documento;
- dos tesis consecutivas SIEMPRE entran, en los dos órdenes;
- una ráfaga se corta: tras un número acotado de tesis, alguna recibe
  429 con una espera coherente con el mensaje;
- el cupo no altera el semáforo de ninguna tesis.

El test compara contra el presupuesto VIGENTE (el que el limitador tiene
ajustado), no contra la constante: el operador puede cambiarlo con
`VISTOBUENO_RATE_LIMIT_CPU_SEG`.
"""

from pathlib import Path

import pytest
from conftest import CLIENTE, MIME_DOCX

import validator.api

RECURSOS_DIR = Path(__file__).resolve().parent.parent / "recursos"

# Tesis que se pueden subir antes de esperar que la ráfaga se corte.
MAX_INTENTOS_RAFAGA = 6


def _tesis_reales() -> list[Path]:
    """Devuelve las tesis del corpus, ordenadas por nombre.

    Excluye `TESIS DIGITAL MODELO B-2026.docx`: es la plantilla de la
    constancia, no una tesis.
    """
    return sorted(
        ruta for ruta in RECURSOS_DIR.glob("TESIS*.docx") if "MODELO B" not in ruta.name.upper()
    )


pytestmark = pytest.mark.skipif(
    len(_tesis_reales()) < 2,
    reason="El corpus local no tiene las dos tesis reales (recursos/ está en .gitignore)",
)


class TestCupoConTesisReales:
    """RI-01 sobre el corpus real: el cupo no bloquea el uso normal."""

    @staticmethod
    def _subir(ruta: Path):
        with open(ruta, "rb") as f:
            return CLIENTE.post(
                "/validar",
                files={"archivo": (ruta.name, f, MIME_DOCX)},
            )

    @staticmethod
    def _presupuesto_vigente() -> float:
        """Presupuesto que el limitador tiene ajustado ahora mismo."""
        return validator.api._LIMITADOR_CPU_VALIDACION.presupuesto

    def test_una_tesis_real_siempre_entra(self):
        """Una tesis completa cabe en el presupuesto: no bloquea al operador."""
        tesis = _tesis_reales()

        respuesta = self._subir(tesis[0])

        assert respuesta.status_code == 200, respuesta.text
        presupuesto = self._presupuesto_vigente()
        deuda = validator.api._LIMITADOR_CPU_VALIDACION.deuda
        assert deuda < presupuesto, (
            f"una tesis real costó {deuda:.2f} s de CPU y no cabe en el "
            f"presupuesto vigente de {presupuesto:.2f} s; suba "
            "VISTOBUENO_RATE_LIMIT_CPU_SEG en esta máquina"
        )

    @pytest.mark.parametrize("orden", ["primero_bueno", "primero_rojo"])
    def test_dos_tesis_consecutivas_entrambas(self, orden):
        """En ambos órdenes, la segunda tesis entra: el uso normal no se corta."""
        tesis = _tesis_reales()
        buena, otra = tesis[0], tesis[1]
        if orden == "primero_rojo":
            buena, otra = otra, buena

        primera = self._subir(buena)
        segunda = self._subir(otra)

        assert primera.status_code == 200, primera.text
        assert segunda.status_code == 200, segunda.text

    def test_la_rafaga_de_tesis_se_corta(self):
        """Una ráfaga no pasa entera: alguna carga recibe 429 con la espera."""
        tesis = _tesis_reales()

        estados = []
        rebotada = None
        for _ in range(MAX_INTENTOS_RAFAGA):
            respuesta = self._subir(tesis[0])
            estados.append(respuesta.status_code)
            if respuesta.status_code == 429:
                rebotada = respuesta
                break

        assert rebotada is not None, (
            f"ninguna de las {MAX_INTENTOS_RAFAGA} cargas recibió 429 (estados: {estados}); "
            "si el presupuesto vigente es enorme, bájalo con VISTOBUENO_RATE_LIMIT_CPU_SEG"
        )

        espera = int(rebotada.headers["Retry-After"])
        detalle = rebotada.json()["detail"].lower()
        assert espera >= 1
        # El mensaje dice la misma espera que el header.
        unidad = "segundo" if espera == 1 else "segundos"
        assert f"{espera} {unidad}" in detalle
        assert "validación" in detalle

    def test_el_cupo_no_altera_el_semaforo(self):
        """Las dos tesis del corpus conservan su semáforo con el cupo puesto."""
        tesis = _tesis_reales()

        buena = self._subir(tesis[0])
        otra = self._subir(tesis[1])

        assert buena.status_code == 200, buena.text
        assert buena.json()["semaforo"] == "verde"
        assert otra.status_code == 200, otra.text
        assert otra.json()["semaforo"] == "rojo"
