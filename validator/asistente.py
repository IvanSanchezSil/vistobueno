"""Asistente del encargado — Funcionalidad 2: explicación y priorización (diseño 16).

Toma el reporte determinista del motor (reglas fallidas) y le pide a un LLM
local que (a) explique por qué falla cada regla en lenguaje llano y (b) ordene
las correcciones por impacto. Todo es **advisory**: nunca produce un
`RuleResult` ni toca el semáforo (principio P1 del diseño).

La IA **no lee la tesis**: solo recibe el bloque de fallos ya estructurado por
el motor (mensaje, esperado/encontrado, cita). Eso protege la privacidad y
abarata el cómputo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .llm import LLMClient
from .models import RuleResult

# Número máximo de intentos ante una respuesta no interpretable (1 reintento).
MAX_INTENTOS = 2

ESFUERZOS_VALIDOS = frozenset({"bajo", "medio", "alto"})


class RespuestaIAInvalida(Exception):
    """La IA no devolvió el JSON esperado ni siquiera tras el reintento."""


# ---------------------------------------------------------------------------
# Modelos advisory (internos del motor; I1 los mapea a DTOs Pydantic)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Explicacion:
    """Explicación en lenguaje llano de por qué falla una regla."""

    rule_id: str
    explicacion: str


@dataclass(frozen=True)
class Prioridad:
    """Orden recomendado de corrección de un fallo."""

    orden: int
    rule_id: str
    razon: str
    esfuerzo: str


@dataclass(frozen=True)
class ExplicacionYPrioridad:
    """Salida advisory de la Funcionalidad 2 (no interviene en el semáforo)."""

    explicaciones: list[Explicacion]
    prioridades: list[Prioridad]
    modelo: str = ""


# ---------------------------------------------------------------------------
# Esquema JSON esperado del modelo
# ---------------------------------------------------------------------------

ESQUEMA_EXPLICACION: dict[str, Any] = {
    "type": "object",
    "properties": {
        "explicaciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string"},
                    "explicacion": {"type": "string"},
                },
                "required": ["rule_id", "explicacion"],
            },
        },
        "prioridades": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "orden": {"type": "integer"},
                    "rule_id": {"type": "string"},
                    "razon": {"type": "string"},
                    "esfuerzo": {"type": "string", "enum": ["bajo", "medio", "alto"]},
                },
                "required": ["orden", "rule_id", "razon", "esfuerzo"],
            },
        },
    },
    "required": ["explicaciones", "prioridades"],
}

_SYSTEM_PROMPT = """\
Eres un asistente técnico del personal del repositorio de tesis de la FECyC \
(Universidad Nacional de Trujillo). Recibirás, en JSON, la lista de reglas de \
formato que NO se cumplieron en una tesis, y debes ayudar al encargado a \
interpretarlas y priorizar su corrección.

Reglas estrictas:
- Usa EXCLUSIVAMENTE los fallos de la lista; no inventes observaciones ni \
reglas que no aparezcan.
- No decides si la tesis se aprueba: el semáforo es determinista y ajeno a ti.
- Responde en español y SOLO con un objeto JSON válido, sin texto adicional.
- Formato exacto:
  {"explicaciones": [{"rule_id": "...", "explicacion": "..."}],
   "prioridades": [{"orden": 1, "rule_id": "...", "razon": "...",
                    "esfuerzo": "bajo"}]}
