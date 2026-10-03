<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Images, Grid2X2, FolderLock, Tag, Search, Upload, LogOut, Menu, X, ChevronRight, ArrowUpRight } from 'lucide-vue-next'
import AuthDialog from './components/AuthDialog.vue'
import UploadDialog from './components/UploadDialog.vue'
import { api, formatBytes } from './api'
import { changed, clearSession, refreshSession, requestUpload, session } from './session'
const route = useRoute(), router = useRouter(), search = ref(''), error = ref(''), ready = ref(false), mobileOpen = ref(false)
async function initialize() { try { await refreshSession(); error.value = ''; ready.value = true } catch { error.value = '暂时无法连接图库服务，请确认后端已启动。' } }
async function logout() { try { await api('/auth/logout', { method: 'POST' }); clearSession(); await router.push('/'); await changed(); error.value = '' } catch (e) { error.value = (e as Error).message } }
function searchPictures() { router.push({ path: '/', query: { q: search.value || undefined } }) }
watch(() => route.query.q, value => { search.value = value ? String(value) : '' }, { immediate: true })
onMounted(initialize)
</script>
<template>
  <div class="app-shell">
    <aside :class="['sidebar', { 'mobile-open': mobileOpen }]">
      <RouterLink to="/" class="brand" @click="mobileOpen = false"><span class="brand-icon"><Images :size="23" /></span><strong>云图库<span>CLOUD GALLERY</span></strong></RouterLink>
      <button v-if="mobileOpen" class="mobile-close icon-button" aria-label="关闭导航" @click="mobileOpen = false"><X :size="20" /></button>
      <p class="nav-label">图库管理</p>
      <nav><RouterLink to="/" :class="{ active: route.path === '/' }" @click="mobileOpen = false"><Grid2X2 :size="18" />全部图片<ChevronRight :size="14" /></RouterLink><RouterLink to="/spaces" :class="{ active: route.path === '/spaces' }" @click="mobileOpen = false"><FolderLock :size="18" />我的空间</RouterLink><RouterLink to="/tags" :class="{ active: route.path === '/tags' }" @click="mobileOpen = false"><Tag :size="18" />标签索引</RouterLink></nav>
      <div class="sidebar-bottom"><div class="storage"><div><span>可见图片用量</span><strong>{{ formatBytes(session.visibleBytes) }}</strong></div><div class="storage-track"><div :style="{ width: `${Math.min(100, session.visibleBytes / session.quotaBytes * 100)}%` }" /></div><p>图库总配额 {{ formatBytes(session.quotaBytes) }}</p></div><button class="account" @click="!session.user && (session.authOpen = true)"><span class="avatar">{{ session.user?.username.slice(0, 1).toUpperCase() || '访' }}</span><span>{{ session.user?.username || '访客浏览' }}<small>{{ session.user ? '你的图片，妥善收藏' : '登录后管理私有图片' }}</small></span></button><button v-if="session.user" class="logout" @click="logout"><LogOut :size="15" />退出登录</button></div>
    </aside>
    <div class="workspace">
      <header class="topbar"><button class="mobile-menu icon-button" aria-label="打开导航" @click="mobileOpen = true"><Menu :size="21" /></button><form class="search-box" @submit.prevent="searchPictures"><Search :size="19" /><input v-model="search" aria-label="搜索图片" placeholder="搜索图片名称或标签" maxlength="100" /><button type="submit" aria-label="执行搜索"><ArrowUpRight :size="18" /></button></form><div class="top-actions"><button v-if="!session.user" class="button login-button" @click="session.authOpen = true">{{ session.setupRequired ? '创建账户' : '登录' }}</button><button class="button primary" @click="requestUpload"><Upload :size="17" /><span>上传图片</span></button></div></header>
      <main><div v-if="error" class="error-banner" role="alert">{{ error }}<button class="text-button" @click="initialize">重试连接</button></div><RouterView v-if="ready" /><div v-else-if="!error" class="empty-state"><p>正在打开你的图库…</p></div></main>
      <footer><span>云图库</span><span>让每一张图片，都有自己的位置。</span></footer>
    </div>
    <AuthDialog v-if="session.authOpen" /><UploadDialog v-if="session.uploadOpen && session.user" />
  </div>
</template>
