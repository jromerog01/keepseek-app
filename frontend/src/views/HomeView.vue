<script setup>
import { computed } from 'vue'
import { PLATFORMS } from '../lib/platforms.js'
import { pick } from '../lib/styles.js'
import { useClipo } from '../store/useClipo.js'
import Icon from '../components/Icon.vue'

const { state, detectedName, placeholder, setUrl, paste, selectPlatform, analyze, toggleTheme } = useClipo()

const ytdlpTag = computed(() => {
  const version = state.system?.ytdlp_version
  return version ? 'yt-dlp ' + version.split('.').slice(0, 3).join('.') : 'yt-dlp'
})
const cantAnalyze = computed(() => !state.url || state.analyzing)

const tileStyle = (id) => {
  const s = pick('tile', state.platform === id)
  return { background: s.bg, boxShadow: s.shadow }
}
const monoStyle = (id) => {
  const s = pick('tile', state.platform === id)
  return { background: s.monoBg, color: s.monoColor }
}
</script>

<template>
  <div style="padding:20px 22px 32px;display:flex;flex-direction:column;gap:24px">
    <div style="display:flex;align-items:center;justify-content:space-between">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:32px;height:32px;border-radius:var(--radius-md);border:1px solid var(--color-accent);display:grid;place-items:center;color:var(--color-accent);box-shadow:0 0 18px color-mix(in srgb, var(--color-accent) 35%, transparent)">
          <Icon name="download" :size="18" />
        </div>
        <span style="font-size:18px;font-weight:500">Clipo</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="tag tag-neutral">{{ ytdlpTag }}</span>
        <button
          class="btn btn-secondary btn-icon"
          :aria-label="state.theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
          style="width:36px;height:36px;border-radius:18px"
          @click="toggleTheme"
        >
          <Icon :name="state.theme === 'dark' ? 'sun' : 'moon'" :size="18" />
        </button>
      </div>
    </div>

    <div>
      <h2 style="font-size:30px;margin:0 0 6px;text-wrap:pretty">¿Qué quieres guardar hoy?</h2>
      <p style="margin:0;font-size:14px;color:var(--color-neutral-500)">Pega un video o una playlist de cualquier plataforma.</p>
    </div>

    <div style="display:flex;flex-direction:column;gap:10px">
      <div style="position:relative;display:flex;align-items:center">
        <div style="position:absolute;left:14px;color:var(--color-neutral-500);display:flex">
          <Icon name="link" :size="18" />
        </div>
        <input
          class="input"
          type="url"
          inputmode="url"
          autocapitalize="off"
          autocomplete="off"
          autocorrect="off"
          spellcheck="false"
          :value="state.url"
          :placeholder="placeholder"
          style="min-height:52px;padding:0 84px 0 42px;font-size:16px;border-radius:var(--radius-lg)"
          @input="setUrl($event.target.value)"
          @keyup.enter="analyze"
        />
        <button class="btn btn-ghost" style="position:absolute;right:8px;height:36px;padding:0 10px;font-size:13px" @click="paste">Pegar</button>
      </div>

      <div v-if="state.url && detectedName" style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--color-neutral-400)">
        <span style="width:6px;height:6px;border-radius:3px;background:var(--color-accent);box-shadow:0 0 8px var(--color-accent)"></span>
        Detectado: <span style="color:var(--color-accent-300)">{{ detectedName }}</span>
      </div>

      <button
        class="btn btn-primary"
        :disabled="cantAnalyze"
        style="height:52px;border-radius:var(--radius-lg);font-size:15px;box-shadow:0 0 24px color-mix(in srgb, var(--color-accent) 22%, transparent)"
        @click="analyze"
      >
        <span
          v-if="state.analyzing"
          style="width:16px;height:16px;border-radius:8px;border:2px solid var(--color-accent-800);border-top-color:var(--color-accent);animation:spin .8s linear infinite"
        ></span>
        {{ state.analyzing ? 'Analizando enlace…' : 'Analizar enlace' }}
      </button>
    </div>

    <div style="display:flex;flex-direction:column;gap:12px">
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <h6 style="margin:0;color:var(--color-neutral-500)">Plataformas</h6>
        <span style="font-size:11px;color:var(--color-neutral-600)">+1000 sitios</span>
      </div>
      <div class="platform-grid">
        <button
          v-for="p in PLATFORMS"
          :key="p.id"
          :style="tileStyle(p.id)"
          class="reset" style="cursor:pointer;display:flex;flex-direction:column;gap:10px;padding:14px 12px;border-radius:var(--radius-lg)"
          @click="selectPlatform(p.id)"
        >
          <span
            :style="monoStyle(p.id)"
            style="width:34px;height:34px;border-radius:var(--radius-md);display:grid;place-items:center;font-size:12px;font-weight:600"
          >{{ p.mono }}</span>
          <span style="font-size:13px;font-weight:500">{{ p.name }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
