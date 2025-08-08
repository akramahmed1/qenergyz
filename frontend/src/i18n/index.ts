import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import Backend from 'i18next-http-backend'
import LanguageDetector from 'i18next-browser-languagedetector'

// Import translation files
import enTranslations from './locales/en.json'
import arTranslations from './locales/ar.json'

export const defaultNS = 'translation'
export const resources = {
  en: {
    translation: enTranslations,
  },
  ar: {
    translation: arTranslations,
  },
} as const

export function initializeI18n() {
  return i18n
    .use(Backend)
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      lng: import.meta.env.VITE_DEFAULT_LANGUAGE || 'en',
      fallbackLng: 'en',
      supportedLngs: ['en', 'ar'],
      debug: import.meta.env.DEV,
      defaultNS,
      resources,
      
      detection: {
        order: [
          'localStorage',
          'sessionStorage', 
          'navigator',
          'htmlTag',
          'path',
          'subdomain'
        ],
        lookupLocalStorage: 'i18nextLng',
        lookupSessionStorage: 'i18nextLng',
        caches: ['localStorage'],
        checkWhitelist: true,
      },

      backend: {
        loadPath: '/locales/{{lng}}/{{ns}}.json',
        crossDomain: false,
        requestOptions: {
          cache: 'default',
        },
      },

      interpolation: {
        escapeValue: false,
        formatSeparator: ',',
        format: function(value, format, lng) {
          if (format === 'uppercase') return value.toUpperCase()
          if (format === 'lowercase') return value.toLowerCase()
          if (format === 'currency') {
            const currency = lng === 'ar' ? 'AED' : 'USD'
            return new Intl.NumberFormat(lng, {
              style: 'currency',
              currency: currency
            }).format(value)
          }
          if (format === 'number') {
            return new Intl.NumberFormat(lng).format(value)
          }
          if (format === 'date') {
            return new Intl.DateTimeFormat(lng).format(value)
          }
          if (format === 'datetime') {
            return new Intl.DateTimeFormat(lng, {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            }).format(value)
          }
          return value
        }
      },

      react: {
        bindI18n: 'languageChanged',
        bindI18nStore: '',
        useSuspense: true,
        wait: true,
      },

      pluralSeparator: '_',
      contextSeparator: '_',
      cleanCode: true,
      returnEmptyString: !import.meta.env.DEV,
      returnNull: false,
      initImmediate: false,
      
      parseMissingKeyHandler: (key: string) => {
        if (import.meta.env.DEV) {
          console.warn(`Missing translation key: ${key}`)
        }
        return key
      },
      
      missingKeyHandler: (lng, ns, key) => {
        if (import.meta.env.DEV) {
          console.warn(`Missing key "${key}" in language "${lng}" and namespace "${ns}"`)
        }
      },
      
      postProcess: ['rtl'],
    })
}

  // Handle RTL languages
  i18n.on('languageChanged', (lng) => {
    const isRTL = lng === 'ar'
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr'
    document.documentElement.lang = lng
    
    // Update CSS custom property for text direction
    document.documentElement.style.setProperty('--text-direction', isRTL ? 'rtl' : 'ltr')
  })

  // Set initial direction
  const currentLang = i18n.language || 'en'
  const isRTL = currentLang === 'ar'
  document.documentElement.dir = isRTL ? 'rtl' : 'ltr'
  document.documentElement.lang = currentLang

  return i18n
}

// Helper functions
export function getCurrentLanguage() {
  return i18n.language || 'en'
}

export function isRTL() {
  return getCurrentLanguage() === 'ar'
}

export function switchLanguage(lng: string) {
  return i18n.changeLanguage(lng)
}

export function formatCurrency(amount: number, currency?: string) {
  const lang = getCurrentLanguage()
  const curr = currency || (lang === 'ar' ? 'AED' : 'USD')
  
  return new Intl.NumberFormat(lang, {
    style: 'currency',
    currency: curr
  }).format(amount)
}

export function formatNumber(number: number) {
  return new Intl.NumberFormat(getCurrentLanguage()).format(number)
}

export function formatDate(date: Date | string | number, options?: Intl.DateTimeFormatOptions) {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date
  return new Intl.DateTimeFormat(getCurrentLanguage(), options).format(dateObj)
}

export default i18n