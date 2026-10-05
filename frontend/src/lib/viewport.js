const MAX_GAP_PX = 100

export function computeAppHeight({ standalone, innerWidth, innerHeight, screenHeight }) {
  const portrait = innerHeight > innerWidth
  const gap = screenHeight - innerHeight
  if (standalone && portrait && gap > 1 && gap < MAX_GAP_PX) return `${screenHeight}px`
  return '100%'
}

export function fitAppToScreen() {
  const standalone = window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches
  const height = computeAppHeight({
    standalone,
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    screenHeight: window.screen.height,
  })
  document.documentElement.style.setProperty('--app-h', height)
}

export function watchAppHeight() {
  fitAppToScreen()
  window.addEventListener('resize', fitAppToScreen)
  window.addEventListener('orientationchange', fitAppToScreen)
  document.addEventListener('visibilitychange', fitAppToScreen)
}
