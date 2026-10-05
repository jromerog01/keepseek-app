<script setup>
import { pick } from '../lib/styles.js'
import { useClipo } from '../store/useClipo.js'
import Icon from './Icon.vue'

const { state, badgeCount, setTab } = useClipo()

const tabs = [
  { id: 'home', label: 'Inicio', icon: 'home' },
  { id: 'queue', label: 'Biblioteca', icon: 'library' },
]
</script>

<template>
  <nav
    style="position:absolute;left:0;right:0;bottom:0;height:var(--tabbar-h);background:color-mix(in srgb, var(--color-bg) 92%, transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);z-index:5"
  >
    <div style="position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(to right, transparent, var(--color-neutral-800) 48px, var(--color-neutral-800) calc(100% - 48px), transparent)"></div>
    <div class="col" style="padding:8px min(60px, 15vw) 0;display:grid;grid-template-columns:repeat(2,1fr)">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :aria-label="tab.label"
        :aria-current="state.tab === tab.id ? 'page' : undefined"
        :style="{ color: pick('tab', state.tab === tab.id).color }"
        class="reset" style="cursor:pointer;position:relative;display:flex;flex-direction:column;align-items:center;gap:4px;padding-top:6px;height:48px"
        @click="setTab(tab.id)"
      >
        <Icon :name="tab.icon" :size="24" />
        <span style="font-size:10px;font-weight:500">{{ tab.label }}</span>
        <span
          v-if="tab.id === 'queue' && badgeCount > 0"
          style="position:absolute;top:0;left:calc(50% + 8px);min-width:16px;height:16px;padding:0 4px;border-radius:8px;background:var(--color-accent);color:var(--color-bg);font-size:10px;font-weight:600;display:grid;place-items:center"
        >{{ badgeCount }}</span>
      </button>
    </div>
  </nav>
</template>
