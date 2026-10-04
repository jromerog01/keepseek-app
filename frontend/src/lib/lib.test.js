import { describe, expect, it } from 'vitest'
import { detect, isPlaylistUrl } from './platforms.js'
import { etaLabel, fileName, fmtBytes, fmtDuration, sizeLabel, stagesFor, statusLabel } from './format.js'
import { glowFor, pick } from './styles.js'

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
