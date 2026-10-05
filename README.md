# Clipo

PWA para descargar videos de cualquier plataforma con yt-dlp. Corre en un solo contenedor de Docker en tu homelab, se instala en el iPhone como app y además expone endpoints para un Atajo de iOS que se lanza desde **Compartir**.

```
iPhone (PWA) ──┐                       ┌─ FastAPI ── /            → PWA (Vue)
               ├─ HTTPS ─ Cloudflare ──┤             /api/*       → analizar, cola, archivos
iPhone (Atajo)─┘          Tunnel       └─ JobManager ─ yt-dlp + ffmpeg + Deno
                                          └─ /data  (SQLite + descargas temporales)
```

- **Backend:** Python 3.12 + FastAPI. yt-dlp se usa como librería, así que se lee el progreso y los errores directamente.
- **Frontend:** Vue 3 + Vite + `vite-plugin-pwa`, con el diseño Nocturne (claro y oscuro).
- **Descargas "de paso":** el archivo se guarda `FILE_TTL_HOURS` horas (6 por defecto) y luego se borra. En la Biblioteca queda el historial.
- **yt-dlp siempre al día:** la imagen usa el canal *nightly* y se reconstruye cada noche.

## Puesta en marcha

Requisitos: Docker con Compose.

```bash
cp .env.example .env
# Rellena API_TOKEN y SECRET_KEY:
#   openssl rand -hex 24    (API_TOKEN)
#   openssl rand -hex 32    (SECRET_KEY)
mkdir -p data
docker compose up -d --build
```

Abre `http://127.0.0.1:8010` (o el valor de `CLIPO_PORT` en tu `.env`) e inicia sesión con tu `API_TOKEN`.

> Clipo solo escucha en `127.0.0.1:CLIPO_PORT` del servidor (por defecto 8010). Si ese puerto ya está ocupado, cambia `CLIPO_PORT` en `.env` y vuelve a ejecutar `docker compose up -d`. Dentro del contenedor el puerto siempre es 8000.

> Para probar por `http://` sin HTTPS pon `SECURE_COOKIES=false` en `.env`. En producción déjalo en `true`.

## Publicarlo en `clipo.jromerog.dev`

iOS solo instala la PWA y registra el service worker sobre **HTTPS**. La opción recomendada es un túnel de Cloudflare: no abre puertos y funciona aunque tu ISP use CGNAT. Requiere que el DNS de `jromerog.dev` esté en Cloudflare.

1. En Cloudflare: *Zero Trust → Networks → Tunnels → Create a tunnel* (tipo *Cloudflared*).
2. Copia el token del túnel a `TUNNEL_TOKEN` en `.env` y deja `COMPOSE_PROFILES=tunnel`.
3. En el túnel, agrega un *Public hostname*: `clipo.jromerog.dev` → servicio `http://clipo:8000`.
4. `docker compose up -d`.

**Si ya tienes un `cloudflared` corriendo en el servidor**, no uses este contenedor (deja `COMPOSE_PROFILES` vacío) y apunta el hostname según cómo corra el tuyo:

- Como servicio del sistema (systemd): `http://localhost:8010` (o tu `CLIPO_PORT`).
- Como contenedor: conéctalo a la red de Docker de Clipo y usa `http://clipo:8000`.

Como queda expuesto a internet, usa un `API_TOKEN` largo y aleatorio. Todas las rutas, salvo `/api/health` y el login, exigen credenciales.

## Instalarla en el iPhone

1. Abre `https://clipo.jromerog.dev` en **Safari**.
2. Compartir → **Agregar a pantalla de inicio**.
3. Para descargar un video al teléfono: en el detalle de una descarga terminada toca **Preparar archivo** y luego **Guardar en iPhone** (iOS exige dos toques) → *Guardar video*.

## Atajo de iOS

Receta paso a paso en [`docs/atajo-ios.md`](docs/atajo-ios.md).

## Actualización diaria de yt-dlp

```bash
./scripts/install-timer.sh     # una sola vez, pide sudo
```

Instala un timer de systemd que ejecuta `scripts/rebuild.sh` todos los días a las 04:30: espera a que no haya descargas activas, reconstruye la imagen con el yt-dlp nightly del momento, reinicia el contenedor y limpia imágenes viejas. Las descargas que el reinicio interrumpa quedan en **pausa** y se reanudan desde la Biblioteca.

Probarlo a mano: `./scripts/rebuild.sh`. Ver el timer: `systemctl list-timers clipo-rebuild.timer`. Ver el log: `journalctl -u clipo-rebuild`.

## API

Autenticación: header `X-API-Key: <API_TOKEN>` (Atajo) o cookie de sesión (PWA, vía `POST /api/auth/login`).

| Método | Ruta | Para qué |
|---|---|---|
| GET | `/api/health` | Healthcheck (sin auth) |
| GET | `/api/system` | Versiones de yt-dlp, ffmpeg y deno |
| POST | `/api/auth/login` · `/logout` · GET `/me` | Sesión de la PWA |
| POST | `/api/analyze` | `{url}` → metadatos, entradas de playlist y calidades reales |
| POST | `/api/jobs` | `{url, mode, quality, fps, format, items?}` → lista de jobs |
| GET | `/api/jobs` | Cola e historial |
| GET | `/api/jobs/{id}` | Un job |
| GET | `/api/jobs/{id}/wait?timeout=50` | Long-poll hasta que termine |
| POST | `/api/jobs/{id}/pause` · `/resume` | Pausar / reanudar (también reintenta los errores) |
| POST | `/api/jobs/pause-all` · `/resume-all` | Todo a la vez |
| DELETE | `/api/jobs/{id}` | Cancelar o borrar del historial |
| DELETE | `/api/jobs?status=done` | Limpiar terminados |
| GET | `/api/jobs/{id}/file` | El archivo (soporta `Range`) |
| POST | `/api/quick` | `{url, mode?}` → preset para iPhone (MP4 H.264 ≤1080p, o MP3) |

## Cookies (opcional)

Para contenido que pide sesión (Instagram, videos con restricción de edad, o cuando YouTube pide confirmar que no eres un bot) guarda tus cookies en formato Netscape en `data/cookies.txt`. Se detectan solas, sin reiniciar.

## Notas de formato

- **MP4** exige H.264 + AAC, que es lo que acepta la app Fotos. Al terminar, Clipo revisa el archivo con `ffprobe` y, si salió en otro códec (VP9, AV1, audio Opus o H.264 de 10 bits), lo convierte con ffmpeg y copia sin recodificar lo que ya sea compatible.
- **4K en MP4**: YouTube no ofrece H.264 en 4K, así que la conversión automática tarda bastante más. Con 1080p o menos no hace falta.
- **WEBM y MKV** no se convierten: son para reproducirse fuera de Fotos.
- Los archivos de más de 300 MB se descargan directo con el gestor de Safari en lugar de cargarse en memoria.

## Desarrollo

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip install -U --pre "yt-dlp[default]"
.venv/bin/python -m pytest
API_TOKEN=dev SECRET_KEY=dev-secret DATA_DIR=/tmp/clipo SECURE_COOKIES=false STATIC_DIR=../frontend/dist \
  .venv/bin/python -m uvicorn app.main:create_app --factory --reload

# Frontend (proxy de /api a :8000)
cd frontend
npm install
npm run dev
npm test
npm run icons      # regenera los íconos PWA desde public/logo.svg
```

`design/` guarda el handoff original de Claude Design (solo referencia, no se despliega).
