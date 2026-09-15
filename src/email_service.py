import html
import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _formatear_costo(costo) -> str:
    """180000 → '$ 180.000 COP'. Si no es número, se muestra tal cual."""
    if costo is None:
        return ""
    if isinstance(costo, bool):
        return str(costo)
    if isinstance(costo, int):
        return f"$ {costo:,}".replace(",", ".") + " COP"
    if isinstance(costo, float):
        if costo.is_integer():
            return f"$ {int(costo):,}".replace(",", ".") + " COP"
        return str(costo)
    texto = str(costo).strip()
    if texto.isdigit() or (texto.startswith("-") and texto[1:].isdigit()):
        return f"$ {int(texto):,}".replace(",", ".") + " COP"
    return str(costo)


def _fila_dato(etiqueta: str, valor_html: str) -> str:
    return (
        "<tr>"
        f'<td style="padding:10px 16px;font-family:Arial,Helvetica,sans-serif;'
        "font-size:13px;color:#5c6b7a;width:140px;vertical-align:top;"
        f'border-bottom:1px solid #e8edf2;">{etiqueta}</td>'
        f'<td style="padding:10px 16px;font-family:Arial,Helvetica,sans-serif;'
        "font-size:15px;color:#1a2332;vertical-align:top;"
        f'border-bottom:1px solid #e8edf2;">{valor_html}</td>'
        "</tr>"
    )


class EmailService:
    def __init__(self, remitente, password):
        self.remitente = remitente.strip()
        self.password = password.replace(" ", "").strip()

    def enviar(self, destinatario, curso: dict) -> None:
        nombre = curso.get("nombre") or "curso"
        codigo = curso.get("id") or ""
        descripcion = curso.get("descripcion") or ""
        modalidad = curso.get("modalidad") or ""
        duracion = curso.get("duracion") or ""
        requisitos = curso.get("requisitos") or ""
        inversion = _formatear_costo(curso.get("costo", ""))

        asunto = f"Tu ficha de inscripción — {nombre}"

        cuerpo_plano = (
            "Hola,\n\n"
            "Confirmamos tu interés y te adjuntamos la ficha del curso que elegiste, "
            "para que la tengas a mano cuando quieras inscribirte.\n\n"
            f"{nombre}\n\n"
            f"Código: {codigo}\n"
            f"Modalidad: {modalidad}\n"
            f"Duración: {duracion}\n"
            f"Inversión: {inversion}\n\n"
            "Requisitos\n"
            f"{requisitos}\n\n"
            "Descripción\n"
            f"{descripcion}\n\n"
            "Este mensaje lo envió el agente de asesoría académica. "
            "Si no pediste esta ficha, puedes ignorarlo.\n"
        )

        dest_html = html.escape(str(destinatario))
        nombre_html = html.escape(str(nombre))
        codigo_html = html.escape(str(codigo))
        modalidad_html = html.escape(str(modalidad))
        duracion_html = html.escape(str(duracion))
        inversion_html = html.escape(str(inversion))
        requisitos_html = html.escape(str(requisitos)).replace("\n", "<br>")
        descripcion_html = html.escape(str(descripcion)).replace("\n", "<br>")

        cuerpo_html = f"""\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(asunto)}</title>
</head>
<body style="margin:0;padding:0;background-color:#eef2f6;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#eef2f6;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
               style="width:600px;max-width:600px;background-color:#ffffff;">
          <tr>
            <td style="background-color:#14324f;padding:28px 32px;">
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:13px;
                        color:#9ec4e6;letter-spacing:0.4px;">Asesor académico</p>
              <h1 style="margin:8px 0 0 0;font-family:Arial,Helvetica,sans-serif;
                         font-size:24px;line-height:1.3;color:#ffffff;font-weight:bold;">
                Ficha de inscripción
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 32px 8px 32px;font-family:Arial,Helvetica,sans-serif;
                       font-size:16px;line-height:1.55;color:#1a2332;">
              <p style="margin:0 0 12px 0;font-size:18px;font-weight:bold;">Hola,</p>
              <p style="margin:0 0 20px 0;">
                Confirmamos tu interés y te adjuntamos la ficha del curso que elegiste,
                para que la revises con calma y sepas qué esperar al inscribirte.
              </p>
              <p style="margin:0 0 20px 0;font-size:22px;line-height:1.35;font-weight:bold;
                        color:#14324f;">
                {nombre_html}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 8px 32px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="width:100%;background-color:#f7fafc;border:1px solid #e8edf2;">
                {_fila_dato("Código", codigo_html)}
                {_fila_dato("Modalidad", modalidad_html)}
                {_fila_dato("Duración", duracion_html)}
                {_fila_dato("Inversión", inversion_html)}
                {_fila_dato("Requisitos", requisitos_html)}
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px 28px 32px;font-family:Arial,Helvetica,sans-serif;
                       font-size:15px;line-height:1.6;color:#1a2332;">
              <p style="margin:0 0 8px 0;font-size:13px;color:#5c6b7a;font-weight:bold;">
                Descripción
              </p>
              <p style="margin:0;">{descripcion_html}</p>
            </td>
          </tr>
          <tr>
            <td style="background-color:#f4f7fa;padding:18px 32px;font-family:Arial,Helvetica,sans-serif;
                       font-size:12px;line-height:1.5;color:#6b7785;border-top:1px solid #e8edf2;">
              Este mensaje lo envió el agente de asesoría académica a {dest_html}.
              Si no pediste esta ficha, puedes ignorarlo.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = asunto
        mensaje["From"] = self.remitente
        mensaje["To"] = destinatario
        mensaje.attach(MIMEText(cuerpo_plano, "plain", "utf-8"))
        mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        contexto = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(self.remitente, self.password)
            servidor.send_message(mensaje)
