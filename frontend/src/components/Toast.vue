<script setup>
import { useClipo } from '../store/useClipo.js'

const { state } = useClipo()
</script>

<template>
  <div
    v-if="state.toast"
    style="position:absolute;left:0;right:0;bottom:calc(var(--tabbar-h) + 16px);z-index:6;pointer-events:none"
  >
    <div class="col" style="padding:0 22px">
      <div
        role="status"
        style="padding:12px 14px;border-radius:var(--radius-lg);background:var(--color-surface);box-shadow:var(--shadow-md);font-size:13px;display:flex;align-items:center;gap:10px"
      >
        <span style="width:6px;height:6px;flex:none;border-radius:3px;background:var(--color-accent);box-shadow:0 0 8px var(--color-accent)"></span>{{ state.toast }}
      </div>
    </div>
  </div>
</template>
