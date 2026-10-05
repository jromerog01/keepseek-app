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

const preparingLabel = computed(() => {
  const { received, total } = progress.value
  if (total > 0) return `Descargando ${Math.min(99, Math.round((received / total) * 100))} % · ${fmtBytes(received)} de ${fmtBytes(total)}`
  return received > 0 ? `Descargando ${fmtBytes(received)}` : 'Preparando archivo…'
})

watch(() => props.job.id, () => {
  phase.value = 'idle'
  file = null
})

function downloadWithLink(blob) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = fileName(props.job)
  link.click()
  setTimeout(() => URL.revokeObjectURL(link.href), 10000)
}

async function prepare() {
  if (props.job.size_bytes > LARGE_FILE_BYTES) {
    window.location.href = api.fileUrl(props.job.id)
    return
  }
  phase.value = 'preparing'
  try {
    progress.value = { received: 0, total: props.job.size_bytes || 0 }
    const response = await fetch(api.fileUrl(props.job.id), { credentials: 'same-origin' })
    if (!response.ok) throw new Error('descarga fallida')
    const blob = await readBody(response, (p) => { progress.value = p }, props.job.size_bytes || 0)
    file = new File([blob], fileName(props.job), { type: blob.type })
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      phase.value = 'ready'
    } else {
      downloadWithLink(blob)
      phase.value = 'idle'
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
    downloadWithLink(file)
    flash(`No se abrió el menú de compartir (${error.name}); se descargó el archivo`)
  }
}

const onTap = () => (phase.value === 'ready' ? share() : prepare())
</script>

<template>
  <button
    class="btn btn-primary"
    :disabled="phase === 'preparing'"
    style="height:52px;border-radius:var(--radius-lg);width:100%;gap:10px;font-size:15px;box-shadow:0 0 24px color-mix(in srgb, var(--color-accent) 22%, transparent)"
    @click="onTap"
  >
    <span
      v-if="phase === 'preparing'"
      style="width:16px;height:16px;border-radius:8px;border:2px solid var(--color-accent-800);border-top-color:var(--color-accent);animation:spin .8s linear infinite"
    ></span>
    <Icon v-else :name="phase === 'ready' ? 'share' : 'download'" :size="18" />
    <template v-if="phase === 'preparing'">{{ preparingLabel }}</template>
    <template v-else-if="phase === 'ready'">Guardar en iPhone</template>
    <template v-else-if="phase === 'error'">Reintentar</template>
    <template v-else>Preparar archivo</template>
  </button>
</template>
