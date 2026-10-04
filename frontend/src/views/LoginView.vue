<script setup>
import { ref } from 'vue'
import { useClipo } from '../store/useClipo.js'
import Icon from '../components/Icon.vue'

const { state, login } = useClipo()
const token = ref('')

const submit = () => {
  if (token.value.trim()) login(token.value.trim())
}
</script>

<template>
  <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:32px 22px">
    <form style="width:100%;max-width:360px;display:flex;flex-direction:column;gap:22px" @submit.prevent="submit">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:32px;height:32px;border-radius:var(--radius-md);border:1px solid var(--color-accent);display:grid;place-items:center;color:var(--color-accent);box-shadow:0 0 18px color-mix(in srgb, var(--color-accent) 35%, transparent)">
          <Icon name="download" :size="18" />
        </div>
        <span style="font-size:18px;font-weight:500">Clipo</span>
      </div>

      <div>
        <h2 style="font-size:30px;margin:0 0 6px;text-wrap:pretty">Acceso</h2>
        <p style="margin:0;font-size:14px;color:var(--color-neutral-500)">Ingresa tu token para usar la app.</p>
      </div>

      <div style="display:flex;flex-direction:column;gap:10px">
        <input
          v-model="token"
          class="input"
          type="password"
          autocomplete="current-password"
          autocapitalize="off"
          placeholder="Token de acceso"
          style="min-height:52px;padding:0 14px;font-size:16px;border-radius:var(--radius-lg)"
        />
        <div v-if="state.loginError" style="font-size:12px;color:var(--color-accent-300)">{{ state.loginError }}</div>
        <button
          class="btn btn-primary"
          type="submit"
          :disabled="!token.trim() || state.loginBusy"
          style="height:52px;border-radius:var(--radius-lg);font-size:15px;box-shadow:0 0 24px color-mix(in srgb, var(--color-accent) 22%, transparent)"
        >
          <span
            v-if="state.loginBusy"
            style="width:16px;height:16px;border-radius:8px;border:2px solid var(--color-accent-800);border-top-color:var(--color-accent);animation:spin .8s linear infinite"
          ></span>
          {{ state.loginBusy ? 'Entrando…' : 'Entrar' }}
        </button>
      </div>
    </form>
  </div>
</template>