- "explicacion": causa probable y qué significa para la entrega, en lenguaje llano.
- "prioridades": orden de corrección (1 = primero), por impacto y esfuerzo.
- Cada "rule_id" debe pertenecer a la lista de fallos.\
"""


# ---------------------------------------------------------------------------
# Construcción del prompt
# ---------------------------------------------------------------------------


def _fallo_a_dict(fallo: RuleResult) -> dict[str, Any]:
    return {
        "rule_id": fallo.rule_id,
        "severidad": fallo.severity.value,
        "mensaje": fallo.message,
        "esperado": fallo.expected,
        "encontrado": fallo.found,
        "referencia": fallo.location,
        "cita": fallo.cita,
    }


def construir_prompt_explicar(
    fallidos: list[RuleResult],
    tipo_documento: str | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """Arma (system, user, json_schema) para la Funcionalidad 2.

    El `user` es solo el bloque de fallos (nunca el texto de la tesis).
    """
    contenido = {
        "tipo_documento": tipo_documento,
        "reglas_validas": sorted({fallo.rule_id for fallo in fallidos}),
        "fallos": [_fallo_a_dict(fallo) for fallo in fallidos],
    }
    user = json.dumps(contenido, ensure_ascii=False, indent=2)
    return _SYSTEM_PROMPT, user, ESQUEMA_EXPLICACION


# ---------------------------------------------------------------------------
# Parseo y validación de la respuesta
# ---------------------------------------------------------------------------


def _extraer_json(crudo: str) -> dict[str, Any]:
    """Extrae un objeto JSON del texto devuelto por el modelo.

    Aunque Ollama con `format="json"` devuelve JSON puro, se tolera que el
    modelo envuelva la respuesta en vallas Markdown (```json ... ```).
    """
    texto = crudo.strip()
    if texto.startswith("```"):
        _, _, resto = texto.partition("\n")
        texto = resto if resto else texto
        if texto.rstrip().endswith("```"):
            texto = texto.rstrip()[:-3]
        texto = texto.strip()

    try:
        data = json.loads(texto)
    except json.JSONDecodeError as e:
        raise RespuestaIAInvalida(f"la IA no devolvió JSON válido: {e}") from e
    if not isinstance(data, dict):
        raise RespuestaIAInvalida("se esperaba un objeto JSON en la respuesta de la IA")
    return data


def parse_explicacion(
    data: dict[str, Any],
    rule_ids_validos: set[str],
    modelo: str = "",
) -> ExplicacionYPrioridad:
    """Valida y normaliza la respuesta del modelo al modelo advisory.

    Descarta silenciosamente las entradas cuyo `rule_id` no esté entre los
    fallos reales: la IA no puede introducir observaciones inventadas.
    Lanza `RespuestaIAInvalida` si la estructura no es la esperada.
    """
    explicaciones_raw = data.get("explicaciones")
    prioridades_raw = data.get("prioridades")
    if not isinstance(explicaciones_raw, list) or not isinstance(prioridades_raw, list):
        raise RespuestaIAInvalida("faltan las listas 'explicaciones' y/o 'prioridades'")

    explicaciones: list[Explicacion] = []
    for item in explicaciones_raw:
        if not isinstance(item, dict):
            raise RespuestaIAInvalida("una 'explicacion' no es un objeto JSON")
        rule_id = item.get("rule_id")
        explicacion = item.get("explicacion")
        if not isinstance(rule_id, str) or not isinstance(explicacion, str):
            raise RespuestaIAInvalida("una 'explicacion' tiene campos inválidos")
        if rule_id not in rule_ids_validos:
            continue
        explicaciones.append(Explicacion(rule_id=rule_id, explicacion=explicacion))

    prioridades: list[Prioridad] = []
    for item in prioridades_raw:
        if not isinstance(item, dict):
            raise RespuestaIAInvalida("una 'prioridad' no es un objeto JSON")
        orden = item.get("orden")
        rule_id = item.get("rule_id")
        razon = item.get("razon")
        esfuerzo = item.get("esfuerzo")
        if not isinstance(orden, int) or isinstance(orden, bool):
            raise RespuestaIAInvalida("una 'prioridad' tiene 'orden' inválido")
        if not isinstance(rule_id, str) or not isinstance(razon, str):
            raise RespuestaIAInvalida("una 'prioridad' tiene campos inválidos")
        if not isinstance(esfuerzo, str) or esfuerzo not in ESFUERZOS_VALIDOS:
            raise RespuestaIAInvalida("una 'prioridad' tiene 'esfuerzo' inválido")
        if rule_id not in rule_ids_validos:
            continue
        prioridades.append(Prioridad(orden=orden, rule_id=rule_id, razon=razon, esfuerzo=esfuerzo))

    prioridades.sort(key=lambda p: p.orden)
    return ExplicacionYPrioridad(
        explicaciones=explicaciones,
        prioridades=prioridades,
        modelo=modelo,
    )


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------


async def explicar_y_priorizar(
    resultados: list[RuleResult],
    *,
    client: LLMClient,
    tipo_documento: str | None = None,
) -> ExplicacionYPrioridad:
    """Explica y prioriza los fallos usando el cliente LLM dado.

    - Si no hay fallos, no llama a la IA (devuelve una salida vacía).
    - Ante una respuesta no interpretable, reintenta una vez (MAX_INTENTOS).
    - `LLMError` (servicio caído) se propaga sin consumir el reintento.
    """
    fallidos = [r for r in resultados if not r.passed]
    rule_ids = {r.rule_id for r in fallidos}
    if not fallidos:
        return ExplicacionYPrioridad(explicaciones=[], prioridades=[], modelo=client.modelo)

    system, user, esquema = construir_prompt_explicar(fallidos, tipo_documento)

    ultimo_error: RespuestaIAInvalida | None = None
    for _ in range(MAX_INTENTOS):
        crudo = await client.chat(system, user, json_schema=esquema)
        try:
            data = _extraer_json(crudo)
            return parse_explicacion(data, rule_ids, modelo=client.modelo)
        except RespuestaIAInvalida as e:
            ultimo_error = e

    raise RespuestaIAInvalida(f"la IA no devolvió un formato interpretable: {ultimo_error}")
