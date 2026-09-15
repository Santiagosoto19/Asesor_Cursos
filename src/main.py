import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from agente import AgenteAsesor, CatalogoCursos
from email_service import EmailService

console = Console()


def extraer_accion_correo(texto) -> dict | None:
    if not texto:
        return None
    limpio = texto.strip()
    if limpio.startswith("```"):
        limpio = limpio.removeprefix("```json").removeprefix("```")
        limpio = limpio.removesuffix("```")
        limpio = limpio.strip()
    try:
        datos = json.loads(limpio)
    except json.JSONDecodeError:
        inicio = limpio.find("{")
        fin = limpio.rfind("}")
        if inicio == -1 or fin == -1 or fin <= inicio:
            return None
        try:
            datos = json.loads(limpio[inicio : fin + 1])
        except json.JSONDecodeError:
            return None
    if (
        isinstance(datos, dict)
        and datos.get("accion") == "enviar_correo"
        and datos.get("email")
        and datos.get("curso_id")
    ):
        return datos
    return None


def formatear_costo(costo) -> str:
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


def tabla_catalogo(catalogo: CatalogoCursos) -> Table:
    tabla = Table(show_header=True, header_style="bold")
    tabla.add_column("ID")
    tabla.add_column("Curso")
    tabla.add_column("Modalidad")
    tabla.add_column("Duración")
    tabla.add_column("Inversión", justify="right")
    for curso in catalogo.cursos:
        tabla.add_row(
            str(curso.get("id", "?")),
            str(curso.get("nombre", "")),
            str(curso.get("modalidad", "")),
            str(curso.get("duracion", "")),
            formatear_costo(curso.get("costo")),
        )
    return tabla


def imprimir_banner(catalogo: CatalogoCursos) -> None:
    intro = (
        "Ya cargué el catálogo remoto. Puedes preguntarme, por ejemplo:\n"
        "  • ¿Qué cursos hay y cuánto cuestan?\n"
        "  • Cuéntame del curso de Python (C01)\n"
        "  • Requisitos de Git o de redes\n"
        "  • ¿Cuál me conviene si soy principiante?\n"
        "  • Quiero inscribirme en C05  → te pediré el correo y te envío la ficha"
    )
    contenido = Group(
        intro,
        "",
        tabla_catalogo(catalogo),
        "",
        Text("Escribe 'salir' o 'exit' para terminar.", style="dim"),
    )
    console.print(
        Panel(
            contenido,
            title="Asesor académico — oferta de cursos",
            border_style="blue",
        )
    )


def main():
    ruta_env = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(ruta_env)

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    url_catalogo = os.getenv("CURSOS_JSON_URL", "").strip()
    modelo = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
    remitente = os.getenv("EMAIL_REMITENTE", "").strip()
    password = os.getenv("EMAIL_APP_PASSWORD", "").strip()

    if not api_key or not url_catalogo:
        console.print("[red]✗[/red] Error: faltan GROQ_API_KEY o CURSOS_JSON_URL en el archivo .env")
        sys.exit(1)
    if not remitente or not password:
        console.print(
            "[yellow]⚠[/yellow] Aviso: faltan EMAIL_REMITENTE o EMAIL_APP_PASSWORD. "
            "El chat arranca, pero el envío de correo fallará hasta configurar Gmail."
        )

    catalogo = CatalogoCursos(url_catalogo)
    try:
        catalogo.cargar()
    except Exception as exc:
        console.print(f"[red]✗[/red] Error al cargar el catálogo de cursos: {exc}")
        sys.exit(1)

    agente = AgenteAsesor(api_key, modelo, catalogo)
    correo = EmailService(remitente, password)

    try:
        agente.verificar_conexion()
        console.print(f"[green]✓[/green] Conexión con Groq OK ({modelo}).")
    except Exception as exc:
        mensaje = str(exc)
        if api_key:
            mensaje = mensaje.replace(api_key, "***")
        console.print(f"[red]✗[/red] Error al conectar con Groq: {mensaje}")
        sys.exit(1)

    console.print(f"[green]✓[/green] Catálogo OK: {len(catalogo.cursos)} cursos desde GitHub.")
    imprimir_banner(catalogo)
    try:
        while True:
            try:
                entrada = Prompt.ask("Tú", console=console)
            except EOFError:
                console.print("\n[dim]Hasta luego.[/dim]")
                break
            entrada = entrada.strip()
            if not entrada:
                continue
            if entrada.casefold() in {"salir", "exit"}:
                console.print("[dim]Hasta luego. Éxitos con tu formación.[/dim]")
                break
            try:
                with console.status("Consultando al asesor...", spinner="dots"):
                    respuesta = agente.responder(entrada)
            except Exception as exc:
                console.print(f"[red]✗[/red] Error al consultar el modelo: {exc}")
                continue

            accion = extraer_accion_correo(respuesta)
            if accion:
                email = str(accion.get("email", "")).strip()
                curso_id = str(accion.get("curso_id", "")).strip()
                if "@" not in email:
                    console.print(
                        "[red]✗[/red] Error: el correo no es válido. El asesor necesita un email con @."
                    )
                    agente.historial.append({
                        "role": "user",
                        "content": "El correo NO se envió (email inválido, falta @). No asumas que se envió. Si el usuario insiste, vuelve a emitir el JSON de acción.",
                    })
                    continue
                curso = catalogo.obtener_por_id(curso_id)
                if curso is None:
                    console.print(
                        f"[red]✗[/red] Error: el curso {curso_id} no existe en el catálogo local."
                    )
                    agente.historial.append({
                        "role": "user",
                        "content": f"El correo NO se envió (el curso {curso_id} no existe en el catálogo). No asumas que se envió. Si el usuario insiste, vuelve a emitir el JSON de acción.",
                    })
                    continue
                try:
                    correo.enviar(email, curso)
                    console.print(
                        f"[green]✓[/green] Listo. Enviamos la ficha de '{curso.get('nombre')}' a {email}."
                    )
                    console.print(
                        Panel(
                            (
                                f"[bold]{curso.get('nombre')}[/bold]\n"
                                f"ID: {curso.get('id')}\n"
                                f"Modalidad: {curso.get('modalidad')}\n"
                                f"Duración: {curso.get('duracion')}\n"
                                f"Inversión: {formatear_costo(curso.get('costo'))}\n"
                                f"Destino: {email}"
                            ),
                            title="Ficha enviada",
                            border_style="green",
                        )
                    )
                    agente.historial.append({
                        "role": "user",
                        "content": f"El sistema confirma: ficha enviada a {email}.",
                    })
                except Exception as exc:
                    console.print(f"[red]✗[/red] Error al enviar el correo: {exc}")
                    agente.historial.append({
                        "role": "user",
                        "content": f"El correo NO se envió (error SMTP: {exc}). No asumas que se envió. Si el usuario insiste, vuelve a emitir el JSON de acción.",
                    })
                continue

            console.print(Panel(Markdown(respuesta), title="Asesor", border_style="cyan"))
    except KeyboardInterrupt:
        console.print("\n[dim]Interrumpido. Hasta luego.[/dim]")


if __name__ == "__main__":
    main()
