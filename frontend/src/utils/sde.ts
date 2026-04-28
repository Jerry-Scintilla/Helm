export interface SdeName {
  de?: string
  en?: string
  es?: string
  fr?: string
  ja?: string
  ko?: string
  ru?: string
  zh?: string
  [key: string]: string | undefined
}

const SDE_LANG_KEYS = ['de', 'en', 'es', 'fr', 'ja', 'ko', 'ru', 'zh'] as const

function getPreferredLang(): string {
  const nav = navigator.language.toLowerCase()
  for (const key of SDE_LANG_KEYS) {
    if (nav === key || nav.startsWith(key + '-')) return key
  }
  return 'en'
}

export function resolveSdeName(name: SdeName | null | undefined, fallback = '—'): string {
  if (!name) return fallback
  const lang = getPreferredLang()
  return name[lang] ?? name['en'] ?? Object.values(name).find(v => !!v) ?? fallback
}
