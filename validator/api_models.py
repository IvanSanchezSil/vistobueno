"""Modelos Pydantic DTO para la API de validación.

Estos modelos definen el contrato externo de la API. Existen separados
del modelo interno `RuleResult` (dataclass) para:
1. Usar nombres en español en el JSON de respuesta (paso, severidad, mensaje...).
2. Agregar campos que solo existen en la capa API (metadatos).
3. Permitir versionar el contrato sin romper el motor de validación.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SeveridadAPI(str, Enum):
    """Severidad de una regla de validación."""

    ERROR = "error"
    WARNING = "warning"


class ResultadoReglaAPI(BaseModel):
    """Resultado de una regla individual en la respuesta de la API.

    Equivalente al `RuleResult` interno del motor, pero con campos
    renombrados a español y en formato snake_case para JSON.
    """

    rule_id: str = Field(..., description="Identificador único de la regla")
    paso: bool = Field(..., description="True si la regla se cumplió")
    severidad: SeveridadAPI = Field(..., description="error o warning")
    mensaje: str = Field(..., description="Descripción de la regla en lenguaje natural")
    esperado: str = Field(default="", description="Valor esperado según el reglamento")
    encontrado: str = Field(default="", description="Lo que encontró el validador")
    ubicacion: Optional[str] = Field(default=None, description="Referencia al documento del reglamento")
    fuente: str = Field(default="", description="Archivo fuente del que se extrajo la regla")
    cita: str = Field(default="", description="Cita textual del reglamento")


class PromptIA(BaseModel):
    """Bloque 'cómo preguntar a una IA' para una regla fallida.

    Contiene un prompt listo para copiar y pegar en un LLM externo,
    con el contexto de la regla incumplida.
    """

    rule_id: str = Field(..., description="ID de la regla fallida")
    prompt: str = Field(..., description="Prompt completo en español")


class ResumenValidacion(BaseModel):
    """Resumen cuantitativo de la validación."""

    total: int = Field(..., description="Total de reglas evaluadas")
    fallidos_error: int = Field(..., description="Reglas con severidad error que no pasaron")
    fallidos_warning: int = Field(..., description="Reglas con severidad warning que no pasaron")


class MetadatosValidacion(BaseModel):
    """Metadatos del procesamiento, agregados por la capa API.

    Estos campos no existen en el motor interno; se agregan aquí
    para dar contexto al frontend sobre el archivo procesado.
    """

    archivo_nombre: str = Field(..., description="Nombre original del archivo subido")
    archivo_tamano_bytes: int = Field(..., description="Tamaño en bytes del archivo")
    reglas_evaluadas: int = Field(..., description="Cantidad de reglas ejecutadas")
    version_esquema: str = Field(..., description="Versión del esquema YAML de reglas")


class ValidarResponse(BaseModel):
    """Respuesta completa del endpoint POST /validar.

    Agrupa el semáforo, el resumen, los resultados individuales por regla,
    los prompts de IA y los metadatos del procesamiento.
    """

    semaforo: str = Field(
        ..., description='"verde" si todas las reglas error pasan, "rojo" si alguna falla'
    )
    resumen: ResumenValidacion = Field(..., description="Resumen cuantitativo")
    resultados: List[ResultadoReglaAPI] = Field(..., description="Resultados por regla")
    como_preguntar_a_una_ia: List[PromptIA] = Field(
        default_factory=list,
        description="Bloques de prompts IA para reglas fallidas",
    )
    metadatos: MetadatosValidacion = Field(..., description="Metadatos del procesamiento")
