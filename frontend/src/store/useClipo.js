import { computed, reactive } from 'vue'
import { api, ApiError, onUnauthorized } from '../api/client.js'
import { DEFAULT_PLACEHOLDER, detect, isPlaylistUrl, platformById } from '../lib/platforms.js'
import { fmtBytes, fmtDuration } from '../lib/format.js'
import { glowFor } from '../lib/styles.js'

const THEME_KEY = 'clipo-theme'
const THEME_COLORS = { dark: '#1b1a19', light: '#eceef7' }
const ACTIVE = ['waiting', 'running', 'paused', 'error']
const IN_PROGRESS = ['waiting', 'running', 'paused']

export const VIDEO_FORMATS = ['MP4', 'WEBM', 'MKV']
export const AUDIO_FORMATS = ['MP3', 'M4A', 'OPUS']

function readTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* almacenamiento no disponible */ }
  return 'dark'
}

const state = reactive({
  booting: true,
  authed: false,
  loginBusy: false,
  loginError: null,
  theme: readTheme(),
  tab: 'home',
  view: 'home',
  url: '',
  platform: null,
  analyzing: false,
  analysis: null,
  mode: 'video',
  quality: '1080',
  fps: null,
  format: 'MP4',
  plSel: [],
  detailId: null,
  toast: null,
  jobs: [],
  system: null,
})

let toastTimer = null
let pollTimer = null
const canceledIds = new Set()

// ---------- tema ----------

function applyTheme() {
  document.documentElement.dataset.theme = state.theme
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', THEME_COLORS[state.theme])
}

function setTheme(theme) {
  state.theme = theme
  try { localStorage.setItem(THEME_KEY, theme) } catch { /* sin almacenamiento */ }
  applyTheme()
}

const toggleTheme = () => setTheme(state.theme === 'dark' ? 'light' : 'dark')

// ---------- avisos ----------

function flash(message) {
  clearTimeout(toastTimer)
  state.toast = message
  toastTimer = setTimeout(() => { state.toast = null }, 2200)
}

// ---------- datos derivados ----------

const detail = computed(() => state.jobs.find((j) => j.id === state.detailId) || null)
const screen = computed(() => (state.tab === 'home' ? state.view : detail.value ? 'progress' : 'queue'))
const activeJobs = computed(() => state.jobs.filter((j) => ACTIVE.includes(j.status)))
const doneJobs = computed(() => state.jobs.filter((j) => j.status === 'done' || j.status === 'expired'))
const badgeCount = computed(() => state.jobs.filter((j) => IN_PROGRESS.includes(j.status)).length)
const anyRunning = computed(() => state.jobs.some((j) => j.status === 'waiting' || j.status === 'running'))
const glow = computed(() => glowFor(state.platform, state.theme))

const detectedName = computed(() => {
  const platform = platformById(state.platform)
  if (!state.url || !platform) return ''
  const name = platform.id === 'other' ? 'Sitio compatible con yt-dlp' : platform.name
  return name + (isPlaylistUrl(state.url) ? ' · Playlist' : '')
})
const placeholder = computed(() => platformById(state.platform)?.ph || DEFAULT_PLACEHOLDER)

const qualities = computed(() => {
  const a = state.analysis
  if (!a) return []
  return state.mode === 'video' ? a.video_qualities : a.audio_qualities
})
const selectedQuality = computed(() => qualities.value.find((q) => q.id === state.quality) || qualities.value[0] || null)
const formats = computed(() => (state.mode === 'video' ? VIDEO_FORMATS : AUDIO_FORMATS))
const selectedCount = computed(() => state.plSel.filter(Boolean).length)
const itemCount = computed(() => (state.analysis?.is_playlist ? selectedCount.value : 1))

const fpsOptions = computed(() => {
  const available = state.mode === 'video' ? selectedQuality.value?.fps || [] : []
  return available.length > 1 ? available : []
})
const effectiveFps = computed(() => {
  if (!fpsOptions.value.length) return null
  return fpsOptions.value.includes(state.fps) ? state.fps : fpsOptions.value[0]
})

const estimatedBytes = computed(() => {
  const size = selectedQuality.value?.size_bytes
  return size == null ? null : size * itemCount.value
})

