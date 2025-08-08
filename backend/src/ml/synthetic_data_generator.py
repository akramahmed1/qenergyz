"""
Synthetic ETRM Data Generator for Fine-tuning Generative Models

This module generates synthetic Energy Trading and Risk Management data
that can be used to fine-tune generative ML models like GPT-2 or other LLMs.
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

@dataclass
class ETRMDataConfig:
    """Configuration for synthetic ETRM data generation"""
    num_trades: int = 1000
    num_positions: int = 500
    num_risk_reports: int = 100
    start_date: datetime = datetime(2023, 1, 1)
    end_date: datetime = datetime(2024, 12, 31)
    commodities: List[str] = None
    regions: List[str] = None
    
    def __post_init__(self):
        if self.commodities is None:
            self.commodities = ['Crude Oil', 'Natural Gas', 'Gasoline', 'Heating Oil', 'Coal', 'Power']
        if self.regions is None:
            self.regions = ['NYMEX', 'ICE', 'ME', 'EU', 'ASIA', 'AMERICAS']

class SyntheticETRMDataGenerator:
    """Generator for synthetic ETRM data"""
    
    def __init__(self, config: ETRMDataConfig):
        self.config = config
        self.random_state = np.random.RandomState(42)
        
        # Price patterns for different commodities
        self.price_ranges = {
            'Crude Oil': (40, 120),
            'Natural Gas': (2, 15),
            'Gasoline': (1.5, 4.5),
            'Heating Oil': (1.8, 4.2),
            'Coal': (50, 200),
            'Power': (20, 150)
        }
        
        # Trading strategies
        self.strategies = [
            'Momentum', 'Mean Reversion', 'Arbitrage', 'Calendar Spread',
            'Crack Spread', 'Basis Trading', 'Weather Hedge', 'Swing Trading'
        ]
        
        # Risk factors
        self.risk_factors = [
            'Price Risk', 'Basis Risk', 'Volumetric Risk', 'Credit Risk',
            'Operational Risk', 'Regulatory Risk', 'Weather Risk', 'Storage Risk'
        ]

    def generate_price_series(self, commodity: str, days: int) -> np.ndarray:
        """Generate realistic price series using GBM with volatility clustering"""
        base_price, max_price = self.price_ranges[commodity]
        
        # Parameters for geometric brownian motion
        mu = 0.02 / 365  # Annual drift
        
        # Volatility varies by commodity
        volatility_map = {
            'Crude Oil': 0.35,
            'Natural Gas': 0.65,
            'Gasoline': 0.45,
            'Heating Oil': 0.40,
            'Coal': 0.25,
            'Power': 0.85
        }
        sigma = volatility_map.get(commodity, 0.40) / np.sqrt(365)
        
        # Generate price path
        dt = 1
        prices = [base_price + (max_price - base_price) * 0.3]  # Starting price
        
        for _ in range(days - 1):
            # Add volatility clustering
            vol_factor = 1 + 0.3 * np.sin(len(prices) / 30) * self.random_state.normal(0, 0.1)
            current_sigma = sigma * vol_factor
            
            dW = self.random_state.normal(0, np.sqrt(dt))
            price_change = mu * prices[-1] * dt + current_sigma * prices[-1] * dW
            new_price = max(prices[-1] + price_change, base_price * 0.5)  # Floor price
            prices.append(min(new_price, max_price * 1.5))  # Cap price
        
        return np.array(prices)

    def generate_trading_data(self) -> pd.DataFrame:
        """Generate synthetic trading transactions"""
        trades = []
        
        for i in range(self.config.num_trades):
            commodity = self.random_state.choice(self.config.commodities)
            region = self.random_state.choice(self.config.regions)
            strategy = self.random_state.choice(self.strategies)
            
            # Random trade date
            days_range = (self.config.end_date - self.config.start_date).days
            trade_date = self.config.start_date + timedelta(days=self.random_state.randint(0, days_range))
            
            # Trade details
            base_price, max_price = self.price_ranges[commodity]
            price = self.random_state.uniform(base_price, max_price)
            volume = self.random_state.lognormal(mean=5, sigma=1.5)  # Log-normal volume
            
            # Direction and counterparty
            direction = self.random_state.choice(['Buy', 'Sell'])
            counterparty = f"Counterparty_{self.random_state.randint(1, 50)}"
            
            # Contract details
            contract_type = self.random_state.choice(['Spot', 'Forward', 'Future', 'Option', 'Swap'])
            delivery_start = trade_date + timedelta(days=self.random_state.randint(1, 365))
            delivery_end = delivery_start + timedelta(days=self.random_state.randint(1, 30))
            
            trades.append({
                'trade_id': f"TRD_{i:06d}",
                'trade_date': trade_date,
                'commodity': commodity,
                'region': region,
                'strategy': strategy,
                'direction': direction,
                'volume': round(volume, 2),
                'price': round(price, 2),
                'counterparty': counterparty,
                'contract_type': contract_type,
                'delivery_start': delivery_start,
                'delivery_end': delivery_end,
                'trader': f"Trader_{self.random_state.randint(1, 20)}",
                'book': f"Book_{self.random_state.choice(['AMERICAS', 'EMEA', 'APAC'])}"
            })
        
        return pd.DataFrame(trades)

    def generate_position_data(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """Generate position data based on trades"""
        positions = []
        
        # Group trades by commodity, region, and book to create positions
        for (commodity, region, book), group in trades_df.groupby(['commodity', 'region', 'book']):
            # Calculate net position
            buy_volume = group[group['direction'] == 'Buy']['volume'].sum()
            sell_volume = group[group['direction'] == 'Sell']['volume'].sum()
            net_position = buy_volume - sell_volume
            
            if abs(net_position) > 0.01:  # Only include non-zero positions
                avg_price = group['price'].mean()
                
                # Calculate risk metrics
                var_95 = abs(net_position) * avg_price * 0.03  # 3% VaR assumption
                var_99 = var_95 * 1.5
                
                positions.append({
                    'position_id': f"POS_{len(positions):06d}",
                    'commodity': commodity,
                    'region': region,
                    'book': book,
                    'net_position': round(net_position, 2),
                    'avg_price': round(avg_price, 2),
                    'market_value': round(net_position * avg_price, 2),
                    'var_95': round(var_95, 2),
                    'var_99': round(var_99, 2),
                    'last_updated': datetime.now(),
                    'risk_limit': round(var_95 * 10, 2)  # Risk limit
                })
        
        return pd.DataFrame(positions)

    def generate_risk_reports(self, positions_df: pd.DataFrame) -> pd.DataFrame:
        """Generate synthetic risk reports"""
        reports = []
        
        for i in range(self.config.num_risk_reports):
            report_date = self.config.start_date + timedelta(days=i * 3)  # Every 3 days
            
            # Portfolio level metrics
            total_var_95 = positions_df['var_95'].sum() * self.random_state.uniform(0.7, 1.3)
            total_var_99 = positions_df['var_99'].sum() * self.random_state.uniform(0.7, 1.3)
            
            # Risk factor contributions
            risk_contributions = {}
            for factor in self.risk_factors:
                risk_contributions[factor] = self.random_state.uniform(0.05, 0.35)
            
            # Normalize contributions to sum to 1
            total_contrib = sum(risk_contributions.values())
            risk_contributions = {k: v/total_contrib for k, v in risk_contributions.items()}
            
            reports.append({
                'report_id': f"RPT_{i:06d}",
                'report_date': report_date,
                'total_var_95': round(total_var_95, 2),
                'total_var_99': round(total_var_99, 2),
                'positions_count': len(positions_df),
                'risk_contributions': risk_contributions,
                'stress_test_results': {
                    'oil_shock_-20%': round(total_var_95 * self.random_state.uniform(1.5, 2.5), 2),
                    'gas_spike_+50%': round(total_var_95 * self.random_state.uniform(1.2, 2.0), 2),
                    'volatility_spike': round(total_var_95 * self.random_state.uniform(1.8, 3.0), 2)
                },
                'compliance_status': self.random_state.choice(['PASS', 'WARN', 'FAIL'], p=[0.8, 0.15, 0.05]),
                'key_risks': self.random_state.choice(self.risk_factors, size=3, replace=False).tolist()
            })
        
        return pd.DataFrame(reports)

    def generate_text_descriptions(self, trades_df: pd.DataFrame, 
                                 positions_df: pd.DataFrame, 
                                 reports_df: pd.DataFrame) -> List[str]:
        """Generate text descriptions for LLM training"""
        texts = []
        
        # Trade descriptions
        for _, trade in trades_df.head(100).iterrows():  # Sample 100 trades
            text = f"""
