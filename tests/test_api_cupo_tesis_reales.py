"""Prueba del cupo de CPU con las tesis reales del corpus (RI-01).

`recursos/` está en `.gitignore`: en CI este archivo se salta. En la
máquina del operador carga las dos tesis reales y comprueba el criterio
de cierre de RI-01:

- una tesis normal cabe en el presupuesto del cupo;
- dos tesis consecutivas responden 200 en ambos órdenes, sin limpiar el
  estado del proceso entre ellas;
- la tercera carga sí recibe 429, con una espera coherente.

El test usa el estado real del limitador (`deuda`) para detectar una
máquina demasiado lenta: si una sola tesis no cabe en el presupuesto,
el mensaje de fallo lo dice y el operador puede ajustar
`VISTOBUENO_RATE_LIMIT_CPU_SEG`.
"""

from pathlib import Path

import pytest
from conftest import CLIENTE, MIME_DOCX

import validator.api

RECURSOS_DIR = Path(__file__).resolve().parent.parent / "recursos"


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
    """RI-01 sobre el corpus real: dos tesis seguidas no se bloquean."""

    @staticmethod
    def _subir(ruta: Path):
        with open(ruta, "rb") as f:
            return CLIENTE.post(
                "/validar",
                files={"archivo": (ruta.name, f, MIME_DOCX)},
            )

    @pytest.mark.parametrize("orden", ["primero_bueno", "primero_rojo"])
    def test_dos_tesis_seguidas_en_ambos_ordenes(self, orden):
        """En ambos órdenes, la segunda tesis entra y la tercera espera."""
        tesis = _tesis_reales()
        buena, otra = tesis[0], tesis[1]
        if orden == "primero_rojo":
            buena, otra = otra, buena

        primera = self._subir(buena)
        assert primera.status_code == 200, primera.text

        deuda = validator.api._LIMITADOR_CPU_VALIDACION.deuda
        assert deuda < validator.api.PRESUPUESTO_CPU_DEFAULT, (
            f"una tesis real costó {deuda:.2f} s de CPU y no cabe en el "
            f"presupuesto de {validator.api.PRESUPUESTO_CPU_DEFAULT} s; "
            "suba VISTOBUENO_RATE_LIMIT_CPU_SEG en esta máquina"
        )

        segunda = self._subir(otra)
        assert segunda.status_code == 200, segunda.text

        tercera = self._subir(buena)
        assert tercera.status_code == 429, tercera.text
        assert int(tercera.headers["Retry-After"]) > 0
