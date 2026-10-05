const MAX_DEFICIT_PX = 100

// En la PWA instalada de iOS (barra de estado translúcida) window.innerHeight puede ser
// menor que la pantalla: lo que cae fuera de ese alto no se dibuja. Devuelve cuánto falta.
export function computeDeficit({ standalone, innerWidth, innerHeight, screenHeight }) {
  const portrait = innerHeight > innerWidth
  const gap = screenHeight - innerHeight
  return standalone && portrait && gap > 1 && gap < MAX_DEFICIT_PX ? gap : 0
}

function applyDeficit() {
  const standalone = window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches
  const deficit = computeDeficit({
    standalone,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    screenHeight: window.screen.height,
  })
  document.documentElement.style.setProperty('--deficit', `${deficit}px`)
}

export function watchViewport() {
  applyDeficit()
  window.addEventListener('resize', applyDeficit)
  window.addEventListener('orientationchange', applyDeficit)
  window.addEventListener('pageshow', applyDeficit)
  document.addEventListener('visibilitychange', applyDeficit)
}
