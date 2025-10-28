# Info Sur · Generador de artículos HTML estilo Diario Sur

Aplicación Flask para crear y servir artículos satíricos que siguen la plantilla `template.html` y se publican bajo URLs con slug y timestamp.

## 1. Requisitos previos

1. Servidor Ubuntu 22.04 o superior con acceso sudo.
2. Dominio apuntando al servidor (por ejemplo `info-sur.com`).
3. Python 3.11 instalado desde los repositorios oficiales.
4. Cuenta de OpenAI con clave API válida.

### 1.1 Paquetes del sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git caddy
```

## 2. Obtener el código fuente

1. Elige un directorio de trabajo (recomendado `/opt/infosur`).
2. Clona el repositorio dentro de ese directorio.

```bash
sudo mkdir -p /opt/infosur
sudo chown $USER:$USER /opt/infosur
cd /opt/infosur
git clone https://github.com/Julioppeh/infosur.git app
cd app
```

> Si prefieres usar SSH, reemplaza la URL HTTPS por `git@github.com:Julioppeh/infosur.git`.

### 2.1 Clonado cuando el repositorio es privado

Si el proyecto es privado necesitarás autenticarte antes de clonar:

- **Con token personal (PAT):** crea un token con permiso `repo` desde [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens). Después usa:
  ```bash
  git clone https://<TOKEN>@github.com/Julioppeh/infosur.git app
  ```
  El token sustituye a tu contraseña. Borra el token de la consola (por ejemplo, ejecutando `history -d <n>` o cerrando la sesión) tras usarlo.

- **Con GitHub CLI (`gh`):**
  ```bash
  sudo apt install -y gh
  gh auth login --hostname github.com --with-token < ~/.github_token
  gh repo clone Julioppeh/infosur app
  ```
  Guarda previamente el token en `~/.github_token` con permisos correctos (`chmod 600 ~/.github_token`).

- **Con clave SSH:** añade tu clave pública a GitHub y usa `git clone git@github.com:Julioppeh/infosur.git app`.

Si no tienes acceso al repositorio pide al propietario que te invite o que genere un paquete `.zip` y súbelo manualmente al servidor (`scp archivo.zip usuario@servidor:/opt/infosur/`). Luego descomprímelo y renómbralo a `app`:
```bash
cd /opt/infosur
unzip archivo.zip -d infosur_tmp
mv infosur_tmp app
```

## 3. Crear el entorno virtual

Mantén las dependencias aisladas creando un entorno virtual dentro del directorio clonado:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

## 4. Configurar variables de entorno externas

Guarda las variables sensibles fuera del repositorio, por ejemplo en `/etc/infosur.env`:

```bash
sudo tee /etc/infosur.env >/dev/null <<'EOF_ENV'
FLASK_APP=info_sur.app:create_app
OPENAI_API_KEY=tu_api_key
EOF_ENV
```

> Reemplaza `tu_api_key` por la clave real de OpenAI.

Para cargar estas variables cuando trabajes manualmente:
```bash
set -a
source /etc/infosur.env
set +a
```

## 5. Inicializar recursos de la aplicación

Crea los directorios de datos y la base de datos SQLite ejecutando la factoría de Flask una vez:

```bash
cd /opt/infosur/app
mkdir -p data/images
source .venv/bin/activate
python -c "from info_sur.app import create_app; create_app()"
deactivate
```

## 6. Ejecutar en modo desarrollo (opcional)

Para probar la aplicación antes del despliegue:

```bash
cd /opt/infosur/app
source .venv/bin/activate
set -a; source /etc/infosur.env; set +a
flask run --host=0.0.0.0 --port=8000
deactivate
```

Visita `http://<ip-del-servidor>:8000/editor` para acceder al editor con pestañas **Crear**, **Gestionar** y **Editar template**.

## 7. Servicio systemd

Automatiza el arranque con Gunicorn y systemd usando el usuario actual (`$USER`).

```bash
sudo tee /etc/systemd/system/infosur.service >/dev/null <<'EOF_SERVICE'
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
EOF_SERVICE
```

> Sustituye `ubuntu` por el usuario y grupo con los que quieras ejecutar el servicio.

Después activa el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now infosur
sudo systemctl status infosur
```

Comprueba los logs con:
```bash
journalctl -u infosur -f
```

## 8. Proxy inverso y TLS con Caddy

Edita el archivo `/etc/caddy/Caddyfile` para que Caddy gestione TLS y sirva los estáticos.

```bash
sudo tee /etc/caddy/Caddyfile >/dev/null <<'EOF_CADDY'
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
EOF_CADDY
sudo systemctl reload caddy
```

Caddy se encargará de emitir certificados TLS automáticamente mediante Let’s Encrypt.

## 9. Flujo de trabajo diario

- Actualizar el código: `cd /opt/infosur/app && git pull`.
- Reinstalar dependencias si cambió `requirements.txt`: `source .venv/bin/activate && pip install -r requirements.txt`.
- Reiniciar el servicio tras cambios: `sudo systemctl restart infosur`.
- Copias de seguridad: respalda `data/articles.db` y `data/images/`.

## 10. Estructura funcional

- Editor en `/editor` con pestañas Crear, Gestionar y Editar template.
- Recursos estáticos en `/static/` y `/images/`.
- Artículos públicos servidos en `/<slug>-<timestamp>` usando los módulos `mod_*` de `template.html`.

## 11. TODO para futuros despliegues

- Añadir monitoreo de disponibilidad (Prometheus, UptimeRobot, etc.).
- Configurar copias de seguridad automatizadas de la base de datos.
- Implementar pruebas automatizadas antes de cada despliegue.
- Documentar proceso de rotación de claves API y permisos de colaboradores.

## 12. Recursos adicionales

- [Documentación de Flask](https://flask.palletsprojects.com/)
- [Guía oficial de Caddy](https://caddyserver.com/docs/)
- [Referencias de AMP](https://amp.dev/documentation/)

---

Con estos pasos podrás desplegar Info Sur en un servidor Ubuntu desde cero, mantener las variables sensibles fuera del repositorio y operar el servicio con Caddy y systemd.
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
   git clone https://<tu-repo>.git app
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

- El generador usa el modelo `gpt-4.1` y las imágenes opcionales con `gpt-image-1`.
- Puedes actualizar la plantilla base desde la pestaña «Editar template». Cada versión queda registrada en la base de datos.
- El endpoint `/images/<filename>` sirve archivos propios que subas a `data/images/`.
