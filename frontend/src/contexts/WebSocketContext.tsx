import React, { createContext, useContext, useEffect, useState, useRef } from 'react'
import { useAuth } from './AuthContext'

interface WebSocketContextType {
  socket: WebSocket | null
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
  sendMessage: (message: any) => void
  lastMessage: any
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

interface WebSocketProviderProps {
  children: React.ReactNode
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { isAuthenticated, token } = useAuth()
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const [lastMessage, setLastMessage] = useState<any>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5
  const reconnectInterval = useRef<NodeJS.Timeout>()

  const connect = () => {
    if (!isAuthenticated || !token) {
      return
    }

    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    const ws = new WebSocket(`${wsUrl}?token=${token}`)

    setConnectionStatus('connecting')

    ws.onopen = () => {
      console.log('WebSocket connected')
      setConnectionStatus('connected')
      setSocket(ws)
      reconnectAttempts.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        setLastMessage(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setConnectionStatus('disconnected')
      setSocket(null)

      // Attempt to reconnect
      if (reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++
        console.log(`Attempting to reconnect... (${reconnectAttempts.current}/${maxReconnectAttempts})`)
        reconnectInterval.current = setTimeout(connect, 1000 * reconnectAttempts.current)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setConnectionStatus('error')
    }
  }

  const disconnect = () => {
    if (reconnectInterval.current) {
      clearTimeout(reconnectInterval.current)
    }
    if (socket) {
      socket.close()
      setSocket(null)
    }
    setConnectionStatus('disconnected')
  }

  const sendMessage = (message: any) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
  }, [isAuthenticated, token])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [])

  return (
    <WebSocketContext.Provider 
      value={{
        socket,
        connectionStatus,
        sendMessage,
        lastMessage
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}