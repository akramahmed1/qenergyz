// Analytics utility for tracking user interactions and events

declare global {
  interface Window {
    gtag?: (...args: any[]) => void
    mixpanel?: any
    amplitude?: any
  }
}

interface AnalyticsEvent {
  name: string
  properties?: Record<string, any>
  userId?: string
  timestamp?: number
}

class Analytics {
  private isInitialized = false
  private userId: string | null = null

  initialize() {
    if (this.isInitialized) return

    // Initialize Google Analytics
    this.initializeGoogleAnalytics()
    
    // Initialize Mixpanel (if configured)
    this.initializeMixpanel()
    
    // Initialize Amplitude (if configured)
    this.initializeAmplitude()

    this.isInitialized = true
    console.log('Analytics initialized')
  }

  private initializeGoogleAnalytics() {
    const measurementId = import.meta.env.VITE_GA_MEASUREMENT_ID
    if (!measurementId) return

    // Load Google Analytics
    const script = document.createElement('script')
    script.async = true
    script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`
    document.head.appendChild(script)

    window.gtag = function() {
      // @ts-ignore
      (window.dataLayer = window.dataLayer || []).push(arguments)
    }

    window.gtag('js', new Date())
    window.gtag('config', measurementId, {
      send_page_view: false, // We'll handle this manually
      custom_map: {
        custom_definition_1: 'user_type',
        custom_definition_2: 'region'
      }
    })
  }

  private initializeMixpanel() {
    const token = import.meta.env.VITE_MIXPANEL_TOKEN
    if (!token) return

    // Load Mixpanel
    // Note: In production, you'd load this from CDN
    console.log('Mixpanel would be initialized with token:', token)
  }

  private initializeAmplitude() {
    const apiKey = import.meta.env.VITE_AMPLITUDE_API_KEY
    if (!apiKey) return

    // Load Amplitude
    // Note: In production, you'd load this from CDN
    console.log('Amplitude would be initialized with API key:', apiKey)
  }

  setUserId(userId: string) {
    this.userId = userId

    // Set user ID in Google Analytics
    if (window.gtag) {
      window.gtag('config', import.meta.env.VITE_GA_MEASUREMENT_ID, {
        user_id: userId
      })
    }

    // Set user ID in other analytics tools
    if (window.mixpanel) {
      window.mixpanel.identify(userId)
    }

    if (window.amplitude) {
      window.amplitude.setUserId(userId)
    }
  }

  setUserProperties(properties: Record<string, any>) {
    // Set custom dimensions in Google Analytics
    if (window.gtag) {
      window.gtag('event', 'set_user_properties', {
        custom_parameter_1: properties.userType,
        custom_parameter_2: properties.region,
        ...properties
      })
    }

    // Set user properties in other tools
    if (window.mixpanel) {
      window.mixpanel.people.set(properties)
    }

    if (window.amplitude) {
      window.amplitude.setUserProperties(properties)
    }
  }

  track(eventName: string, properties: Record<string, any> = {}) {
    if (!this.isInitialized) {
      console.warn('Analytics not initialized')
      return
    }

    const event: AnalyticsEvent = {
      name: eventName,
      properties: {
        ...properties,
        timestamp: Date.now(),
        url: window.location.href,
        referrer: document.referrer,
        user_agent: navigator.userAgent,
        region: import.meta.env.VITE_REGION,
      },
      userId: this.userId || undefined,
      timestamp: Date.now()
    }

    // Track in Google Analytics
    if (window.gtag) {
      window.gtag('event', eventName, {
        event_category: properties.category || 'General',
        event_label: properties.label,
        value: properties.value,
        custom_parameter_region: import.meta.env.VITE_REGION,
        ...properties
      })
    }

    // Track in Mixpanel
    if (window.mixpanel) {
      window.mixpanel.track(eventName, event.properties)
    }

    // Track in Amplitude
    if (window.amplitude) {
      window.amplitude.logEvent(eventName, event.properties)
    }

    // Log in development
    if (import.meta.env.DEV) {
      console.log('Analytics Event:', event)
    }
  }

  trackPageView(page: string, title?: string) {
    this.track('page_view', {
      page_title: title || document.title,
      page_location: window.location.href,
      page_path: page,
      category: 'Navigation'
    })

    // Send pageview to Google Analytics
    if (window.gtag) {
      window.gtag('config', import.meta.env.VITE_GA_MEASUREMENT_ID, {
        page_title: title || document.title,
        page_location: window.location.href
      })
    }
  }

  trackError(error: Error, context?: Record<string, any>) {
    this.track('error', {
      error_message: error.message,
      error_stack: error.stack,
      error_name: error.name,
      category: 'Error',
      ...context
    })
  }

  trackTiming(name: string, duration: number, category: string = 'Performance') {
    if (window.gtag) {
      window.gtag('event', 'timing_complete', {
        name: name,
        value: duration,
        event_category: category
      })
    }

    this.track('timing', {
      timing_name: name,
      timing_duration: duration,
      category
    })
  }

  // Business-specific tracking methods
  trackTrade(tradeData: any) {
    this.track('trade_executed', {
      trade_type: tradeData.type,
      commodity: tradeData.commodity,
      volume: tradeData.volume,
      value: tradeData.value,
      category: 'Trading'
    })
  }

  trackRiskAlert(riskData: any) {
    this.track('risk_alert', {
      risk_type: riskData.type,
      severity: riskData.severity,
      value: riskData.threshold,
      category: 'Risk Management'
    })
  }

  trackComplianceCheck(complianceData: any) {
    this.track('compliance_check', {
      check_type: complianceData.type,
      result: complianceData.result,
      jurisdiction: complianceData.jurisdiction,
      category: 'Compliance'
    })
  }

  trackUserAction(action: string, target: string, properties?: Record<string, any>) {
    this.track('user_action', {
      action,
      target,
      category: 'User Interaction',
      ...properties
    })
  }
}

// Create and export singleton instance
export const analytics = new Analytics()

// Initialize analytics
export function initializeAnalytics() {
  analytics.initialize()
}

export default analytics