Trade Analysis: {trade['trade_id']}
Date: {trade['trade_date'].strftime('%Y-%m-%d')}
Action: {trade['direction']} {trade['volume']:,.0f} units of {trade['commodity']} at ${trade['price']:.2f}
Strategy: {trade['strategy']}
Region: {trade['region']}
Counterparty: {trade['counterparty']}
Contract Type: {trade['contract_type']}
Book: {trade['book']}
Total Value: ${trade['volume'] * trade['price']:,.2f}
"""
            texts.append(text.strip())
        
        # Position descriptions
        for _, position in positions_df.head(50).iterrows():  # Sample 50 positions
            risk_status = "HIGH RISK" if position['var_95'] > position['risk_limit'] * 0.8 else "NORMAL"
            text = f"""
Position Report: {position['position_id']}
Commodity: {position['commodity']} ({position['region']})
Net Position: {position['net_position']:,.0f} units
Average Price: ${position['avg_price']:.2f}
Market Value: ${position['market_value']:,.2f}
Value at Risk (95%): ${position['var_95']:,.2f}
Value at Risk (99%): ${position['var_99']:,.2f}
Risk Status: {risk_status}
Book: {position['book']}
"""
            texts.append(text.strip())
        
        # Risk report descriptions
        for _, report in reports_df.head(20).iterrows():  # Sample 20 reports
            top_risks = ", ".join(report['key_risks'])
            text = f"""
