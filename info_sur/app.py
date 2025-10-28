"""Main Flask application for Info Sur."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

from flask import Flask, Response, jsonify, redirect, render_template, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest, NotFound

from .database import Base, engine
from .services import (
    ARTICLE_FIELDS,
    create_article_record,
    delete_article,
    generate_article_via_openai,
    get_article,
    get_article_by_slug,
    get_template_html,
    list_articles,
    render_article_html,
    save_template_html,
    update_article,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    Base.metadata.create_all(engine)

    app = Flask(
        __name__,
        static_folder=str(Path(__file__).parent / "static"),
        template_folder=str(Path(__file__).parent / "templates"),
    )

    # Configure rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )

    logger.info("Info Sur application initialized")

    @app.route("/")
    def index() -> Response:
        return redirect("/editor")

    @app.route("/editor")
    def editor() -> str:
        return render_template("editor.html", article_fields=ARTICLE_FIELDS)

    @app.route("/images/<path:filename>")
    def images(filename: str):
        # Validate file extension for security
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise NotFound("Invalid file type")

        images_dir = Path("data/images")
        if not images_dir.exists():
            raise NotFound()

        # Prevent directory traversal
        file_path = (images_dir / filename).resolve()
        if not str(file_path).startswith(str(images_dir.resolve())):
            raise NotFound("Invalid path")

        return send_from_directory(images_dir, filename)

    # API endpoints
    @app.route("/api/articles", methods=["GET"])
    def api_list_articles():
        return jsonify(list_articles())

    @app.route("/api/articles", methods=["POST"])
    @limiter.limit("10 per hour")  # Limit article generation to prevent API abuse
    def api_create_article():
        data = request.get_json(force=True)
        prompt = data.get("prompt")
        satire_level = int(data.get("satire_level", 50))
        image_prompts = [p for p in data.get("image_prompts", []) if p]
        if not prompt:
            raise BadRequest("El prompt es obligatorio")

        logger.info(f"Creating article with prompt: {prompt[:50]}...")

        try:
            generation = generate_article_via_openai(prompt, satire_level, image_prompts)
        except RuntimeError as exc:
            logger.error(f"Failed to generate article: {exc}")
            raise BadRequest(str(exc)) from exc
        modules = generation["modules"]

        # Ensure autores stored as string
        autores = modules.get("mod_autores")
        if isinstance(autores, list):
            modules["mod_autores"] = " y ".join(autores)

        article = create_article_record(
            prompt=prompt,
            satire_level=satire_level,
            modules=modules,
            temas=generation.get("temas", []),
            image_prompts=image_prompts,
            image_urls=generation.get("image_urls", {}),
            image_metadata=generation.get("image_metadata", {}),
        )

        logger.info(f"Article created successfully: {article.slug}")

        return jsonify({
            "id": article.id,
            "slug": article.slug,
            "timestamp": article.timestamp,
        }), 201

    @app.route("/api/articles/<int:article_id>", methods=["GET"])
    def api_get_article(article_id: int):
        article = get_article(article_id)
        if not article:
            raise NotFound()
        payload: Dict[str, Any] = {
            "id": article.id,
            "slug": article.slug,
            "timestamp": article.timestamp,
            "prompt": article.prompt,
            "satire_level": article.satire_level,
            "article_data": article.article_data,
            "image_data": article.image_data,
        }
        return jsonify(payload)

    @app.route("/api/articles/<int:article_id>", methods=["PUT"])
    def api_update_article(article_id: int):
        data = request.get_json(force=True)
        article = update_article(article_id, data)
        if not article:
            raise NotFound()
        return jsonify({"status": "updated"})

    @app.route("/api/articles/<int:article_id>", methods=["DELETE"])
    def api_delete_article(article_id: int):
        deleted = delete_article(article_id)
        if not deleted:
            raise NotFound()
        return jsonify({"status": "deleted"})

    @app.route("/api/template", methods=["GET"])
    def api_get_template():
        return jsonify({"template": get_template_html()})

    @app.route("/api/template", methods=["PUT"])
    def api_update_template():
        data = request.get_json(force=True)
        html = data.get("template")
        if html is None:
            raise BadRequest("Falta el template")
        save_template_html(html)
        return jsonify({"status": "saved"})

    @app.route("/<path:slug_timestamp>")
    def serve_article(slug_timestamp: str):
        if slug_timestamp.startswith("api/") or slug_timestamp == "editor":
            raise NotFound()
        if not slug_timestamp:
            raise NotFound()
        if not slug_timestamp[-14:].isdigit():
            raise NotFound()
        article = get_article_by_slug(slug_timestamp)
        if not article:
            raise NotFound()
        html = render_article_html(article)
        return Response(html, mimetype="text/html")

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
