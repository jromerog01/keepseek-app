const A = 'var(--color-accent)'

export const T = {
  tile: {
    on: {
      bg: 'color-mix(in srgb, var(--color-accent) 10%, var(--color-surface))',
      shadow: '0 0 0 1px ' + A + ', 0 0 20px color-mix(in srgb, var(--color-accent) 25%, transparent)',
      monoBg: 'var(--color-accent-800)',
      monoColor: 'var(--color-accent-200)',
    },
    off: { bg: 'var(--color-surface)', shadow: 'none', monoBg: 'var(--color-neutral-900)', monoColor: 'var(--color-neutral-400)' },
  },
  mode: {
    on: { color: A, shadow: 'inset 0 0 0 1px ' + A },
    off: { color: 'var(--color-neutral-400)', shadow: 'none' },
  },
  q: {
    on: { ring: A, dot: A },
    off: { ring: 'var(--color-neutral-700)', dot: 'transparent' },
  },
  fmt: {
    on: { border: A, color: 'var(--color-accent-200)', bg: 'var(--color-accent-900)' },
    off: { border: 'var(--color-neutral-800)', color: 'var(--color-neutral-400)', bg: 'transparent' },
  },
  check: {
    on: { border: A, bg: A, tick: 1 },
    off: { border: 'var(--color-neutral-700)', bg: 'transparent', tick: 0 },
  },
  stage: {
    done: { color: 'var(--color-neutral-400)', dot: A, ring: A, glow: 'none' },
    active: { color: 'var(--color-text)', dot: 'transparent', ring: A, glow: '0 0 10px ' + A },
    pending: { color: 'var(--color-neutral-600)', dot: 'transparent', ring: 'var(--color-neutral-700)', glow: 'none' },
  },
  tab: {
    on: { color: A },
    off: { color: 'var(--color-neutral-500)' },
  },
}

export const DIVIDER = '1px solid var(--color-neutral-800)'

export const pick = (group, on) => T[group][on ? 'on' : 'off']
export const divider = (index) => (index === 0 ? 'none' : DIVIDER)

const GLOW_DARK = {
  youtube: 'oklch(0.31 0.065 25)',
  instagram: 'oklch(0.38 0.1 55)',
  facebook: 'oklch(0.36 0.11 262)',
  tiktok: 'oklch(0.36 0.08 195)',
  x: 'oklch(0.32 0.005 60)',
  vimeo: 'oklch(0.36 0.09 225)',
  reddit: 'oklch(0.37 0.12 40)',
  soundcloud: 'oklch(0.38 0.12 55)',
  other: 'oklch(0.3 0.03 300)',
  none: 'oklch(0.44 0.07 235)',
}

const GLOW_LIGHT = {
  youtube: 'oklch(0.8 0.11 25)',
  instagram: 'oklch(0.83 0.12 55)',
  facebook: 'oklch(0.8 0.1 262)',
  tiktok: 'oklch(0.82 0.09 195)',
  x: 'oklch(0.8 0.015 270)',
  vimeo: 'oklch(0.82 0.09 225)',
  reddit: 'oklch(0.82 0.11 45)',
  soundcloud: 'oklch(0.84 0.11 60)',
  other: 'oklch(0.8 0.09 290)',
  none: 'oklch(0.84 0.08 235)',
}

export function glowFor(platform, theme) {
  const light = theme === 'light'
  const table = light ? GLOW_LIGHT : GLOW_DARK
  const key = platform && table[platform] ? platform : 'none'
  let glow = table[key]
  let glow2 = glow

  if (key === 'instagram') {
    glow2 = light ? 'oklch(0.79 0.12 320)' : 'oklch(0.36 0.1 315)'
  }
  if (key === 'tiktok') {
    glow = light ? 'oklch(0.6 0.03 300)' : 'oklch(0.13 0.01 300)'
    glow2 = light ? 'oklch(0.76 0.13 305)' : 'oklch(0.34 0.13 305)'
  }
  return { glow, glow2 }
}
