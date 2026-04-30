import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive, { darkTheme, createDiscreteApi } from 'naive-ui'

import App from './App.vue'
import router from './router'

// Naive UI 内部菜单组件注册 wheel 事件时未标记 passive，
// 导致 Chrome DevTools 报 Violation。通过主动添加 passive 解决。
function suppressWheelPassiveWarning() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const add = (EventTarget.prototype.addEventListener as any)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(EventTarget.prototype.addEventListener as any) = function (
    type: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    listener: (...args: any[]) => void,
    options?: boolean | { capture?: boolean; once?: boolean; passive?: boolean; signal?: AbortSignal }
  ) {
    if (type === 'wheel') {
      const opts = options === true ? true : options && typeof options === 'object'
        ? { ...options, passive: true }
        : false
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      add.call(this, type, listener as any, opts)
      return
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    add.call(this, type, listener as any, options)
  }
}
suppressWheelPassiveWarning()

export const { message, notification, dialog } = createDiscreteApi(
  ['message', 'notification', 'dialog'],
  { configProviderProps: { theme: darkTheme } }
)

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(naive)
app.mount('#app')
