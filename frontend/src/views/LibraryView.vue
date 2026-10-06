<script setup>
import { computed, ref } from 'vue'
import { sizeLabel, stageSummary, statusLabel } from '../lib/format.js'
import { useClipo } from '../store/useClipo.js'
import Icon from '../components/Icon.vue'

const {
  activeJobs,
  doneJobs,
  anyRunning,
  openDetail,
  togglePause,
  retry,
  cancel,
  pauseAll,
  removeFromLibrary,
  clearLibrary,
} = useClipo()

const hasPausable = computed(() => activeJobs.value.some((j) => j.status !== 'error'))
const pct = (job) => Math.round(job.progress) + '%'
const activeMeta = (job) => {
  if (job.status === 'error') return job.error || 'La descarga falló'
  return (job.status === 'running' && stageSummary(job)) || job.spec
}
const doneMeta = (job) => [job.spec, sizeLabel(job), job.source === 'shortcut' ? 'Atajo' : null].filter(Boolean).join(' · ')
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

async function confirmClearLibrary() {
  if (!window.confirm('¿Borrar todos los videos de la biblioteca?')) return
  openSwipeId.value = null
  await clearLibrary()
}
</script>

<template>
  <div style="padding:20px 22px 32px;display:flex;flex-direction:column;gap:24px">
    <div style="display:flex;align-items:center;justify-content:space-between">
      <h2 style="font-size:28px;margin:0">Biblioteca</h2>
      <button v-if="hasPausable" class="btn btn-ghost" @click="pauseAll">{{ anyRunning ? 'Pausar todo' : 'Reanudar todo' }}</button>
    </div>

    <div style="display:flex;flex-direction:column;gap:10px">
      <h6 style="margin:0;color:var(--color-neutral-500)">Cola · {{ activeJobs.length }}</h6>
      <div
        v-if="activeJobs.length === 0"
        style="padding:22px 16px;border-radius:var(--radius-lg);border:1px dashed var(--color-neutral-800);font-size:13px;color:var(--color-neutral-500)"
      >La cola está vacía. Pega un enlace en Inicio para empezar.</div>

      <div v-for="job in activeJobs" :key="job.id" class="card" style="padding:14px;gap:12px;border-radius:var(--radius-lg)">
        <div style="display:flex;gap:12px;align-items:center">
          <button class="reset" style="cursor:pointer;flex:1;min-width:0;display:flex;gap:12px;align-items:center" @click="openDetail(job.id)">
            <span style="width:44px;height:44px;flex:none;border-radius:var(--radius-md);background:var(--color-accent-900);color:var(--color-accent-300);display:grid;place-items:center;font-size:12px;font-weight:600">{{ job.mono }}</span>
            <span style="flex:1;min-width:0;display:flex;flex-direction:column">
              <span style="font-size:14px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ job.title }}</span>
              <span style="font-size:12px;color:var(--color-neutral-500);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ activeMeta(job) }}</span>
            </span>
          </button>
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
        <div style="display:flex;flex-direction:column;gap:6px">
          <div style="height:4px;border-radius:2px;background:var(--color-neutral-800);overflow:hidden">
            <div :style="{ width: pct(job) }" style="height:100%;border-radius:2px;background:var(--color-accent);box-shadow:0 0 10px var(--color-accent);transition:width .4s"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--color-neutral-500)">
            <span>{{ pct(job) }} · {{ sizeLabel(job) }}</span><span>{{ statusLabel(job) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="doneJobs.length" style="display:flex;flex-direction:column;gap:6px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <h6 style="margin:0;color:var(--color-neutral-500)">Descargados · {{ doneJobs.length }}</h6>
        <button class="btn btn-ghost" style="font-size:12px;color:var(--color-neutral-500)" @click="confirmClearLibrary">Limpiar biblioteca</button>
      </div>
      <div
        v-for="job in doneJobs"
        :key="job.id"
        class="library-swipe"
      >
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
          <span style="width:44px;height:44px;flex:none;border-radius:var(--radius-md);background:var(--color-surface);color:var(--color-neutral-400);display:grid;place-items:center;font-size:12px;font-weight:600">{{ job.mono }}</span>
          <span style="flex:1;min-width:0;display:flex;flex-direction:column">
            <span style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ job.title }}</span>
            <span style="font-size:12px;color:var(--color-neutral-500);display:flex;gap:6px;align-items:center">
              <span v-if="job.status === 'done'" style="display:flex;color:var(--color-accent)"><Icon name="check" :size="12" :sw="24" /></span>
              <span v-else style="color:var(--color-neutral-600)">Expirado</span>
              {{ doneMeta(job) }}
            </span>
          </span>
        </button>
      </div>
    </div>
  </div>
</template>
