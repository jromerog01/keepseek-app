import { describe, expect, it } from 'vitest'
import { detect, isPlaylistUrl } from './platforms.js'
import { etaLabel, fileName, fmtBytes, fmtDuration, sizeLabel, stageRows, stagesFor, stageSummary, statusLabel } from './format.js'
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
