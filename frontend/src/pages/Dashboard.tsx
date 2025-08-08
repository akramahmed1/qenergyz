import React from 'react'
import { useTranslation } from 'react-i18next'

const Dashboard: React.FC = () => {
  const { t } = useTranslation()

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-foreground mb-6">
        {t('dashboard.title', 'Dashboard')}
      </h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-card p-6 rounded-lg border">
          <h3 className="text-sm font-medium text-secondary mb-2">
            {t('dashboard.portfolioValue', 'Portfolio Value')}
          </h3>
          <p className="text-2xl font-bold text-foreground">$2,456,789</p>
          <p className="text-sm text-success">+2.5% today</p>
        </div>
        
        <div className="bg-card p-6 rounded-lg border">
          <h3 className="text-sm font-medium text-secondary mb-2">
            {t('dashboard.todaysPnL', "Today's P&L")}
          </h3>
          <p className="text-2xl font-bold text-success">+$12,345</p>
          <p className="text-sm text-secondary">+0.5%</p>
        </div>
        
        <div className="bg-card p-6 rounded-lg border">
          <h3 className="text-sm font-medium text-secondary mb-2">
            {t('dashboard.openPositions', 'Open Positions')}
          </h3>
          <p className="text-2xl font-bold text-foreground">23</p>
          <p className="text-sm text-secondary">Active trades</p>
        </div>
        
        <div className="bg-card p-6 rounded-lg border">
          <h3 className="text-sm font-medium text-secondary mb-2">
            {t('dashboard.riskExposure', 'Risk Exposure')}
          </h3>
          <p className="text-2xl font-bold text-warning">Medium</p>
          <p className="text-sm text-secondary">VaR: $45,678</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card p-6 rounded-lg border">
          <h2 className="text-xl font-semibold text-foreground mb-4">
            {t('dashboard.recentTrades', 'Recent Trades')}
          </h2>
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex justify-between items-center">
                <div>
                  <p className="font-medium">Crude Oil WTI</p>
                  <p className="text-sm text-secondary">Buy 1000 BBL @ $75.50</p>
                </div>
                <div className="text-right">
                  <p className="text-success">+$2,450</p>
                  <p className="text-sm text-secondary">2 hours ago</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="bg-card p-6 rounded-lg border">
          <h2 className="text-xl font-semibold text-foreground mb-4">
            {t('dashboard.riskAlerts', 'Risk Alerts')}
          </h2>
          <div className="space-y-3">
            <div className="p-3 bg-warning/10 border border-warning/20 rounded-md">
              <p className="font-medium text-warning">Position Limit Warning</p>
              <p className="text-sm text-secondary">Natural Gas position approaching 80% limit</p>
            </div>
            <div className="p-3 bg-info/10 border border-info/20 rounded-md">
              <p className="font-medium text-info">Market Update</p>
              <p className="text-sm text-secondary">Oil prices showing increased volatility</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard