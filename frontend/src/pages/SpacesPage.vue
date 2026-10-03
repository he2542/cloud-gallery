<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { FolderLock, FolderOpen, Plus, ArrowUpRight, Pencil } from 'lucide-vue-next'
import AppDialog from '../components/AppDialog.vue'
import { api, formatBytes } from '../api'
import { changed, session } from '../session'
import type { Space } from '../types'
const router = useRouter(), open = ref(false), name = ref(''), isPublic = ref(false), editing = ref<Space | null>(null), error = ref(''), busy = ref(false)
const own = computed(() => session.spaces.filter(s => s.owner_id === session.user?.id))
watch(() => session.user?.id, () => { open.value = false; editing.value = null; name.value = '' }, { flush: 'sync' })
function dialog(space?: Space) { editing.value = space ?? null; name.value = space?.name ?? ''; isPublic.value = space?.is_public ?? false; error.value = ''; open.value = true }
async function save() {
  busy.value = true; error.value = ''
  try { await api(editing.value ? `/spaces/${editing.value.id}` : '/spaces', { method: editing.value ? 'PATCH' : 'POST', body: JSON.stringify({ name: name.value, is_public: isPublic.value }) }); await changed(); open.value = false }
  catch (e) { error.value = (e as Error).message } finally { busy.value = false }
}
</script>
<template>
  <div class="page-title"><div><p class="eyebrow">按主题整理你的收藏</p><h1>我的空间 <span>{{ own.length }} 个空间</span></h1></div><button v-if="session.user" class="button primary" @click="dialog()"><Plus :size="18" />新建空间</button></div>
  <div v-if="!session.user" class="empty-state"><FolderLock :size="44" /><h2>为你的图片保留一个私有空间</h2><p>登录后创建空间，只有你能查看私有图片。</p><button class="button primary" @click="session.authOpen = true">登录并管理空间</button></div>
  <div v-else class="space-grid"><article v-for="space in own" :key="space.id" class="space-card"><div class="space-top"><FolderOpen v-if="space.is_public" :size="34" /><FolderLock v-else :size="34" /><button class="icon-button" :aria-label="`编辑${space.name}`" @click="dialog(space)"><Pencil :size="17" /></button></div><h2>{{ space.name }}</h2><span class="privacy">{{ space.is_public ? '公开空间' : '私有空间 · 仅自己可见' }}</span><div class="space-stats"><span>{{ space.picture_count }} 张图片</span><span>{{ formatBytes(space.used_bytes) }}</span></div><button class="button" @click="router.push({ path: '/', query: { space: space.id } })">打开空间<ArrowUpRight :size="16" /></button></article><button class="new-space" @click="dialog()"><Plus :size="28" /><span>新建一个空间</span></button></div>
  <AppDialog v-if="open" :title="editing ? '编辑空间' : '新建空间'" @close="!busy && (open = false)"><form class="form-stack" @submit.prevent="save"><label>空间名称<input v-model="name" required maxlength="60" placeholder="例如：旅行记录、设计灵感" /></label><label>可见范围<select v-model="isPublic"><option :value="false">私有 · 仅自己可见</option><option :value="true">公开 · 访客可以浏览</option></select></label><p v-if="isPublic" class="hint">公开后，这个空间内的所有图片都可被访客查看。</p><p v-if="error" class="error" role="alert">{{ error }}</p><button class="button primary" :disabled="busy">{{ busy ? '保存中…' : '保存空间' }}</button></form></AppDialog>
</template>
