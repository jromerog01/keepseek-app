<script setup>
import { computed, ref, watch } from 'vue'
import { fmtDuration } from '../lib/format.js'

const props = defineProps({
  job: { type: Object, required: true },
  width: { type: Number, default: 96 },
  height: { type: Number, default: 54 },
})

const failed = ref(false)
watch(() => [props.job.id, props.job.has_thumbnail], () => { failed.value = false })

const showImage = computed(() => props.job.has_thumbnail && !failed.value)
const src = computed(() => `/api/jobs/${props.job.id}/thumbnail`)
const duration = computed(() => fmtDuration(props.job.duration))
const dimmed = computed(() => props.job.status === 'expired')
</script>

<template>
  <div
    :style="{ width: width + 'px', height: height + 'px' }"
    style="position:relative;flex:none;border-radius:var(--radius-md);overflow:hidden;background:linear-gradient(135deg, var(--color-neutral-800), var(--color-neutral-900))"
  >
    <img
      v-if="showImage"
      :src="src"
      alt=""
      loading="lazy"
      decoding="async"
      :style="{ opacity: dimmed ? 0.4 : 1, filter: dimmed ? 'grayscale(1)' : 'none' }"
      style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"
      @error="failed = true"
    />
    <span
      v-else
      style="position:absolute;inset:0;display:grid;place-items:center;font-size:13px;font-weight:600;color:var(--color-accent-300)"
    >{{ job.mono }}</span>

    <span
      v-if="showImage"
      style="position:absolute;left:4px;top:4px;padding:1px 5px;border-radius:5px;font-size:9px;font-weight:600;letter-spacing:.02em;background:rgba(0,0,0,.55);color:#fff"
    >{{ job.mono }}</span>
    <span
      v-if="duration"
      style="position:absolute;right:4px;bottom:4px;padding:1px 5px;border-radius:5px;font-size:10px;font-weight:500;font-variant-numeric:tabular-nums;background:rgba(0,0,0,.65);color:#fff"
    >{{ duration }}</span>
  </div>
</template>
