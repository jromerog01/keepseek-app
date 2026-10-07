# Atajo de iOS: "Guardar con Clipo"

Este atajo aparece en el menú **Compartir** de cualquier app (YouTube, TikTok, Instagram, X, Safari…). Le manda el enlace a tu servidor, espera a que termine la descarga y guarda el video en **Fotos**.

> iOS no permite que una PWA aparezca en el menú Compartir. Por eso esta parte es un Atajo y no la PWA.

## Antes de empezar

Necesitas dos datos:

- La URL de tu servidor, por ejemplo `https://clipo.jromerog.dev`.
- Tu `API_TOKEN` (el mismo del archivo `.env`).

## Cómo funciona

```
Compartir enlace ─► POST /api/quick ─► {id}
                    GET /api/jobs/{id}/wait?timeout=50   (se repite hasta 10 veces)
                    status = done ─► GET /api/jobs/{id}/file ─► Guardar en Fotos
```

Se usa `wait` con 50 segundos y no una sola petición larga porque Cloudflare corta cualquier respuesta que tarde más de 100 s en empezar. Con 10 repeticiones el atajo espera hasta unos 8 minutos.

## Armar el atajo (app Atajos)

Crea un atajo nuevo con estas acciones, en este orden. Donde diga **(encabezado)**, agrega el header `X-API-Key` con tu token en la sección *Encabezados* de la acción.

1. **Recibir** *URLs* y *Texto* de **la hoja para compartir**. Si no hay entrada: *Continuar* (o *Pedir*).
2. **Obtener URLs de** *Entrada del atajo*.
   - (Opcional) **Obtener detalles del dispositivo** → *Nombre del dispositivo*, para que la Biblioteca muestre qué dispositivo hizo la descarga.
3. **Obtener contenido de URL**
   - URL: `https://clipo.jromerog.dev/api/quick`
   - Método: **POST**
   - Encabezados: `X-API-Key` = tu token **(encabezado)** y, si hiciste el paso opcional, `X-Device-Name` = *Nombre del dispositivo*
   - Cuerpo de la solicitud: **JSON**, con un campo **Texto** llamado `url` cuyo valor es la variable *URLs*.
4. **Obtener valor del diccionario**: clave `id` de *Contenido de URL*. Guárdalo con **Asignar variable** → `JobID`.
5. **Repetir 10 veces**
   1. **Obtener contenido de URL**
      - URL: `https://clipo.jromerog.dev/api/jobs/` + variable `JobID` + `/wait?timeout=50`
      - Método: **GET** + **(encabezado)**
   2. **Obtener valor del diccionario**: clave `status`. **Asignar variable** → `Estado`.
   3. **Si** `Estado` **es** `done`
      1. **Obtener contenido de URL**
         - URL: `https://clipo.jromerog.dev/api/jobs/` + `JobID` + `/file`
         - Método: **GET** + **(encabezado)**
      2. **Guardar en el álbum de fotos** (álbum *Recientes*).
      3. **Mostrar notificación**: "Guardado en Fotos".
      4. **Detener este atajo**.
   4. **Si** `Estado` **es** `error`
      1. **Obtener valor del diccionario**: clave `error` del último *Contenido de URL* de `wait`.
      2. **Mostrar alerta** con ese texto.
      3. **Detener este atajo**.
6. (Fuera del bucle) **Mostrar notificación**: "Sigue descargando, ábrelo en Clipo".

En **Detalles del atajo** (el botón *i*) activa **Mostrar en la hoja para compartir** y deja como tipos *URLs* y *Texto*.

### Menú de calidad (opcional)

Para elegir la calidad al compartir, con las opciones reales de ese video (un TikTok no ofrece 4K):

1. Después de **Obtener URLs**, agrega **Obtener contenido de URL**: POST a `https://clipo.jromerog.dev/api/quick/options`, mismo encabezado, cuerpo JSON `url` = *URLs*.
2. **Obtener valor del diccionario**: clave `options`.
3. **Elegir de la lista** con ese valor.
4. En el cuerpo JSON del paso 3 (`/api/quick`) agrega un campo **Texto** `quality` con la variable *Elemento elegido*.

`/api/quick/options` devuelve textos como `1080p · Full HD · ~38 MB` y al final `MP3 · solo audio`. `/api/quick` acepta ese texto tal cual en `quality`: usa el número del principio, o baja solo audio si empieza con `MP3`. Con la opción MP3, cambia *Guardar en el álbum de fotos* por *Guardar archivo*.

### Variante de solo audio (MP3)

Duplica el atajo y haz dos cambios:

- En el cuerpo JSON del paso 3 agrega un campo **Texto** `mode` con valor `audio`.
- En el paso 5.3.2 cambia **Guardar en el álbum de fotos** por **Guardar archivo** (Fotos no guarda MP3).

## Qué hace `/api/quick`

Descarga con un preset pensado para el iPhone: **MP4, hasta 1080p, video H.264 y audio AAC**. Es el formato que Fotos acepta. Con `mode: "audio"` entrega MP3 a 320 kbps.

Las descargas del atajo también aparecen en la **Biblioteca** de la PWA con la etiqueta "Atajo". El archivo se borra del servidor pasadas `FILE_TTL_HOURS` horas (6 por defecto).

## Probarlo desde la terminal

```bash
TOKEN=tu_token
URL=https://clipo.jromerog.dev

ID=$(curl -s -H "X-API-Key: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"url":"https://youtu.be/jNQXAC9IVRw"}' $URL/api/quick | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

curl -s -H "X-API-Key: $TOKEN" "$URL/api/jobs/$ID/wait?timeout=50"
curl -s -H "X-API-Key: $TOKEN" -o video.mp4 "$URL/api/jobs/$ID/file"
```

## Problemas comunes

| Síntoma | Causa probable |
|---|---|
| El atajo dice "No autorizado" | El header `X-API-Key` falta o el token no coincide con `API_TOKEN`. |
| `status` se queda en `running` tras 10 vueltas | Video muy pesado o largo. Revisa el avance en la Biblioteca de la PWA. |
| `status` = `error` con "Sign in to confirm you're not a bot" | YouTube pide sesión. Pon un `cookies.txt` en `data/` (ver README). |
| Fotos no guarda el video | Se descargó en un formato que no es H.264. Con `/api/quick` no debería pasar; si usas la PWA, elige MP4 a 1080p o menos. |
