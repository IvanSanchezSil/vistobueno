"""Notificación por correo de observaciones de formato (Actividad 6).

Módulo de la capa API que construye y envía al estudiante el correo con el
reporte de observaciones de formato. Deshabilitado por defecto: solo envía
cuando VISTOBUENO_NOTIFICACIONES=1 y la configuración SMTP está completa.

Seguridad de credenciales:
    La configuración se lee EXCLUSIVAMENTE de variables de entorno del
    proceso (os.environ). El módulo nunca carga archivos .env, por lo que no
    existe razón legítima para que uno viva en el repo. La filtración de
    VISTOBUENO_SMTP_PASSWORD está bloqueada por el hook de pre-commit
    (scripts/verificar_secretos.py) y por un paso de escaneo en la CI.

El correo es best-effort: un fallo de envío NUNCA debe romper la respuesta
HTTP de POST /validar (ver wiring en la Actividad 6). El registro es formal
("usted") porque el remitente institucional es el Repositorio FECyC y el
operador de la herramienta es el personal del repositorio, no el estudiante.
"""

import html
import os
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from .api_models import ValidarResponse

# ---------------------------------------------------------------------------
# Configuración (solo variables de entorno)
# ---------------------------------------------------------------------------

# TODO(Actividad 6): reemplazar por el buzón institucional definitivo una vez
# que el área de Repositorio (Salcedo Quiñones) proporcione las credenciales.
REMITENTE_POR_DEFECTO = "no-responder@unitru.edu.pe"

TIMEOUT_SEGUNDOS = 10


