import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'

interface LayoutProps {
  children: React.ReactNode
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const location = useLocation()

  const navigation = [
    { name: t('navigation.dashboard', 'Dashboard'), href: '/dashboard', icon: '📊' },
    { name: t('navigation.trading', 'Trading'), href: '/trading', icon: '💹' },
    { name: t('navigation.risk', 'Risk Management'), href: '/risk', icon: '⚠️' },
    { name: t('navigation.compliance', 'Compliance'), href: '/compliance', icon: '⚖️' },
    { name: t('navigation.iot', 'IoT Monitoring'), href: '/iot', icon: '🔌' },
    { name: t('navigation.analytics', 'Analytics'), href: '/analytics', icon: '📈' },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-border">
            <h1 className="text-xl font-bold text-foreground">Qenergyz</h1>
            <p className="text-sm text-secondary">Energy Trading Platform</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4">
            <ul className="space-y-2">
              {navigation.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      location.pathname.startsWith(item.href)
                        ? 'bg-primary text-white'
                        : 'text-foreground hover:bg-muted'
                    }`}
                  >
                    <span className="mr-3">{item.icon}</span>
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* User Info */}
          <div className="p-4 border-t border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white text-sm font-medium">
                  {user?.firstName?.[0]}{user?.lastName?.[0]}
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-foreground">
                    {user?.firstName} {user?.lastName}
                  </p>
                  <p className="text-xs text-secondary">{user?.role}</p>
                </div>
              </div>
              <button
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                className="p-1 text-secondary hover:text-foreground"
                title="Toggle theme"
              >
                {theme === 'light' ? '🌙' : '☀️'}
              </button>
            </div>
            <button
              onClick={logout}
              className="mt-3 w-full text-left text-sm text-secondary hover:text-foreground"
            >
              {t('navigation.logout', 'Logout')}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="pl-64">
        <main className="min-h-screen">
          {children}
        </main>
      </div>
    </div>
  )
}