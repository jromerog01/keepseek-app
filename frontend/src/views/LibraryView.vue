<script setup>
import { computed } from 'vue'
import { sizeLabel, statusLabel } from '../lib/format.js'
import { useClipo } from '../store/useClipo.js'
import Icon from '../components/Icon.vue'

const { activeJobs, doneJobs, anyRunning, openDetail, togglePause, retry, cancel, pauseAll, clearDone } = useClipo()

const hasPausable = computed(() => activeJobs.value.some((j) => j.status !== 'error'))
const pct = (job) => Math.round(job.progress) + '%'
const activeMeta = (job) => (job.status === 'error' ? job.error || 'La descarga falló' : job.spec)
const doneMeta = (job) => [job.spec, sizeLabel(job), job.source === 'shortcut' ? 'Atajo' : null].filter(Boolean).join(' · ')
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
        <button class="btn btn-ghost" style="font-size:12px;color:var(--color-neutral-500)" @click="clearDone">Limpiar</button>
      </div>
      <button
        v-for="job in doneJobs"
        :key="job.id"
        class="reset" style="cursor:pointer;display:flex;gap:12px;align-items:center;padding:8px 0"
        @click="openDetail(job.id)"
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
</template>
