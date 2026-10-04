export function fmtBytes(bytes) {
  if (bytes == null) return '—'
  if (bytes === 0) return '0 MB'
  const mb = bytes / 1e6
  if (mb >= 1000) return (mb / 1000).toFixed(1).replace('.', ',') + ' GB'
  return Math.max(1, Math.round(mb)) + ' MB'
}

export function fmtDuration(seconds) {
  if (!seconds) return ''
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ss = String(s).padStart(2, '0')
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${ss}`
  return `${m}:${ss}`
}

export function fmtSpeed(bytesPerSecond) {
  return (bytesPerSecond / 1e6).toFixed(1).replace('.', ',') + ' MB/s'
}

export function statusLabel(job) {
  switch (job.status) {
    case 'done': return 'Completado'
    case 'paused': return 'En pausa'
    case 'waiting': return 'En espera'
    case 'error': return 'Error'
    case 'expired': return 'Expirado'
    default: return job.speed ? fmtSpeed(job.speed) : 'Iniciando…'
  }
}

export function etaLabel(job) {
  if (job.status === 'done') return 'Listo'
  if (job.status !== 'running' || job.eta == null) return '—'
  const secs = Math.max(1, job.eta)
  return secs >= 60 ? `${Math.floor(secs / 60)} min ${secs % 60} s` : `${secs} s`
}

export function sizeLabel(job) {
  if ((job.status === 'done' || job.status === 'expired') && job.size_bytes) return fmtBytes(job.size_bytes)
  if (job.total_bytes) return `${fmtBytes(job.downloaded_bytes)} de ${fmtBytes(job.total_bytes)}`
  return fmtBytes(job.downloaded_bytes)
}

export function stagesFor(job) {
  const p = job.progress
  const list = job.mode === 'audio'
    ? [['Extrayendo información', 0, 8], ['Descargando audio', 8, 85], ['Convirtiendo', 85, 100]]
    : [['Extrayendo información', 0, 8], ['Descargando video', 8, 70], ['Descargando audio', 70, 90], ['Uniendo con ffmpeg', 90, 100]]
  return list.map(([label, from, to]) => ({
    label,
    state: p >= to || job.status === 'done' ? 'done' : p >= from && job.status !== 'waiting' ? 'active' : 'pending',
  }))
}

export function fileName(job) {
  const safe = job.title.replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 90) || 'clipo'
  return `${safe}.${job.format.toLowerCase()}`
}
