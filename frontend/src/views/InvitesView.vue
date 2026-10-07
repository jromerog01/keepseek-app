<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { fmtDateTime, timeLeft } from '../lib/format.js'
import { useClipo } from '../store/useClipo.js'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Icon from '../components/Icon.vue'

const {
  state, createInvite, revokeInvite, deleteInvite, deleteInactiveInvites, dismissNewInvite, refreshInvites, flash,
} = useClipo()

const DURATIONS = [[1, '1 día'], [7, '7 días'], [30, '30 días']]
const label = ref('')
const days = ref(7)
const busy = ref(false)
const revealed = ref(new Set())
// { kind: 'revoke' | 'delete' | 'purge', invite? }
const confirming = ref(null)

// El tiempo restante se recalcula cada 30 s
const now = ref(Date.now())
let ticker = null
onMounted(() => {
  refreshInvites()
  ticker = window.setInterval(() => { now.value = Date.now() }, 30000)
})
onUnmounted(() => window.clearInterval(ticker))

const inactiveCount = computed(() => state.invites.filter((i) => !i.active).length)

async function submit() {
  const name = label.value.trim()
  if (!name || busy.value) return
  busy.value = true
  if (await createInvite(name, days.value)) label.value = ''
  busy.value = false
}

async function copy(token) {
  try {
    await navigator.clipboard.writeText(token)
    flash('Token copiado')
  } catch {
    flash('No se pudo copiar. Toca el token para verlo y selecciónalo a mano.')
  }
}

