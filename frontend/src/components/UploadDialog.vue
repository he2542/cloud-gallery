<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ImagePlus, UploadCloud } from 'lucide-vue-next'
import AppDialog from './AppDialog.vue'
import { api, formatBytes } from '../api'
import { changed, session } from '../session'
const spaces = computed(() => session.spaces.filter(s => s.owner_id === null || s.owner_id === session.user?.id))
const route = useRoute()
const spaceId = ref(spaces.value.find(s => String(s.id) === route.query.space)?.id ?? spaces.value.find(s => !s.is_public)?.id ?? spaces.value[0]?.id)
const file = ref<File | null>(null), title = ref(''), tags = ref(''), error = ref(''), busy = ref(false)
const picker = ref<HTMLInputElement>()
function choose(value: File | undefined) {
  error.value = ''
  if (!value) return
  file.value = null; title.value = ''
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(value.type)) { error.value = '请选择 JPG、PNG 或 WebP 图片'; return }
  if (value.size > session.maxUploadBytes) { error.value = '图片超过上传大小限制'; return }
  file.value = value; title.value = value.name.replace(/\.[^.]+$/, '').slice(0, 100)
}
async function upload() {
  if (!file.value || !spaceId.value) return
  busy.value = true; error.value = ''
  try {
    const body = new FormData(); body.append('file', file.value); body.append('space_id', String(spaceId.value)); body.append('title', title.value); body.append('tags', JSON.stringify(tags.value.split(/[,，]/).map(x => x.trim()).filter(Boolean)))
    await api('/pictures', { method: 'POST', body }); await changed(); session.uploadOpen = false
  } catch (e) { error.value = (e as Error).message } finally { busy.value = false }
}
</script>
<template>
  <AppDialog title="上传图片" @close="!busy && (session.uploadOpen = false)">
    <form class="form-stack" @submit.prevent="upload">
      <button type="button" class="upload-drop" @click="picker?.click()" @dragover.prevent @drop.prevent="choose($event.dataTransfer?.files[0])"><UploadCloud :size="34" /><strong>{{ file ? file.name : '拖拽图片到这里' }}</strong><span>{{ file ? formatBytes(file.size) : '或点击选择文件' }}</span></button>
      <input ref="picker" class="sr-only" type="file" accept="image/jpeg,image/png,image/webp" @change="choose(($event.target as HTMLInputElement).files?.[0])" />
      <p class="hint">JPG、PNG、WebP · 单张最大 {{ formatBytes(session.maxUploadBytes) }} · 最大 {{ (session.maxPixels / 10000).toLocaleString('zh-CN') }} 万像素</p>
      <label>图片名称<input v-model="title" required maxlength="100" placeholder="为图片起个名字" /></label>
      <label>标签<input v-model="tags" placeholder="如：风景，自然（最多 8 个）" /></label>
      <label>保存到<select v-model="spaceId" aria-label="保存到" required><option v-for="s in spaces" :key="s.id" :value="s.id">{{ s.name }} · {{ s.is_public ? '公开' : '私有' }}</option></select></label>
      <p v-if="spaces.find(s => s.id === spaceId)?.is_public" class="hint">这个空间公开可见，上传的图片可被访客浏览。</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="button primary" :disabled="busy || !file"><ImagePlus :size="18" />{{ busy ? '上传与处理图片中…' : '上传图片' }}</button>
    </form>
  </AppDialog>
</template>
