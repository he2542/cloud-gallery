<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Grid2X2, List, Lock, ImagePlus, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { api, imageUrl, formatBytes, dateLabel } from '../api'
import { requestUpload, session } from '../session'
import PictureDialog from '../components/PictureDialog.vue'
import type { Picture, PicturePage, Tag } from '../types'
const route = useRoute(), router = useRouter()
const items = ref<Picture[]>([]), tags = ref<Tag[]>([]), total = ref(0), page = ref(1), loading = ref(true), error = ref(''), list = ref(false), selected = ref<Picture | null>(null)
const title = computed(() => route.query.space ? session.spaces.find(s => String(s.id) === route.query.space)?.name ?? '空间图库' : '全部图片')
let sequence = 0
async function load() {
  const current = ++sequence; loading.value = true; error.value = ''
  const params = new URLSearchParams({ page: String(page.value), size: '24' })
  if (route.query.q) params.set('q', String(route.query.q))
  if (route.query.tag) params.set('tag', String(route.query.tag))
  if (route.query.space) params.set('space_id', String(route.query.space))
  try {
    const [result, allTags] = await Promise.all([api<PicturePage>(`/pictures?${params}`), api<Tag[]>('/tags')])
    if (current !== sequence) return
    const lastPage = Math.max(1, Math.ceil(result.total / 24))
    if (page.value > lastPage) { page.value = lastPage; return }
    items.value = result.items; total.value = result.total; tags.value = allTags
  }
  catch (e) { if (current === sequence) { error.value = (e as Error).message; items.value = []; tags.value = []; total.value = 0 } } finally { if (current === sequence) loading.value = false }
}
watch(() => route.query, () => { page.value = 1; load() }, { immediate: true })
watch(() => session.revision, load)
watch(() => session.user?.id, () => { sequence++; selected.value = null; items.value = []; tags.value = []; total.value = 0; page.value = 1; load() }, { flush: 'sync' })
watch(page, load)
function filter(tag: string) { router.push({ path: '/', query: { ...route.query, tag: tag || undefined } }) }
</script>
<template>
  <div class="page-title"><div><p class="eyebrow">你的图片收藏</p><h1>{{ title }} <span>{{ total }} 张图片</span></h1></div><button v-if="route.query.space" class="button" @click="router.push('/')">查看全部</button></div>
  <div class="gallery-tools"><div class="filters"><button :class="['filter', { active: !route.query.tag }]" @click="filter('')">全部</button><button v-for="tag in tags.slice(0, 6)" :key="tag.name" :class="['filter', { active: route.query.tag === tag.name }]" @click="filter(tag.name)">{{ tag.name }}</button></div><div class="view-controls"><span>最新上传</span><button class="icon-button" :class="{ selected: !list }" aria-label="网格视图" :aria-pressed="!list" @click="list = false"><Grid2X2 :size="18" /></button><button class="icon-button" :class="{ selected: list }" aria-label="列表视图" :aria-pressed="list" @click="list = true"><List :size="19" /></button></div></div>
  <p v-if="route.query.q" class="search-summary">搜索“{{ route.query.q }}”的结果 <button class="text-button" @click="router.push({ path: '/', query: { ...route.query, q: undefined } })">清除</button></p>
  <div v-if="error" class="error-banner" role="alert">{{ error }} <button class="text-button" @click="load">重试</button></div>
  <div v-if="loading" class="picture-grid" aria-label="图片加载中"><div v-for="n in 8" :key="n" class="skeleton" /></div>
  <div v-else-if="!items.length" class="empty-state"><ImagePlus :size="44" /><h2>{{ route.query.q || route.query.tag ? '没有找到匹配图片' : '这里还没有图片' }}</h2><p>{{ route.query.q || route.query.tag ? '试试其他名称或标签。' : '上传第一张图片，开始整理你的图库。' }}</p><button class="button primary" @click="requestUpload">上传图片</button></div>
  <div v-else :class="['picture-grid', { 'picture-list': list }]">
    <button v-for="picture in items" :key="picture.id" class="picture-card" @click="selected = picture">
      <div class="picture-cover"><img :src="imageUrl(picture.id)" :alt="picture.title" loading="lazy" /><span v-if="!picture.is_public" class="lock-badge" aria-label="私有图片"><Lock :size="14" /></span></div>
      <div class="picture-info"><h3>{{ picture.title }}</h3><div class="tag-row"><span v-for="tag in picture.tags.slice(0, 3)" :key="tag">{{ tag }}</span></div><div class="picture-meta"><span>{{ dateLabel(picture.created_at) }}</span><span>{{ formatBytes(picture.byte_size) }}</span></div></div>
    </button>
  </div>
  <div v-if="total > 24" class="pagination"><button class="button" :disabled="page === 1 || loading" @click="page--"><ChevronLeft :size="16" />上一页</button><span>{{ page }} / {{ Math.ceil(total / 24) }}</span><button class="button" :disabled="page * 24 >= total || loading" @click="page++">下一页<ChevronRight :size="16" /></button></div>
  <PictureDialog v-if="selected" :picture="selected" @close="selected = null" />
</template>
