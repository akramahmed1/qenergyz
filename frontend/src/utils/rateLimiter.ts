export interface RateLimiterOptions {
  maxRequests: number
  windowMs: number
  burstLimit: number
}

export class RateLimiter {
  private requests: number[] = []
  private burstCount = 0

  constructor(private options: RateLimiterOptions) {}

  canMakeRequest(): boolean {
    const now = Date.now()
    const windowStart = now - this.options.windowMs

    // Clean old requests
    this.requests = this.requests.filter(time => time > windowStart)

    // Check burst limit
    if (this.burstCount >= this.options.burstLimit) {
      const lastBurstTime = this.requests[this.requests.length - 1] || 0
      if (now - lastBurstTime < 1000) { // 1 second burst window
        return false
      }
      this.burstCount = 0
    }

    // Check overall limit
    if (this.requests.length >= this.options.maxRequests) {
      return false
    }

    // Allow request
    this.requests.push(now)
    this.burstCount++
    return true
  }

  getRemainingRequests(): number {
    return Math.max(0, this.options.maxRequests - this.requests.length)
  }

  getResetTime(): number {
    if (this.requests.length === 0) return 0
    return this.requests[0] + this.options.windowMs
  }

  reset(): void {
    this.requests = []
    this.burstCount = 0
  }
}