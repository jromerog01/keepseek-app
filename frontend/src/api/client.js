export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

let unauthorizedHandler = () => {}
export const onUnauthorized = (handler) => { unauthorizedHandler = handler }

async function request(path, { method = 'GET', body, signal } = {}) {
  let response
  try {
    response = await fetch('/api' + path, {
      method,
      credentials: 'same-origin',
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
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
  fileUrl: (id) => `/api/jobs/${id}/file`,
}
