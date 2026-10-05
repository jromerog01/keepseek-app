import { createApp } from 'vue'
import { registerSW } from 'virtual:pwa-register'
import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import './styles/nocturne.css'
import './styles/app.css'
import App from './App.vue'
import { watchAppHeight } from './lib/viewport.js'

watchAppHeight()
createApp(App).mount('#app')

const ONE_HOUR = 60 * 60 * 1000
registerSW({
  immediate: true,
  onRegisteredSW(_url, registration) {
    if (registration) setInterval(() => registration.update(), ONE_HOUR)
  },
})
