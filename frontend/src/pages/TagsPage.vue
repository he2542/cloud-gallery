<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Tag as TagIcon, ArrowUpRight } from 'lucide-vue-next'
import { api } from '../api'
import { session } from '../session'
import type { Tag } from '../types'
const tags = ref<Tag[]>([]), error = ref(''), router = useRouter()
let sequence = 0
async function load() { const current = ++sequence; try { const result = await api<Tag[]>('/tags'); if (current === sequence) { tags.value = result; error.value = '' } } catch (e) { if (current === sequence) { tags.value = []; error.value = (e as Error).message } } }
onMounted(load); watch(() => session.revision, load)
watch(() => session.user?.id, () => { tags.value = []; load() }, { flush: 'sync' })
</script>
<template><div class="page-title"><div><p class="eyebrow">用关键词串起你的图片</p><h1>标签索引 <span>{{ tags.length }} 个标签</span></h1></div></div><p class="hint">上传图片或编辑图片详情时添加标签，点击标签查看相关图片。</p><p v-if="error" class="error" role="alert">{{ error }}</p><div v-if="!tags.length" class="empty-state"><TagIcon :size="40" /><h2>还没有标签</h2><p>给图片添加标签，让收藏更容易找到。</p></div><div class="tag-grid"><button v-for="tag in tags" :key="tag.name" class="tag-card" @click="router.push({ path: '/', query: { tag: tag.name } })"><TagIcon :size="19" /><strong>{{ tag.name }}</strong><span>{{ tag.count }} 张图片</span><ArrowUpRight :size="16" /></button></div></template>
