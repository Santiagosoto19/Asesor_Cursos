# Agente de Asesoría Académica

**Autores:** Santiago Soto y Benis Gómez

## Introducción

Este proyecto es un agente de consola que asesora sobre un catálogo fijo de cursos online. El modelo de lenguaje (Groq) conversa con el usuario, recuerda el hilo y, solo cuando hay interés real de inscripción, un correo válido y un curso identificado, emite un JSON de acción. Python intercepta ese JSON, busca el curso en el catálogo local (no en lo que diga el modelo) y envía la ficha por Gmail. El catálogo vive en `cursos.json` y se descarga en runtime desde una URL pública.

## URL del catálogo

https://raw.githubusercontent.com/Santiagosoto19/Cursos-Proyecto-electiva/main/cursos.json

## Decisión de arquitectura

Se usa **Groq** (SDK oficial `groq`) y no LangChain ni LlamaIndex. Groq ofrece un plan gratuito, latencia baja y un cliente mínimo (`chat.completions.create`) suficiente para un chat con historial. El catálogo se inyecta en el system prompt; el envío de correo es código propio con `smtplib`. Menos capas, más fácil de explicar en la sustentación.

## Contrato JSON de acción

Cuando hay interés real + correo + `curso_id`, el modelo debe responder **únicamente**:

```json
{"accion":"enviar_correo","email":"usuario@correo.com","curso_id":"C01"}
```

Python lo intercepta así:

1. `strip` del texto.
2. Quitar fences `` ```json `` y `` ``` `` si vienen.
3. `json.loads`.
4. Validar que sea un dict con `accion == "enviar_correo"`, `email` y `curso_id`.
5. Lookup **local** con `CatalogoCursos.obtener_por_id(curso_id)` (nunca se confía en precios o nombres inventados por el modelo).
6. Validar que el email contenga `@` y llamar a `EmailService.enviar`.

Si el parseo falla, se muestra la respuesta del asesor como texto normal.

## Cómo correr

```bash
cd parcial-asesor
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env y rellenar las claves
python src/main.py
```

## Claves

- **Groq:** crea cuenta en [https://console.groq.com](https://console.groq.com), genera una API key y pégala en `GROQ_API_KEY`. El modelo por defecto es `openai/gpt-oss-20b`.
- **Gmail:** en la cuenta de Google, activa 2FA y crea una [contraseña de aplicación](https://myaccount.google.com/apppasswords). Úsala en `EMAIL_APP_PASSWORD` (no la contraseña normal). `EMAIL_REMITENTE` es el correo Gmail que envía.
