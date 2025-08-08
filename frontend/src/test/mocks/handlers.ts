import { rest } from 'msw'

export const handlers = [
  // Handle auth endpoints
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        data: {
          user: {
            id: '1',
            email: 'test@qenergyz.com',
            firstName: 'Test',
            lastName: 'User',
            role: 'trader',
            company: 'Test Company'
          },
          token: 'mock-jwt-token'
        },
        status: 'success',
        timestamp: new Date().toISOString(),
        requestId: 'mock-request-id'
      })
    )
  }),

  // Handle dashboard data
  rest.get('/api/dashboard', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        data: {
          portfolioValue: 2456789,
          todaysPnL: 12345,
          openPositions: 23,
          riskExposure: 'medium'
        },
        status: 'success',
        timestamp: new Date().toISOString(),
        requestId: 'mock-request-id'
      })
    )
  }),

  // Handle health check
  rest.get('/api/health', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        status: 'healthy',
        timestamp: new Date().toISOString()
      })
    )
  }),

  // Handle 404s
  rest.get('*', (req, res, ctx) => {
    console.error(`Please add request handler for ${req.url.toString()}`)
    return res(
      ctx.status(404),
      ctx.json({
        message: 'Not found',
        status: 'error',
        timestamp: new Date().toISOString(),
        requestId: 'mock-request-id'
      })
    )
  })
]