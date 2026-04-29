import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive, { darkTheme, createDiscreteApi } from 'naive-ui'

import App from './App.vue'
import router from './router'

export const { message, notification, dialog } = createDiscreteApi(
  ['message', 'notification', 'dialog'],
  { configProviderProps: { theme: darkTheme } }
)

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(naive)
app.mount('#app')
