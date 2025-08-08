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
  i18n
    // Load translation using http backend
    .use(Backend)
    // Detect user language
    .use(LanguageDetector)
    // Pass the i18n instance to react-i18next
    .use(initReactI18next)
    // Initialize i18next
    .init({
      // Default language
      lng: import.meta.env.VITE_DEFAULT_LANGUAGE || 'en',
      
      // Fallback language
      fallbackLng: 'en',
      
      // Supported languages
      supportedLngs: ['en', 'ar'],
      
      // Debug mode
      debug: import.meta.env.DEV,
      
      // Namespace
      defaultNS,
      
      // Resources
      resources,
      
      // Language detection
      detection: {
        // Order of detection methods
        order: [
          'localStorage',
          'sessionStorage', 
          'navigator',
          'htmlTag',
          'path',
          'subdomain'
        ],
        
        // Keys to lookup language from
        lookupLocalStorage: 'i18nextLng',
        lookupSessionStorage: 'i18nextLng',
        
        // Cache user language
        caches: ['localStorage'],
        
        // Only detect on initialize
        checkWhitelist: true,
      },

      // Backend configuration
      backend: {
        // Path to load resources from
        loadPath: '/locales/{{lng}}/{{ns}}.json',
        
        // Allow cross domain requests
        crossDomain: false,
        
        // Request timeout
        requestOptions: {
          cache: 'default',
        },
      },

      // Interpolation
      interpolation: {
        escapeValue: false, // React already does escaping
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

      // React options
      react: {
        // Bind i18n instance
        bindI18n: 'languageChanged',
        bindI18nStore: '',
        
        // Use Suspense
        useSuspense: true,
        
        // Wait for translation to be loaded
        wait: true,
      },

      // Pluralization
      pluralSeparator: '_',
      contextSeparator: '_',

      // Clean code on production
      cleanCode: true,
      
      // Return empty string for missing keys in production
      returnEmptyString: !import.meta.env.DEV,
      
      // Return key if missing in development
      returnNull: false,
      
      // Callbacks
      initImmediate: false,
      
      // Parsing
      parseMissingKeyHandler: (key: string) => {
        if (import.meta.env.DEV) {
          console.warn(`Missing translation key: ${key}`)
        }
        return key
      },
      
      // Missing key handler
      missingKeyHandler: (lng, ns, key, fallbackValue) => {
        if (import.meta.env.DEV) {
          console.warn(`Missing key "${key}" in language "${lng}" and namespace "${ns}"`)
        }
      },
      
      // Postprocessor to handle RTL languages
      postProcess: ['rtl'],
    })

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