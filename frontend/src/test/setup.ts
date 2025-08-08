import '@testing-library/jest-dom'
import { TextEncoder, TextDecoder } from 'util'
import { server } from './mocks/server'

// Polyfill for TextEncoder/TextDecoder
global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder

// Mock environment variables
process.env.VITE_API_URL = 'http://localhost:8000'
process.env.VITE_WS_URL = 'ws://localhost:8000/ws'
process.env.VITE_REGION = 'middle_east'
process.env.VITE_DEFAULT_LANGUAGE = 'en'

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
global.localStorage = localStorageMock

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
global.sessionStorage = sessionStorageMock

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn()

// Establish API mocking before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})

// Reset any request handlers that are declared in individual tests
afterEach(() => {
  server.resetHandlers()
  // Clear all mocks
  jest.clearAllMocks()
  // Clear storage mocks
  localStorageMock.clear()
  sessionStorageMock.clear()
})

// Clean up after the tests are finished
afterAll(() => {
  server.close()
})

// Global test utilities
global.testUtils = {
  mockUser: {
    id: '1',
    email: 'test@qenergyz.com',
    firstName: 'Test',
    lastName: 'User',
    role: 'trader',
    company: 'Test Company',
  },
  mockTrade: {
    id: '1',
    commodity: 'crude_oil',
    side: 'buy',
    quantity: 1000,
    price: 75.50,
    status: 'executed',
    timestamp: '2024-01-01T00:00:00Z',
  },
}