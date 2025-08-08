import '@testing-library/jest-dom'

// Mock environment variables
process.env.VITE_API_URL = 'http://localhost:8000'
process.env.VITE_WS_URL = 'ws://localhost:8000/ws'
process.env.VITE_REGION = 'middle_east'
process.env.VITE_DEFAULT_LANGUAGE = 'en'

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock localStorage
const localStorageMock = (() => {
  let store = {} as Record<string, string>
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value.toString() },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} }
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => 'mocked-url')

// Global test utilities
declare global {
  // eslint-disable-next-line no-var
  var testUtils: {
    mockUser: any
    mockTrade: any
  }
}

globalThis.testUtils = {
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