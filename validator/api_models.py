"""Modelos Pydantic DTO para la API de validación.

Estos modelos definen el contrato externo de la API. Existen separados
del modelo interno `RuleResult` (dataclass) para:
1. Usar nombres en español en el JSON de respuesta (paso, severidad, mensaje...).
2. Agregar campos que solo existen en la capa API (metadatos).
3. Permitir versionar el contrato sin romper el motor de validación.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Handle institucional del Repositorio UNT. Un enlace a otro repositorio
# no identifica un ítem de esta institución y no puede confirmar un depósito.
PATRON_HANDLE = r"^https://hdl\.handle\.net/20\.500\.14414/\d+/?$"


class SeveridadAPI(StrEnum):
    """Severidad de una regla de validación."""

    ERROR = "error"
    WARNING = "warning"


class EstadoNotificacionAPI(StrEnum):
    """Estado del envío del correo de observaciones al estudiante.

    La herramienta es de uso interno (personal del repositorio): el estado
    describe qué pasó con el envío para que el operador pueda informar al
    estudiante o reintentar manualmente. El envío es opt-in por solicitud
    (campo `notificar`): el operador decide cuándo el reporte está listo
    para llegarle al estudiante.
    """

    ENVIADO = "enviado"
    FALLO = "fallo"
    SIN_CORREO = "sin_correo"
    NO_SOLICITADO = "no_solicitado"
    SIN_OBSERVACIONES = "sin_observaciones"
    DESHABILITADO = "deshabilitado"


class EstadoDepositoAPI(StrEnum):
    """Estado del depósito del documento en DSpace (Actividad 10).

    DEPRECADO (decisión 2026-10-28): la app no escribe en la API de DSpace.
    Los valores `enviado` y `fallo` se conservan para no romper el
    contrato, pero el flujo vigente solo emite `sin_solicitud` o
    `deshabilitado`: el depósito real lo hace el encargado con el
    formulario oficial y el userscript.
    """

    ENVIADO = "enviado"
    FALLO = "fallo"
    SIN_SOLICITUD = "sin_solicitud"
    NO_APTO = "no_apto"
    DESHABILITADO = "deshabilitado"


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
    ubicacion: str | None = Field(
        default=None, description="Referencia al documento del reglamento"
    )
    fuente: str = Field(default="", description="Archivo fuente del que se extrajo la regla")
    cita: str = Field(default="", description="Cita textual del reglamento")
    aplicable: bool = Field(
        True,
        description="True si la regla se evaluó. False = la regla no aplica a este tipo de documento",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "rule_id": "papel_tamano",
                    "paso": True,
                    "severidad": "error",
                    "mensaje": "El tamaño del papel debe ser A4",
                    "esperado": "210 x 297 mm",
                    "encontrado": "cumple",
                    "aplicable": True,
                    "ubicacion": 'Sección "Formato general" (párr. 124-125)',
                    "fuente": "MANUAL REVISADO TERCERA VERSION OBSERVACIONES 11-07-2025.docx",
                    "cita": '"Tamaño A4/papel (210x297 cm)"',
                },
                {
                    "rule_id": "estructura_tinv_cualitativo",
                    "paso": True,
                    "severidad": "error",
                    "mensaje": "Se deben incluir las secciones del diseño cualitativo",
                    "esperado": "secciones obligatorias del esquema cualitativo",
                    "encontrado": "no aplica a este documento",
                    "aplicable": False,
                    "ubicacion": "Capítulo II — esquemas formales por tipo de título (párr. 75-90)",
                    "fuente": "MANUAL REVISADO TERCERA VERSION OBSERVACIONES 11-07-2025.docx",
                    "cita": '"Cada título profesional exige un esquema formal distinto"',
                },
            ]
        }
    }


class PromptIA(BaseModel):
    """Bloque 'cómo preguntar a una IA' para una regla fallida.

    Contiene un prompt listo para copiar y pegar en un LLM externo,
    con el contexto de la regla incumplida.
    """

    rule_id: str = Field(..., description="ID de la regla fallida")
    prompt: str = Field(..., description="Prompt completo en español")


class ResumenValidacion(BaseModel):
    """Resumen cuantitativo de la validación."""

    total: int = Field(..., description="Total de reglas presentes en el YAML")
    total_evaluadas: int = Field(..., description="Reglas realmente evaluadas sobre el documento")
    reglas_no_aplicables: int = Field(
        ..., description="Reglas omitidas porque no aplican a este tipo de documento"
    )
    fallidos_error: int = Field(..., description="Reglas con severidad error que no pasaron")
    fallidos_warning: int = Field(..., description="Reglas con severidad warning que no pasaron")


class MetadatosValidacion(BaseModel):
    """Metadatos del procesamiento, agregados por la capa API.

    Estos campos no existen en el motor interno; se agregan aquí
    para dar contexto al frontend sobre el archivo procesado.
    """

    archivo_nombre: str = Field(..., description="Nombre original del archivo subido")
    archivo_tamano_bytes: int = Field(..., description="Tamaño en bytes del archivo")
    reglas_evaluadas: int = Field(..., description="Reglas realmente ejecutadas")
    reglas_totales: int = Field(..., description="Total de reglas presentes en el YAML")
    version_esquema: str = Field(..., description="Versión del esquema YAML de reglas")
    tipo_documento_declarado: str | None = Field(
        None, description="Lo que declara el Anexo 10; None si no declaró"
    )
    tipo_documento_inferido: str | None = Field(
        None, description="Lo que se dedujo de las firmas estructurales; None si no pudo inferirse"
    )
    tipo_documento_estado: str | None = Field(
        None, description="Estado de la detección: vigente, sin_determinar o contradictorio"
    )


class NotificacionAPI(BaseModel):
    """Estado de la notificación por correo de observaciones.

    Exposición para el personal del repositorio: con `estado` "enviado" la
    interfaz puede informar "enviamos las observaciones al correo del
    estudiante"; con "fallo", el `detalle` explica el motivo técnico para
    reintentar o enviar manualmente; con "deshabilitado", el `detalle`
    indica cómo habilitar el servidor (nota de configuración).
    """

    estado: EstadoNotificacionAPI = Field(..., description="Veredicto del envío")
    detalle: str | None = Field(
        default=None,
        description=(
            "Motivo técnico cuando el envío falló; nota de configuración "
            "cuando el servidor está deshabilitado; None en el resto de casos"
        ),
    )


class DepositoAPI(BaseModel):
    """Estado del depósito del documento en DSpace (Actividad 10).

    DEPRECADO (decisión 2026-10-28). Misma forma que NotificacionAPI: el
    campo se conserva por compatibilidad del contrato, pero el flujo
    vigente solo devuelve `sin_solicitud` (no se pidió) o `deshabilitado`
    con la nota que explica el flujo oficial (formulario + userscript).
    """

    estado: EstadoDepositoAPI = Field(..., description="Veredicto del depósito")
    detalle: str | None = Field(
        default=None,
        description=(
            "Nota de seguimiento cuando se depositó (cola de aprobación); "
            "motivo técnico cuando falló; nota de configuración cuando el "
            "servidor está deshabilitado; None en el resto de casos"
        ),
    )


class CampoExtraidoFicha(BaseModel):
    """Valor extraído del DOCX por el motor (ficha de depósito, v1.7.0).

    Hasta que el motor publique sus extracciones (handover
    HANDOVER_MOTOR_FICHA_DEPOSITO), todos los campos extraídos viajan con
    `detectado=false` y `valor=null`; la forma del contrato es estable.
    """

    campo: str = Field(..., description="Clave acordada (dc.title, escuela, …)")
    valor: str | list[str] | None = Field(
        default=None,
        description="Texto completo o lista de textos (autores, palabras clave); None si no detectado",
    )
    pagina: int | None = Field(
        default=None, description="Página de origen en el DOCX, si el motor la conoce"
    )
    detectado: bool = Field(default=False, description="True si el motor encontró el elemento")


class CampoManualFicha(BaseModel):
    """Campo que el operador teclea en la pantalla de ficha (v1.7.0).

    El operador completa matrícula y DNI del autor o asesor. Las fichas
    anteriores también pueden enviar el ORCID del asesor en esta sección.
    """

    campo: str = Field(..., description="Clave acordada (matricula, renati.author.dni, …)")
    valor: str | list[str] | None = Field(
        default=None,
        description=(
            "Valor tecleado por el operador; None hasta que lo llene. "
            "`matricula` y `renati.author.dni` aceptan una LISTA alineada "
            "por posición con los autores (una por estudiante): las tesis "
            "con dos autores generan dos constancias y dos filas"
        ),
    )


class FichaDeposito(BaseModel):
    """Ficha de depósito: valores detectados + campos manuales (v1.7.0).

    La SPA la recibe en la respuesta de POST /validar (solo con semáforo
    verde), el operador la corrige y completa, y viaja intacta por el
    buzón hasta el userscript que rellena el formulario oficial.
    """

    extraidos: list[CampoExtraidoFicha] = Field(
        ...,
        description="Valores extraídos del DOCX por el motor (título, autores, asesor, resumen, palabras clave, año, escuela, jurado, ORCID del asesor)",
    )
    manuales: list[CampoManualFicha] = Field(
        ...,
        description="Campos que el operador teclea (matrícula, DNI del autor y DNI del asesor; admite ORCID del asesor en fichas anteriores)",
    )


class FichaPendientePublicada(BaseModel):
    """Respuesta de POST /ficha-pendiente (v1.14.0).

    El trámite identifica esta ficha concreta. La SPA lo conserva y lo
    envía en cada solicitud de papeleo y de conciliación. Publicar una
    ficha nueva crea un trámite nuevo, aunque el título sea el mismo.

    `vence_en` se conserva como alias deprecado de `autofill_hasta` para
    los clientes v1.13.0. La retención del trámite (`retenido_hasta`) es
    independiente y más larga: vencer el autorelleno no borra la ficha.
    """

    tramite_id: str = Field(..., description="Identificador efímero de la ficha publicada")
    revision: int = Field(..., ge=0, description="Revisión de la ficha canónica")
    autofill_hasta: datetime = Field(..., description="Fin de la ventana de autorelleno (UTC)")
    retenido_hasta: datetime = Field(
        ..., description="Fin de la retención del trámite completo (UTC)"
    )
    vence_en: datetime | None = Field(
        default=None,
        description="DEPRECADO: alias de autofill_hasta; se retirará en una próxima versión",
    )


class FichaPendienteLeida(BaseModel):
    """Respuesta de GET /ficha-pendiente (v1.14.0).

    El userscript lee la ficha y su trámite juntos. El `tramite_id` y la
    `revision` deben viajar de vuelta en POST /deposito: evitan confirmar
    un ítem o una revisión que ya cambiaron.
    """

    ficha: FichaDeposito = Field(..., description="Ficha completada por el operador")
    tramite_id: str = Field(..., description="Identificador efímero de esta ficha")
    revision: int = Field(..., ge=0, description="Revisión de la ficha canónica")
    autofill_hasta: datetime = Field(..., description="Fin de la ventana de autorelleno (UTC)")
    retenido_hasta: datetime = Field(..., description="Fin de la retención del trámite (UTC)")
    vence_en: datetime | None = Field(
        default=None,
        description="DEPRECADO: alias de autofill_hasta; se retirará en una próxima versión",
    )


class InconsistenciaAPI(BaseModel):
    """Inconsistencia detectada entre el ítem y la ficha canónica."""

    motivos: list[str] = Field(..., description="Motivos legibles reportados")
    revision: int = Field(..., ge=0, description="Revisión sobre la que se reportó")
    reportada_en: datetime = Field(..., description="Momento del reporte (UTC)")


class DepositoReportado(BaseModel):
    """Cuerpo de POST /deposito (v1.14.0): confirmación explícita.

    Este endpoint ya no acepta un "reporte automático". `atestacion` y
    `revision_esperada` son obligatorios: un payload de la versión anterior
    no confirma nada (422). El servidor genera `confirmado_en`; `timestamp`
    se conserva como el momento del clic en Depositar, que alimenta la HORA
    del registro y de la constancia.

    `autores_observados` es evidencia OPCIONAL: null significa que la
    página no exponía autores. En ese caso el servidor registra
    `autores_verificados=false`, nunca "coinciden".
    """

    tramite_id: str = Field(..., min_length=1, description="Trámite de la ficha en vuelo")
    handle: str = Field(
        ...,
        pattern=PATRON_HANDLE,
        description="URI del ítem archivado (https://hdl.handle.net/20.500.14414/…)",
    )
    titulo_observado: str = Field(
        ..., min_length=1, description="Título leído en la página del ítem archivado"
    )
    autores_observados: list[str] | None = Field(
        default=None,
        description=(
            "Autores leídos de la página del ítem, o null si la página no los "
            "expone. Si vienen y no coinciden con la ficha, la confirmación falla."
        ),
    )
    timestamp: str = Field(
        ..., min_length=1, description="Momento del clic en Depositar (ISO 8601), hora de Perú"
    )
    revision_esperada: int = Field(
        ...,
        ge=0,
        description="Revisión de la ficha que el operador revisó en el panel",
    )
    atestacion: Literal["operador"] = Field(
        ...,
        description=(
            "Atestación explícita del operador. Sin este campo no hay "
            "confirmación: los reportes automáticos de versiones anteriores "
            "reciben 422."
        ),
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "tramite_id": "a1b2c3",
                    "handle": "https://hdl.handle.net/20.500.14414/27871",
                    "titulo_observado": "Taller de dramatización de títeres",
                    "autores_observados": ["Cerna Vidal Kassiel"],
                    "timestamp": "2026-11-16T09:30:00-05:00",
                    "revision_esperada": 0,
                    "atestacion": "operador",
                }
            ]
        },
    )

    @field_validator("autores_observados")
    @classmethod
    def _normalizar_autores(cls, valor: list[str] | None) -> list[str] | None:
        """Una lista vacía equivale a "no disponible"; nunca a "coinciden"."""
        if valor is None:
            return None
        limpios = [a.strip() for a in valor if isinstance(a, str) and a.strip()]
        return limpios or None


class DepositoRecibido(BaseModel):
    """Respuesta de GET /deposito y del bloque `deposito` de GET /tramite.

    Describe una **confirmación del operador**, no un estado verificado
    por el servidor de DSpace. `confirmado_en` es solo auditoría: la HORA
    del papeleo sale de `timestamp` (clic en Depositar).
    """

    tramite_id: str = Field(..., description="Trámite al que pertenece la confirmación")
    handle: str = Field(..., description="URI del ítem confirmado")
    titulo_observado: str = Field(..., description="Título leído en la página del ítem")
    titulo_verificado: bool = Field(
        default=False,
        description=(
            "True si el título canónico existe y coincide con el observado. "
            "False significa que no se pudo comparar, no que difieran."
        ),
    )
    autores_observados: list[str] | None = Field(
        default=None, description="Autores leídos del ítem, o null si no estaban disponibles"
    )
    autores_verificados: bool = Field(
        default=False,
        description=(
            "True solo si la página exponía autores y coincidían con la ficha. "
            "False no significa que no coincidan: significa que no se verificaron."
        ),
    )
    timestamp: str = Field(
        ..., description="Momento del clic en Depositar (fuente de la HORA del papeleo)"
    )
    revision_confirmada: int = Field(
        ..., ge=0, description="Revisión exacta que el operador confirmó"
    )
    confirmado_en: datetime = Field(
        ..., description="Momento en que se aceptó la confirmación (UTC)"
    )
    confirmado_por: Literal["operador"] = Field(
        default="operador", description="Autor de la atestación"
    )
    confirmacion_vigente: bool = Field(
        default=True,
        description="False si una conciliación posterior cambió la revisión",
    )
    titulo: str | None = Field(
        default=None,
        description="DEPRECADO: alias de titulo_observado; se retirará en una próxima versión",
    )


class TramiteLeido(BaseModel):
    """Respuesta de GET /tramite (v1.14.0).

    Es la vista canónica del trámite retenido. La SPA la usa después de
    vencer el autorelleno y antes de cada solicitud de papeleo. El
    userscript la usa para construir el panel de confirmación con la
    revisión vigente, no con un valor guardado.
    """

    ficha: FichaDeposito = Field(..., description="Ficha canónica vigente")
    tramite_id: str = Field(..., description="Identificador del trámite")
    revision: int = Field(..., ge=0, description="Revisión vigente de la ficha")
    inconsistencia: InconsistenciaAPI | None = Field(
        default=None, description="Inconsistencia pendiente de conciliación"
    )
    deposito: DepositoRecibido | None = Field(
        default=None, description="Confirmación de depósito, si existe"
    )
    publicada_en: datetime = Field(..., description="Publicación original (UTC)")
    autofill_hasta: datetime = Field(..., description="Fin de la ventana de autorelleno (UTC)")
    retenido_hasta: datetime = Field(..., description="Fin de la retención del trámite (UTC)")
    autofill_habil: bool = Field(
        ..., description="True si la ficha todavía se puede servir para rellenar"
    )
    confirmacion_vigente: bool = Field(
        ...,
        description=(
            "True si hay depósito confirmado y su revisión es la vigente. "
            "Una conciliación posterior exige reconfirmar."
        ),
    )


class ReconciliarRequest(BaseModel):
    """Cuerpo de POST /ficha-pendiente/reconciliar (v1.14.0).

    Reemplaza la ficha canónica con una corrección revisada por el
    operador. Funciona antes de la confirmación (no fabrica evidencia de
    depósito) y después (conserva el depósito, pero invalida la
    confirmación hasta reconfirmar la revisión nueva).
    """

    tramite_id: str = Field(..., min_length=1, description="Trámite a corregir")
    handle: str = Field(
        ...,
        pattern=PATRON_HANDLE,
        description="Handle del ítem que el operador está mirando",
    )
    ficha: FichaDeposito = Field(..., description="Ficha corregida")
    motivo: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Motivo de la corrección, revisado por el operador",
    )
    revision_esperada: int = Field(
        ..., ge=0, description="Revisión sobre la que se preparó la corrección"
    )

    model_config = ConfigDict(extra="forbid")


class ReconciliacionResponse(BaseModel):
    """Respuesta de POST /ficha-pendiente/reconciliar (v1.14.0)."""

    tramite_id: str = Field(..., description="Trámite corregido")
    revision: int = Field(..., ge=0, description="Revisión nueva")
    handle: str = Field(..., description="Handle revisado")
    confirmacion_vigente: bool = Field(
        ..., description="False si la corrección invalidó una confirmación previa"
    )
    deposito: DepositoRecibido | None = Field(
        default=None, description="Evidencia conservada, si ya existía un depósito"
    )


class InconsistenciaRequest(BaseModel):
    """Cuerpo de POST /ficha-pendiente/inconsistencia (v1.14.0)."""

    tramite_id: str = Field(..., min_length=1, description="Trámite con la divergencia")
    handle: str = Field(
        ...,
        pattern=PATRON_HANDLE,
        description="Handle del ítem donde se observó la divergencia",
    )
    motivos: list[str] = Field(
        ...,
        min_length=1,
        description="Motivos legibles; al menos uno",
    )
    revision_esperada: int = Field(
        ..., ge=0, description="Revisión sobre la que se observó la divergencia"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("motivos")
    @classmethod
    def _motivos_no_vacios(cls, valor: list[str]) -> list[str]:
        limpios = [m.strip() for m in valor if isinstance(m, str) and m.strip()]
        if not limpios:
            raise ValueError("se exige al menos un motivo no vacío")
        return limpios


class FilaRegistroRequest(BaseModel):
    """Solicitud de la fila de registro (v1.7.0; trámite desde v1.13.0).

    La SPA la envía cuando el buzón reporta el depósito. La API compara
    `ficha`, `tramite_id`, `handle` y `timestamp` con el estado canónico
    del servidor. Si algo no coincide, responde 409. El papeleo se genera
    con la ficha publicada y el depósito vigente, no con los valores del
    cliente. El timestamp alimenta DD/MM/AA, HORA, AÑO y la fecha del
    documento, igual que en el registro oficial de la biblioteca.
    """

    ficha: FichaDeposito = Field(
        ...,
        description="La ficha completada por el operador; debe coincidir con la ficha publicada",
    )
    tramite_id: str = Field(
        ..., min_length=1, description="Trámite de la ficha que produjo este depósito"
    )
    handle: str = Field(..., description="URI del ítem depositado (https://hdl.handle.net/…)")
    timestamp: str = Field(
        ...,
        description="Momento del clic en Depositar (ISO 8601), reportado por el userscript",
    )


class ConstanciaRequest(FilaRegistroRequest):
    """Solicitud de UNA constancia (Modelo B) en particular (v1.7.0).

    Una constancia por autor: la SPA descarga una por cada estudiante,
    iterando `indice_autor` sobre la lista de autores de la ficha.
    """

    indice_autor: int = Field(
        default=0,
        ge=0,
        description="Índice (0-based) del autor cuya constancia se descarga",
    )


class FilasRegistroResponse(BaseModel):
    """Filas TSV listas para pegar en el registro oficial (v1.7.0).

    Una fila por autor, en el orden exacto de columnas del registro
    (N°, TESIS/TSP, BACHILLER/LICENCIADO, N° MATRIC., DD, MM, AA, HORA,
    DIRECCION URL, FIRMA, FECHA DEL DOC., ESCUELAS, AÑO). La columna N°
    va vacía: la numeración es del registro de la biblioteca.
    """

    filas: list[str] = Field(
        ..., description="Filas TSV (una por autor) con los valores separados por tabuladores"
    )


class ValidarResponse(BaseModel):
    """Respuesta completa del endpoint POST /validar.

    Agrupa el semáforo, el resumen, los resultados individuales por regla,
    los prompts de IA y los metadatos del procesamiento.
    """

    semaforo: str = Field(
        ..., description='"verde" si todas las reglas error pasan, "rojo" si alguna falla'
    )
    notificacion: NotificacionAPI = Field(
        default_factory=lambda: NotificacionAPI(estado=EstadoNotificacionAPI.SIN_CORREO),
        description=(
            "Estado del envío del correo de observaciones al estudiante. "
            "El envío es opt-in (campo de formulario `notificar`): solo se "
            "intenta cuando el operador lo solicita, hay observaciones "
            'bloqueantes (semáforo "rojo"), se envió un campo `correo` '
            "válido y la notificación está habilitada en el servidor."
        ),
    )
    deposito: DepositoAPI = Field(
        default_factory=lambda: DepositoAPI(estado=EstadoDepositoAPI.SIN_SOLICITUD),
        description=(
            "Estado del depósito del documento en el repositorio "
            "institucional DSpace (actividad 10). Opt-in del operador "
            "(campo `depositar`): solo se intenta con semáforo verde y "
            "configuración completa en el servidor. El ítem queda en la "
            "cola de aprobación de la sede, no se publica directo."
        ),
    )
    ficha_deposito: FichaDeposito | None = Field(
        default=None,
        description=(
            "Ficha de depósito detectada (v1.7.0). SOLO materializa con "
            'semáforo "verde": en cualquier otro caso es null. Contiene los '
            "valores extraídos del DOCX (listos para que el operador los "
            "corrija) y los campos manuales que el operador debe llenar "
            "(matrícula, DNI, ORCID)."
        ),
    )
    resumen: ResumenValidacion = Field(..., description="Resumen cuantitativo")
    resultados: list[ResultadoReglaAPI] = Field(..., description="Resultados por regla")
    como_preguntar_a_una_ia: list[PromptIA] = Field(
        default_factory=list,
        description="Bloques de prompts IA para reglas fallidas",
    )
    metadatos: MetadatosValidacion = Field(..., description="Metadatos del procesamiento")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "semaforo": "verde",
                    "notificacion": {"estado": "sin_correo", "detalle": None},
                    "deposito": {"estado": "sin_solicitud", "detalle": None},
                    "resumen": {
                        "total": 49,
                        "total_evaluadas": 43,
                        "reglas_no_aplicables": 6,
                        "fallidos_error": 0,
                        "fallidos_warning": 2,
                    },
                    "resultados": [
                        {
                            "rule_id": "papel_tamano",
                            "paso": True,
                            "severidad": "error",
                            "mensaje": "El tamaño del papel debe ser A4",
                            "esperado": "210 x 297 mm",
                            "encontrado": "cumple",
                            "aplicable": True,
                            "ubicacion": 'Sección "Formato general" (párr. 124-125)',
                            "fuente": "MANUAL REVISADO TERCERA VERSION OBSERVACIONES 11-07-2025.docx",
                            "cita": '"Tamaño A4/papel (210x297 cm)"',
                        }
                    ],
                    "como_preguntar_a_una_ia": [],
                    "metadatos": {
                        "archivo_nombre": "mi_tesis.docx",
                        "archivo_tamano_bytes": 123456,
                        "reglas_evaluadas": 43,
                        "reglas_totales": 49,
                        "version_esquema": "2026-09-01",
                        "tipo_documento_declarado": None,
                        "tipo_documento_inferido": None,
                        "tipo_documento_estado": "vigente",
                    },
                }
            ]
        }
    }


class ExplicacionItemAPI(BaseModel):
    """Explicación en lenguaje llano de una regla fallida (Funcionalidad 2)."""

    rule_id: str = Field(..., description="ID de la regla a la que se refiere la explicación")
    explicacion: str = Field(..., description="Causa probable y qué significa para la entrega")


class PrioridadItemAPI(BaseModel):
    """Orden recomendado de corrección de un fallo (Funcionalidad 2)."""

    orden: int = Field(..., ge=1, description="Orden de corrección (1 = primero)")
    rule_id: str = Field(..., description="ID de la regla a corregir")
    razon: str = Field(..., description="Por qué se recomienda ese orden")
    esfuerzo: Literal["bajo", "medio", "alto"] = Field(
        ..., description="Esfuerzo estimado de la corrección"
    )


class ExplicacionYPrioridadAPI(BaseModel):
    """Respuesta de POST /asistente/explicar (Funcionalidad 2, advisory).

    La salida de IA es solo texto de apoyo: nunca toca el semáforo ni
    produce un `RuleResult`.
    """

    explicaciones: list[ExplicacionItemAPI] = Field(
        ..., description="Explicación de cada regla fallida que el modelo menciona"
    )
    prioridades: list[PrioridadItemAPI] = Field(..., description="Orden recomendado de corrección")
    modelo: str = Field(default="", description="Modelo de IA que generó la respuesta")


class EstadoAsistenteAPI(BaseModel):
    """Respuesta de GET /asistente/estado.

    Si el módulo de IA no está configurado (`OLLAMA_URL` ausente) o el
    servicio no responde, `disponible` es `false` y la SPA debe mostrar el
    botón deshabilitado.
    """

    disponible: bool = Field(..., description="True si el servicio de IA responde")
    modelo: str = Field(default="", description="Modelo en uso; vacío si no está disponible")