function toggleReveal(id) {
  const next = new Set(revealed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  revealed.value = next
}

const masked = (token) => token.slice(0, 6) + '•'.repeat(10)

const statusOf = (invite) => {
  if (invite.revoked) return 'Revocado'
  if (!invite.active) return 'Expirado'
  const left = timeLeft(invite.expires_at, now.value)
  return left ? `Quedan ${left}` : 'Expirado'
}

const dialog = computed(() => {
  const c = confirming.value
  if (!c) return { title: '', message: '', label: '' }
  if (c.kind === 'revoke') {
    return { title: '¿Revocar este acceso?', message: `${c.invite.label} perderá el acceso de inmediato.`, label: 'Revocar' }
  }
  if (c.kind === 'delete') {
    return { title: '¿Borrar este acceso?', message: `${c.invite.label} desaparecerá de la lista. Sus descargas se conservan.`, label: 'Borrar' }
  }
  return {
    title: '¿Borrar los accesos inactivos?',
    message: `Se quitarán ${inactiveCount.value} ${inactiveCount.value === 1 ? 'acceso expirado o revocado' : 'accesos expirados o revocados'}. Sus descargas se conservan.`,
    label: 'Borrar',
  }
})

async function confirmAction() {
  const c = confirming.value
  confirming.value = null
  if (c.kind === 'revoke') await revokeInvite(c.invite)
  else if (c.kind === 'delete') await deleteInvite(c.invite)
  else await deleteInactiveInvites()
}
</script>

<template>
  <div style="padding:20px 22px 32px;display:flex;flex-direction:column;gap:18px">
    <div>
      <h2 style="font-size:28px;margin:0">Accesos</h2>
      <div style="font-size:12px;color:var(--color-neutral-500);margin-top:4px;text-wrap:pretty">
        Tokens temporales para que otras personas prueben Clipo. Cada invitado solo ve lo que descarga con su token.
      </div>
    </div>

    <!-- Token recién creado -->
    <div v-if="state.newInvite" class="card" style="padding:14px;gap:10px;border-radius:var(--radius-lg);border:1px solid var(--color-accent)">
      <div style="font-size:13px;color:var(--color-neutral-400)">
        Token para <b>{{ state.newInvite.label }}</b>. También puedes copiarlo después desde la lista.
      </div>
      <code style="display:block;padding:10px 12px;border-radius:var(--radius-md);background:var(--color-surface);font-size:14px;word-break:break-all;user-select:all">{{ state.newInvite.token }}</code>
      <div style="display:flex;gap:8px">
        <button class="btn btn-primary" style="flex:1;height:42px;border-radius:var(--radius-lg)" @click="copy(state.newInvite.token)">Copiar token</button>
        <button class="btn btn-ghost" style="height:42px" @click="dismissNewInvite">Listo</button>
      </div>
    </div>

    <!-- Crear -->
    <form style="display:flex;flex-direction:column;gap:10px" @submit.prevent="submit">
      <h6 style="margin:0;color:var(--color-neutral-500)">Nuevo acceso</h6>
      <input
        v-model="label"
        class="input"
        maxlength="80"
        placeholder="Nombre de la persona"
        autocomplete="off"
        style="min-height:48px;padding:0 14px;font-size:16px;border-radius:var(--radius-lg)"
      />
      <div style="display:grid;grid-template-columns:repeat(3,1fr);padding:4px;border-radius:var(--radius-lg);background:var(--color-surface);gap:4px">
        <button
          v-for="[value, text] in DURATIONS"
          :key="value"
          type="button"
          class="reset"
          :aria-pressed="days === value"
          :style="{
            color: days === value ? 'var(--color-accent-200)' : 'var(--color-neutral-400)',
            background: days === value ? 'var(--color-accent-900)' : 'transparent',
          }"
          style="cursor:pointer;height:38px;border-radius:var(--radius-md);font-size:13px;font-weight:500"
          @click="days = value"
        >{{ text }}</button>
      </div>
      <button
        class="btn btn-primary"
        type="submit"
        :disabled="!label.trim() || busy"
        style="height:48px;border-radius:var(--radius-lg)"
      >Crear acceso</button>
    </form>

    <!-- Lista -->
    <section style="display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px">
        <h6 style="margin:0;color:var(--color-neutral-500)">Accesos creados · {{ state.invites.length }}</h6>
        <button
          v-if="inactiveCount"
          class="btn btn-ghost"
          style="font-size:12px;color:var(--color-neutral-500)"
          @click="confirming = { kind: 'purge' }"
        >Borrar inactivos ({{ inactiveCount }})</button>
      </div>

      <div
        v-if="!state.invites.length"
        style="padding:28px 16px;text-align:center;border-radius:var(--radius-lg);border:1px dashed var(--color-neutral-800);font-size:13px;color:var(--color-neutral-500)"
      >Todavía no has creado accesos.</div>

      <div
        v-for="invite in state.invites"
        :key="invite.id"
        class="card"
        style="padding:12px 14px;gap:10px;border-radius:var(--radius-lg)"
      >
        <div :style="{ opacity: invite.active ? 1 : 0.6 }" style="display:flex;align-items:center;gap:12px">
          <span style="flex:none;display:grid;place-items:center;color:var(--color-accent)"><Icon name="key" :size="22" /></span>
          <span style="flex:1;min-width:0;display:flex;flex-direction:column;gap:2px">
            <span style="font-size:14px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ invite.label }}</span>
            <span
              :style="{ color: invite.active ? 'var(--color-accent-300)' : 'var(--color-neutral-500)' }"
              style="font-size:12px"
            >{{ statusOf(invite) }} · {{ invite.active ? 'vence' : 'venció' }} {{ fmtDateTime(invite.expires_at) }}</span>
            <span style="font-size:11px;color:var(--color-neutral-600)">
              {{ invite.last_used_at ? 'Último uso ' + fmtDateTime(invite.last_used_at) : 'Sin usar' }}
            </span>
          </span>
          <button
            v-if="invite.active"
            class="btn btn-ghost"
            :aria-label="'Revocar acceso de ' + invite.label"
            style="flex:none;font-size:12px;color:var(--color-neutral-400)"
            @click="confirming = { kind: 'revoke', invite }"
          >Revocar</button>
          <button
            v-else
            class="btn btn-ghost btn-icon"
            :aria-label="'Borrar acceso de ' + invite.label"
            style="flex:none"
            @click="confirming = { kind: 'delete', invite }"
          ><Icon name="trash" :size="18" /></button>
        </div>

        <div v-if="invite.active && invite.token" style="display:flex;align-items:center;gap:8px">
          <button
            class="reset"
            :aria-label="revealed.has(invite.id) ? 'Ocultar token' : 'Mostrar token'"
            style="cursor:pointer;flex:1;min-width:0;text-align:left;padding:8px 10px;border-radius:var(--radius-md);background:var(--color-surface);font-family:var(--font-mono, monospace);font-size:13px;word-break:break-all"
            @click="toggleReveal(invite.id)"
          >{{ revealed.has(invite.id) ? invite.token : masked(invite.token) }}</button>
          <button class="btn btn-secondary" style="flex:none;height:36px;padding:0 14px;font-size:13px" @click="copy(invite.token)">Copiar</button>
        </div>
        <div v-else-if="invite.active" style="font-size:11px;color:var(--color-neutral-600)">
          Este token se creó antes de poder guardarse y ya no se puede volver a mostrar.
        </div>
      </div>
    </section>

    <ConfirmDialog
      :open="!!confirming"
      :title="dialog.title"
      :message="dialog.message"
      :confirm-label="dialog.label"
      danger
      @confirm="confirmAction"
      @cancel="confirming = null"
    />
  </div>
</template>
