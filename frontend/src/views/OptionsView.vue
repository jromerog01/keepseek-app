<script setup>
import { computed, ref, watch } from 'vue'
import { fmtApprox } from '../lib/format.js'
import { divider, pick } from '../lib/styles.js'
import { useClipo } from '../store/useClipo.js'
import Icon from '../components/Icon.vue'

const {
  state, optionsMeta: meta, qualities, selectedQuality, formats, fpsOptions, effectiveFps, itemCount,
  selectedCount, sizeFor, back, setMode, setQuality, setFormat, setFps, togglePlaylistItem, togglePlaylistAll,
} = useClipo()

const thumbFailed = ref(false)
watch(() => state.analysis, () => { thumbFailed.value = false })

const isPlaylist = computed(() => state.analysis?.is_playlist)
const modes = [['video', 'Video'], ['audio', 'Solo audio']]
const showHdNote = computed(() => state.mode === 'video' && selectedQuality.value?.id === '2160' && state.format === 'MP4')

const sizeText = (q) => fmtApprox(sizeFor(q))
const modeDisabled = (id) => id === 'video' && state.analysis?.audio_only
</script>

<template>
  <div v-if="meta" style="padding:12px 22px 120px;display:flex;flex-direction:column;gap:22px">
    <div style="display:flex;align-items:center;gap:10px">
      <button class="btn btn-secondary btn-icon" aria-label="Volver" style="width:40px;height:40px;border-radius:20px" @click="back">
        <Icon name="back" :size="18" />
      </button>
      <span style="font-size:15px;font-weight:500">Opciones de descarga</span>
    </div>

    <div style="display:flex;flex-direction:column;gap:12px">
      <div style="position:relative;aspect-ratio:16/9;border-radius:var(--radius-lg);overflow:hidden;background:linear-gradient(135deg, var(--color-neutral-800), var(--color-neutral-900));display:grid;place-items:center">
        <img
          v-if="meta.thumbnail && !thumbFailed"
          :src="meta.thumbnail"
          alt=""
          referrerpolicy="no-referrer"
          style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"
          @error="thumbFailed = true"
        />
        <div
          :style="{ background: meta.thumbnail && !thumbFailed ? 'color-mix(in srgb, var(--color-bg) 55%, transparent)' : 'transparent' }"
          style="position:relative;width:54px;height:54px;border-radius:27px;border:1px solid var(--color-accent);display:grid;place-items:center;color:var(--color-accent);box-shadow:0 0 30px color-mix(in srgb, var(--color-accent) 40%, transparent)"
        >
          <Icon name="play" :size="20" />
        </div>
        <span class="tag tag-accent" style="position:absolute;left:10px;top:10px">{{ meta.platformName }}</span>
        <span v-if="meta.duration" class="tag tag-neutral" style="position:absolute;right:10px;bottom:10px">{{ meta.duration }}</span>
      </div>
      <div>
        <div style="font-size:17px;font-weight:500;line-height:1.3;text-wrap:pretty">{{ meta.title }}</div>
        <div style="font-size:13px;color:var(--color-neutral-500);margin-top:4px">{{ meta.author }}</div>
      </div>
    </div>

    <div v-if="isPlaylist" style="display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <h6 style="margin:0;color:var(--color-neutral-500)">{{ selectedCount }} de {{ state.plSel.length }} seleccionados</h6>
        <button class="btn btn-ghost" style="font-size:13px" @click="togglePlaylistAll">
          {{ selectedCount === state.plSel.length ? 'Ninguno' : 'Todos' }}
        </button>
      </div>
      <div style="display:flex;flex-direction:column;border-radius:var(--radius-lg);background:var(--color-surface);overflow:hidden">
        <button
          v-for="(entry, i) in state.analysis.entries"
          :key="entry.url"
          :style="{ borderTop: divider(i) }"
          class="reset" style="cursor:pointer;display:flex;align-items:center;gap:12px;padding:0 14px;min-height:48px"
          @click="togglePlaylistItem(i)"
        >
          <span
            :style="{ border: '1.5px solid ' + pick('check', state.plSel[i]).border, background: pick('check', state.plSel[i]).bg }"
            style="width:20px;height:20px;flex:none;border-radius:6px;display:grid;place-items:center;color:var(--color-bg)"
          >
            <span :style="{ opacity: pick('check', state.plSel[i]).tick }" style="display:flex"><Icon name="check" :size="12" /></span>
          </span>
          <span style="font-size:12px;color:var(--color-neutral-600);width:18px">{{ String(i + 1).padStart(2, '0') }}</span>
          <span style="flex:1;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ entry.title }}</span>
          <span v-if="entry.duration" style="font-size:12px;color:var(--color-neutral-500)">{{ Math.floor(entry.duration / 60) }}:{{ String(entry.duration % 60).padStart(2, '0') }}</span>
        </button>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;padding:4px;border-radius:var(--radius-lg);background:var(--color-surface);gap:4px">
      <button
        v-for="[id, label] in modes"
        :key="id"
        :disabled="modeDisabled(id)"
        :style="{ color: pick('mode', state.mode === id).color, boxShadow: pick('mode', state.mode === id).shadow, opacity: modeDisabled(id) ? 0.4 : 1 }"
        class="reset" style="cursor:pointer;height:40px;display:flex;align-items:center;justify-content:center;border-radius:var(--radius-md);font-size:14px;font-weight:500"
        @click="setMode(id)"
      >{{ label }}</button>
    </div>

    <div style="display:flex;flex-direction:column;gap:8px">
      <h6 style="margin:0;color:var(--color-neutral-500)">Calidad</h6>
      <div style="display:flex;flex-direction:column;border-radius:var(--radius-lg);background:var(--color-surface);overflow:hidden">
        <button
          v-for="(q, i) in qualities"
          :key="q.id"
          :style="{ borderTop: divider(i) }"
          class="reset" style="cursor:pointer;display:flex;align-items:center;gap:12px;padding:0 14px;min-height:50px"
          @click="setQuality(q.id)"
        >
          <span
            :style="{ border: '1.5px solid ' + pick('q', q.id === selectedQuality?.id).ring, background: pick('q', q.id === selectedQuality?.id).dot }"
            style="width:18px;height:18px;border-radius:9px;flex:none;box-shadow:inset 0 0 0 4px var(--color-surface)"
          ></span>
          <span style="flex:1;font-size:14px">{{ q.label }} <span style="color:var(--color-neutral-500)">· {{ q.sub }}</span></span>
          <span v-if="q.note" class="tag tag-accent" style="padding:2px 8px;font-size:10px">{{ q.note }}</span>
          <span style="font-size:13px;color:var(--color-neutral-500);min-width:56px;text-align:right">{{ sizeText(q) }}</span>
        </button>
      </div>
    </div>

    <div v-if="fpsOptions.length" style="display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <h6 style="margin:0;color:var(--color-neutral-500)">Fotogramas</h6>
        <span style="font-size:11px;color:var(--color-neutral-600)">Disponible en {{ selectedQuality.id }}p</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));padding:4px;border-radius:var(--radius-lg);background:var(--color-surface);gap:4px">
        <button
          v-for="n in fpsOptions"
          :key="n"
          :style="{ color: pick('mode', n === effectiveFps).color, boxShadow: pick('mode', n === effectiveFps).shadow }"
          class="reset" style="cursor:pointer;height:44px;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:var(--radius-md)"
          @click="setFps(n)"
        >
          <span style="font-size:14px;font-weight:500">{{ n }} fps</span>
          <span style="font-size:10px;color:var(--color-neutral-500)">{{ n === 60 ? 'Fluido · +40% tamaño' : 'Estándar' }}</span>
        </button>
      </div>
    </div>

    <div style="display:flex;flex-direction:column;gap:8px">
      <h6 style="margin:0;color:var(--color-neutral-500)">Formato</h6>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        <button
          v-for="f in formats"
          :key="f"
          :style="{ border: '1px solid ' + pick('fmt', state.format === f).border, color: pick('fmt', state.format === f).color, background: pick('fmt', state.format === f).bg }"
          class="reset" style="cursor:pointer;height:36px;padding:0 16px;display:flex;align-items:center;border-radius:18px;font-size:13px;font-weight:500"
          @click="setFormat(f)"
        >{{ f }}</button>
      </div>
      <p v-if="showHdNote" style="margin:0;font-size:12px;color:var(--color-neutral-500)">
        YouTube no ofrece 4K en H.264. Clipo baja el 4K real y lo convierte al terminar para que Fotos lo acepte: tarda más y el archivo final pesa más que el estimado. Con 1080p no hace falta.
      </p>
    </div>
  </div>
</template>
