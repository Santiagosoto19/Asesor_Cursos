import json

import requests
from groq import Groq


class CatalogoCursos:
    def __init__(self, url):
        self.url = url
        self.cursos = []

    def cargar(self) -> list[dict]:
        respuesta = requests.get(self.url, timeout=15)
        respuesta.raise_for_status()
        datos = respuesta.json()
        if isinstance(datos, dict) and "cursos" in datos:
            self.cursos = datos["cursos"]
        elif isinstance(datos, list):
            self.cursos = datos
        else:
            raise ValueError("El catálogo debe ser una lista o un objeto con clave 'cursos'.")
        return self.cursos

    def obtener_por_id(self, curso_id) -> dict | None:
        for curso in self.cursos:
            if curso.get("id") == curso_id:
                return curso
        return None

    def texto_para_prompt(self) -> str:
        return json.dumps(self.cursos, ensure_ascii=False, indent=2)


class AgenteAsesor:
    def __init__(self, api_key, modelo, catalogo):
        self.cliente = Groq(api_key=api_key)
        self.modelo = modelo
        self.catalogo = catalogo
        self.historial = [
            {"role": "system", "content": self._prompt_sistema()},
        ]

    def _prompt_sistema(self) -> str:
        catalogo_texto = self.catalogo.texto_para_prompt()
        return (
            "Eres un asesor académico de cursos online.\n"
            "SOLO puedes hablar de los cursos del catálogo inyectado más abajo. "
            "No inventes precios, nombres, duraciones ni requisitos. "
            "Si te preguntan por algo fuera del catálogo, indícalo con claridad y ofrece alternativas del listado.\n"
            "Si el usuario muestra interés REAL en inscribirse (quiere inscribirse, matricularse o recibir la ficha), "
            "pide su correo electrónico.\n"
            "SOLO cuando tengas las tres condiciones a la vez: interés real en inscribirse, "
            "un correo del usuario y un curso identificado del catálogo, responde ÚNICAMENTE "
            "con este JSON (sin markdown, sin texto extra, sin explicaciones):\n"
            '{"accion":"enviar_correo","email":"usuario@correo.com","curso_id":"C01"}\n'
            "Usa el email real del usuario y el id real del curso (C01, C02, etc.).\n"
            "Si falta el correo o el curso, pregunta lo que falte. Nunca envíes JSON a medias "
            "ni un JSON sin ambos campos.\n"
            "En cualquier otro caso responde en español, de forma clara y breve.\n\n"
            "Catálogo de cursos:\n"
            f"{catalogo_texto}"
        )

    def verificar_conexion(self) -> None:
        self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
        )

    def responder(self, texto_usuario) -> str:
        self.historial.append({"role": "user", "content": texto_usuario})
        respuesta = self.cliente.chat.completions.create(
            model=self.modelo,
            messages=self.historial,
        )
        contenido = respuesta.choices[0].message.content or ""
        self.historial.append({"role": "assistant", "content": contenido})
        return contenido
