/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_REGION: string
  readonly VITE_DEFAULT_LANGUAGE: string
  readonly VITE_ANALYTICS_KEY: string
  readonly VITE_GA_MEASUREMENT_ID: string
  readonly VITE_MIXPANEL_TOKEN: string
  readonly VITE_AMPLITUDE_API_KEY: string
  readonly VITE_GROK_API_KEY: string
  readonly VITE_SENTRY_DSN: string
  readonly VITE_SENTRY_ENVIRONMENT: string
  readonly VITE_SENTRY_TRACES_SAMPLE_RATE: string
  readonly VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE: string
  readonly VITE_API_RATE_LIMIT: string
  readonly VITE_API_BURST_LIMIT: string
  readonly VITE_API_TIMEOUT: string
  readonly VITE_DEBUG_MODE: string
  readonly VITE_MOCK_API: string
  // more env variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}