const specLabel = computed(() => {
  const q = selectedQuality.value
  if (!q) return ''
  if (state.mode === 'audio') return `${q.id} kbps · ${state.format}`
  return `${q.id}p${effectiveFps.value ? ' ' + effectiveFps.value + ' fps' : ''} · ${state.format}`
})
const summary = computed(() => specLabel.value + (estimatedBytes.value != null ? ' · ' + fmtBytes(estimatedBytes.value) : ''))

const optionsMeta = computed(() => {
  const a = state.analysis
  if (!a) return null
  const author = [a.uploader, a.is_playlist ? 'Playlist' : null].filter(Boolean).join(' · ')
  return {
    title: a.title,
    author,
    platformName: a.platform.name,
    thumbnail: a.thumbnail,
    duration: a.is_playlist ? `${a.entries.length} videos` : fmtDuration(a.duration),
  }
})

// ---------- sesión ----------

onUnauthorized(() => {
  state.authed = false
  stopPolling()
})

async function boot() {
  applyTheme()
  try {
    await api.me()
    state.authed = true
    await afterLogin()
  } catch {
    state.authed = false
  } finally {
    state.booting = false
  }
  consumeSharedUrl()
}

async function afterLogin() {
  await refreshJobs()
  startPolling()
  api.system().then((info) => { state.system = info }).catch(() => {})
}

async function login(token) {
  state.loginBusy = true
  state.loginError = null
  try {
    await api.login(token)
    state.authed = true
    await afterLogin()
    consumeSharedUrl()
  } catch (error) {
    state.loginError = error instanceof ApiError ? error.message : 'No se pudo iniciar sesión'
  } finally {
    state.loginBusy = false
  }
}

async function logout() {
  await api.logout().catch(() => {})
  state.authed = false
  state.jobs = []
  stopPolling()
}

// ---------- polling de jobs ----------

async function refreshJobs() {
  try {
    const list = await api.listJobs()
    for (const id of canceledIds) {
      if (!list.some((j) => j.id === id)) canceledIds.delete(id)
    }
    state.jobs = list.filter((j) => !canceledIds.has(j.id))
  } catch { /* fallo transitorio, se reintenta */ }
}

function scheduleNextPoll() {
  clearTimeout(pollTimer)
  if (!state.authed) return
  const delay = anyRunning.value ? 1000 : 8000
  pollTimer = setTimeout(async () => {
    if (!document.hidden) await refreshJobs()
    scheduleNextPoll()
  }, delay)
}

function startPolling() {
  scheduleNextPoll()
}

function stopPolling() {
  clearTimeout(pollTimer)
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden && state.authed) {
    refreshJobs()
    scheduleNextPoll()
  }
})

// ---------- pantalla de inicio ----------

function setUrl(url) {
  state.url = url
  state.platform = detect(url)
}

async function paste() {
  try {
    const text = (await navigator.clipboard.readText()).trim()
    if (!text) return flash('El portapapeles está vacío')
    setUrl(text)
  } catch {
    flash('No se pudo leer el portapapeles. Pega el enlace a mano.')
  }
}

function selectPlatform(id) {
  state.platform = id
  state.url = state.url && detect(state.url) === id ? state.url : ''
}

function defaultQuality(list) {
  return (list.find((q) => q.note) || list[0])?.id ?? null
}

async function analyze() {
  if (!state.url || state.analyzing) return
  state.analyzing = true
  try {
    const result = await api.analyze(state.url)
    state.analysis = result
    state.platform = result.platform.id
    state.plSel = result.entries.map(() => true)
    state.mode = result.audio_only ? 'audio' : 'video'
    state.quality = defaultQuality(result.audio_only ? result.audio_qualities : result.video_qualities)
    state.format = result.audio_only ? 'MP3' : 'MP4'
    state.fps = null
    state.view = 'options'
  } catch (error) {
    flash(error instanceof ApiError ? error.message : 'No se pudo analizar el enlace')
  } finally {
    state.analyzing = false
  }
}

// ---------- opciones de descarga ----------

const back = () => { state.view = 'home' }