class ConfigSMTP:
    """Configuración SMTP leída de variables de entorno.

    Atributos:
        host: Servidor SMTP institucional.
        port: Puerto SMTP (habitual: 587 con STARTTLS).
        user: Usuario SMTP (vacío = sin autenticación, p. ej. sink local).
        password: Contraseña SMTP. NUNCA se commitea al repo.
        starttls: Negociar STARTTLS tras conectar.
        remitente: Buzón institucional que figura como From.
        notificaciones: Flag de habilitación (VISTOBUENO_NOTIFICACIONES=1).
    """

    def __init__(
        self,
        host: str = "",
        port: int = 587,
        user: str = "",
        password: str = "",
        starttls: bool = True,
        remitente: str = REMITENTE_POR_DEFECTO,
        notificaciones: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.starttls = starttls
        self.remitente = remitente
        self.notificaciones = notificaciones

    @classmethod
    def desde_entorno(cls) -> ConfigSMTP:
        """Construye la configuración desde os.environ.

        La conversión de puerto es defensiva: un valor no numérico cae al
        puerto por defecto en lugar de romper el request.
        """
        try:
            port = int(os.environ.get("VISTOBUENO_SMTP_PORT", "587"))
        except ValueError:
            port = 587
        return cls(
            host=os.environ.get("VISTOBUENO_SMTP_HOST", ""),
            port=port,
            user=os.environ.get("VISTOBUENO_SMTP_USER", ""),
            password=os.environ.get("VISTOBUENO_SMTP_PASSWORD", ""),
            starttls=os.environ.get("VISTOBUENO_SMTP_STARTTLS", "true").strip().lower()
            in ("1", "true", "yes"),
            remitente=os.environ.get("VISTOBUENO_CORREO_REMITENTE", REMITENTE_POR_DEFECTO),
            notificaciones=os.environ.get("VISTOBUENO_NOTIFICACIONES", "") == "1",
        )

    @property
    def enabled(self) -> bool:
        """True solo si el envío está habilitado y hay servidor configurado."""
        return self.notificaciones and self.host != ""


# ---------------------------------------------------------------------------
# Plantilla del correo (HTML + texto plano)
# ---------------------------------------------------------------------------


def _esc(texto: str | None) -> str:
    """Escapa contenido dinámico para su inclusion segura en HTML."""
    return html.escape(texto if texto is not None else "")


def plantilla_correo(respuesta: ValidarResponse) -> tuple[str, str]:
    """Construye el cuerpo del correo a partir de la respuesta de la API.

    Registro formal ("Estimado(a) estudiante", "su documento") porque el
    remitente es institucional. Devuelve (html, texto_plano) para un
    multipart/alternative.

    Args:
        respuesta: DTO ValidarResponse con el reporte de validación.

    Returns:
        Tupla (cuerpo_html, cuerpo_texto_plano).
    """
    fallidas = [r for r in respuesta.resultados if not r.paso]
    nombre = respuesta.metadatos.archivo_nombre
    resumen = respuesta.resumen

    # --- Encabezado y resumen ---
    # El texto plano NO se escapa (no hay riesgo de inyección fuera de HTML
    # y las entidades (<...) degradarían la lectura); el HTML sí.
    intro_texto = (
        f"Estimado(a) estudiante: se realizó la verificación de formato de su "
        f"documento «{nombre}» contra las directivas institucionales de la "
        f"UNT. A continuación encontrará el detalle de las observaciones detectadas."
    )
    intro_html = (
        f"Estimado(a) estudiante: se realizó la verificación de formato de su "
        f"documento «{_esc(nombre)}» contra las directivas institucionales de la "
        f"UNT. A continuación encontrará el detalle de las observaciones detectadas."
    )
    resumen_texto = (
        f"Reglas evaluadas: {resumen.total}. "
        f"Observaciones de tipo error: {resumen.fallidos_error}. "
        f"Advertencias (no bloquean): {resumen.fallidos_warning}."
    )

    if fallidas:
        # --- Tabla de observaciones (HTML) ---
        filas_html = []
        for r in fallidas:
            referencia = _esc(r.ubicacion) if r.ubicacion else "—"
            if r.cita:
                referencia += f"<br><em>«{_esc(r.cita)}»</em>"
            filas_html.append(
                "<tr>"
                f"<td><strong>{_esc(r.severidad.value)}</strong></td>"
                f"<td>{_esc(r.mensaje)}<br>"
                f'<small style="color:#888;">[{_esc(r.rule_id)}]</small></td>'
                f"<td>{_esc(r.esperado)}</td>"
                f"<td>{_esc(r.encontrado)}</td>"
                f"<td>{referencia}</td>"
                "</tr>"
            )
        cuerpo_html = f"""\
<html lang="es">
<body>
    <h1>Observaciones de formato</h1>
    <p>{intro_html}</p>
    <p>{_esc(resumen_texto)}</p>
    <table border="1" cellpadding="6" cellspacing="0">
        <thead>
            <tr>
                <th>Severidad</th>
                <th>Observación</th>
                <th>Valor esperado</th>
                <th>Valor encontrado</th>
                <th>Referencia normativa</th>
            </tr>
        </thead>
        <tbody>
            {"".join(filas_html)}
        </tbody>
    </table>
    <p>Para corregir su documento, siga los valores esperados indicados en la
    tabla. Si una observación no le resulta clara, el reporte completo incluye
    prompts de ayuda listos para consultar a una IA.</p>
    <hr>
    <p style="font-size: 0.85em; color: #555;">
        Repositorio institucional — Facultad de Educación y Ciencias de la
        Comunicación, Universidad Nacional de Trujillo.<br>
        Este mensaje fue generado automáticamente por VistoBueno.
    </p>
</body>
</html>"""

        # --- Versión texto plano ---
        lineas_texto = [intro_texto, "", resumen_texto, "", "OBSERVACIONES:"]
        for i, r in enumerate(fallidas, start=1):
            lineas_texto.append(
                f"{i}. [{r.severidad.value}] {r.mensaje}\n"
                f"   Esperado: {r.esperado}\n"
                f"   Encontrado: {r.encontrado}\n"
                f"   Referencia: {r.ubicacion if r.ubicacion else '—'}"
            )
        lineas_texto += [
            "",
            "Repositorio institucional — FECyC, Universidad Nacional de Trujillo.",
            "Mensaje generado automáticamente por VistoBueno.",
        ]
        cuerpo_texto = "\n".join(lineas_texto)
    else:
        # --- Sin observaciones (defensivo: el wiring solo envía en rojo) ---
        cuerpo_html = f"""\
<html lang="es">
<body>
    <h1>Verificación de formato</h1>
    <p>{intro_html}</p>
    <p>{_esc(resumen_texto)}</p>
    <p>No se detectaron observaciones de formato en su documento.</p>
    <hr>
    <p style="font-size: 0.85em; color: #555;">
        Repositorio institucional — Facultad de Educación y Ciencias de la
        Comunicación, Universidad Nacional de Trujillo.<br>
        Este mensaje fue generado automáticamente por VistoBueno.
    </p>
</body>
</html>"""
        cuerpo_texto = "\n".join(
            [
                intro_texto,
                "",
                resumen_texto,
                "",
                "No se detectaron observaciones de formato en su documento.",
                "",
                "Repositorio institucional — FECyC, Universidad Nacional de Trujillo.",
                "Mensaje generado automáticamente por VistoBueno.",
            ]
        )

    return cuerpo_html, cuerpo_texto


# ---------------------------------------------------------------------------
# Envío (best-effort: nunca lanza)
# ---------------------------------------------------------------------------


def enviar_notificacion(
    respuesta: ValidarResponse,
    destino: str,
    config: ConfigSMTP | None = None,
) -> bool:
    """Envía el correo de observaciones al estudiante.

    Devuelve True si el envío fue aceptado por el servidor SMTP; False en
    cualquier otro caso (deshabilitado, conexión rechazada, error SMTP,
    timeout). NUNCA lanza: un fallo de notificación no debe romper la
    respuesta HTTP de POST /validar.

    Args:
        respuesta: DTO con el reporte de validación.
        destino: Correo normalizado del estudiante.
        config: Configuración SMTP explícita (tests/scripts); por defecto se
            lee del entorno.

    Returns:
        True si se envió; False en caso contrario.
    """
    cfg = config if config is not None else ConfigSMTP.desde_entorno()
    if not cfg.enabled:
        return False

    cuerpo_html, cuerpo_texto = plantilla_correo(respuesta)

    msg = EmailMessage()
    msg["Subject"] = (
        f"VistoBueno — Observaciones de formato en «{respuesta.metadatos.archivo_nombre}»"
    )
    msg["From"] = cfg.remitente
    msg["To"] = destino
    # smtplib.send_message() NO agrega Date ni Message-ID; varios servidores
    # reales rechazan correo sin ambos encabezados, así que se generan aquí.
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain="vistobueno.unitru.edu.pe")
    msg.set_content(cuerpo_texto)
    msg.add_alternative(cuerpo_html, subtype="html")

    try:
        with smtplib.SMTP(cfg.host, cfg.port, timeout=TIMEOUT_SEGUNDOS) as smtp:
            if cfg.starttls:
                smtp.starttls()
            if cfg.user:
                smtp.login(cfg.user, cfg.password)
            smtp.send_message(msg)
        return True
    except OSError, smtplib.SMTPException:
        # Conexión rechazada, timeout, fallo de EHLO/STARTTLS/AUTH o del propio
        # envío: notificación best-effort, se registra silenciosamente.
        return False
