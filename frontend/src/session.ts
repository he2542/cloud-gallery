import { reactive } from 'vue'
import { api, setCsrf } from './api'
import type { User, Space } from './types'

export const session = reactive({ user: null as User | null, spaces: [] as Space[], setupRequired: false, visibleBytes: 0, quotaBytes: 10 * 1024 ** 3, maxUploadBytes: 10 * 1024 ** 2, maxPixels: 12000000, authOpen: false, uploadOpen: false, revision: 0 })
let generation = 0
export function clearSession(openLogin = false) {
  generation++
  session.user = null; session.spaces = []; session.visibleBytes = 0
  session.uploadOpen = false; session.authOpen = openLogin
  setCsrf(''); session.revision++
}
window.addEventListener('gallery:unauthorized', () => clearSession(true))
export async function refreshSession() {
  const current = ++generation
  const [health, auth] = await Promise.all([api<{ setup_required: boolean }>('/health'), api<{ user: User | null; csrf_token: string }>('/auth/me')])
  if (current !== generation) return
  session.setupRequired = health.setup_required
  session.user = auth.user
  setCsrf(auth.csrf_token)
  const [spaces, storage] = await Promise.all([api<Space[]>('/spaces'), api<{ visible_bytes: number; quota_bytes: number; max_upload_bytes: number; max_pixels: number }>('/storage')])
  if (current !== generation) return
  session.spaces = spaces
  session.visibleBytes = storage.visible_bytes
  session.quotaBytes = storage.quota_bytes
  session.maxUploadBytes = storage.max_upload_bytes
  session.maxPixels = storage.max_pixels
}
export async function changed() { await refreshSession(); session.revision++ }
export function requestUpload() { if (session.user) session.uploadOpen = true; else session.authOpen = true }
