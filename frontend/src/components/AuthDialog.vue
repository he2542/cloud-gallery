<script setup lang="ts">
import { ref } from 'vue'
import { LockKeyhole } from 'lucide-vue-next'
import AppDialog from './AppDialog.vue'
import { api, setCsrf } from '../api'
import { changed, session } from '../session'
const username = ref(''), password = ref(''), error = ref(''), busy = ref(false)
async function submit() {
  busy.value = true; error.value = ''
  try {
    const auth = await api<{ csrf_token: string }>(session.setupRequired ? '/auth/setup' : '/auth/login', { method: 'POST', body: JSON.stringify({ username: username.value, password: password.value }) })
    setCsrf(auth.csrf_token); await changed(); session.authOpen = false
  } catch (e) { error.value = (e as Error).message } finally { busy.value = false }
}
</script>
<template>
  <AppDialog :title="session.setupRequired ? '创建你的图库账户' : '欢迎回来'" @close="session.authOpen = false">
    <div class="auth-intro"><LockKeyhole :size="26" /><p>{{ session.setupRequired ? '设置账户，开始管理图片与私有空间。' : '登录后上传图片，管理你的私有空间。' }}</p></div>
    <form class="form-stack" @submit.prevent="submit">
      <label>用户名<input v-model="username" required minlength="2" maxlength="40" autocomplete="username" placeholder="输入用户名" /></label>
      <label>密码<input v-model="password" type="password" required minlength="10" maxlength="128" :autocomplete="session.setupRequired ? 'new-password' : 'current-password'" placeholder="至少 10 个字符" /></label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="button primary" :disabled="busy">{{ busy ? '正在处理…' : session.setupRequired ? '创建账户并进入' : '登录' }}</button>
    </form>
  </AppDialog>
</template>
