<script setup>
import { onMounted, ref } from 'vue'
import { fmtDateTime } from '../lib/format.js'
import { useClipo } from '../store/useClipo.js'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Icon from '../components/Icon.vue'

const { state, createInvite, revokeInvite, dismissNewInvite, refreshInvites, flash } = useClipo()

const DURATIONS = [[1, '1 día'], [7, '7 días'], [30, '30 días']]
const label = ref('')
const days = ref(7)
const busy = ref(false)
const revoking = ref(null)

onMounted(refreshInvites)

async function submit() {
  const name = label.value.trim()
  if (!name || busy.value) return
  busy.value = true
  if (await createInvite(name, days.value)) label.value = ''
  busy.value = false
}

async function copyToken() {
  try {
    await navigator.clipboard.writeText(state.newInvite.token)
    flash('Token copiado')
  } catch {
    flash('No se pudo copiar. Selecciónalo a mano.')
  }
}

async function confirmRevoke() {
  const invite = revoking.value
  revoking.value = null
  await revokeInvite(invite)
}

const statusOf = (invite) => {
  if (invite.revoked) return 'Revocado'
  return invite.active ? 'Activo' : 'Expirado'
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

    <!-- Token recién creado: solo se muestra una vez -->
    <div v-if="state.newInvite" class="card" style="padding:14px;gap:10px;border-radius:var(--radius-lg);border:1px solid var(--color-accent)">
      <div style="font-size:13px;color:var(--color-neutral-400)">
        Token para <b>{{ state.newInvite.label }}</b>. Cópialo ahora: no se vuelve a mostrar.
      </div>
      <code style="display:block;padding:10px 12px;border-radius:var(--radius-md);background:var(--color-surface);font-size:14px;word-break:break-all;user-select:all">{{ state.newInvite.token }}</code>
      <div style="display:flex;gap:8px">
        <button class="btn btn-primary" style="flex:1;height:42px;border-radius:var(--radius-lg)" @click="copyToken">Copiar token</button>
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
      <h6 style="margin:0;color:var(--color-neutral-500)">Accesos creados · {{ state.invites.length }}</h6>

      <div
        v-if="!state.invites.length"
        style="padding:28px 16px;text-align:center;border-radius:var(--radius-lg);border:1px dashed var(--color-neutral-800);font-size:13px;color:var(--color-neutral-500)"
      >Todavía no has creado accesos.</div>

      <div
        v-for="invite in state.invites"
        :key="invite.id"
        class="card"
        :style="{ opacity: invite.active ? 1 : 0.6 }"
        style="padding:12px 14px;gap:12px;border-radius:var(--radius-lg);flex-direction:row;align-items:center"
      >
        <span style="flex:none;display:grid;place-items:center;color:var(--color-accent)"><Icon name="key" :size="22" /></span>
        <span style="flex:1;min-width:0;display:flex;flex-direction:column;gap:2px">
          <span style="font-size:14px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ invite.label }}</span>
          <span style="font-size:12px;color:var(--color-neutral-500)">
            {{ statusOf(invite) }} · {{ invite.active ? 'vence' : 'venció' }} {{ fmtDateTime(invite.expires_at) }}
          </span>
          <span style="font-size:11px;color:var(--color-neutral-600)">
            {{ invite.last_used_at ? 'Último uso ' + fmtDateTime(invite.last_used_at) : 'Sin usar' }}
          </span>
        </span>
        <button
          v-if="!invite.revoked"
          class="btn btn-ghost btn-icon"
          :aria-label="'Revocar acceso de ' + invite.label"
          style="flex:none"
          @click="revoking = invite"
        >
          <Icon name="trash" :size="18" />
        </button>
      </div>
    </section>

    <ConfirmDialog
      :open="!!revoking"
      title="¿Revocar este acceso?"
      :message="revoking ? `${revoking.label} perderá el acceso de inmediato.` : ''"
      confirm-label="Revocar"
      danger
      @confirm="confirmRevoke"
      @cancel="revoking = null"
    />
  </div>
</template>
