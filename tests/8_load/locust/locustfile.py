"""
Locust Load Testing Configuration for Qenergyz API
"""
import random
import json
from locust import HttpUser, task, between


class QenergyZAPIUser(HttpUser):
    """
    Simulates a typical Qenergyz platform user
    """
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Initialize user session"""
        self.auth_token = None
        self.user_id = f"load_test_user_{random.randint(1000, 9999)}"
        self.login()
    
    def login(self):
        """Simulate user authentication"""
        # Mock authentication for load testing
        login_data = {
            "username": self.user_id,
            "password": "load_test_password"
        }
        
        with self.client.post("/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                self.auth_token = "mock_token_" + self.user_id
                response.success()
            else:
                response.failure(f"Login failed with status {response.status_code}")
    
    @property
    def auth_headers(self):
        """Return authentication headers"""
        return {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
    
    @task(3)
    def check_health(self):
        """Basic health check - most frequent task"""
        self.client.get("/health")
    
    @task(2)
    def get_market_data(self):
        """Fetch market data"""
        symbols = ["WTI", "BRENT", "NATGAS", "HEATING_OIL"]
        symbol = random.choice(symbols)
        
        with self.client.get(f"/api/v1/market-data/{symbol}", 
                           headers=self.auth_headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "price" in data:
                    response.success()
                else:
                    response.failure("Missing price data")
            else:
                response.failure(f"Market data request failed: {response.status_code}")
    
    @task(2)
    def get_portfolio(self):
        """Get user portfolio"""
        with self.client.get("/api/v1/portfolio",
                           headers=self.auth_headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Portfolio request failed: {response.status_code}")
    
    @task(1)
    def create_trade(self):
        """Create a new trade"""
        symbols = ["WTI", "BRENT", "NATGAS"]
        sides = ["buy", "sell"]
        
        trade_data = {
            "symbol": random.choice(symbols),
            "side": random.choice(sides),
            "quantity": random.randint(100, 10000),
            "price": round(random.uniform(50.0, 100.0), 2),
            "order_type": "limit"
        }
        
        with self.client.post("/api/v1/trades",
                            json=trade_data,
                            headers=self.auth_headers,
                            catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Trade creation failed: {response.status_code}")
    
    @task(1)
    def get_risk_metrics(self):
        """Fetch risk management metrics"""
        with self.client.get("/api/v1/risk/metrics",
                           headers=self.auth_headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Risk metrics request failed: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates administrative user behavior
    """
    wait_time = between(10, 30)  # Admin actions are less frequent
    weight = 1  # Lower weight means fewer admin users
    
    def on_start(self):
        """Initialize admin session"""
        self.auth_token = "admin_token_" + str(random.randint(1, 10))
    
    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    @task(1)
    def get_system_metrics(self):
        """Fetch system-wide metrics"""
        self.client.get("/api/v1/admin/metrics", headers=self.auth_headers)
    
    @task(1)
    def get_user_list(self):
        """Get list of users"""
        self.client.get("/api/v1/admin/users", headers=self.auth_headers)


class HighFrequencyTrader(HttpUser):
    """
    Simulates high-frequency trading behavior
    """
    wait_time = between(0.1, 0.5)  # Very fast trading
    weight = 2  # Moderate number of HFT users
    
    def on_start(self):
        self.auth_token = "hft_token_" + str(random.randint(1, 100))
    
    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    @task(5)
    def get_realtime_prices(self):
        """Get real-time price feeds"""
        symbol = random.choice(["WTI", "BRENT"])
        self.client.get(f"/api/v1/realtime/prices/{symbol}", headers=self.auth_headers)
    
    @task(3)
    def execute_rapid_trades(self):
        """Execute rapid trades"""
        trade_data = {
            "symbol": "WTI",
            "side": random.choice(["buy", "sell"]),
            "quantity": random.randint(1000, 50000),
            "order_type": "market"
        }
        
        self.client.post("/api/v1/trades/rapid", json=trade_data, headers=self.auth_headers)


# Load test configuration
class LoadTestConfig:
    """Configuration for different load test scenarios"""
    
    SCENARIOS = {
        "light": {
            "users": 10,
            "spawn_rate": 2,
            "duration": "5m"
        },
        "normal": {
            "users": 50, 
            "spawn_rate": 5,
            "duration": "10m"
        },
        "peak": {
            "users": 200,
            "spawn_rate": 10,
            "duration": "30m"
        },
        "stress": {
            "users": 500,
            "spawn_rate": 20,
            "duration": "15m"
        }
    }