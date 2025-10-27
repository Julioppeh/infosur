# Info Sur · Generador de artículos HTML estilo Diario Sur

Aplicación Flask para generar y gestionar artículos satíricos ambientados en Málaga usando la plantilla `template.html`.

## Requisitos

- Python 3.11+
- Clave válida en la variable de entorno `OPENAI_API_KEY`

Instala dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

Inicia el servidor de desarrollo:

```bash
export FLASK_APP=info_sur.app:create_app
flask run --host=0.0.0.0 --port=8000
```

Accede a `http://localhost:8000/editor` para usar el editor con pestañas **Crear**, **Gestionar** y **Editar template**. El contenido se guarda en una base de datos SQLite (`data/articles.db`).

Las URLs públicas de los artículos siguen el formato `/<slug>-<timestamp>` y renderizan el HTML AMP de `template.html` con los módulos `mod_*` reemplazados.

## Notas

- El generador usa el modelo `gpt-4.1` y las imágenes opcionales con `gpt-image-1`.
- Puedes actualizar la plantilla base desde la pestaña «Editar template». Cada versión queda registrada en la base de datos.
- El endpoint `/images/<filename>` sirve archivos propios que subas a `data/images/`.
