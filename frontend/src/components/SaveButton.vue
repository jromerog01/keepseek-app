<script setup>
import { computed } from 'vue'
import { api } from '../api/client.js'
import { fileName } from '../lib/format.js'
import Icon from './Icon.vue'

const props = defineProps({ job: { type: Object, required: true } })

const isIos = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)

const downloadUrl = computed(() => api.fileUrl(props.job.id))
const downloadName = computed(() => fileName(props.job))
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
  </div>
</template>
