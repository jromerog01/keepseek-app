import { describe, expect, it } from 'vitest'
import { detect, isPlaylistUrl } from './platforms.js'
import { estimateBytes, estimateTotal, DEFAULT_SECONDS } from './size.js'
import { dayGroup, etaLabel, fmtSpeed, phaseLabel, speedLabel, expiresIn, fileName, groupByDay, relativeTime, storageUsed, fmtBytes, fmtDuration, sizeLabel, stageRows, stagesFor, stageSummary, statusLabel } from './format.js'
import { computeDeficit } from './viewport.js'
import { glowFor, pick } from './styles.js'
import { readBody } from './download.js'

describe('detect', () => {
  it('reconoce las plataformas del diseño', () => {
    expect(detect('https://youtu.be/abc')).toBe('youtube')
    expect(detect('https://www.instagram.com/reel/x')).toBe('instagram')
    expect(detect('https://fb.watch/x')).toBe('facebook')
    expect(detect('https://www.tiktok.com/@a/video/1')).toBe('tiktok')
    expect(detect('https://x.com/a/status/1')).toBe('x')
    expect(detect('https://twitter.com/a/status/1')).toBe('x')
    expect(detect('https://vimeo.com/1')).toBe('vimeo')
    expect(detect('https://redd.it/x')).toBe('reddit')
    expect(detect('https://soundcloud.com/a/b')).toBe('soundcloud')
  })
  it('usa "other" para sitios desconocidos y null sin url', () => {
    expect(detect('https://www.twitch.tv/videos/1')).toBe('other')
    expect(detect('')).toBeNull()
  })
  it('detecta playlists', () => {
    expect(isPlaylistUrl('https://youtube.com/playlist?list=PL1')).toBe(true)
    expect(isPlaylistUrl('https://soundcloud.com/a/sets/b')).toBe(true)
    expect(isPlaylistUrl('https://youtu.be/abc')).toBe(false)
  })
})

describe('format', () => {
  it('formatea tamaños', () => {
    expect(fmtBytes(null)).toBe('—')
    expect(fmtBytes(0)).toBe('0 MB')
    expect(fmtBytes(412e6)).toBe('412 MB')
    expect(fmtBytes(1.2e9)).toBe('1,2 GB')
    expect(fmtBytes(10)).toBe('1 MB')
  })
  it('formatea duraciones', () => {
    expect(fmtDuration(null)).toBe('')
    expect(fmtDuration(34)).toBe('0:34')
    expect(fmtDuration(1122)).toBe('18:42')
    expect(fmtDuration(8040)).toBe('2:14:00')
  })
  it('etiqueta estados y tiempo restante', () => {
    expect(statusLabel({ status: 'running', speed: 3.2e6 })).toBe('3,2 MB/s')
    expect(statusLabel({ status: 'running', speed: null })).toBe('Iniciando…')
    expect(statusLabel({ status: 'paused' })).toBe('En pausa')
    expect(etaLabel({ status: 'running', eta: 45 })).toBe('45 s')
    expect(etaLabel({ status: 'running', eta: 125 })).toBe('2 min 5 s')
    expect(etaLabel({ status: 'paused', eta: 5 })).toBe('—')
    expect(etaLabel({ status: 'done' })).toBe('Listo')
  })
  it('arma la etiqueta de tamaño', () => {
    expect(sizeLabel({ status: 'running', downloaded_bytes: 100e6, total_bytes: 400e6 })).toBe('100 MB de 400 MB')
    expect(sizeLabel({ status: 'running', downloaded_bytes: 100e6, total_bytes: null })).toBe('100 MB')
    expect(sizeLabel({ status: 'done', size_bytes: 38e6, downloaded_bytes: 38e6, total_bytes: 38e6 })).toBe('38 MB')
    expect(sizeLabel({ status: 'expired', size_bytes: 40e6, downloaded_bytes: 40e6, total_bytes: 40e6 })).toBe('40 MB')
  })
  it('calcula las etapas igual que el prototipo', () => {
    const video = (progress, status = 'running') => stagesFor({ mode: 'video', progress, status }).map((s) => s.state)
    expect(video(0)).toEqual(['active', 'pending', 'pending', 'pending'])
    expect(video(30)).toEqual(['done', 'active', 'pending', 'pending'])
    expect(video(95)).toEqual(['done', 'done', 'done', 'active'])
    expect(video(100, 'done')).toEqual(['done', 'done', 'done', 'done'])
    expect(video(0, 'waiting')).toEqual(['pending', 'pending', 'pending', 'pending'])
    const audio = stagesFor({ mode: 'audio', progress: 50, status: 'running' }).map((s) => s.label)
    expect(audio).toEqual(['Extrayendo información', 'Descargando audio', 'Convirtiendo'])
  })
  it('genera un nombre de archivo seguro', () => {
    expect(fileName({ title: 'Cómo: hacer/pan?', format: 'MP4' })).toBe('Cómo hacer pan.mp4')
    expect(fileName({ title: '???', format: 'MP3' })).toBe('clipo.mp3')
  })
})

