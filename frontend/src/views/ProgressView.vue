<script setup>
import { computed } from 'vue'
import { etaLabel, sizeLabel, stageRows, statusLabel } from '../lib/format.js'
import { T } from '../lib/styles.js'
import { useClipo } from '../store/useClipo.js'
import Icon from '../components/Icon.vue'
import SaveButton from '../components/SaveButton.vue'

const { detail: job, closeDetail, togglePause, cancel, retry, newDownload } = useClipo()

const pct = computed(() => Math.round(job.value.progress) + '%')
const inProgress = computed(() => ['waiting', 'running', 'paused'].includes(job.value.status))
const stages = computed(() => stageRows(job.value).map((g) => ({ ...g, ...T.stage[g.state] })))
const headerTitle = computed(() => {
  if (job.value.status === 'error') return 'Error en la descarga'
  return job.value.status === 'done' || job.value.status === 'expired' ? 'Descarga' : 'Descargando'
})
</script>

<template>
  <div v-if="job" style="padding:12px 22px 32px;display:flex;flex-direction:column;gap:26px">
    <div style="display:flex;align-items:center;gap:10px">
      <button class="btn btn-secondary btn-icon" aria-label="Volver" style="width:40px;height:40px;border-radius:20px" @click="closeDetail">
        <Icon name="back" :size="18" />
      </button>
      <span style="font-size:15px;font-weight:500">{{ headerTitle }}</span>
    </div>

    <div style="display:flex;flex-direction:column;align-items:center;gap:18px;padding-top:6px">
      <div
        :style="{ background: `conic-gradient(var(--color-accent) ${pct}, var(--color-neutral-800) 0)` }"
        style="width:200px;height:200px;border-radius:100px;padding:6px;box-shadow:0 0 40px color-mix(in srgb, var(--color-accent) 25%, transparent)"
      >
        <div style="width:100%;height:100%;border-radius:50%;background:var(--color-bg);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px">
          <span style="font-size:44px;font-weight:500;letter-spacing:-.03em">{{ pct }}</span>
          <span style="font-size:12px;color:var(--color-neutral-500)">{{ sizeLabel(job) }}</span>
        </div>
      </div>
      <div style="text-align:center;max-width:300px">
        <div style="font-size:16px;font-weight:500;line-height:1.3;text-wrap:pretty">{{ job.title }}</div>
        <div style="font-size:13px;color:var(--color-neutral-500);margin-top:4px">{{ job.spec }}</div>
      </div>
    </div>

    <div
      v-if="job.status === 'error'"
      style="display:flex;gap:10px;align-items:flex-start;padding:12px 14px;border-radius:var(--radius-lg);background:var(--color-surface);font-size:13px"
    >
      <span style="color:var(--color-accent);display:flex;margin-top:1px"><Icon name="warn" :size="16" /></span>
      <span style="color:var(--color-neutral-300);text-wrap:pretty">{{ job.error || 'La descarga falló' }}</span>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="card" style="padding:12px 14px;border-radius:var(--radius-lg)">
        <span style="font-size:11px;color:var(--color-neutral-500)">Estado</span>
        <span style="font-size:15px">{{ statusLabel(job) }}</span>
      </div>
      <div class="card" style="padding:12px 14px;border-radius:var(--radius-lg)">
        <span style="font-size:11px;color:var(--color-neutral-500)">Tiempo restante</span>
        <span style="font-size:15px">{{ etaLabel(job) }}</span>
      </div>
    </div>

    <div style="display:flex;flex-direction:column;gap:16px;padding-left:4px">
      <div v-for="g in stages" :key="g.label" :style="{ color: g.color }" style="display:flex;align-items:flex-start;gap:12px;font-size:14px">
        <span
          :style="{ background: g.dot, border: '1.5px solid ' + g.ring, boxShadow: g.glow }"
          style="width:10px;height:10px;border-radius:5px;flex:none;margin-top:5px"
        ></span>
        <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:6px">
          <span>{{ g.label }}</span>
          <div
            v-if="g.state === 'active' && g.pct != null"
            style="height:3px;border-radius:2px;background:var(--color-neutral-800);overflow:hidden"
          >
            <div :style="{ width: Math.round(g.pct) + '%' }" style="height:100%;border-radius:2px;background:var(--color-accent);box-shadow:0 0 8px var(--color-accent);transition:width .4s"></div>
          </div>
        </div>
        <span style="font-size:13px;font-variant-numeric:tabular-nums;flex:none;min-width:58px;text-align:right">{{ g.detail }}</span>
      </div>
    </div>

    <div v-if="inProgress || job.status === 'error'" style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <button
        v-if="job.status === 'error'"
        class="btn btn-secondary"
        style="height:48px;border-radius:var(--radius-lg)"
        @click="retry(job)"
      >Reintentar</button>
      <button
        v-else
        class="btn btn-secondary"
        style="height:48px;border-radius:var(--radius-lg)"
        @click="togglePause(job)"
      >{{ job.status === 'paused' ? 'Reanudar' : 'Pausar' }}</button>
      <button
        class="btn btn-secondary"
        style="height:48px;border-radius:var(--radius-lg);color:var(--color-neutral-400)"
        @click="cancel(job)"
      >Cancelar</button>
    </div>

    <div v-if="job.status === 'done'" style="display:flex;flex-direction:column;gap:10px">
      <SaveButton v-if="job.file_available" :job="job" />
      <button
        class="btn"
        :class="job.file_available ? 'btn-secondary' : 'btn-primary'"
        style="height:52px;border-radius:var(--radius-lg)"
        @click="newDownload"
      >Descargar otro</button>
    </div>

    <div v-if="job.status === 'expired'" style="display:flex;flex-direction:column;gap:10px">
      <p style="margin:0;font-size:13px;color:var(--color-neutral-500)">
        El archivo ya expiró en el servidor. Vuelve a descargarlo si lo necesitas.
      </p>
      <button class="btn btn-primary" style="height:52px;border-radius:var(--radius-lg)" @click="newDownload">Descargar otro</button>
    </div>
  </div>
</template>
