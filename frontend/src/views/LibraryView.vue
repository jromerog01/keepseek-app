<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  expiresIn, fmtBytes, fmtSpeed, groupByDay, relativeTime, sizeLabel, stageSummary, statusLabel, storageUsed,
} from '../lib/format.js'
import { useClipo } from '../store/useClipo.js'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Icon from '../components/Icon.vue'
import JobThumb from '../components/JobThumb.vue'

const {
  activeJobs, doneJobs, anyRunning, openDetail, togglePause, retry, cancel, pauseAll,
  removeFromLibrary, clearLibrary, newDownload,
} = useClipo()

// ---------- filtros y búsqueda ----------
const filter = ref('all')
const query = ref('')
const confirmingClear = ref(false)

const total = computed(() => activeJobs.value.length + doneJobs.value.length)
const showSearch = computed(() => total.value >= 6)
const matches = (job) => {
  const text = query.value.trim().toLowerCase()
  return !text || job.title.toLowerCase().includes(text) || (job.uploader || '').toLowerCase().includes(text)
}
const shownActive = computed(() => (filter.value === 'done' ? [] : activeJobs.value.filter(matches)))
const shownDone = computed(() => (filter.value === 'active' ? [] : doneJobs.value.filter(matches)))

const filters = computed(() => [
  { id: 'all', label: 'Todo', count: total.value },
  { id: 'active', label: 'En curso', count: activeJobs.value.length },
  { id: 'done', label: 'Listos', count: doneJobs.value.length },
])
const nothingToShow = computed(() => total.value > 0 && shownActive.value.length === 0 && shownDone.value.length === 0)

// ---------- tiempo ----------
const now = ref(Date.now())
let ticker = null
onMounted(() => { ticker = window.setInterval(() => { now.value = Date.now() }, 30000) })
onUnmounted(() => window.clearInterval(ticker))

const groups = computed(() => groupByDay(shownDone.value, now.value))
const summary = computed(() => {
  const ready = doneJobs.value.filter((j) => j.status === 'done').length
  const parts = [`${doneJobs.value.length} ${doneJobs.value.length === 1 ? 'video' : 'videos'}`]
  if (ready) parts.push(`${fmtBytes(storageUsed(doneJobs.value))} en el servidor`)
  return parts.join(' · ')
})

// ---------- textos de cada fila ----------
const pct = (job) => Math.round(job.progress) + '%'
const activeMeta = (job) => {
  if (job.status === 'error') return job.error || 'La descarga falló'
  return (job.status === 'running' && stageSummary(job)) || job.spec
}
const rightText = (job) => (job.status === 'running' && job.speed ? `↓ ${fmtSpeed(job.speed)}` : statusLabel(job))
const doneMeta = (job) => [job.spec, sizeLabel(job), job.source === 'shortcut' ? 'Atajo' : null].filter(Boolean).join(' · ')
const when = (job) => relativeTime(job.finished_at || job.created_at, now.value)
const expiry = (job) => (job.status === 'done' ? expiresIn(job.expires_at, now.value) : null)

// ---------- deslizar para ver o borrar ----------
const swipeWidth = 152
const openSwipeId = ref(null)
const suppressClickId = ref(null)
const drag = ref({ id: null, pointerId: null, startX: 0, deltaX: 0, moved: false })

const rowOffset = (job) => {
  if (drag.value.id === job.id) return drag.value.deltaX
  return openSwipeId.value === job.id ? -swipeWidth : 0
}