describe('readBody', () => {
  const streamOf = (chunks, headers) => new Response(new ReadableStream({
    start(controller) { chunks.forEach((c) => controller.enqueue(c)); controller.close() },
  }), { headers })

  it('arma el archivo y reporta el avance por partes', async () => {
    const response = streamOf([new Uint8Array(40), new Uint8Array(60)], { 'Content-Type': 'video/mp4', 'Content-Length': '100' })
    const seen = []
    const blob = await readBody(response, (p) => seen.push(p))
    expect(blob.size).toBe(100)
    expect(blob.type).toBe('video/mp4')
    expect(seen).toEqual([{ received: 40, total: 100 }, { received: 100, total: 100 }])
  })
  it('usa el tamaño del job si no hay Content-Length', async () => {
    const seen = []
    await readBody(streamOf([new Uint8Array(10)], {}), (p) => seen.push(p), 50)
    expect(seen).toEqual([{ received: 10, total: 50 }])
  })
})

describe('estilos', () => {
  it('alterna on/off', () => {
    expect(pick('mode', true).color).toBe('var(--color-accent)')
    expect(pick('mode', false).shadow).toBe('none')
  })
  it('calcula el glow por plataforma y tema', () => {
    expect(glowFor('youtube', 'dark')).toEqual({ glow: 'oklch(0.31 0.065 25)', glow2: 'oklch(0.31 0.065 25)' })
    expect(glowFor(null, 'dark').glow).toBe('oklch(0.44 0.07 235)')
    expect(glowFor('instagram', 'dark').glow2).toBe('oklch(0.36 0.1 315)')
    expect(glowFor('tiktok', 'light')).toEqual({ glow: 'oklch(0.6 0.03 300)', glow2: 'oklch(0.76 0.13 305)' })
  })
})


describe('etapas con su propio porcentaje', () => {
  const live = {
    status: 'running', mode: 'video', progress: 55,
    stages: [
      { key: 'info', label: 'Extrayendo información', state: 'done', pct: 100 },
      { key: 'video', label: 'Descargando video', state: 'done', pct: 100 },
      { key: 'audio', label: 'Descargando audio', state: 'active', pct: 42.4 },
      { key: 'merge', label: 'Uniendo audio y video', state: 'pending', pct: 0 },
    ],
  }

  it('muestra cada etapa con su estado y su porcentaje', () => {
    expect(stageRows(live).map((r) => [r.label, r.state, r.detail])).toEqual([
      ['Extrayendo información', 'done', '100 %'],
      ['Descargando video', 'done', '100 %'],
      ['Descargando audio', 'active', '42 %'],
      ['Uniendo audio y video', 'pending', '—'],
    ])
  })
  it('una etapa en curso sin porcentaje conocido dice "En curso"', () => {
    const merging = { ...live, stages: [{ key: 'merge', label: 'Uniendo audio y video', state: 'active', pct: null }] }
    expect(stageRows(merging)[0].detail).toBe('En curso')
  })
  it('oculta las etapas que no aplicaron', () => {
    const single = { ...live, stages: [
      { key: 'video', label: 'Descargando video', state: 'done', pct: 100 },
      { key: 'audio', label: 'Descargando audio', state: 'skipped', pct: null },
    ] }
    expect(stageRows(single).map((r) => r.label)).toEqual(['Descargando video'])
  })
  it('muestra la conversión para iPhone cuando existe', () => {
    const converting = { ...live, stages: [...live.stages.slice(0, 3), { key: 'convert_ios', label: 'Convirtiendo para iPhone', state: 'active', pct: 63 }] }
    expect(stageRows(converting).at(-1)).toMatchObject({ label: 'Convirtiendo para iPhone', detail: '63 %' })
  })
  it('sin detalle en vivo calcula cada porcentaje a partir del avance total', () => {
    const rows = stageRows({ status: 'running', mode: 'video', progress: 39 })
    expect(rows.map((r) => r.state)).toEqual(['done', 'active', 'pending', 'pending'])
    expect(rows[1].detail).toBe('50 %')
  })
  it('resume la etapa actual para la cola', () => {
    expect(stageSummary(live)).toBe('Descargando audio · 42 %')
    expect(stageSummary({ ...live, stages: [{ key: 'merge', label: 'Uniendo audio y video', state: 'active', pct: null }] })).toBe('Uniendo audio y video')
    expect(stageSummary({ status: 'done', mode: 'video', progress: 100 })).toBeNull()
  })
})

