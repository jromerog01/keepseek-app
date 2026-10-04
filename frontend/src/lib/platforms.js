export const PLATFORMS = [
  { id: 'youtube', name: 'YouTube', mono: 'YT', re: /youtu\.?be/, ph: 'youtube.com/watch?v=…' },
  { id: 'instagram', name: 'Instagram', mono: 'IG', re: /instagram|instagr\.am/, ph: 'instagram.com/reel/…' },
  { id: 'facebook', name: 'Facebook', mono: 'FB', re: /facebook|fb\.watch/, ph: 'fb.watch/…' },
  { id: 'tiktok', name: 'TikTok', mono: 'TT', re: /tiktok/, ph: 'tiktok.com/@usuario/video/…' },
  { id: 'x', name: 'X', mono: 'X', re: /(^|\/\/|\.)(x|twitter)\.com/, ph: 'x.com/usuario/status/…' },
  { id: 'vimeo', name: 'Vimeo', mono: 'VI', re: /vimeo/, ph: 'vimeo.com/…' },
  { id: 'reddit', name: 'Reddit', mono: 'RD', re: /reddit|redd\.it/, ph: 'reddit.com/r/…' },
  { id: 'soundcloud', name: 'SoundCloud', mono: 'SC', re: /soundcloud/, ph: 'soundcloud.com/…' },
  { id: 'other', name: 'Otros', mono: '+', re: null, ph: 'Cualquier enlace compatible' },
]

export const DEFAULT_PLACEHOLDER = 'Pega un enlace o playlist'

export const platformById = (id) => PLATFORMS.find((p) => p.id === id) || null

export function detect(url) {
  if (!url) return null
  const lowered = url.toLowerCase()
  const match = PLATFORMS.find((p) => p.re && p.re.test(lowered))
  return match ? match.id : 'other'
}

export const isPlaylistUrl = (url) => /list=|\/sets\//.test(url || '')
