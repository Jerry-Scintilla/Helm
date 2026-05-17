import { useLocaleStore } from '@/stores/locale'

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

export function resolveSdeName(name: SdeName | null | undefined, fallback = '—'): string {
  if (!name) return fallback
  const lang = useLocaleStore().locale
  return name[lang] ?? name['en'] ?? Object.values(name).find(v => !!v) ?? fallback
}
