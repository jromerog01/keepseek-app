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
const phase = ref('idle')
const progress = ref({ received: 0, total: 0 })
let file = null

const isIos = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
const canShareFiles = typeof navigator.canShare === 'function' && typeof navigator.share === 'function'

const downloadUrl = computed(() => api.fileUrl(props.job.id))
const downloadName = computed(() => fileName(props.job))

watch(() => props.job.id, () => {
  phase.value = 'idle'
  file = null
})

const preparingLabel = computed(() => {
  const { received, total } = progress.value
  if (total > 0) return `Descargando ${Math.min(99, Math.round((received / total) * 100))} % · ${fmtBytes(received)} de ${fmtBytes(total)}`
  return received > 0 ? `Descargando ${fmtBytes(received)}` : 'Preparando archivo…'
})

async function prepareShare() {
  if (props.job.size_bytes > LARGE_FILE_BYTES) {
    flash('El archivo es grande: usa "Descargar archivo"')
    return
  }
  phase.value = 'preparing'
  try {
    progress.value = { received: 0, total: props.job.size_bytes || 0 }
    const response = await fetch(downloadUrl.value, { credentials: 'same-origin' })
    if (!response.ok) throw new Error('descarga fallida')
    const blob = await readBody(response, (p) => { progress.value = p }, props.job.size_bytes || 0)
    file = new File([blob], downloadName.value, { type: blob.type })
    if (navigator.canShare({ files: [file] })) {
      phase.value = 'ready'
    } else {
      phase.value = 'idle'
      flash('Este dispositivo no permite compartir el archivo: usa "Descargar archivo"')
    }
  } catch {
    phase.value = 'error'
    flash('No se pudo preparar el archivo')
  }
}

async function share() {
  try {
    await navigator.share({ files: [file] })
  } catch (error) {
    if (error.name === 'AbortError') return
    console.error('navigator.share falló:', error)
    flash(`No se abrió el menú de compartir (${error.name}). Usa "Descargar archivo".`)
  }
}

const onShareTap = () => (phase.value === 'ready' ? share() : prepareShare())
</script>

<template>
  <div style="display:flex;flex-direction:column;gap:10px">
    <a
      :href="downloadUrl"
      :download="downloadName"
      class="btn btn-primary"
      style="height:52px;border-radius:var(--radius-lg);width:100%;gap:10px;font-size:15px;box-shadow:0 0 24px color-mix(in srgb, var(--color-accent) 22%, transparent)"
    >
      <Icon name="download" :size="18" />
      Descargar archivo
    </a>

    <p v-if="isIos" style="margin:0;font-size:12px;color:var(--color-neutral-500);text-wrap:pretty">
      En iPhone se guarda en Archivos › Descargas. Para llevarlo a Fotos: ábrelo, toca Compartir y elige Guardar video.
    </p>

    <button
      v-if="canShareFiles"
      class="btn btn-secondary"
      :disabled="phase === 'preparing'"
      style="height:44px;border-radius:var(--radius-lg);width:100%;gap:10px;font-size:14px"
      @click="onShareTap"
    >
      <span
        v-if="phase === 'preparing'"
        style="width:14px;height:14px;border-radius:7px;border:2px solid var(--color-accent-800);border-top-color:var(--color-accent);animation:spin .8s linear infinite"
      ></span>
      <Icon v-else name="share" :size="16" />
      <template v-if="phase === 'preparing'">{{ preparingLabel }}</template>
      <template v-else-if="phase === 'ready'">Abrir menú de compartir</template>
      <template v-else-if="phase === 'error'">Reintentar compartir</template>
      <template v-else>Compartir o guardar en Fotos</template>
    </button>
  </div>
</template>
