export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

let unauthorizedHandler = () => {}
export const onUnauthorized = (handler) => { unauthorizedHandler = handler }

// Modelo del teléfono en Android (Chrome, Edge, Samsung Internet…): el User-Agent ya no lo trae
const deviceModel = (async () => {
  try {
    const data = navigator.userAgentData
    if (!data || data.platform !== 'Android') return null
    const { model } = await data.getHighEntropyValues(['model'])
    return model?.trim() || null
  } catch {
    return null
  }
})()

async function request(path, { method = 'GET', body, signal } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method === 'POST') {
    const model = await deviceModel
    if (model) headers['X-Device-Model'] = model
  }
  let response
  try {
    response = await fetch('/api' + path, {
      method,
      credentials: 'same-origin',
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError(0, 'Sin conexión con el servidor')
  }

  if (response.status === 401 && path !== '/auth/login' && path !== '/auth/me') {
    unauthorizedHandler()
    throw new ApiError(401, 'Sesión expirada')
  }

  if (!response.ok) {
    let detail = null
    try { detail = (await response.json()).detail } catch { /* sin cuerpo JSON */ }
    throw new ApiError(response.status, typeof detail === 'string' ? detail : 'Error del servidor')
  }

  return response.status === 204 ? null : response.json()
}

export const api = {
  me: () => request('/auth/me'),
  login: (token) => request('/auth/login', { method: 'POST', body: { token } }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  system: () => request('/system'),
  analyze: (url) => request('/analyze', { method: 'POST', body: { url } }),
  createJobs: (payload) => request('/jobs', { method: 'POST', body: payload }),
  listJobs: () => request('/jobs'),
  pause: (id) => request(`/jobs/${id}/pause`, { method: 'POST' }),
  resume: (id) => request(`/jobs/${id}/resume`, { method: 'POST' }),
  remove: (id) => request(`/jobs/${id}`, { method: 'DELETE' }),
  pauseAll: () => request('/jobs/pause-all', { method: 'POST' }),
  resumeAll: () => request('/jobs/resume-all', { method: 'POST' }),
  clearFinished: () => request('/jobs?status=done', { method: 'DELETE' }),
  listInvites: () => request('/invites'),
  createInvite: (label, days) => request('/invites', { method: 'POST', body: { label, days } }),
  revokeInvite: (id) => request(`/invites/${id}`, { method: 'DELETE' }),
  deleteInvite: (id) => request(`/invites/${id}/purge`, { method: 'DELETE' }),
  deleteInactiveInvites: () => request('/invites', { method: 'DELETE' }),
  fileUrl: (id) => `/api/jobs/${id}/file`,
}