describe('déficit de altura en la PWA de iOS', () => {
  const base = { standalone: true, innerWidth: 393, innerHeight: 793, screenHeight: 852 }
  it('mide cuánto falta cuando iOS reporta menos alto que la pantalla', () => {
    expect(computeDeficit(base)).toBe(59)
  })
  it('es 0 si el alto coincide, en Safari normal, en horizontal o con diferencias enormes', () => {
    expect(computeDeficit({ ...base, innerHeight: 852 })).toBe(0)
    expect(computeDeficit({ ...base, standalone: false })).toBe(0)
    expect(computeDeficit({ ...base, innerWidth: 852, innerHeight: 393 })).toBe(0)
    expect(computeDeficit({ ...base, innerHeight: 600 })).toBe(0)
  })
})


describe('historial de la biblioteca', () => {
  const NOW = new Date('2026-10-05T15:00:00').getTime()
  const ago = (ms) => new Date(NOW - ms).toISOString()
  const H = 3600e3

  it('escribe cuánto hace que se descargó', () => {
    expect(relativeTime(ago(10e3), NOW)).toBe('Ahora')
    expect(relativeTime(ago(5 * 60e3), NOW)).toBe('Hace 5 min')
    expect(relativeTime(ago(3 * H), NOW)).toBe('Hace 3 h')
    expect(relativeTime(ago(30 * H), NOW)).toBe('Ayer')
    expect(relativeTime(ago(72 * H), NOW)).toBe('Hace 3 días')
    expect(relativeTime(null, NOW)).toBe('')
  })
  it('avisa cuánto le queda al archivo y marca lo urgente', () => {
    const inFuture = (ms) => new Date(NOW + ms).toISOString()
    expect(expiresIn(inFuture(20 * 60e3), NOW)).toEqual({ label: 'Expira en 20 min', urgent: true })
    expect(expiresIn(inFuture(1.5 * H), NOW)).toEqual({ label: 'Expira en 1 h', urgent: true })
    expect(expiresIn(inFuture(5 * H), NOW)).toEqual({ label: 'Expira en 5 h', urgent: false })
    expect(expiresIn(inFuture(-1000), NOW)).toEqual({ label: 'Expira pronto', urgent: true })
    expect(expiresIn(null, NOW)).toBeNull()
  })
  it('clasifica por día natural, no por horas transcurridas', () => {
    expect(dayGroup('2026-10-05T00:30:00', NOW)).toBe('Hoy')
    expect(dayGroup('2026-10-04T23:30:00', NOW)).toBe('Ayer')
    expect(dayGroup('2026-10-01T10:00:00', NOW)).toBe('Esta semana')
    expect(dayGroup('2026-09-20T10:00:00', NOW)).toBe('Antes')
  })
  it('agrupa de más reciente a más antiguo', () => {
    const jobs = [
      { id: 'a', finished_at: '2026-10-04T10:00:00' },
      { id: 'b', finished_at: '2026-10-05T14:00:00' },
      { id: 'c', finished_at: '2026-10-05T09:00:00' },
      { id: 'd', created_at: '2026-09-01T09:00:00' },
    ]
    const groups = groupByDay(jobs, NOW)
    expect(groups.map((g) => [g.label, g.jobs.map((j) => j.id)])).toEqual([
      ['Hoy', ['b', 'c']], ['Ayer', ['a']], ['Antes', ['d']],
    ])
  })
  it('suma solo los archivos que aún están en el servidor', () => {
    expect(storageUsed([
      { status: 'done', size_bytes: 100e6 }, { status: 'done', size_bytes: 50e6 }, { status: 'expired', size_bytes: 999e6 },
    ])).toBe(150e6)
  })
})


