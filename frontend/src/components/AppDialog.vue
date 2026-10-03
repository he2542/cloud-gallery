<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
defineProps<{ title: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement>()
onMounted(() => dialog.value?.showModal())
onUnmounted(() => dialog.value?.close())
</script>
<template>
  <dialog ref="dialog" :aria-label="title" :class="['dialog', { 'dialog-wide': wide }]" @cancel.prevent="emit('close')" @click="($event.target === dialog) && emit('close')">
    <div class="dialog-head"><h2>{{ title }}</h2><button class="icon-button" type="button" aria-label="关闭" @click="emit('close')"><X :size="20" /></button></div>
    <slot />
  </dialog>
</template>
