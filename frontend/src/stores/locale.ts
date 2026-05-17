import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Locale = 'zh' | 'en'

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<Locale>(
    (localStorage.getItem('helm-locale') as Locale | null) ?? 'zh'
  )

  function setLocale(lang: Locale) {
    locale.value = lang
    localStorage.setItem('helm-locale', lang)
  }

  return { locale, setLocale }
})
