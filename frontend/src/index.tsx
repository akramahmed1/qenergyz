import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { ReactQueryDevtools } from 'react-query/devtools'
import { HelmetProvider } from 'react-helmet-async'
import { ErrorBoundary } from 'react-error-boundary'
import * as Sentry from '@sentry/react'
import { Toaster } from 'react-hot-toast'

import App from './App'
import { GlobalErrorFallback } from './components/error/GlobalErrorFallback'
import { initializeI18n } from './i18n'
import { initializeSentry } from './utils/sentry'
import { initializeAnalytics } from './utils/analytics'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import { WebSocketProvider } from './contexts/WebSocketContext'

import './styles/global.css'

// Declare global variables
declare global {
  interface Window {
    gtag?: (...args: any[]) => void
  }
  const __APP_VERSION__: string
  const __BUILD_TIME__: string
}

// Initialize services
initializeSentry()
initializeAnalytics()
initializeI18n()

// Create React Query client with robust configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors (client errors)
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false
        }
        // Retry up to 3 times for other errors
        return failureCount < 3
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      refetchOnReconnect: 'always',
    },
    mutations: {
      retry: (failureCount, error: any) => {
        // Don't retry mutations on 4xx errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false
        }
        return failureCount < 2
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    },
  },
})

// Enhanced error logging
const logError = (error: Error, errorInfo: React.ErrorInfo) => {
  console.error('Application Error:', error)
  console.error('Error Info:', errorInfo)
  
  // Send to Sentry
  Sentry.captureException(error, {
    contexts: {
      react: {
        componentStack: errorInfo.componentStack,
      },
    },
  })

  // Send to analytics
  if (window.gtag) {
    window.gtag('event', 'exception', {
      description: error.message,
      fatal: false,
    })
  }
}

// Create the root element
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
)

// Render the application with all providers
root.render(
  <React.StrictMode>
    <ErrorBoundary
      FallbackComponent={GlobalErrorFallback}
      onError={logError}
      onReset={() => window.location.reload()}
    >
      <HelmetProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <ThemeProvider>
              <AuthProvider>
                <WebSocketProvider>
                  <App />
                  <Toaster
                    position="top-right"
                    toastOptions={{
                      duration: 4000,
                      style: {
                        background: 'var(--background)',
                        color: 'var(--foreground)',
                        border: '1px solid var(--border)',
                      },
                    }}
                  />
                </WebSocketProvider>
              </AuthProvider>
            </ThemeProvider>
          </BrowserRouter>
          {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        </QueryClientProvider>
      </HelmetProvider>
    </ErrorBoundary>
  </React.StrictMode>
)

// Register service worker for PWA functionality
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        console.log('SW registered: ', registration)
      })
      .catch((registrationError) => {
        console.log('SW registration failed: ', registrationError)
      })
  })
}

// Hot module replacement for development
if (import.meta.hot) {
  import.meta.hot.accept()
}