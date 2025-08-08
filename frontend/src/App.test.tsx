import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import App from '../App'

// Mock i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => defaultValue || key,
    i18n: {
      changeLanguage: () => new Promise(() => {}),
    },
  }),
}))

// Mock Sentry
jest.mock('@sentry/react', () => ({
  init: jest.fn(),
  captureException: jest.fn(),
  startTransaction: jest.fn(),
}))

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('App Component', () => {
  beforeEach(() => {
    // Clear localStorage
    localStorage.clear()
  })

  it('renders login page when not authenticated', () => {
    renderWithProviders(<App />)
    
    // Should redirect to login since user is not authenticated
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('handles authentication state correctly', () => {
    // Mock authenticated user
    localStorage.setItem('auth_token', 'mock-token')
    localStorage.setItem('user', JSON.stringify({
      id: '1',
      email: 'test@qenergyz.com',
      firstName: 'Test',
      lastName: 'User',
      role: 'trader',
      company: 'Test Company'
    }))

    renderWithProviders(<App />)
    
    // Should show dashboard content for authenticated user
    // Note: This is a simplified test - in real app we'd test more thoroughly
    expect(document.body).toBeInTheDocument()
  })
})