describe('velocidad de descarga', () => {
  it('usa KB/s por debajo de 1 MB/s y MB/s por encima', () => {
    expect(fmtSpeed(850e3)).toBe('850 KB/s')
    expect(fmtSpeed(10)).toBe('1 KB/s')
    expect(fmtSpeed(3.2e6)).toBe('3,2 MB/s')
  })
  it('solo hay velocidad mientras se descarga', () => {
    expect(speedLabel({ status: 'running', speed: 5e6 })).toBe('5,0 MB/s')
    expect(speedLabel({ status: 'running', speed: null })).toBe('—')
    expect(speedLabel({ status: 'paused', speed: 5e6 })).toBe('—')
    expect(speedLabel({ status: 'done', speed: null })).toBe('—')
  })
  it('el estado nombra la etapa en curso en vez de "Iniciando…" durante la unión', () => {
    expect(phaseLabel({ status: 'running', stage: 'Uniendo audio y video', speed: null })).toBe('Uniendo audio y video')
    expect(phaseLabel({ status: 'running', stage: null })).toBe('Iniciando…')
    expect(phaseLabel({ status: 'paused' })).toBe('En pausa')
    expect(statusLabel({ status: 'running', stage: 'Convirtiendo para iPhone', speed: null })).toBe('Convirtiendo para iPhone')
  })
})


describe('tamaño aproximado', () => {
  const q1080 = { id: '1080', bps: 500_000, bps_30: 350_000 }
  const q4k = { id: '2160', bps: 2_000_000, bps_30: null }
  const base = { quality: q1080, mode: 'video', format: 'MP4', fps: 60, seconds: 100 }

  it('video: tasa por segundo por duración', () => {
    expect(estimateBytes(base)).toBe(50_000_000)
  })
  it('los fps cambian el peso cuando hay datos de 30 fps', () => {
    expect(estimateBytes({ ...base, fps: 30 })).toBe(35_000_000)
    expect(estimateBytes({ ...base, quality: q4k, fps: 30, seconds: 10 })).toBeGreaterThan(0)
  })
  it('el formato cambia el peso: WEBM y MKV pesan menos que MP4', () => {
    const mp4 = estimateBytes(base)
    expect(estimateBytes({ ...base, format: 'WEBM' })).toBeLessThan(mp4)
    expect(estimateBytes({ ...base, format: 'MKV' })).toBeLessThan(estimateBytes({ ...base, format: 'WEBM' }))
  })
  it('4K en MP4 pesa más porque se convierte a H.264', () => {
    expect(estimateBytes({ ...base, quality: q4k, fps: null })).toBeGreaterThan(estimateBytes({ ...base, quality: q4k, fps: null, format: 'MKV' }) * 1.5)
  })
  it('audio: MP3 usa los kbps elegidos; M4A y OPUS no pasan de su tope', () => {
    const audio = { mode: 'audio', seconds: 100 }
    expect(estimateBytes({ ...audio, quality: { id: '320' }, format: 'MP3' })).toBe(4_000_000)
    expect(estimateBytes({ ...audio, quality: { id: '320' }, format: 'M4A' })).toBe(1_600_000)
    expect(estimateBytes({ ...audio, quality: { id: '320' }, format: 'OPUS' })).toBe(1_400_000)
    expect(estimateBytes({ ...audio, quality: { id: '128' }, format: 'M4A' })).toBe(1_600_000)
  })
  it('sin duración usa una típica en vez de dejar el tamaño vacío', () => {
    expect(estimateBytes({ ...base, seconds: null })).toBe(Math.round(500_000 * DEFAULT_SECONDS))
    expect(estimateBytes({ ...base, seconds: 0 })).toBeGreaterThan(0)
  })
  it('playlist: suma los videos elegidos, con duración típica donde falte', () => {
    const total = estimateTotal({ ...base, durations: [100, 50, null] })
    expect(total).toBe(50_000_000 + 25_000_000 + Math.round(500_000 * DEFAULT_SECONDS))
    expect(estimateTotal({ ...base, durations: [] })).toBe(0)
  })
})
