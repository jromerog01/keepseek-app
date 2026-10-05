<script>
// Archivo ya traído del servidor: se conserva para no volver a transferirlo
// si el usuario sale de la pantalla y regresa, o si el menú se cierra.
const prepared = { jobId: null, file: null }
</script>

<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api/client.js'
import { readBody } from '../lib/download.js'
import { fileName, fmtBytes } from '../lib/format.js'
import { useClipo } from '../store/useClipo.js'
import Icon from './Icon.vue'

const props = defineProps({ job: { type: Object, required: true } })
const { flash } = useClipo()

const LARGE_FILE_BYTES = 300e6
const progress = ref({ received: 0, total: 0 })

const isIos = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
const canShareFiles = typeof navigator.canShare === 'function' && typeof navigator.share === 'function'

const downloadUrl = computed(() => api.fileUrl(props.job.id))
const downloadName = computed(() => fileName(props.job))
const hasPrepared = () => prepared.jobId === props.job.id && prepared.file !== null

const phase = ref(hasPrepared() ? 'ready' : 'idle')

watch(() => props.job.id, () => {
  phase.value = hasPrepared() ? 'ready' : 'idle'
})

const preparingLabel = computed(() => {
  const { received, total } = progress.value
  if (total > 0) return `Descargando ${Math.min(99, Math.round((received / total) * 100))} % · ${fmtBytes(received)} de ${fmtBytes(total)}`
  return received > 0 ? `Descargando ${fmtBytes(received)}` : 'Preparando archivo…'
})

async function fetchFile() {
  progress.value = { received: 0, total: props.job.size_bytes || 0 }
  const response = await fetch(downloadUrl.value, { credentials: 'same-origin' })
  if (!response.ok) throw new Error('descarga fallida')
  const blob = await readBody(response, (p) => { progress.value = p }, props.job.size_bytes || 0)
  return new File([blob], downloadName.value, { type: blob.type })
}

async function openShareSheet() {
  try {
    await navigator.share({ files: [prepared.file] })
    phase.value = 'ready'
  } catch (error) {
    phase.value = 'ready'
    if (error.name === 'AbortError') return
    if (error.name === 'NotAllowedError') return // iOS pide un toque nuevo: queda en "Listo"
    console.error('navigator.share falló:', error)
    flash(`No se abrió el menú de compartir (${error.name}). Usa "Descargar a Archivos".`)
  }
}

async function onTap() {
  if (hasPrepared()) return openShareSheet()

  if (props.job.size_bytes > LARGE_FILE_BYTES) {
    flash('El archivo es muy grande para Fotos desde la app: usa "Descargar a Archivos"')
    return
  }

  phase.value = 'preparing'
  try {
    const file = await fetchFile()
    if (!navigator.canShare({ files: [file] })) {
      phase.value = 'idle'
      flash('Este dispositivo no permite guardar este archivo en Fotos: usa "Descargar a Archivos"')
      return
    }
    prepared.jobId = props.job.id
    prepared.file = file
    await openShareSheet()
  } catch {
    phase.value = 'error'
    flash('No se pudo traer el archivo del servidor')
  }
}
</script>

<template>
  <div style="display:flex;flex-direction:column;gap:10px">
    <button
      v-if="canShareFiles"
      class="btn btn-primary"
      :disabled="phase === 'preparing'"
      style="height:52px;border-radius:var(--radius-lg);width:100%;gap:10px;font-size:15px;box-shadow:0 0 24px color-mix(in srgb, var(--color-accent) 22%, transparent)"
      @click="onTap"
    >
      <span
        v-if="phase === 'preparing'"
        style="width:16px;height:16px;border-radius:8px;border:2px solid var(--color-accent-800);border-top-color:var(--color-accent);animation:spin .8s linear infinite"
      ></span>
      <Icon v-else name="share" :size="18" />
      <template v-if="phase === 'preparing'">{{ preparingLabel }}</template>
      <template v-else-if="phase === 'ready'">Listo: toca para guardar en Fotos</template>
      <template v-else-if="phase === 'error'">Reintentar</template>
      <template v-else>Guardar en Fotos</template>
    </button>

    <a
      :href="downloadUrl"
      :download="downloadName"
      class="btn"
      :class="canShareFiles ? 'btn-secondary' : 'btn-primary'"
      style="height:48px;border-radius:var(--radius-lg);width:100%;gap:10px;font-size:14px"
    >
      <Icon name="download" :size="16" />
      Descargar a Archivos
    </a>

    <p v-if="isIos" style="margin:0;font-size:12px;color:var(--color-neutral-500);text-wrap:pretty">
      "Guardar en Fotos" pasa el video del servidor a tu teléfono una sola vez. "Descargar a Archivos" es otra copia aparte: usa solo una de las dos.
    </p>
  </div>
</template>
