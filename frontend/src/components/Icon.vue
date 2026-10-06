<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 18 },
  sw: { type: Number, default: null },
})

const ICONS = {
  download: { sw: 18, cap: true, join: true, body: '<path d="M128 40v112"></path><path d="M84 112l44 44 44-44"></path><path d="M48 200h160"></path>' },
  sun: { sw: 16, cap: true, body: '<circle cx="128" cy="128" r="48"></circle><path d="M128 24v20M128 212v20M54 54l14 14M188 188l14 14M24 128h20M212 128h20M54 202l14-14M188 68l14-14"></path>' },
  moon: { sw: 16, join: true, body: '<path d="M216 144A88 88 0 0 1 112 40a88 88 0 1 0 104 104z"></path>' },
  link: { sw: 16, cap: true, body: '<path d="M136 72l12-12a40 40 0 0 1 56 56l-28 28a40 40 0 0 1-56 0"></path><path d="M120 184l-12 12a40 40 0 0 1-56-56l28-28a40 40 0 0 1 56 0"></path>' },
  back: { sw: 18, cap: true, join: true, body: '<path d="M160 208L80 128l80-80"></path>' },
  play: { fill: true, body: '<path d="M88 52l120 76-120 76z"></path>' },
  playSm: { fill: true, body: '<path d="M80 44l136 84-136 84z"></path>' },
  pause: { fill: true, body: '<rect x="60" y="40" width="44" height="176" rx="8"></rect><rect x="152" y="40" width="44" height="176" rx="8"></rect>' },
  close: { sw: 18, cap: true, body: '<path d="M200 56L56 200M56 56l144 144"></path>' },
  check: { sw: 32, cap: true, join: true, body: '<path d="M40 136l56 56 120-120"></path>' },
  home: { sw: 16, join: true, body: '<path d="M40 216V116l88-76 88 76v100h-60v-60h-56v60z"></path>' },
  library: { sw: 16, cap: true, join: true, body: '<rect x="40" y="88" width="176" height="128" rx="12"></rect><path d="M64 60h128M88 32h80"></path><path d="M112 128l40 24-40 24z"></path>' },
  share: { sw: 16, cap: true, join: true, body: '<path d="M128 160V32"></path><path d="M88 72l40-40 40 40"></path><path d="M88 112H64a8 8 0 0 0-8 8v96a8 8 0 0 0 8 8h128a8 8 0 0 0 8-8v-96a8 8 0 0 0-8-8h-24"></path>' },
  retry: { sw: 16, cap: true, join: true, body: '<path d="M200 72a80 80 0 1 0 16 56"></path><path d="M200 32v40h-40"></path>' },
  warn: { sw: 16, cap: true, body: '<circle cx="128" cy="128" r="96"></circle><path d="M128 80v56"></path><path d="M128 172h.01"></path>' },
  info: { sw: 16, cap: true, body: '<circle cx="128" cy="128" r="96"></circle><path d="M128 116v60"></path><path d="M128 80h.01"></path>' },
  trash: { sw: 16, cap: true, join: true, body: '<path d="M52 68h152"></path><path d="M96 68V44h64v24"></path><path d="M76 68l12 148h80l12-148"></path><path d="M112 108v64M144 108v64"></path>' },
}

const icon = computed(() => ICONS[props.name])
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 256 256"
    :fill="icon.fill ? 'currentColor' : 'none'"
    :stroke="icon.fill ? undefined : 'currentColor'"
    :stroke-width="icon.fill ? undefined : (sw ?? icon.sw)"
    :stroke-linecap="icon.cap ? 'round' : undefined"
    :stroke-linejoin="icon.join ? 'round' : undefined"
    aria-hidden="true"
    v-html="icon.body"
  ></svg>
</template>
