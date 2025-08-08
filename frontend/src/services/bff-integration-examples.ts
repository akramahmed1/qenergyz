/**
 * Frontend Integration Examples for Qenergyz BFF API
 * 
 * This file demonstrates how to integrate the React frontend
 * with the new Backend-for-Frontend (BFF) API Gateway.
 */

// Example 1: OAuth/SSO Login Flow
export const initiateOAuthLogin = async (provider: string) => {
  try {
    const response = await fetch('/api/v1/bff/oauth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        provider: provider, // 'google', 'microsoft', 'github', etc.
        redirect_uri: `${window.location.origin}/auth/callback`
      })
    });

    const data = await response.json();
    
    if (response.ok) {
      // Redirect to OAuth provider
      window.location.href = data.authorization_url;
    } else {
      throw new Error(data.detail || 'OAuth login failed');
    }
  } catch (error) {
    console.error('OAuth login error:', error);
    throw error;
  }
};

// Example 2: Handle OAuth Callback
export const handleOAuthCallback = async (code: string, state: string, provider: string) => {
  try {
    const response = await fetch('/api/v1/bff/oauth/callback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        provider: provider,
        code: code,
        state: state
      })
    });

    const data = await response.json();
    
    if (response.ok && data.success) {
      // Store user info and tokens
      localStorage.setItem('auth_token', data.token.access_token);
      localStorage.setItem('user_info', JSON.stringify(data.user));
      return data.user;
    } else {
      throw new Error(data.detail || 'OAuth callback failed');
    }
  } catch (error) {
    console.error('OAuth callback error:', error);
    throw error;
  }
};

// Example 3: BFF Service Request (Trading)
export const getPortfolio = async () => {
  try {
    const token = localStorage.getItem('auth_token');
    
    const response = await fetch('/api/v1/bff/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        service: 'trading',
        operation: 'get_portfolio',
        data: {},
        region: 'usa' // or user's region
      })
    });

    const result = await response.json();
    
    if (result.success) {
      return result.data.portfolio;
    } else {
      throw new Error(result.error || 'Failed to fetch portfolio');
    }
  } catch (error) {
    console.error('Portfolio fetch error:', error);
    throw error;
  }
};

// Example 4: Risk Analysis Request
export const calculateRisk = async (portfolioId: string, confidenceLevel: number = 0.95) => {
  try {
    const token = localStorage.getItem('auth_token');
    
    const response = await fetch('/api/v1/bff/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        service: 'risk',
        operation: 'calculate_var',
        data: {
          portfolio_id: portfolioId,
          confidence_level: confidenceLevel,
          time_horizon: 1
        },
        region: 'usa'
      })
    });

    const result = await response.json();
    
    if (result.success) {
      return result.data.var;
    } else {
      throw new Error(result.error || 'Risk calculation failed');
    }
  } catch (error) {
    console.error('Risk calculation error:', error);
    throw error;
  }
};

// Example 5: Compliance Validation
export const validateTrade = async (tradeData: any) => {
  try {
    const token = localStorage.getItem('auth_token');
    
    const response = await fetch('/api/v1/bff/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        service: 'compliance',
        operation: 'validate_trade',
        data: tradeData,
        region: 'middle_east' // Adjust based on user's jurisdiction
      })
    });

    const result = await response.json();
    
    if (result.success) {
      return result.data.validation;
    } else {
      throw new Error(result.error || 'Trade validation failed');
    }
  } catch (error) {
    console.error('Trade validation error:', error);
    throw error;
  }
};

// Example 6: WebSocket Connection for Real-time Updates
export class QenergyzWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  connect(userId: string, sessionId: string) {
    const wsUrl = `ws://localhost:8000/api/v1/bff/ws?user_id=${userId}&session_id=${sessionId}`;
    
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      
      // Send ping to keep connection alive
      this.sendMessage({ type: 'ping' });
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.reconnect(userId, sessionId);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
  
  private handleMessage(message: any) {
    switch (message.type) {
      case 'pong':
        // Handle ping response
        break;
      case 'service_update':
        // Handle service updates (trading, risk, etc.)
        this.onServiceUpdate?.(message);
        break;
      case 'market_update':
        // Handle market data updates
        this.onMarketUpdate?.(message);
        break;
      case 'portfolio_update':
        // Handle portfolio updates
        this.onPortfolioUpdate?.(message);
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }
  
  private reconnect(userId: string, sessionId: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect(userId, sessionId);
      }, 1000 * Math.pow(2, this.reconnectAttempts)); // Exponential backoff
    }
  }
  
  sendMessage(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }
  
  subscribeToMarketData(symbols: string[]) {
    this.sendMessage({
      type: 'subscribe',
      subscription: 'market_data',
      symbols: symbols
    });
  }
  
  subscribeToPortfolioUpdates() {
    this.sendMessage({
      type: 'subscribe',
      subscription: 'portfolio_updates'
    });
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  // Event handlers (to be set by application)
  onServiceUpdate?: (message: any) => void;
  onMarketUpdate?: (message: any) => void;
  onPortfolioUpdate?: (message: any) => void;
}

