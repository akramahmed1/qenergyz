import React from 'react'
import { useTranslation } from 'react-i18next'

const NotFound: React.FC = () => {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-foreground mb-4">404</h1>
        <p className="text-xl text-secondary mb-8">
          {t('errors.notFound', 'The requested resource was not found')}
        </p>
        <button 
          onClick={() => window.history.back()}
          className="bg-primary text-white px-6 py-2 rounded-md hover:bg-primary/90"
        >
          {t('app.back', 'Go Back')}
        </button>
      </div>
    </div>
  )
}

export default NotFound