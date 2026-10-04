<script setup>
import { onMounted } from 'vue'
import { useClipo } from './store/useClipo.js'
import HomeView from './views/HomeView.vue'
import OptionsView from './views/OptionsView.vue'
import ProgressView from './views/ProgressView.vue'
import LibraryView from './views/LibraryView.vue'
import LoginView from './views/LoginView.vue'
import TabBar from './components/TabBar.vue'
import Toast from './components/Toast.vue'
import Icon from './components/Icon.vue'

const { state, screen, glow, summary, itemCount, boot, download } = useClipo()

onMounted(boot)
</script>

<template>
  <div class="app" :style="{ '--glow': glow.glow, '--glow2': glow.glow2 }">
    <template v-if="!state.booting">
      <LoginView v-if="!state.authed" />

      <template v-else>
        <main
          class="scr"
          style="position:absolute;top:env(safe-area-inset-top, 0px);left:0;right:0;bottom:var(--tabbar-h);overflow-y:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none"
        >
          <HomeView v-if="screen === 'home'" />
          <OptionsView v-else-if="screen === 'options'" />
          <ProgressView v-else-if="screen === 'progress'" />
          <LibraryView v-else />
        </main>

        <div
          v-if="screen === 'options'"
          style="position:absolute;left:0;right:0;bottom:var(--tabbar-h);padding:14px 22px;background:linear-gradient(to top, var(--color-bg) 70%, transparent);z-index:4"
        >
          <button
            class="btn btn-primary"
            :disabled="itemCount === 0"
            style="width:100%;height:54px;border-radius:var(--radius-lg);justify-content:space-between;padding:0 18px;background:var(--color-bg);box-shadow:0 0 28px color-mix(in srgb, var(--color-accent) 30%, transparent)"
            @click="download"
          >
            <span style="display:flex;align-items:center;gap:10px;font-size:15px">
              <Icon name="download" :size="18" />{{ state.analysis?.is_playlist ? `Descargar ${itemCount} ${itemCount === 1 ? 'video' : 'videos'}` : 'Descargar' }}
            </span>
            <span style="font-size:12px;color:var(--color-accent-300)">{{ summary }}</span>
          </button>
        </div>

        <Toast />
        <TabBar />
      </template>
    </template>
  </div>
</template>