Daily Risk Report: {report['report_date'].strftime('%Y-%m-%d')}
Portfolio Value at Risk (95%): ${report['total_var_95']:,.2f}
Portfolio Value at Risk (99%): ${report['total_var_99']:,.2f}
Number of Positions: {report['positions_count']}
Compliance Status: {report['compliance_status']}
Key Risk Factors: {top_risks}
Stress Test - Oil Shock (-20%): ${report['stress_test_results']['oil_shock_-20%']:,.2f}
Stress Test - Gas Spike (+50%): ${report['stress_test_results']['gas_spike_+50%']:,.2f}
Stress Test - Volatility Spike: ${report['stress_test_results']['volatility_spike']:,.2f}
"""
            texts.append(text.strip())
        
        return texts

    def generate_complete_dataset(self) -> Dict:
        """Generate complete synthetic ETRM dataset"""
        print("Generating trading data...")
        trades_df = self.generate_trading_data()
        
        print("Generating position data...")
        positions_df = self.generate_position_data(trades_df)
        
        print("Generating risk reports...")
        reports_df = self.generate_risk_reports(positions_df)
        
        print("Generating text descriptions...")
        text_descriptions = self.generate_text_descriptions(trades_df, positions_df, reports_df)
        
        # Price series for each commodity
        print("Generating price series...")
        price_series = {}
        days = (self.config.end_date - self.config.start_date).days
        for commodity in self.config.commodities:
            price_series[commodity] = self.generate_price_series(commodity, days)
        
        return {
            'trades': trades_df,
            'positions': positions_df,
            'risk_reports': reports_df,
            'text_descriptions': text_descriptions,
            'price_series': price_series,
            'metadata': {
                'num_trades': len(trades_df),
                'num_positions': len(positions_df),
                'num_reports': len(reports_df),
                'num_texts': len(text_descriptions),
                'date_range': (self.config.start_date, self.config.end_date),
                'commodities': self.config.commodities,
                'regions': self.config.regions
            }
        }

def save_dataset(dataset: Dict, output_dir: str = "synthetic_etrm_data"):
    """Save generated dataset to files"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # Save dataframes
    dataset['trades'].to_csv(f"{output_dir}/trades.csv", index=False)
    dataset['positions'].to_csv(f"{output_dir}/positions.csv", index=False)
    dataset['risk_reports'].to_csv(f"{output_dir}/risk_reports.csv", index=False)
    
    # Save text descriptions
    with open(f"{output_dir}/text_descriptions.txt", 'w') as f:
        for text in dataset['text_descriptions']:
            f.write(text + "\n\n---\n\n")
    
    # Save price series
    np.savez(f"{output_dir}/price_series.npz", **dataset['price_series'])
    
    # Save metadata
    with open(f"{output_dir}/metadata.json", 'w') as f:
        metadata = dataset['metadata'].copy()
        metadata['date_range'] = [d.isoformat() for d in metadata['date_range']]
        json.dump(metadata, f, indent=2)
    
    print(f"Dataset saved to {output_dir}/")


if __name__ == "__main__":
    # Generate synthetic dataset
    config = ETRMDataConfig(
        num_trades=5000,
        num_risk_reports=200,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 12, 31)
    )
    
    generator = SyntheticETRMDataGenerator(config)
    dataset = generator.generate_complete_dataset()
    
    # Save dataset
    save_dataset(dataset)
    
    # Print summary
    print("\nDataset Summary:")
    print(f"Trades: {len(dataset['trades'])}")
    print(f"Positions: {len(dataset['positions'])}")
    print(f"Risk Reports: {len(dataset['risk_reports'])}")
    print(f"Text Descriptions: {len(dataset['text_descriptions'])}")
    print(f"Commodities: {dataset['metadata']['commodities']}")