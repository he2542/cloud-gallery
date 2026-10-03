let csrf = ''
export function setCsrf(value: string) { csrf = value }
export const apiBase = `${import.meta.env.BASE_URL}api`
export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); this.name = 'ApiError' }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (options.method && !['GET', 'HEAD'].includes(options.method.toUpperCase())) headers.set('X-CSRF-Token', csrf)
  const response = await fetch(`${apiBase}${path}`, { ...options, headers, credentials: 'same-origin' })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    if (response.status === 401 && !['/auth/login', '/auth/setup'].includes(path)) window.dispatchEvent(new Event('gallery:unauthorized'))
    throw new ApiError(typeof body.detail === 'string' ? body.detail : `请求失败（${response.status}），请检查输入后重试`, response.status)
  }
  return response.status === 204 ? undefined as T : response.json()
}
export const imageUrl = (id: string, thumb = true) => `${apiBase}/pictures/${encodeURIComponent(id)}/content?thumb=${thumb}`
export const formatBytes = (bytes: number) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(0)} KB` : bytes < 1024 ** 3 ? `${(bytes / 1024 ** 2).toFixed(1)} MB` : `${(bytes / 1024 ** 3).toFixed(1)} GB`
export const dateLabel = (timestamp: number) => new Date(timestamp * 1000).toLocaleDateString('zh-CN')
