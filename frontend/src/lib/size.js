// Tamaño aproximado de una descarga. Las calidades traen una tasa en bytes por segundo (real si el sitio
// publica peso o bitrate, o un valor típico si no); aquí se ajusta por formato, fps y duración.
export const DEFAULT_SECONDS = 180 // si el sitio no da duración (directos, algunos sitios)

const VIDEO_FORMAT_FACTOR = { MP4: 1, WEBM: 0.85, MKV: 0.8 } // frente a H.264
const AUDIO_CAP_KBPS = { MP3: Infinity, M4A: 128, OPUS: 112 } // M4A y OPUS conservan el audio original
const MP4_4K_CONVERSION = 1.6 // el 4K no existe en H.264: se convierte y pesa más

export function estimateBytes({ quality, mode, format, fps, seconds }) {
  const secs = seconds > 0 ? seconds : DEFAULT_SECONDS

  if (mode === 'audio') {
    const kbps = Math.min(Number(quality.id), AUDIO_CAP_KBPS[format] ?? Infinity)
    return Math.round(kbps * 125 * secs)
  }

  const rate = fps === 30 && quality.bps_30 ? quality.bps_30 : quality.bps
  let bytes = rate * secs * (VIDEO_FORMAT_FACTOR[format] ?? 1)
  if (format === 'MP4' && quality.id === '2160') bytes *= MP4_4K_CONVERSION
  return Math.round(bytes)
}

// durations: segundos de cada video incluido (uno solo, o los seleccionados de una playlist)
export function estimateTotal({ quality, mode, format, fps, durations }) {
  return durations.reduce((sum, seconds) => sum + estimateBytes({ quality, mode, format, fps, seconds }), 0)
}
