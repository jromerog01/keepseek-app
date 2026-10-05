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

const clamp = (value) => Math.max(0, Math.min(100, value))

// Etapas de respaldo para jobs sin detalle en vivo (por ejemplo, tras reiniciar el servidor)
export function stagesFor(job) {
  const p = job.progress
  const list = job.mode === 'audio'
    ? [['Extrayendo información', 0, 8], ['Descargando audio', 8, 85], ['Convirtiendo', 85, 100]]
    : [['Extrayendo información', 0, 8], ['Descargando video', 8, 70], ['Descargando audio', 70, 90], ['Uniendo audio y video', 90, 100]]
  return list.map(([label, from, to]) => {
    const state = p >= to || job.status === 'done' ? 'done' : p >= from && job.status !== 'waiting' ? 'active' : 'pending'
    return { label, state, pct: state === 'done' ? 100 : state === 'active' ? clamp(((p - from) / (to - from)) * 100) : 0 }
  })
}

export function stageDetail(stage) {
  if (stage.state === 'done') return '100 %'
  if (stage.state === 'pending') return '—'
  return stage.pct == null ? 'En curso' : `${Math.round(stage.pct)} %`
}

// Lo que se muestra en la pantalla de descarga: cada etapa con su estado y su porcentaje
export function stageRows(job) {
  const source = job.stages?.length ? job.stages : stagesFor(job)
  return source
    .filter((s) => s.state !== 'skipped')
    .map((s) => ({ label: s.label, state: s.state, pct: s.pct, detail: stageDetail(s) }))
}

// "Descargando video · 45 %" para la tarjeta de la cola
export function stageSummary(job) {
  const active = stageRows(job).find((s) => s.state === 'active')
  if (!active) return null
  return active.pct == null ? active.label : `${active.label} · ${Math.round(active.pct)} %`
}

export function fileName(job) {
  const safe = job.title.replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 90) || 'clipo'
  return `${safe}.${job.format.toLowerCase()}`
}
