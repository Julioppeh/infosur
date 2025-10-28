"""Service layer for Info Sur."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from openai import OpenAI

from .database import get_session
from .models import Article, TemplateRevision

ARTICLE_FIELDS: List[str] = [
    "mod_titulo",
    "mod_subtitulo",
    "mod_autores",
    "mod_ciudad",
    "mod_fecha",
    "mod_pie1",
    "mod_cuerpo1",
    "mod_cuerpo2",
    "mod_relacionada",
    "mod_pie2",
    "mod_cuerpo3",
    "mod_cuerpo4",
    "mod_catchline",
    "mod_cuerpo5",
    "mod_cuerpo6",
    "mod_cuerpo7",
]

TAG_PREFIX = "mod_tema"


def slugify(value: str) -> str:
    """Create a slug suitable for URLs."""
    value = value.lower()
    value = re.sub(r"[^a-z0-9áéíóúñü\s-]", "", value)
    value = value.replace(" ", "-")
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def current_timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")


def ensure_template(session) -> TemplateRevision:
    template = TemplateRevision.latest(session)
    if not template:
        default_path = os.path.join(os.path.dirname(__file__), "..", "template.html")
        with open(os.path.abspath(default_path), "r", encoding="utf-8") as f:
            html = f.read()
        template = TemplateRevision(template_html=html)
        session.add(template)
        session.flush()
    return template


def get_template_html() -> str:
    with get_session() as session:
        template = ensure_template(session)
        return template.template_html


def save_template_html(html: str) -> TemplateRevision:
    with get_session() as session:
        template = TemplateRevision(template_html=html)
        session.add(template)
        session.flush()
        return template


def generate_article_via_openai(prompt: str, satire_level: int, image_prompts: List[str]) -> Dict[str, Any]:
    """Use the OpenAI API to generate article content and optional images."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    client = OpenAI(api_key=api_key)
    satire_descriptor = (
        "totalmente sobrio y profesional" if satire_level <= 10
        else "equilibrio entre rigor y sátira" if satire_level <= 60
        else "altamente absurdo, pero manteniendo estructura periodística"
    )

    system_prompt = (
        "Eres un periodista malagueño del Diario Sur que redacta noticias satíricas "
        "con estructura periodística y formato específico. Responde únicamente en JSON válido."
    )

    user_prompt = f"""
Genera un artículo periodístico ficticio sobre Málaga siguiendo estas instrucciones:
- Tono: {satire_descriptor}.
- Longitud: entre 5 y 7 párrafos principales.
- Incluye título, subtítulo, autores (lista), ciudad, fecha en formato "Día de la semana, día de mes año, hora:minutos | Actualizado hora:minutosh.".
- Añade catchline, noticia relacionada opcional, y hasta 6 temas.
- Cada párrafo debe tener máximo 3 frases.
- Asegúrate de que la ciudad siempre sea Málaga.
- El prompt original del usuario es: {prompt}
Devuelve un JSON con la siguiente estructura:
{{
  "slug_title": "string",
  "modules": {{
    "mod_titulo": "",
    "mod_subtitulo": "",
    "mod_autores": ["autor1", "autor2"],
    "mod_ciudad": "",
    "mod_fecha": "",
    "mod_pie1": "",
    "mod_cuerpo1": "",
    "mod_cuerpo2": "",
    "mod_relacionada": "",
    "mod_pie2": "",
    "mod_cuerpo3": "",
    "mod_cuerpo4": "",
    "mod_catchline": "",
    "mod_cuerpo5": "",
    "mod_cuerpo6": "",
    "mod_cuerpo7": ""
  }},
  "temas": [""],
  "imagenes": {{
    "primary": "Descripción de la primera imagen",
    "secondary": "Descripción de la segunda imagen opcional"
  }}
}}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1",
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=1200,
            system=system_prompt,
            input=user_prompt,
            response_format={"type": "json_object"},
        )
        content = response.output[0].content[0].text
        data = json.loads(content)
    except Exception as exc:
        raise RuntimeError("No se pudo generar el artículo con OpenAI") from exc

    modules = data.get("modules", {})
    modules.setdefault("mod_ciudad", "Málaga")
    modules.setdefault("mod_autores", [])

    if isinstance(modules.get("mod_autores"), list):
        modules["mod_autores"] = " y ".join(modules["mod_autores"])

    image_captions = data.get("imagenes", {})
    temas = data.get("temas", [])

    image_urls: Dict[str, Optional[str]] = {"primary": None, "secondary": None}
    generated_images: Dict[str, Any] = {}

    if image_prompts:
        for idx, prompt_text in enumerate(image_prompts[:2]):
            if not prompt_text:
                continue
            image_prompt = f"Ilustración satírica estilo fotoperiodismo andaluz. Contexto del artículo: {prompt}. Detalle: {prompt_text}."
            try:
                image_response = client.images.generate(
                    model="gpt-image-1",
                    prompt=image_prompt,
                    size="1024x1024",
                )
                image_data = image_response.data[0]
                image_urls["primary" if idx == 0 else "secondary"] = image_data.url
                generated_images["prompt" if idx == 0 else "prompt_secondary"] = image_prompt
            except Exception:
                continue

    return {
        "slug_title": data.get("slug_title") or modules.get("mod_titulo", ""),
        "modules": modules,
        "temas": temas,
        "image_captions": image_captions,
        "image_urls": image_urls,
        "image_metadata": generated_images,
    }


def create_article_record(
    prompt: str,
    satire_level: int,
    modules: Dict[str, Any],
    temas: List[str],
    image_prompts: List[str],
    image_urls: Dict[str, Optional[str]],
    image_metadata: Dict[str, Any],
) -> Article:
    title = modules.get("mod_titulo", "")
    slug_base = slugify(title or modules.get("mod_subtitulo", "noticia"))
    timestamp = current_timestamp()
    slug = f"{slug_base}-{timestamp}"

    article_payload = {field: modules.get(field, "") for field in ARTICLE_FIELDS}
    article_payload["temas"] = temas
    article_payload["image_prompts"] = image_prompts

    image_payload = {
        "primary": image_urls.get("primary"),
        "secondary": image_urls.get("secondary"),
        "captions": image_metadata,
        "caption_primary": modules.get("mod_pie1"),
        "caption_secondary": modules.get("mod_pie2"),
    }

    with get_session() as session:
        article = Article(
            slug=slug,
            timestamp=timestamp,
            prompt=prompt,
            satire_level=satire_level,
            image_prompt_primary=image_prompts[0] if image_prompts else None,
            image_prompt_secondary=image_prompts[1] if len(image_prompts) > 1 else None,
            article_data=article_payload,
            image_data=image_payload,
        )
        session.add(article)
        session.flush()
        session.refresh(article)
        return article


def list_articles() -> List[Dict[str, Any]]:
    with get_session() as session:
        articles = session.query(Article).order_by(Article.created_at.desc()).all()
        return [
            {
                "id": article.id,
                "slug": article.slug,
                "timestamp": article.timestamp,
                "title": article.article_data.get("mod_titulo"),
                "created_at": article.created_at.isoformat(),
            }
            for article in articles
        ]


def get_article(article_id: int) -> Optional[Article]:
    with get_session() as session:
        article = session.get(Article, article_id)
        if article:
            session.expunge(article)
        return article


def get_article_by_slug(slug: str) -> Optional[Article]:
    with get_session() as session:
        article = session.query(Article).filter(Article.slug == slug).one_or_none()
        if article:
            session.expunge(article)
        return article


def update_article(article_id: int, payload: Dict[str, Any]) -> Optional[Article]:
    with get_session() as session:
        article = session.get(Article, article_id)
        if not article:
            return None
        article.article_data.update(payload.get("article_data", {}))
        if "temas" in payload:
            article.article_data["temas"] = payload["temas"]
        if "image_prompts" in payload:
            article.article_data["image_prompts"] = payload["image_prompts"]
        if "image_data" in payload:
            article.image_data.update(payload["image_data"])
        article.updated_at = datetime.utcnow()
        session.add(article)
        session.flush()
        session.refresh(article)
        return article


def delete_article(article_id: int) -> bool:
    with get_session() as session:
        article = session.get(Article, article_id)
        if not article:
            return False
        session.delete(article)
        return True


def render_article_html(article: Article) -> str:
    template_html = get_template_html()
    soup = BeautifulSoup(template_html, "lxml")

    modules = article.article_data.copy()
    temas: List[str] = modules.get("temas", [])

    for field in ARTICLE_FIELDS:
        value = modules.get(field, "")
        text_value = "" if value is None else str(value)
        for tag in soup.select(f".{field}"):
            if tag.name == "img":
                if field == "mod_pie1" and article.image_data.get("primary"):
                    tag["src"] = article.image_data["primary"]
                    tag["alt"] = text_value or tag.get("alt", "")
                elif field == "mod_pie2" and article.image_data.get("secondary"):
                    tag["src"] = article.image_data["secondary"]
                    tag["alt"] = text_value or tag.get("alt", "")
                continue
            tag.clear()
            if text_value:
                tag.append(text_value)

    # Handle autores ensuring separators
    for tag in soup.select(".mod_autores"):
        autores = modules.get("mod_autores")
        if isinstance(autores, list):
            autores = " y ".join(autores)
        if autores:
            tag.clear()
            tag.append(autores)

    # Replace temas
    tema_tags = soup.select(f"[class*={TAG_PREFIX}]")
    for idx, tema in enumerate(temas, start=1):
        selector = f".{TAG_PREFIX}{idx}"
        for tag in soup.select(selector):
            tag.clear()
            tag.append(tema)
    # Remove extra temas
    for idx in range(len(temas) + 1, 10):
        selector = f".{TAG_PREFIX}{idx}"
        for tag in soup.select(selector):
            tag.decompose()

    return soup.prettify(formatter="html")
