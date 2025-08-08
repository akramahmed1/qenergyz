"""
Qenergyz Trading Service

Implements advanced order management, portfolio tracking, and real-time trading
with WebSocket/Kafka integration, retry logic, circuit breakers, and design patterns
including Factory, Strategy, and Command patterns.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from pybreaker import CircuitBreaker
import aioredis
import aiokafka

logger = structlog.get_logger(__name__)

# Enums for trading operations
class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class InstrumentType(str, Enum):
    CRUDE_OIL = "crude_oil"
    NATURAL_GAS = "natural_gas"
    REFINED_PRODUCTS = "refined_products"
    POWER = "power"
    RENEWABLE = "renewable"

class TradingRegion(str, Enum):
    MIDDLE_EAST = "middle_east"
    USA = "usa"
    UK = "uk"
    EUROPE = "europe"
    GUYANA = "guyana"

# Data classes for trading entities
@dataclass
class TradingInstrument:
    """Represents a tradable energy instrument"""
    symbol: str
    name: str
    instrument_type: InstrumentType
    region: TradingRegion
    currency: str
    minimum_quantity: float
    tick_size: float
    contract_size: float
    expiry_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Order:
    """Represents a trading order"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: str = ""
    instrument: TradingInstrument = None
    order_type: OrderType = OrderType.MARKET
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_fill_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    trader_id: str = ""
    portfolio_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.remaining_quantity = self.quantity - self.filled_quantity

@dataclass
class Trade:
    """Represents an executed trade"""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    instrument: TradingInstrument = None
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    price: float = 0.0
    execution_time: datetime = field(default_factory=datetime.utcnow)
    counterparty: str = ""
    trader_id: str = ""
    portfolio_id: str = ""
    commission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Position:
    """Represents a portfolio position"""
    position_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    instrument: TradingInstrument = None
    quantity: float = 0.0
    average_cost: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    portfolio_id: str = ""
    last_updated: datetime = field(default_factory=datetime.utcnow)

@dataclass  
class Portfolio:
    """Represents a trading portfolio"""
    portfolio_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    trader_id: str = ""
    positions: Dict[str, Position] = field(default_factory=dict)
    cash_balance: float = 0.0
    total_value: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

# Strategy Pattern for Order Execution
class OrderExecutionStrategy(ABC):
    """Abstract base class for order execution strategies"""
    
    @abstractmethod
    async def execute_order(self, order: Order) -> List[Trade]:
        """Execute an order using specific strategy"""
        pass

class MarketOrderStrategy(OrderExecutionStrategy):
    """Strategy for market order execution"""
    
    async def execute_order(self, order: Order) -> List[Trade]:
        """Execute market order at current market price"""
        logger.info("Executing market order", order_id=order.order_id)
        
        # Simulate market execution - in real implementation would connect to exchanges
        market_price = await self._get_market_price(order.instrument)
        
        trade = Trade(
            order_id=order.order_id,
            instrument=order.instrument,
            side=order.side,
            quantity=order.quantity,
            price=market_price,
            trader_id=order.trader_id,
            portfolio_id=order.portfolio_id
        )
        
        return [trade]
    
    async def _get_market_price(self, instrument: TradingInstrument) -> float:
        """Get current market price for instrument"""
        # Mock implementation - would integrate with real market data
        base_price = {
            InstrumentType.CRUDE_OIL: 75.50,
            InstrumentType.NATURAL_GAS: 3.25,
            InstrumentType.REFINED_PRODUCTS: 2.15,
            InstrumentType.POWER: 45.00,
            InstrumentType.RENEWABLE: 35.00
        }.get(instrument.instrument_type, 50.00)
        
        return base_price

class LimitOrderStrategy(OrderExecutionStrategy):
    """Strategy for limit order execution"""
    
    async def execute_order(self, order: Order) -> List[Trade]:
        """Execute limit order when price conditions are met"""
        logger.info("Processing limit order", order_id=order.order_id)
        
        current_price = await self._get_market_price(order.instrument)
        
        # Check if limit order can be executed
        can_execute = False
        if order.side == OrderSide.BUY and current_price <= order.price:
            can_execute = True
        elif order.side == OrderSide.SELL and current_price >= order.price:
            can_execute = True
        
        if can_execute:
            trade = Trade(
                order_id=order.order_id,
                instrument=order.instrument,
                side=order.side,
                quantity=order.quantity,
                price=order.price,
                trader_id=order.trader_id,
                portfolio_id=order.portfolio_id
            )
            return [trade]
        
        return []  # Order not executed
    
    async def _get_market_price(self, instrument: TradingInstrument) -> float:
        """Get current market price for instrument"""
        # Mock implementation
        return 75.50

