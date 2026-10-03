<script setup lang="ts">
import { ref } from 'vue'
import { Download, Lock, Globe2, Trash2 } from 'lucide-vue-next'
import AppDialog from './AppDialog.vue'
import { api, imageUrl, formatBytes, dateLabel } from '../api'
import { changed } from '../session'
import type { Picture } from '../types'
const props = defineProps<{ picture: Picture }>()
const emit = defineEmits<{ close: [] }>()
const title = ref(props.picture.title), description = ref(props.picture.description), tags = ref(props.picture.tags.join('，'))
const busy = ref(false), error = ref(''), deleting = ref(false)
async function save() {
  busy.value = true; error.value = ''
  try { await api(`/pictures/${props.picture.id}`, { method: 'PATCH', body: JSON.stringify({ title: title.value, description: description.value, tags: tags.value.split(/[,，]/).map(x => x.trim()).filter(Boolean) }) }); await changed(); emit('close') }
  catch (e) { error.value = (e as Error).message } finally { busy.value = false }
}
async function remove() {
  busy.value = true; error.value = ''
  try { await api(`/pictures/${props.picture.id}`, { method: 'DELETE' }); await changed(); emit('close') }
  catch (e) { error.value = (e as Error).message } finally { busy.value = false }
}
</script>
<template>
  <AppDialog :title="picture.title" wide @close="!busy && emit('close')">
    <div class="detail-layout">
      <div class="detail-image"><img :src="imageUrl(picture.id, false)" :alt="picture.title" /></div>
      <form class="form-stack" @submit.prevent="save">
        <span class="privacy"><Globe2 v-if="picture.is_public" :size="15" /><Lock v-else :size="15" />{{ picture.space_name }} · {{ picture.is_public ? '公开' : '私有' }}</span>
        <label>图片名称<input v-model="title" :readonly="!picture.can_edit" required maxlength="100" /></label>
        <label>标签<input v-model="tags" :readonly="!picture.can_edit" placeholder="用逗号分隔" /></label>
        <label>描述<textarea v-model="description" :readonly="!picture.can_edit" maxlength="1000" rows="3" placeholder="记录图片背后的故事" /></label>
        <div class="detail-meta"><span>{{ picture.width }} × {{ picture.height }}</span><span>{{ formatBytes(picture.byte_size) }}</span><span>{{ dateLabel(picture.created_at) }}</span></div>
        <a class="button" :href="imageUrl(picture.id, false)" target="_blank" rel="noopener"><Download :size="16" />查看原图</a>
        <button v-if="picture.can_edit" class="button primary" :disabled="busy">{{ busy ? '正在保存…' : '保存修改' }}</button>
        <button v-if="picture.can_edit && !deleting" type="button" class="button danger-ghost" @click="deleting = true"><Trash2 :size="16" />删除图片</button>
        <div v-if="deleting" class="delete-confirm"><p>删除后，原图与缩略图都会移除。</p><div class="actions"><button type="button" class="button danger" :disabled="busy" @click="remove">确认删除</button><button type="button" class="button" @click="deleting = false">取消</button></div></div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </form>
    </div>
  </AppDialog>
</template>
