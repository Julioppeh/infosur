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

## Despliegue en Ubuntu con systemd y Caddy

Si prefieres no crear un usuario dedicado, puedes ejecutar el servicio con tu usuario habitual (p. ej. `ubuntu`). Asegúrate de que dicho usuario tenga permisos de lectura/escritura sobre `/opt/infosur` y la base de datos.

1. **Preparar entorno**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3.11 python3.11-venv python3-pip git caddy

   sudo mkdir -p /opt/infosur
   sudo chown $USER:$USER /opt/infosur
   cd /opt/infosur

   # Para clonar el repositorio público:
   git clone https://github.com/Julioppeh/infosur.git app

   # Para clonar el repositorio privado (necesitas credenciales):
   # git clone https://<tu-token>@github.com/Julioppeh/infosur.git app

   cd app
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   deactivate
   ```

2. **Configurar variables de entorno**
   ```bash
   sudo tee /etc/infosur.env >/dev/null <<'EOF'
   FLASK_APP=info_sur.app:create_app
   OPENAI_API_KEY=tu_api_key
   EOF
   ```

3. **Inicializar estructura de datos**
   ```bash
   cd /opt/infosur/app
   mkdir -p data/images
   source .venv/bin/activate
   python -c "from info_sur.app import create_app; create_app()"
   deactivate
   ```

4. **Servicio systemd**
   Crea el servicio apuntando al usuario actual (sustituye `ubuntu` por el que corresponda):
   ```bash
   sudo tee /etc/systemd/system/infosur.service >/dev/null <<'EOF'
   [Unit]
   Description=Info Sur Flask Service
   After=network.target

   [Service]
   User=ubuntu
   Group=ubuntu
   WorkingDirectory=/opt/infosur/app
   EnvironmentFile=/etc/infosur.env
   ExecStart=/opt/infosur/app/.venv/bin/gunicorn -w 3 -b 127.0.0.1:8000 "info_sur.app:create_app()"
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   EOF
   sudo systemctl daemon-reload
   sudo systemctl enable --now infosur
   sudo systemctl status infosur
   ```

   El servicio queda ligado al usuario indicado sin necesidad de crear otro.

5. **Reverse proxy con Caddy**
   Caddy se encarga del TLS automático y del proxy hacia Gunicorn.
   ```bash
   sudo tee /etc/caddy/Caddyfile >/dev/null <<'EOF'
   info-sur.com {
       encode gzip

       handle_path /static/* {
           root * /opt/infosur/app/info_sur/static
           file_server
       }

       handle_path /images/* {
           root * /opt/infosur/app/data/images
           file_server
       }

       reverse_proxy 127.0.0.1:8000
   }
   EOF
   sudo systemctl reload caddy
   ```

Con esta configuración, el editor estará disponible en `https://info-sur.com/editor` y las URLs públicas seguirán el patrón `<slug>-<timestamp>`.

Las URLs públicas de los artículos siguen el formato `/<slug>-<timestamp>` y renderizan el HTML AMP de `template.html` con los módulos `mod_*` reemplazados.

## Notas

- El generador usa el modelo `gpt-4o` de OpenAI y las imágenes opcionales con `dall-e-3`.
- Puedes actualizar la plantilla base desde la pestaña «Editar template». Cada versión queda registrada en la base de datos.
- El endpoint `/images/<filename>` sirve archivos propios que subas a `data/images/` (solo permite extensiones seguras: jpg, png, gif, webp, svg).
- La aplicación incluye rate limiting para prevenir abuso de la API (10 artículos por hora por IP).
- Logging configurado para facilitar debugging en producción.

## Seguridad

La aplicación implementa las siguientes medidas de seguridad:
- Rate limiting en endpoints de generación de artículos
- Validación de tipos de archivo en el endpoint de imágenes
- Protección contra directory traversal
- Logging de operaciones críticas
