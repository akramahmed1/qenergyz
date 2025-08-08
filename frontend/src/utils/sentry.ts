import * as Sentry from '@sentry/react'
import { BrowserTracing } from '@sentry/tracing'

export function initializeSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  const environment = import.meta.env.VITE_SENTRY_ENVIRONMENT || 'development'
  
  if (!dsn) {
    console.warn('Sentry DSN not configured')
    return
  }

  Sentry.init({
    dsn,
    environment,
    integrations: [
      new BrowserTracing(),
    ],
    
    // Performance monitoring
    tracesSampleRate: parseFloat(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE) || 0.1,
    
    // Session replay
    replaysSessionSampleRate: parseFloat(import.meta.env.VITE_SENTRY_REPLAYS_SESSION_SAMPLE_RATE) || 0.1,
    replaysOnErrorSampleRate: 1.0,

    // Release tracking
    release: `qenergyz-frontend@${__APP_VERSION__ || 'unknown'}`,

    // User context
    beforeSend: (event, hint) => {
      // Filter out development errors
      if (environment === 'development') {
        console.error('Sentry Event:', event, hint)
        return null
      }

      // Add additional context
      if (event.exception) {
        const error = hint.originalException
        console.error('Error captured by Sentry:', error)
      }

      return event
    },

    // Configure what data to send
    sendDefaultPii: false,
    attachStacktrace: true,
    
    // Transport options
    transport: Sentry.makeBrowserTransport,
    
    // Additional options
    maxBreadcrumbs: 50,
    debug: environment === 'development',
  })

  // Set user context if available
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  if (user.id) {
    Sentry.setUser({
      id: user.id,
      email: user.email,
      username: user.username,
    })
  }

  // Set additional tags
  Sentry.setTags({
    component: 'frontend',
    region: import.meta.env.VITE_REGION || 'unknown',
    version: __APP_VERSION__ || 'unknown',
    buildTime: __BUILD_TIME__ || 'unknown',
  })
}

// Helper function to capture errors with context
export function captureErrorWithContext(error: Error, context: Record<string, any>) {
  Sentry.withScope(scope => {
    Object.keys(context).forEach(key => {
      scope.setContext(key, context[key])
    })
    Sentry.captureException(error)
  })
}

// Helper function for performance monitoring
export function startTransaction(name: string, operation: string) {
  return Sentry.startTransaction({
    name,
    op: operation,
  })
}