function setMode(mode) {
  if (mode === 'video' && state.analysis?.audio_only) return
  state.mode = mode
  const list = mode === 'video' ? state.analysis.video_qualities : state.analysis.audio_qualities
  state.quality = defaultQuality(list)
  state.format = mode === 'video' ? 'MP4' : 'MP3'
  state.fps = null
}

const setQuality = (id) => { state.quality = id }
const setFormat = (format) => { state.format = format }
const setFps = (fps) => { state.fps = fps }
const togglePlaylistItem = (index) => { state.plSel[index] = !state.plSel[index] }

function togglePlaylistAll() {
  const select = selectedCount.value !== state.plSel.length
  state.plSel = state.plSel.map(() => select)
}

async function download() {
  const a = state.analysis
  const q = selectedQuality.value
  if (!a || !q || itemCount.value === 0) return

  const common = { mode: state.mode, quality: q.id, fps: effectiveFps.value, format: state.format }
  const payload = a.is_playlist
    ? {
        url: state.url,
        ...common,
        items: a.entries
          .filter((_, i) => state.plSel[i])
          .map((e) => ({ url: e.url, title: e.title, duration: e.duration })),
      }
    : {
        url: state.url,
        ...common,
        title: a.title,
        uploader: a.uploader,
        thumbnail: a.thumbnail,
        duration: a.duration,
        size_estimate: q.size_bytes,
      }

  try {
    const created = await api.createJobs(payload)
    state.jobs = [...created, ...state.jobs.filter((j) => !created.some((c) => c.id === j.id))]
    state.tab = 'queue'
    state.detailId = a.is_playlist ? null : created[0].id
    state.view = 'home'
    state.url = ''
    state.platform = null
    state.analysis = null
    flash(a.is_playlist ? `${created.length} videos añadidos a la cola` : 'Descarga iniciada')
    scheduleNextPoll()
  } catch (error) {
    flash(error instanceof ApiError ? error.message : 'No se pudo iniciar la descarga')
  }
}

// ---------- cola y biblioteca ----------

function setTab(id) {
  state.tab = id
  state.detailId = null
  if (id === 'queue') refreshJobs()
}

const openDetail = (id) => { state.tab = 'queue'; state.detailId = id }
const closeDetail = () => { state.detailId = null }
const newDownload = () => { state.tab = 'home'; state.view = 'home'; state.detailId = null }

async function runAction(action) {
  try {
    await action()
  } catch (error) {
    flash(error instanceof ApiError ? error.message : 'No se pudo completar la acción')
  }
  await refreshJobs()
  scheduleNextPoll()
}

const togglePause = (job) =>
  runAction(() => (job.status === 'paused' ? api.resume(job.id) : api.pause(job.id)))

const retry = (job) => runAction(() => api.resume(job.id))

async function cancel(job) {
  canceledIds.add(job.id)
  state.jobs = state.jobs.filter((j) => j.id !== job.id)
  state.detailId = null
  flash('Descarga cancelada')
  await runAction(() => api.remove(job.id))
}

const pauseAll = () => runAction(() => (anyRunning.value ? api.pauseAll() : api.resumeAll()))

async function clearDone() {
  await runAction(() => api.clearFinished())
}

// ---------- enlace compartido (?url=) ----------

function consumeSharedUrl() {
  if (!state.authed) return
  const params = new URLSearchParams(window.location.search)
  const shared = params.get('url') || params.get('text')
  if (!shared) return
  window.history.replaceState({}, '', window.location.pathname)
  const match = shared.match(/https?:\/\/\S+/)
  if (match) {
    setUrl(match[0])
    analyze()
  }
}

export function useClipo() {
  return {
    state,
    detail, screen, activeJobs, doneJobs, badgeCount, anyRunning, glow,
    detectedName, placeholder,
    qualities, selectedQuality, formats, selectedCount, itemCount,
    fpsOptions, effectiveFps, estimatedBytes, specLabel, summary, optionsMeta,
    boot, login, logout,
    toggleTheme, setTheme,
    setUrl, paste, selectPlatform, analyze,
    back, setMode, setQuality, setFormat, setFps, togglePlaylistItem, togglePlaylistAll, download,
    setTab, openDetail, closeDetail, newDownload,
    togglePause, retry, cancel, pauseAll, clearDone,
    flash,
  }
}
