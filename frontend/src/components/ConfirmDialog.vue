<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Aceptar' },
  danger: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])

const onKey = (event) => { if (props.open && event.key === 'Escape') emit('cancel') }
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div v-if="open" class="dialog-backdrop" style="z-index:20" @click.self="emit('cancel')">
    <div class="dialog" role="alertdialog" aria-modal="true" :aria-label="title" style="width:min(340px, 100%)">
      <div class="dialog-title" style="font-size:18px">{{ title }}</div>
      <div v-if="message" class="dialog-body" style="font-size:13px;text-wrap:pretty">{{ message }}</div>
      <div class="dialog-actions">
        <button class="btn btn-secondary" style="height:42px;padding:0 16px" @click="emit('cancel')">Cancelar</button>
        <button
          class="btn"
          :class="danger ? '' : 'btn-primary'"
          :style="danger ? 'height:42px;padding:0 16px;color:#ffb4aa;border-color:#d73a31;background:color-mix(in srgb, #d73a31 18%, transparent)' : 'height:42px;padding:0 16px'"
          @click="emit('confirm')"
        >{{ confirmLabel }}</button>
      </div>
    </div>
  </div>
</template>