function onSwipeStart(event, job) {
  if (event.button != null && event.button !== 0) return
  const base = openSwipeId.value === job.id ? -swipeWidth : 0
  if (openSwipeId.value && openSwipeId.value !== job.id) openSwipeId.value = null
  drag.value = { id: job.id, pointerId: event.pointerId, startX: event.clientX, deltaX: base, moved: false }
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function onSwipeMove(event, job) {
  if (drag.value.id !== job.id || drag.value.pointerId !== event.pointerId) return
  const base = openSwipeId.value === job.id ? -swipeWidth : 0
  const delta = base + event.clientX - drag.value.startX
  drag.value.deltaX = Math.max(-swipeWidth, Math.min(0, delta))
  if (Math.abs(delta - base) > 8) drag.value.moved = true
}

function onSwipeEnd(event, job) {
  if (drag.value.id !== job.id || drag.value.pointerId !== event.pointerId) return
  const moved = drag.value.moved
  openSwipeId.value = drag.value.deltaX < -swipeWidth / 2 ? job.id : null
  drag.value = { id: null, pointerId: null, startX: 0, deltaX: 0, moved: false }
  if (moved) {
    suppressClickId.value = job.id
    window.setTimeout(() => { suppressClickId.value = null }, 0)
  }
}

function openDone(job) {
  if (suppressClickId.value === job.id) return
  if (openSwipeId.value === job.id) {
    openSwipeId.value = null
    return
  }
  openDetail(job.id)
}

async function deleteDone(job) {
  openSwipeId.value = null
  await removeFromLibrary(job)
}

async function confirmClear() {
  confirmingClear.value = false
  openSwipeId.value = null
  await clearLibrary()
}
</script>

<template>
  <div style="padding:20px 22px 32px;display:flex;flex-direction:column;gap:18px">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
      <div style="min-width:0">
        <h2 style="font-size:28px;margin:0">Biblioteca</h2>
        <div v-if="total" style="font-size:12px;color:var(--color-neutral-500);margin-top:4px">{{ summary }}</div>
      </div>
      <button v-if="activeJobs.some((j) => j.status !== 'error')" class="btn btn-ghost" style="flex:none" @click="pauseAll">
        {{ anyRunning ? 'Pausar todo' : 'Reanudar todo' }}
      </button>
    </div>

    <!-- Estado vacío -->
    <div
      v-if="total === 0"
      style="display:flex;flex-direction:column;align-items:center;gap:14px;text-align:center;padding:48px 24px;border-radius:var(--radius-lg);border:1px dashed var(--color-neutral-800)"
    >
      <span style="width:64px;height:64px;border-radius:32px;display:grid;place-items:center;color:var(--color-accent);border:1px solid var(--color-accent);box-shadow:0 0 30px color-mix(in srgb, var(--color-accent) 25%, transparent)">
        <Icon name="library" :size="28" />
      </span>
      <div>
        <div style="font-size:17px;font-weight:500">Aún no hay descargas</div>
        <div style="font-size:13px;color:var(--color-neutral-500);margin-top:6px;text-wrap:pretty">
          Los videos que descargues aparecerán aquí con su miniatura. Los archivos se conservan unas horas en el servidor.
        </div>
      </div>
      <button class="btn btn-primary" style="height:44px;padding:0 20px;border-radius:var(--radius-lg)" @click="newDownload">Pegar un enlace</button>
    </div>

    <template v-else>
      <!-- Filtros y búsqueda -->
      <div style="display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;margin:0 -22px;padding:0 22px">
        <button
          v-for="f in filters"
          :key="f.id"
          class="reset"
          :aria-pressed="filter === f.id"
          :style="{
            border: '1px solid ' + (filter === f.id ? 'var(--color-accent)' : 'var(--color-neutral-800)'),
            color: filter === f.id ? 'var(--color-accent-200)' : 'var(--color-neutral-400)',
            background: filter === f.id ? 'var(--color-accent-900)' : 'transparent',
          }"
          style="cursor:pointer;flex:none;height:34px;padding:0 14px;display:flex;align-items:center;gap:6px;border-radius:17px;font-size:13px;font-weight:500"
          @click="filter = f.id"
        >
          {{ f.label }}
          <span style="font-size:11px;opacity:.7;font-variant-numeric:tabular-nums">{{ f.count }}</span>
        </button>
      </div>

      <input
        v-if="showSearch"
        v-model="query"
        class="input"
        type="search"
        placeholder="Buscar por título o canal"
        autocomplete="off"
        style="min-height:44px;font-size:16px;border-radius:var(--radius-lg)"
      />

      <div
        v-if="nothingToShow"
        style="padding:28px 16px;text-align:center;border-radius:var(--radius-lg);border:1px dashed var(--color-neutral-800);font-size:13px;color:var(--color-neutral-500)"
      >
        {{ query.trim() ? 'Ningún video coincide con la búsqueda.' : filter === 'active' ? 'No hay descargas en curso.' : 'Todavía no hay videos listos.' }}
      </div>

      <!-- En curso -->
      <section v-if="shownActive.length" style="display:flex;flex-direction:column;gap:10px">
        <h6 style="margin:0;color:var(--color-neutral-500)">En curso · {{ shownActive.length }}</h6>

        <div v-for="job in shownActive" :key="job.id" class="card" style="padding:12px;gap:12px;border-radius:var(--radius-lg)">
          <div class="active-top">
            <button class="reset active-main" @click="openDetail(job.id)">
              <JobThumb :job="job" :width="88" :height="50" />
              <span style="flex:1;min-width:0;display:flex;flex-direction:column;gap:2px">
                <span class="clamp-2" style="font-size:14px;font-weight:500;line-height:1.25">{{ job.title }}</span>
                <span
                  :style="{ color: job.status === 'error' ? '#ffb4aa' : 'var(--color-neutral-500)' }"
                  style="font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
                >{{ activeMeta(job) }}</span>
              </span>
            </button>
            <div class="active-controls">
              <button
                v-if="job.status === 'error'"
                class="btn btn-secondary btn-icon"
                aria-label="Reintentar"
                style="width:36px;height:36px;border-radius:18px"
                @click="retry(job)"
              ><Icon name="retry" :size="16" /></button>
              <button
                v-else
                class="btn btn-secondary btn-icon"
                :aria-label="job.status === 'paused' ? 'Reanudar' : 'Pausar'"
                style="width:36px;height:36px;border-radius:18px"
                @click="togglePause(job)"
              ><Icon :name="job.status === 'paused' ? 'playSm' : 'pause'" :size="14" /></button>
              <button
                class="btn btn-ghost btn-icon"
                aria-label="Cancelar"
                style="width:36px;height:36px;color:var(--color-neutral-500)"
                @click="cancel(job)"
              ><Icon name="close" :size="16" /></button>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;gap:6px">
            <div style="height:4px;border-radius:2px;background:var(--color-neutral-800);overflow:hidden">
              <div :style="{ width: pct(job) }" style="height:100%;border-radius:2px;background:var(--color-accent);box-shadow:0 0 10px var(--color-accent);transition:width .4s"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--color-neutral-500)">
              <span>{{ pct(job) }} · {{ sizeLabel(job) }}</span><span>{{ rightText(job) }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Descargados, agrupados por día -->
      <section v-if="shownDone.length" style="display:flex;flex-direction:column;gap:14px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <h6 style="margin:0;color:var(--color-neutral-500)">Descargados · {{ shownDone.length }}</h6>
          <button class="btn btn-ghost" style="font-size:12px;color:var(--color-neutral-500)" @click="confirmingClear = true">Limpiar biblioteca</button>
        </div>

        <div v-for="group in groups" :key="group.label" style="display:flex;flex-direction:column;gap:6px">
          <div style="font-size:12px;font-weight:500;color:var(--color-neutral-400)">{{ group.label }}</div>

          <div v-for="job in group.jobs" :key="job.id" class="library-swipe">
            <div class="library-swipe-actions">
              <button class="btn library-action" type="button" aria-label="Ver detalles" @click.stop="openDetail(job.id)">
                <Icon name="info" :size="16" />
                <span>Ver</span>
              </button>
              <button class="btn library-action library-action-danger" type="button" aria-label="Borrar de la biblioteca" @click.stop="deleteDone(job)">
                <Icon name="trash" :size="16" />
                <span>Borrar</span>
              </button>
            </div>
            <button
              type="button"
              class="reset library-swipe-front"
              :class="{ 'is-open': openSwipeId === job.id }"
              :style="{ transform: `translateX(${rowOffset(job)}px)` }"
              @pointerdown="onSwipeStart($event, job)"
              @pointermove="onSwipeMove($event, job)"
              @pointerup="onSwipeEnd($event, job)"
              @pointercancel="onSwipeEnd($event, job)"
              @click="openDone(job)"
            >
              <JobThumb :job="job" :width="96" :height="54" />
              <span style="flex:1;min-width:0;display:flex;flex-direction:column;gap:3px">
                <span
                  class="clamp-2"
                  :style="{ color: job.status === 'expired' ? 'var(--color-neutral-500)' : 'var(--color-text)' }"
                  style="font-size:14px;line-height:1.25"
                >{{ job.title }}</span>
                <span style="font-size:12px;color:var(--color-neutral-500);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ doneMeta(job) }}</span>
                <span style="display:flex;gap:8px;align-items:center;font-size:11px;color:var(--color-neutral-600)">
                  <span>{{ when(job) }}</span>
                  <span
                    v-if="job.status === 'expired'"
                    style="padding:1px 7px;border-radius:8px;background:var(--color-neutral-800);color:var(--color-neutral-400)"
                  >Expirado</span>
                  <span
                    v-else-if="expiry(job)"
                    :style="{ color: expiry(job).urgent ? '#ffb4aa' : 'var(--color-neutral-500)' }"
                    style="display:flex;align-items:center;gap:4px"
                  >· {{ expiry(job).label }}</span>
                </span>
              </span>
            </button>
          </div>
        </div>
      </section>
    </template>

    <ConfirmDialog
      :open="confirmingClear"
      title="¿Limpiar la biblioteca?"
      :message="`Se borrarán ${doneJobs.length} ${doneJobs.length === 1 ? 'video' : 'videos'} del servidor y su historial. No se puede deshacer.`"
      confirm-label="Borrar todo"
      danger
      @confirm="confirmClear"
      @cancel="confirmingClear = false"
    />
  </div>
</template>
