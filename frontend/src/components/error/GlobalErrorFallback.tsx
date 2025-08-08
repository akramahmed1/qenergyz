import React from 'react'
import { useTranslation } from 'react-i18next'

interface GlobalErrorFallbackProps {
  error?: Error
  resetError?: () => void
}

export const GlobalErrorFallback: React.FC<GlobalErrorFallbackProps> = ({ 
  error, 
  resetError 
}) => {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="max-w-md w-full mx-4 text-center">
        <div className="bg-card p-8 rounded-lg shadow-lg border">
          <div className="mb-4">
            <svg
              className="w-16 h-16 mx-auto text-destructive"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          
          <h1 className="text-2xl font-bold text-foreground mb-4">
            {t('errors.generic', 'Something went wrong')}
          </h1>
          
          <p className="text-secondary mb-6">
            {error?.message || t('errors.generic', 'An unexpected error occurred')}
          </p>
          
          {resetError && (
            <button
              onClick={resetError}
              className="bg-primary text-white px-6 py-2 rounded-md hover:bg-primary/90 transition-colors"
            >
              {t('app.retry', 'Try Again')}
            </button>
          )}
          
          <details className="mt-6 text-left">
            <summary className="cursor-pointer text-sm text-secondary hover:text-foreground">
              Technical Details
            </summary>
            <pre className="mt-2 text-xs bg-muted p-4 rounded overflow-auto">
              {error?.stack}
            </pre>
          </details>
        </div>
      </div>
    </div>
  )
}