class IcebergOrderStrategy(OrderExecutionStrategy):
    """Strategy for iceberg order execution"""
    
    def __init__(self, slice_size: float = 100.0):
        self.slice_size = slice_size
    
    async def execute_order(self, order: Order) -> List[Trade]:
        """Execute iceberg order in smaller slices"""
        logger.info("Executing iceberg order", order_id=order.order_id, slice_size=self.slice_size)
        
        trades = []
        remaining_qty = order.quantity
        
        while remaining_qty > 0:
            slice_qty = min(self.slice_size, remaining_qty)
            
            # Create slice order
            slice_order = Order(
                instrument=order.instrument,
                order_type=OrderType.MARKET,
                side=order.side,
                quantity=slice_qty,
                trader_id=order.trader_id,
                portfolio_id=order.portfolio_id
            )
            
            # Execute slice
            market_strategy = MarketOrderStrategy()
            slice_trades = await market_strategy.execute_order(slice_order)
            trades.extend(slice_trades)
            
            remaining_qty -= slice_qty
            
            # Add delay between slices to avoid market impact
            await asyncio.sleep(1.0)
        
        return trades

# Factory Pattern for Order Execution Strategies
class OrderExecutionStrategyFactory:
    """Factory for creating order execution strategies"""
    
    @staticmethod
    def create_strategy(order_type: OrderType) -> OrderExecutionStrategy:
        """Create appropriate execution strategy based on order type"""
        if order_type == OrderType.MARKET:
            return MarketOrderStrategy()
        elif order_type == OrderType.LIMIT:
            return LimitOrderStrategy()
        elif order_type == OrderType.ICEBERG:
            return IcebergOrderStrategy()
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

