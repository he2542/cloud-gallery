import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import GalleryPage from './pages/GalleryPage.vue'
import SpacesPage from './pages/SpacesPage.vue'
import TagsPage from './pages/TagsPage.vue'
import './style.css'

const router = createRouter({ history: createWebHistory(import.meta.env.BASE_URL), routes: [
  { path: '/', component: GalleryPage }, { path: '/spaces', component: SpacesPage }, { path: '/tags', component: TagsPage },
  { path: '/:pathMatch(.*)*', redirect: '/' },
] })
createApp(App).use(router).mount('#app')