// Example 7: Complete Trading Workflow
export const executeCompleteTradeFlow = async (tradeRequest: any) => {
  try {
    // Step 1: Get current portfolio
    const portfolio = await getPortfolio();
    
    // Step 2: Calculate risk
    const risk = await calculateRisk(portfolio.id);
    
    // Step 3: Validate compliance
    const compliance = await validateTrade(tradeRequest);
    
    if (!compliance.compliant) {
      throw new Error(`Trade not compliant: ${compliance.violations.join(', ')}`);
    }
    
    // Step 4: Execute trade if all checks pass
    const token = localStorage.getItem('auth_token');
    
    const response = await fetch('/api/v1/bff/request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        service: 'trading',
        operation: 'create_order',
        data: tradeRequest,
        region: 'usa'
      })
    });

    const result = await response.json();
    
    if (result.success) {
      return {
        trade: result.data.trade,
        portfolio: portfolio,
        risk: risk,
        compliance: compliance
      };
    } else {
      throw new Error(result.error || 'Trade execution failed');
    }
  } catch (error) {
    console.error('Complete trade flow error:', error);
    throw error;
  }
};

// Example 8: Error Handling with Retry Logic
export const apiRequestWithRetry = async (requestConfig: any, maxRetries = 3) => {
  let lastError;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch('/api/v1/bff/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify(requestConfig)
      });

      if (response.status === 429) { // Rate limit
        const retryAfter = response.headers.get('Retry-After') || '1';
        await new Promise(resolve => setTimeout(resolve, parseInt(retryAfter) * 1000));
        continue;
      }

      const result = await response.json();
      
      if (result.success) {
        return result.data;
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      lastError = error;
      
      if (attempt < maxRetries) {
        // Exponential backoff
        await new Promise(resolve => 
          setTimeout(resolve, 1000 * Math.pow(2, attempt - 1))
        );
      }
    }
  }
  
  throw lastError;
};

// Example 9: Health Check for BFF Status
export const checkBFFHealth = async () => {
  try {
    const response = await fetch('/api/v1/bff/health');
    const health = await response.json();
    
    return {
      status: health.status,
      services: health.services,
      oauthProviders: health.oauth_providers,
      timestamp: health.timestamp
    };
  } catch (error) {
    console.error('BFF health check failed:', error);
    return {
      status: 'unhealthy',
      error: error.message
    };
  }
};

// Example 10: Logout and Token Cleanup
export const logout = async (provider: string) => {
  try {
    const token = localStorage.getItem('auth_token');
    
    if (token) {
      // Revoke OAuth token if possible
      await fetch('/api/v1/bff/oauth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          provider: provider,
          access_token: token
        })
      });
    }
  } catch (error) {
    console.warn('Token revocation failed:', error);
  } finally {
    // Clean up local storage
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
    
    // Redirect to login
    window.location.href = '/login';
  }
};

// Usage Example in React Component:
/*
import { useEffect, useState } from 'react';

const TradingDashboard = () => {
  const [portfolio, setPortfolio] = useState(null);
  const [ws, setWs] = useState(null);
  
  useEffect(() => {
    // Initialize WebSocket connection
    const websocket = new QenergyzWebSocket();
    websocket.onPortfolioUpdate = (message) => {
      setPortfolio(message.data);
    };
    websocket.connect('user123', 'session456');
    setWs(websocket);
    
    // Load initial portfolio
    getPortfolio().then(setPortfolio);
    
    return () => websocket.disconnect();
  }, []);
  
  const handleTrade = async (tradeData) => {
    try {
      const result = await executeCompleteTradeFlow(tradeData);
      console.log('Trade executed successfully:', result);
      // Update UI
    } catch (error) {
      console.error('Trade failed:', error);
      // Show error message
    }
  };
  
  return (
    <div>
      {portfolio && (
        <div>
          <h2>Portfolio Value: ${portfolio.total_value}</h2>
          // ... render portfolio details
        </div>
      )}
    </div>
  );
};
*/