# Command Pattern for Trading Operations
class TradingCommand(ABC):
    """Abstract base class for trading commands"""
    
    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Execute the trading command"""
        pass
    
    @abstractmethod
    async def undo(self) -> Dict[str, Any]:
        """Undo the trading command"""
        pass

class PlaceOrderCommand(TradingCommand):
    """Command to place a trading order"""
    
    def __init__(self, trading_service: 'TradingService', order: Order):
        self.trading_service = trading_service
        self.order = order
        self.executed_trades: List[Trade] = []
    
    async def execute(self) -> Dict[str, Any]:
        """Execute order placement"""
        logger.info("Executing place order command", order_id=self.order.order_id)
        
        # Validate order
        validation_result = await self.trading_service.validate_order(self.order)
        if not validation_result['valid']:
            raise ValueError(f"Order validation failed: {validation_result['error']}")
        
        # Execute order using appropriate strategy
        strategy = OrderExecutionStrategyFactory.create_strategy(self.order.order_type)
        self.executed_trades = await strategy.execute_order(self.order)
        
        # Update order status
        if self.executed_trades:
            self.order.status = OrderStatus.FILLED
            self.order.filled_quantity = sum(t.quantity for t in self.executed_trades)
            self.order.average_fill_price = sum(t.price * t.quantity for t in self.executed_trades) / self.order.filled_quantity
        
        # Store order and trades
        await self.trading_service.store_order(self.order)
        for trade in self.executed_trades:
            await self.trading_service.store_trade(trade)
        
        # Update portfolio
        await self.trading_service.update_portfolio_positions(self.order.portfolio_id, self.executed_trades)
        
        return {
            'order_id': self.order.order_id,
            'status': self.order.status,
            'trades': [t.__dict__ for t in self.executed_trades]
        }
    
    async def undo(self) -> Dict[str, Any]:
        """Undo order placement (cancel order)"""
        logger.info("Undoing place order command", order_id=self.order.order_id)
        
        if self.order.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
            # Cannot undo filled orders, but can cancel remaining quantity
            if self.order.remaining_quantity > 0:
                self.order.status = OrderStatus.CANCELLED
                await self.trading_service.store_order(self.order)
        
        return {'order_id': self.order.order_id, 'action': 'cancelled'}

class CancelOrderCommand(TradingCommand):
    """Command to cancel a trading order"""
    
    def __init__(self, trading_service: 'TradingService', order_id: str):
        self.trading_service = trading_service
        self.order_id = order_id
        self.original_status = None
    
    async def execute(self) -> Dict[str, Any]:
        """Execute order cancellation"""
        logger.info("Executing cancel order command", order_id=self.order_id)
        
        order = await self.trading_service.get_order(self.order_id)
        if not order:
            raise ValueError(f"Order not found: {self.order_id}")
        
        self.original_status = order.status
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel order in status: {order.status}")
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        await self.trading_service.store_order(order)
        
        return {'order_id': self.order_id, 'status': 'cancelled'}
    
    async def undo(self) -> Dict[str, Any]:
        """Undo order cancellation (reactivate order)"""
        logger.info("Undoing cancel order command", order_id=self.order_id)
        
        order = await self.trading_service.get_order(self.order_id)
        if order and self.original_status:
            order.status = self.original_status
            order.updated_at = datetime.utcnow()
            await self.trading_service.store_order(order)
        
        return {'order_id': self.order_id, 'status': 'reactivated'}

# Main Trading Service
class TradingService:
    """
    Main trading service implementing order management, portfolio tracking,
    and real-time communication with circuit breakers and retry logic.
    """
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.trades: Dict[str, Trade] = {}
        self.portfolios: Dict[str, Portfolio] = {}
        self.instruments: Dict[str, TradingInstrument] = {}
        
        # Circuit breaker for external API calls
        self.api_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            expected_exception=Exception
        )
        
        # Redis client for caching
        self.redis_client: Optional[aioredis.Redis] = None
        
        # Kafka producer for real-time updates
        self.kafka_producer: Optional[aiokafka.AIOKafkaProducer] = None
        
        logger.info("Trading service initialized")
    
    async def initialize(self):
        """Initialize trading service with external connections"""
        try:
            # Initialize Redis connection
            self.redis_client = await aioredis.from_url("redis://localhost:6379")
            
            # Initialize Kafka producer
            self.kafka_producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers='localhost:9092',
                value_serializer=lambda v: json.dumps(v).encode()
            )
            await self.kafka_producer.start()
            
            # Load trading instruments
            await self._load_trading_instruments()
            
            logger.info("Trading service initialization completed")
        except Exception as e:
            logger.error("Trading service initialization failed", error=str(e))
            raise
    
    async def shutdown(self):
        """Graceful shutdown of trading service"""
        try:
            if self.kafka_producer:
                await self.kafka_producer.stop()
            
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("Trading service shutdown completed")
        except Exception as e:
            logger.error("Trading service shutdown error", error=str(e))
    
    async def _load_trading_instruments(self):
        """Load available trading instruments"""
        # Mock data - in real implementation would load from database
        instruments = [
            TradingInstrument("WTI", "West Texas Intermediate", InstrumentType.CRUDE_OIL, TradingRegion.USA, "USD", 1.0, 0.01, 1000.0),
            TradingInstrument("BRENT", "Brent Crude", InstrumentType.CRUDE_OIL, TradingRegion.EUROPE, "USD", 1.0, 0.01, 1000.0),
            TradingInstrument("NATGAS", "Natural Gas", InstrumentType.NATURAL_GAS, TradingRegion.USA, "USD", 10.0, 0.001, 10000.0),
            TradingInstrument("POWER_PJM", "PJM Power", InstrumentType.POWER, TradingRegion.USA, "USD", 1.0, 0.01, 1.0),
        ]
        
        for instrument in instruments:
            self.instruments[instrument.symbol] = instrument
        
        logger.info("Loaded trading instruments", count=len(instruments))
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def validate_order(self, order: Order) -> Dict[str, Any]:
        """Validate trading order with retry logic"""
        try:
            logger.info("Validating order", order_id=order.order_id)
            
            # Basic validation
            if not order.instrument:
                return {'valid': False, 'error': 'Missing instrument'}
            
            if order.quantity <= 0:
                return {'valid': False, 'error': 'Invalid quantity'}
            
            if order.order_type == OrderType.LIMIT and not order.price:
                return {'valid': False, 'error': 'Missing price for limit order'}
            
            # Check instrument minimum quantity
            if order.quantity < order.instrument.minimum_quantity:
                return {'valid': False, 'error': 'Below minimum quantity'}
            
            # Additional validations...
            
            return {'valid': True}
            
        except Exception as e:
            logger.error("Order validation error", error=str(e))
            raise
    
    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place a trading order using Command pattern"""
        command = PlaceOrderCommand(self, order)
        return await command.execute()
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a trading order using Command pattern"""
        command = CancelOrderCommand(self, order_id)
        return await command.execute()
    
    async def store_order(self, order: Order):
        """Store order in database and cache"""
        self.orders[order.order_id] = order
        
        # Cache in Redis
        if self.redis_client:
            await self.redis_client.setex(
                f"order:{order.order_id}",
                3600,  # 1 hour TTL
                json.dumps(order.__dict__, default=str)
            )
        
        # Publish to Kafka for real-time updates
        if self.kafka_producer:
            await self.kafka_producer.send(
                'trading.orders',
                {
                    'event': 'order_updated',
                    'order_id': order.order_id,
                    'status': order.status,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
    
    async def store_trade(self, trade: Trade):
        """Store trade in database and cache"""
        self.trades[trade.trade_id] = trade
        
        # Publish trade execution event
        if self.kafka_producer:
            await self.kafka_producer.send(
                'trading.trades',
                {
                    'event': 'trade_executed',
                    'trade_id': trade.trade_id,
                    'order_id': trade.order_id,
                    'symbol': trade.instrument.symbol,
                    'side': trade.side,
                    'quantity': trade.quantity,
                    'price': trade.price,
                    'timestamp': trade.execution_time.isoformat()
                }
            )
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve order by ID"""
        return self.orders.get(order_id)
    
    async def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Retrieve portfolio by ID"""
        return self.portfolios.get(portfolio_id)
    
    async def update_portfolio_positions(self, portfolio_id: str, trades: List[Trade]):
        """Update portfolio positions based on executed trades"""
        if portfolio_id not in self.portfolios:
            self.portfolios[portfolio_id] = Portfolio(portfolio_id=portfolio_id)
        
        portfolio = self.portfolios[portfolio_id]
        
        for trade in trades:
            symbol = trade.instrument.symbol
            
            if symbol not in portfolio.positions:
                portfolio.positions[symbol] = Position(
                    instrument=trade.instrument,
                    portfolio_id=portfolio_id
                )
            
            position = portfolio.positions[symbol]
            
            # Update position based on trade
            if trade.side == OrderSide.BUY:
                new_quantity = position.quantity + trade.quantity
                if new_quantity != 0:
                    position.average_cost = (
                        (position.average_cost * position.quantity + trade.price * trade.quantity) 
                        / new_quantity
                    )
                position.quantity = new_quantity
            else:  # SELL
                position.quantity -= trade.quantity
                position.realized_pnl += (trade.price - position.average_cost) * trade.quantity
            
            position.last_updated = datetime.utcnow()
        
        portfolio.updated_at = datetime.utcnow()
        
        # Publish portfolio update
        if self.kafka_producer:
            await self.kafka_producer.send(
                'trading.portfolios',
                {
                    'event': 'portfolio_updated',
                    'portfolio_id': portfolio_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for instrument with circuit breaker protection"""
        try:
            @self.api_circuit_breaker
            async def _fetch_market_data():
                # Mock market data - would integrate with real market data providers
                return {
                    'symbol': symbol,
                    'price': 75.50,
                    'bid': 75.45,
                    'ask': 75.55,
                    'volume': 1000000,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            return await _fetch_market_data()
            
        except Exception as e:
            logger.error("Market data fetch failed", symbol=symbol, error=str(e))
            # Return cached data if available
            if self.redis_client:
                cached_data = await self.redis_client.get(f"market_data:{symbol}")
                if cached_data:
                    return json.loads(cached_data)
            raise
    
    async def handle_websocket_message(self, message: str) -> str:
        """Handle WebSocket messages from clients"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscribe_market_data':
                symbol = data.get('symbol')
                market_data = await self.get_market_data(symbol)
                return json.dumps({
                    'type': 'market_data',
                    'data': market_data
                })
            
            elif message_type == 'place_order':
                order_data = data.get('order')
                # Create order from data and place it
                # This would involve proper validation and parsing
                return json.dumps({
                    'type': 'order_response',
                    'data': {'status': 'received', 'message': 'Order processing started'}
                })
            
            else:
                return json.dumps({
                    'type': 'error',
                    'data': {'message': f'Unknown message type: {message_type}'}
                })
                
        except Exception as e:
            logger.error("WebSocket message handling error", error=str(e))
            return json.dumps({
                'type': 'error',
                'data': {'message': 'Message processing failed'}
            })