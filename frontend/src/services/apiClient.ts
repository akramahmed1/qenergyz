import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  AxiosResponse, 
  AxiosError 
} from 'axios'
import * as Sentry from '@sentry/react'
import { toast } from 'react-hot-toast'

import { authStore } from '../store/authStore'
import { CircuitBreaker, CircuitBreakerOptions } from '../utils/circuitBreaker'
import { RateLimiter } from '../utils/rateLimiter'

// API Response Types
export interface ApiResponse<T = any> {
  data: T
  message?: string
  status: 'success' | 'error'
  timestamp: string
  requestId: string
}

export interface ApiError {
  message: string
  code: string
  details?: any
  timestamp: string
  requestId: string
}

// Circuit breaker configuration
const circuitBreakerOptions: CircuitBreakerOptions = {
  failureThreshold: 5,
  resetTimeout: 60000, // 1 minute
  monitoringPeriod: 10000, // 10 seconds
}

// Rate limiter configuration
const rateLimiter = new RateLimiter({
  maxRequests: parseInt(import.meta.env.VITE_API_RATE_LIMIT) || 100,
  windowMs: 60000, // 1 minute
  burstLimit: parseInt(import.meta.env.VITE_API_BURST_LIMIT) || 20,
})

class ApiClient {
  private client: AxiosInstance
  private circuitBreaker: CircuitBreaker
  private baseURL: string

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: parseInt(import.meta.env.VITE_API_TIMEOUT) || 30000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    })

    this.circuitBreaker = new CircuitBreaker(
      this.executeRequest.bind(this),
      circuitBreakerOptions
    )

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add authentication token
        const token = authStore.getState().token
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }

        // Add request ID for tracing
        config.headers['X-Request-ID'] = this.generateRequestId()

        // Add region and locale headers
        config.headers['X-Region'] = import.meta.env.VITE_REGION || 'middle_east'
        config.headers['Accept-Language'] = localStorage.getItem('i18nextLng') || 'en'

        // Rate limiting
        if (!rateLimiter.canMakeRequest()) {
          return Promise.reject(new Error('Rate limit exceeded'))
        }

        // Log request in development
        if (import.meta.env.DEV) {
          console.log('API Request:', {
            method: config.method?.toUpperCase(),
            url: config.url,
            params: config.params,
            data: config.data,
          })
        }

        return config
      },
      (error) => {
        console.error('Request interceptor error:', error)
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => {
        // Log successful response in development
        if (import.meta.env.DEV) {
          console.log('API Response:', {
            status: response.status,
            data: response.data,
            headers: response.headers,
          })
        }

        return response
      },
      (error: AxiosError<ApiError>) => {
        this.handleResponseError(error)
        return Promise.reject(this.formatError(error))
      }
    )
  }

  private async executeRequest(config: AxiosRequestConfig): Promise<AxiosResponse> {
    return this.client(config)
  }

  private handleResponseError(error: AxiosError<ApiError>) {
    const status = error.response?.status
    const data = error.response?.data

    // Handle specific error cases
    switch (status) {
      case 401:
        // Unauthorized - clear auth and redirect to login
        authStore.getState().logout()
        toast.error('Session expired. Please log in again.')
        window.location.href = '/login'
        break

      case 403:
        // Forbidden
        toast.error('You don\'t have permission to perform this action')
        break

      case 404:
        // Not found
        toast.error('The requested resource was not found')
        break

      case 429:
        // Rate limited
        toast.error('Too many requests. Please slow down.')
        break

      case 500:
        // Server error
        toast.error('Server error. Please try again later.')
        break

      case 503:
        // Service unavailable
        toast.error('Service temporarily unavailable')
        break

      default:
        if (data?.message) {
          toast.error(data.message)
        } else if (error.message) {
          toast.error(error.message)
        } else {
          toast.error('An unexpected error occurred')
        }
    }

    // Send error to Sentry
    Sentry.captureException(error, {
      tags: {
        section: 'api_client',
        status: status?.toString(),
      },
      extra: {
        url: error.config?.url,
        method: error.config?.method,
        data: error.config?.data,
        response: data,
      },
    })
  }

  private formatError(error: AxiosError<ApiError>): ApiError {
    return {
      message: error.response?.data?.message || error.message || 'An unexpected error occurred',
      code: error.response?.data?.code || error.code || 'UNKNOWN_ERROR',
      details: error.response?.data?.details || error.response?.data,
      timestamp: new Date().toISOString(),
      requestId: error.config?.headers?.['X-Request-ID'] as string || '',
    }
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // Public API methods
  async get<T = any>(
    url: string, 
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.circuitBreaker.execute({
      method: 'GET',
      url,
      ...config,
    })
    return response.data
  }

  async post<T = any>(
    url: string, 
    data?: any, 
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.circuitBreaker.execute({
      method: 'POST',
      url,
      data,
      ...config,
    })
    return response.data
  }

  async put<T = any>(
    url: string, 
    data?: any, 
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.circuitBreaker.execute({
      method: 'PUT',
      url,
      data,
      ...config,
    })
    return response.data
  }

  async patch<T = any>(
    url: string, 
    data?: any, 
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.circuitBreaker.execute({
      method: 'PATCH',
      url,
      data,
      ...config,
    })
    return response.data
  }

  async delete<T = any>(
    url: string, 
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.circuitBreaker.execute({
      method: 'DELETE',
      url,
      ...config,
    })
    return response.data
  }

  // File upload with progress
  async upload<T = any>(
    url: string,
    file: File,
    onUploadProgress?: (progressEvent: any) => void
  ): Promise<ApiResponse<T>> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.circuitBreaker.execute({
      method: 'POST',
      url,
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    })
    return response.data
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      await this.get('/health')
      return true
    } catch {
      return false
    }
  }

  // Get circuit breaker status
  getCircuitBreakerStatus() {
    return this.circuitBreaker.getStatus()
  }

  // Reset circuit breaker manually
  resetCircuitBreaker() {
    this.circuitBreaker.reset()
  }
}

// Export singleton instance
export const apiClient = new ApiClient()
export default apiClient