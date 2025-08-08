import React, { Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { useTranslation } from 'react-i18next'

import { Layout } from './components/layout/Layout'
import { LoadingSpinner } from './components/ui/LoadingSpinner'
import { useAuth } from './hooks/useAuth'
import { useTheme } from './hooks/useTheme'
import { ProtectedRoute } from './components/auth/ProtectedRoute'

// Lazy load pages for better performance
const Dashboard = React.lazy(() => import('./pages/Dashboard'))
const Trading = React.lazy(() => import('./pages/Trading'))
const RiskManagement = React.lazy(() => import('./pages/RiskManagement'))
const Compliance = React.lazy(() => import('./pages/Compliance'))
const IoTMonitoring = React.lazy(() => import('./pages/IoTMonitoring'))
const Analytics = React.lazy(() => import('./pages/Analytics'))
const Settings = React.lazy(() => import('./pages/Settings'))
const Login = React.lazy(() => import('./pages/auth/Login'))
const Register = React.lazy(() => import('./pages/auth/Register'))
const OnboardingFlow = React.lazy(() => import('./pages/onboarding/OnboardingFlow'))
const NotFound = React.lazy(() => import('./pages/NotFound'))

function App() {
  const { t } = useTranslation()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const { theme } = useTheme()

  // Apply theme to document
  React.useEffect(() => {
    document.documentElement.className = theme
  }, [theme])

  // Show loading while auth is being determined
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <>
      <Helmet>
        <title>{t('app.title', 'Qenergyz - Energy Trading Risk Management')}</title>
        <meta name="description" content={t('app.description', 'Advanced Energy Trading and Risk Management Platform')} />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="theme-color" content={theme === 'dark' ? '#1a1a1a' : '#ffffff'} />
      </Helmet>

      <div className="min-h-screen bg-background text-foreground">
        <Suspense 
          fallback={
            <div className="flex items-center justify-center min-h-screen">
              <LoadingSpinner size="lg" />
            </div>
          }
        >
          <Routes>
            {/* Authentication Routes */}
            <Route 
              path="/login" 
              element={
                isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />
              } 
            />
            <Route 
              path="/register" 
              element={
                isAuthenticated ? <Navigate to="/dashboard" replace /> : <Register />
              } 
            />
            
            {/* Onboarding Flow */}
            <Route 
              path="/onboarding/*" 
              element={
                <ProtectedRoute>
                  <OnboardingFlow />
                </ProtectedRoute>
              } 
            />

            {/* Protected Application Routes */}
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      <Route path="/" element={<Navigate to="/dashboard" replace />} />
                      <Route path="/dashboard" element={<Dashboard />} />
                      
                      {/* Trading Module */}
                      <Route path="/trading/*" element={<Trading />} />
                      
                      {/* Risk Management Module */}
                      <Route path="/risk/*" element={<RiskManagement />} />
                      
                      {/* Compliance Module */}
                      <Route path="/compliance/*" element={<Compliance />} />
                      
                      {/* IoT Monitoring Module */}
                      <Route path="/iot/*" element={<IoTMonitoring />} />
                      
                      {/* Analytics Module */}
                      <Route path="/analytics/*" element={<Analytics />} />
                      
                      {/* Settings */}
                      <Route path="/settings/*" element={<Settings />} />
                      
                      {/* 404 Page */}
                      <Route path="/404" element={<NotFound />} />
                      <Route path="*" element={<Navigate to="/404" replace />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </Suspense>
      </div>
    </>
  )
}

export default App