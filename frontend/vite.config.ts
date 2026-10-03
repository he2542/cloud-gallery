import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const configuredBase = process.env.VITE_BASE_PATH || '/'
if (!configuredBase.startsWith('/') || configuredBase.startsWith('//') || configuredBase.includes('?') || configuredBase.includes('#')) {
  throw new Error('VITE_BASE_PATH must be an absolute URL path')
}
const base = configuredBase.endsWith('/') ? configuredBase : configuredBase + '/'
const apiPath = base + 'api'
export default defineConfig({
  plugins: [vue()],
  base,
  server: { port: 5173, strictPort: true, proxy: { [apiPath]: {
    target: process.env.GALLERY_API_TARGET || 'http://127.0.0.1:8040', changeOrigin: true,
    rewrite: path => '/api' + path.slice(apiPath.length),
  } } },
})
