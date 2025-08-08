"""
Unit tests for trading service
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from src.services.trading import (
    TradingService, Order, Trade, OrderType, OrderSide, OrderStatus,
    TradingInstrument, InstrumentType, TradingRegion,
    PlaceOrderCommand, CancelOrderCommand,
    MarketOrderStrategy, LimitOrderStrategy, IcebergOrderStrategy,
    OrderExecutionStrategyFactory
)

@pytest.fixture
def trading_service():
    """Create a trading service instance"""
    return TradingService()

@pytest.fixture
def sample_instrument():
    """Create a sample trading instrument"""
    return TradingInstrument(
        symbol="WTI",
        name="West Texas Intermediate",
        instrument_type=InstrumentType.CRUDE_OIL,
        region=TradingRegion.USA,
        currency="USD",
        minimum_quantity=1.0,
        tick_size=0.01,
        contract_size=1000.0
    )

@pytest.fixture
def sample_order(sample_instrument):
    """Create a sample order"""
    return Order(
        instrument=sample_instrument,
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=100.0,
        trader_id="test_trader",
        portfolio_id="test_portfolio"
    )

class TestTradingService:
    """Test trading service functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, trading_service):
        """Test service initialization"""
        with patch('aioredis.from_url') as mock_redis, \
             patch('aiokafka.AIOKafkaProducer') as mock_kafka:
            
            mock_redis.return_value = Mock()
            mock_kafka.return_value.start = AsyncMock()
            
            await trading_service.initialize()
            
            assert mock_redis.called
            assert len(trading_service.instruments) > 0

    @pytest.mark.asyncio 
    async def test_validate_order_success(self, trading_service, sample_order):
        """Test successful order validation"""
        result = await trading_service.validate_order(sample_order)
        
        assert result['valid'] is True

    @pytest.mark.asyncio
    async def test_validate_order_missing_instrument(self, trading_service):
        """Test order validation with missing instrument"""
        order = Order(
            instrument=None,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100.0
        )
        
        result = await trading_service.validate_order(order)
        
        assert result['valid'] is False
        assert 'Missing instrument' in result['error']

    @pytest.mark.asyncio
    async def test_validate_order_invalid_quantity(self, trading_service, sample_instrument):
        """Test order validation with invalid quantity"""
        order = Order(
            instrument=sample_instrument,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=0.0
        )
        
        result = await trading_service.validate_order(order)
        
        assert result['valid'] is False
        assert 'Invalid quantity' in result['error']

class TestOrderExecutionStrategies:
    """Test order execution strategies"""
    
    @pytest.mark.asyncio
    async def test_market_order_strategy(self, sample_order):
        """Test market order execution strategy"""
        strategy = MarketOrderStrategy()
        trades = await strategy.execute_order(sample_order)
        
        assert len(trades) == 1
        assert trades[0].order_id == sample_order.order_id
        assert trades[0].quantity == sample_order.quantity
        assert trades[0].price > 0

    @pytest.mark.asyncio
    async def test_limit_order_strategy_executable(self, sample_instrument):
        """Test limit order strategy when executable"""
        order = Order(
            instrument=sample_instrument,
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=100.0,
            price=100.0  # High price to ensure execution
        )
        
        strategy = LimitOrderStrategy()
        with patch.object(strategy, '_get_market_price', return_value=75.50):
            trades = await strategy.execute_order(order)
        
        assert len(trades) == 1
        assert trades[0].price == order.price

    @pytest.mark.asyncio
    async def test_limit_order_strategy_not_executable(self, sample_instrument):
        """Test limit order strategy when not executable"""
        order = Order(
            instrument=sample_instrument,
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=100.0,
            price=50.0  # Low price to prevent execution
        )
        
        strategy = LimitOrderStrategy()
        with patch.object(strategy, '_get_market_price', return_value=75.50):
            trades = await strategy.execute_order(order)
        
        assert len(trades) == 0

    @pytest.mark.asyncio
    async def test_iceberg_order_strategy(self, sample_instrument):
        """Test iceberg order strategy"""
        order = Order(
            instrument=sample_instrument,
            order_type=OrderType.ICEBERG,
            side=OrderSide.BUY,
            quantity=250.0  # Will be split into multiple slices
        )
        
        strategy = IcebergOrderStrategy(slice_size=100.0)
        with patch('asyncio.sleep'):  # Skip delays in tests
            trades = await strategy.execute_order(order)
        
        assert len(trades) >= 2  # Should be split into multiple trades
        total_quantity = sum(trade.quantity for trade in trades)
        assert total_quantity == order.quantity

class TestOrderExecutionStrategyFactory:
    """Test order execution strategy factory"""
    
    def test_create_market_strategy(self):
        """Test creating market order strategy"""
        strategy = OrderExecutionStrategyFactory.create_strategy(OrderType.MARKET)
        assert isinstance(strategy, MarketOrderStrategy)

    def test_create_limit_strategy(self):
        """Test creating limit order strategy"""
        strategy = OrderExecutionStrategyFactory.create_strategy(OrderType.LIMIT)
        assert isinstance(strategy, LimitOrderStrategy)

    def test_create_iceberg_strategy(self):
        """Test creating iceberg order strategy"""
        strategy = OrderExecutionStrategyFactory.create_strategy(OrderType.ICEBERG)
        assert isinstance(strategy, IcebergOrderStrategy)

    def test_create_unsupported_strategy(self):
        """Test creating unsupported strategy raises error"""
        with pytest.raises(ValueError):
            OrderExecutionStrategyFactory.create_strategy("unsupported")

class TestTradingCommands:
    """Test trading command pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_place_order_command(self, trading_service, sample_order):
        """Test place order command execution"""
        command = PlaceOrderCommand(trading_service, sample_order)
        
        with patch.object(trading_service, 'validate_order', return_value={'valid': True}), \
             patch.object(trading_service, 'store_order'), \
             patch.object(trading_service, 'store_trade'), \
             patch.object(trading_service, 'update_portfolio_positions'):
            
            result = await command.execute()
            
            assert result['order_id'] == sample_order.order_id
            assert 'status' in result
            assert 'trades' in result

    @pytest.mark.asyncio
    async def test_cancel_order_command(self, trading_service, sample_order):
        """Test cancel order command execution"""
        # First place the order
        trading_service.orders[sample_order.order_id] = sample_order
        
        command = CancelOrderCommand(trading_service, sample_order.order_id)
        
        with patch.object(trading_service, 'store_order'):
            result = await command.execute()
            
            assert result['order_id'] == sample_order.order_id
            assert result['status'] == 'cancelled'