"""
Qenergyz IoT Integration Service

Implements IoT device integration with MQTT, PyModbus, and OPC UA for oil rigs
and energy infrastructure. Uses Proxy and Composite design patterns with
circuit breakers and timeout handling.
"""

import asyncio
import json
import struct
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import ssl

import structlog
import aiofiles
from pybreaker import CircuitBreaker
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio_mqtt as mqtt
from asyncua import Client as OPCUAClient
from asyncua import ua
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

logger = structlog.get_logger(__name__)

# Enums for IoT operations
class DeviceType(str, Enum):
    OIL_RIG = "oil_rig"
    REFINERY = "refinery"  
    PIPELINE = "pipeline"
    STORAGE_TANK = "storage_tank"
    POWER_PLANT = "power_plant"
    RENEWABLE_FARM = "renewable_farm"
    SENSOR_STATION = "sensor_station"

class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    UNKNOWN = "unknown"

class DataType(str, Enum):
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    FLOW_RATE = "flow_rate"
    VOLUME = "volume"
    POWER = "power"
    VOLTAGE = "voltage"
    FREQUENCY = "frequency"
    VIBRATION = "vibration"
    LEVEL = "level"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class Protocol(str, Enum):
    MQTT = "mqtt"
    MODBUS_TCP = "modbus_tcp"
    OPC_UA = "opc_ua"
    HTTP = "http"

# Data classes for IoT entities
@dataclass
class IoTDevice:
    """Represents an IoT device"""
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    device_type: DeviceType = DeviceType.SENSOR_STATION
    protocol: Protocol = Protocol.MQTT
    connection_string: str = ""
    location: Dict[str, float] = field(default_factory=lambda: {"lat": 0.0, "lon": 0.0})
    status: DeviceStatus = DeviceStatus.UNKNOWN
    last_heartbeat: Optional[datetime] = None
    firmware_version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SensorReading:
    """Represents a sensor reading from IoT device"""
    reading_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    sensor_name: str = ""
    data_type: DataType = DataType.TEMPERATURE
    value: float = 0.0
    unit: str = ""
    quality: float = 1.0  # Data quality score 0-1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    location: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IoTAlert:
    """Represents an IoT device alert"""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    alert_type: str = ""
    sensor_reading: Optional[SensorReading] = None
    threshold_value: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DeviceCommand:
    """Represents a command to send to IoT device"""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    command_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    scheduled_time: Optional[datetime] = None
    executed: bool = False
    execution_time: Optional[datetime] = None
    response: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 30
    retry_count: int = 0
    max_retries: int = 3

# Proxy Pattern for IoT Protocol Abstraction
class IoTProtocolProxy(ABC):
    """Abstract proxy for IoT protocol implementations"""
    
    @abstractmethod
    async def connect(self, connection_config: Dict[str, Any]) -> bool:
        """Connect to IoT device"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from IoT device"""
        pass
    
    @abstractmethod
    async def read_data(self, read_config: Dict[str, Any]) -> List[SensorReading]:
        """Read data from IoT device"""
        pass
    
    @abstractmethod
    async def send_command(self, command: DeviceCommand) -> Dict[str, Any]:
        """Send command to IoT device"""
        pass
    
    @abstractmethod
    async def check_status(self) -> DeviceStatus:
        """Check device status"""
        pass

class MQTTProtocolProxy(IoTProtocolProxy):
    """MQTT protocol proxy implementation"""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.connection_config = {}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=Exception
        )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def connect(self, connection_config: Dict[str, Any]) -> bool:
        """Connect to MQTT broker"""
        try:
            self.connection_config = connection_config
            
            broker_host = connection_config.get('host', 'localhost')
            broker_port = connection_config.get('port', 1883)
            username = connection_config.get('username')
            password = connection_config.get('password')
            use_tls = connection_config.get('use_tls', False)
            
            client_id = f"qenergyz_iot_{uuid.uuid4().hex[:8]}"
            
            self.client = mqtt.Client(
                hostname=broker_host,
                port=broker_port,
                client_id=client_id,
                username=username,
                password=password
            )
            
            if use_tls:
                context = ssl.create_default_context()
                self.client._client.tls_set_context(context)
            
            await self.client.__aenter__()
            self.connected = True
            
            logger.info("MQTT connection established",
                       broker=f"{broker_host}:{broker_port}")
            
            return True
            
        except Exception as e:
            logger.error("MQTT connection failed", error=str(e))
            self.connected = False
            raise
    
    async def disconnect(self) -> bool:
        """Disconnect from MQTT broker"""
        try:
            if self.client and self.connected:
                await self.client.__aexit__(None, None, None)
                self.connected = False
                logger.info("MQTT connection closed")
            return True
        except Exception as e:
            logger.error("MQTT disconnection error", error=str(e))
            return False
    
    @circuit_breaker
    async def read_data(self, read_config: Dict[str, Any]) -> List[SensorReading]:
        """Subscribe to MQTT topics and read sensor data"""
        if not self.connected:
            raise ConnectionError("MQTT client not connected")
        
        topics = read_config.get('topics', [])
        timeout = read_config.get('timeout', 30)
        device_id = read_config.get('device_id', '')
        
        readings = []
        
        try:
            # Subscribe to topics
            for topic in topics:
                await self.client.subscribe(topic)
            
            # Wait for messages with timeout
            start_time = datetime.utcnow()
            
            async for message in self.client.messages:
                if (datetime.utcnow() - start_time).total_seconds() > timeout:
                    break
                
                try:
                    # Parse MQTT message
                    payload = json.loads(message.payload.decode())
                    
                    # Create sensor reading
                    reading = SensorReading(
                        device_id=device_id,
                        sensor_name=payload.get('sensor_name', 'unknown'),
                        data_type=DataType(payload.get('data_type', 'temperature')),
                        value=float(payload.get('value', 0.0)),
                        unit=payload.get('unit', ''),
                        timestamp=datetime.fromisoformat(payload.get('timestamp', datetime.utcnow().isoformat())),
                        metadata={'topic': message.topic, 'qos': message.qos}
                    )
                    
                    readings.append(reading)
                    
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning("Failed to parse MQTT message",
                                 topic=message.topic,
                                 error=str(e))
            
            logger.info("MQTT data read completed",
                       topics=topics,
                       readings_count=len(readings))
            
            return readings
            
        except Exception as e:
            logger.error("MQTT data read failed", error=str(e))
            raise
    
    async def send_command(self, command: DeviceCommand) -> Dict[str, Any]:
        """Send command via MQTT"""
        if not self.connected:
            raise ConnectionError("MQTT client not connected")
        
        try:
            topic = f"commands/{command.device_id}"
            payload = {
                'command_id': command.command_id,
                'command_type': command.command_type,
                'parameters': command.parameters,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await self.client.publish(topic, json.dumps(payload))
            
            logger.info("MQTT command sent",
                       command_id=command.command_id,
                       device_id=command.device_id)
            
            return {'status': 'sent', 'timestamp': datetime.utcnow().isoformat()}
            
        except Exception as e:
            logger.error("MQTT command send failed",
                        command_id=command.command_id,
                        error=str(e))
            raise
    
    async def check_status(self) -> DeviceStatus:
        """Check MQTT connection status"""
        if self.connected and self.client:
            return DeviceStatus.ONLINE
        return DeviceStatus.OFFLINE

class ModbusProtocolProxy(IoTProtocolProxy):
    """Modbus TCP protocol proxy implementation"""
    
    def __init__(self):
        self.client: Optional[AsyncModbusTCPClient] = None
        self.connected = False
        self.connection_config = {}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=Exception
        )
    
    async def connect(self, connection_config: Dict[str, Any]) -> bool:
        """Connect to Modbus TCP device"""
        try:
            self.connection_config = connection_config
            
            host = connection_config.get('host', 'localhost')
            port = connection_config.get('port', 502)
            unit_id = connection_config.get('unit_id', 1)
            timeout = connection_config.get('timeout', 10)
            
            from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient
            from pymodbus.client.asynchronous import schedulers
            
            # Initialize Modbus client
            loop = asyncio.get_event_loop()
            _, self.client = AsyncModbusTCPClient(
                schedulers.ASYNC_IO,
                host=host,
                port=port,
                loop=loop,
                timeout=timeout
            )
            
            # Connect
            connection = await self.client.connect()
            if connection:
                self.connected = True
                logger.info("Modbus TCP connection established",
                           host=f"{host}:{port}")
                return True
            else:
                raise ConnectionError("Failed to establish Modbus connection")
                
        except Exception as e:
            logger.error("Modbus TCP connection failed", error=str(e))
            self.connected = False
            raise
    
    async def disconnect(self) -> bool:
        """Disconnect from Modbus device"""
        try:
            if self.client and self.connected:
                self.client.close()
                self.connected = False
                logger.info("Modbus TCP connection closed")
            return True
        except Exception as e:
            logger.error("Modbus TCP disconnection error", error=str(e))
            return False
    
    @circuit_breaker
    async def read_data(self, read_config: Dict[str, Any]) -> List[SensorReading]:
        """Read data from Modbus registers"""
        if not self.connected:
            raise ConnectionError("Modbus client not connected")
        
        device_id = read_config.get('device_id', '')
        unit_id = read_config.get('unit_id', 1)
        registers = read_config.get('registers', [])
        
        readings = []
        
        try:
            for register_config in registers:
                address = register_config.get('address', 0)
                count = register_config.get('count', 1)
                register_type = register_config.get('type', 'holding')  # holding, input, coil, discrete
                data_type = register_config.get('data_type', 'float32')
                sensor_name = register_config.get('sensor_name', f'register_{address}')
                unit = register_config.get('unit', '')
                
                # Read registers based on type
                if register_type == 'holding':
                    result = await self.client.read_holding_registers(address, count, unit=unit_id)
                elif register_type == 'input':
                    result = await self.client.read_input_registers(address, count, unit=unit_id)
                elif register_type == 'coil':
                    result = await self.client.read_coils(address, count, unit=unit_id)
                elif register_type == 'discrete':
                    result = await self.client.read_discrete_inputs(address, count, unit=unit_id)
                else:
                    continue
                
                if result.isError():
                    logger.warning("Modbus register read error",
                                 address=address,
                                 error=str(result))
                    continue
                
                # Decode register values
                if register_type in ['holding', 'input']:
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        result.registers,
                        byteorder=Endian.Big,
                        wordorder=Endian.Big
                    )
                    
                    # Decode based on data type
                    if data_type == 'float32':
                        value = decoder.decode_32bit_float()
                    elif data_type == 'int16':
                        value = decoder.decode_16bit_int()
                    elif data_type == 'int32':
                        value = decoder.decode_32bit_int()
                    elif data_type == 'uint16':
                        value = decoder.decode_16bit_uint()
                    elif data_type == 'uint32':
                        value = decoder.decode_32bit_uint()
                    else:
                        value = float(result.registers[0])
                else:
                    # Boolean values for coils/discrete inputs
                    value = float(result.bits[0] if result.bits else 0)
                
                # Create sensor reading
                reading = SensorReading(
                    device_id=device_id,
                    sensor_name=sensor_name,
                    data_type=DataType(register_config.get('sensor_type', 'temperature')),
                    value=value,
                    unit=unit,
                    metadata={
                        'address': address,
                        'register_type': register_type,
                        'data_type': data_type
                    }
                )
                
                readings.append(reading)
            
            logger.info("Modbus data read completed",
                       registers_count=len(registers),
                       readings_count=len(readings))
            
            return readings
            
        except Exception as e:
            logger.error("Modbus data read failed", error=str(e))
            raise
    
    async def send_command(self, command: DeviceCommand) -> Dict[str, Any]:
        """Send command to Modbus device"""
        if not self.connected:
            raise ConnectionError("Modbus client not connected")
        
        try:
            unit_id = command.parameters.get('unit_id', 1)
            address = command.parameters.get('address', 0)
            value = command.parameters.get('value', 0)
            register_type = command.parameters.get('register_type', 'holding')
            
            if register_type == 'holding':
                if isinstance(value, list):
                    result = await self.client.write_registers(address, value, unit=unit_id)
                else:
                    result = await self.client.write_register(address, value, unit=unit_id)
            elif register_type == 'coil':
                if isinstance(value, list):
                    result = await self.client.write_coils(address, value, unit=unit_id)
                else:
                    result = await self.client.write_coil(address, bool(value), unit=unit_id)
            else:
                raise ValueError(f"Unsupported register type for write: {register_type}")
            
            if result.isError():
                raise Exception(f"Modbus write error: {result}")
            
            logger.info("Modbus command executed",
                       command_id=command.command_id,
                       address=address,
                       value=value)
            
            return {
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat(),
                'address': address,
                'value': value
            }
            
        except Exception as e:
            logger.error("Modbus command execution failed",
                        command_id=command.command_id,
                        error=str(e))
            raise
    
    async def check_status(self) -> DeviceStatus:
        """Check Modbus device status"""
        if self.connected and self.client:
            try:
                # Try to read a register to test connection
                result = await self.client.read_holding_registers(0, 1, unit=1)
                if not result.isError():
                    return DeviceStatus.ONLINE
                else:
                    return DeviceStatus.ERROR
            except Exception:
                return DeviceStatus.ERROR
        return DeviceStatus.OFFLINE

class OPCUAProtocolProxy(IoTProtocolProxy):
    """OPC UA protocol proxy implementation"""
    
    def __init__(self):
        self.client: Optional[OPCUAClient] = None
        self.connected = False
        self.connection_config = {}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=Exception
        )
    
    async def connect(self, connection_config: Dict[str, Any]) -> bool:
        """Connect to OPC UA server"""
        try:
            self.connection_config = connection_config
            
            server_url = connection_config.get('url', 'opc.tcp://localhost:4840')
            username = connection_config.get('username')
            password = connection_config.get('password')
            certificate = connection_config.get('certificate')
            private_key = connection_config.get('private_key')
            
            self.client = OPCUAClient(url=server_url)
            
            # Configure authentication
            if username and password:
                self.client.set_user(username)
                self.client.set_password(password)
            
            if certificate and private_key:
                await self.client.set_security_string(
                    f"Basic256Sha256,SignAndEncrypt,{certificate},{private_key}"
                )
            
            # Connect
            await self.client.connect()
            self.connected = True
            
            logger.info("OPC UA connection established", server_url=server_url)
            return True
            
        except Exception as e:
            logger.error("OPC UA connection failed", error=str(e))
            self.connected = False
            raise
    
    async def disconnect(self) -> bool:
        """Disconnect from OPC UA server"""
        try:
            if self.client and self.connected:
                await self.client.disconnect()
                self.connected = False
                logger.info("OPC UA connection closed")
            return True
        except Exception as e:
            logger.error("OPC UA disconnection error", error=str(e))
            return False
    
    @circuit_breaker
    async def read_data(self, read_config: Dict[str, Any]) -> List[SensorReading]:
        """Read data from OPC UA nodes"""
        if not self.connected:
            raise ConnectionError("OPC UA client not connected")
        
        device_id = read_config.get('device_id', '')
        nodes = read_config.get('nodes', [])
        
        readings = []
        
        try:
            for node_config in nodes:
                node_id = node_config.get('node_id', '')
                sensor_name = node_config.get('sensor_name', node_id)
                data_type_name = node_config.get('data_type', 'temperature')
                unit = node_config.get('unit', '')
                
                # Get node
                node = self.client.get_node(node_id)
                
                # Read value
                value = await node.read_value()
                
                # Read data type
                data_type_node = await node.read_data_type()
                
                # Convert value based on OPC UA data type
                if isinstance(value, (int, float)):
                    numeric_value = float(value)
                elif isinstance(value, bool):
                    numeric_value = float(value)
                else:
                    # Try to convert to float
                    try:
                        numeric_value = float(str(value))
                    except (ValueError, TypeError):
                        numeric_value = 0.0
                
                # Create sensor reading
                reading = SensorReading(
                    device_id=device_id,
                    sensor_name=sensor_name,
                    data_type=DataType(data_type_name),
                    value=numeric_value,
                    unit=unit,
                    metadata={
                        'node_id': node_id,
                        'opc_data_type': str(data_type_node),
                        'raw_value': str(value)
                    }
                )
                
                readings.append(reading)
            
            logger.info("OPC UA data read completed",
                       nodes_count=len(nodes),
                       readings_count=len(readings))
            
            return readings
            
        except Exception as e:
            logger.error("OPC UA data read failed", error=str(e))
            raise
    
    async def send_command(self, command: DeviceCommand) -> Dict[str, Any]:
        """Send command to OPC UA server"""
        if not self.connected:
            raise ConnectionError("OPC UA client not connected")
        
        try:
            node_id = command.parameters.get('node_id', '')
            value = command.parameters.get('value', 0)
            data_type = command.parameters.get('data_type', 'Double')
            
            # Get node
            node = self.client.get_node(node_id)
            
            # Convert value to appropriate OPC UA data type
            if data_type == 'Boolean':
                opc_value = ua.DataValue(ua.Variant(bool(value), ua.VariantType.Boolean))
            elif data_type == 'Int32':
                opc_value = ua.DataValue(ua.Variant(int(value), ua.VariantType.Int32))
            elif data_type == 'Double':
                opc_value = ua.DataValue(ua.Variant(float(value), ua.VariantType.Double))
            else:
                opc_value = ua.DataValue(ua.Variant(value, ua.VariantType.String))
            
            # Write value
            await node.write_value(opc_value)
            
            logger.info("OPC UA command executed",
                       command_id=command.command_id,
                       node_id=node_id,
                       value=value)
            
            return {
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat(),
                'node_id': node_id,
                'value': value
            }
            
        except Exception as e:
            logger.error("OPC UA command execution failed",
                        command_id=command.command_id,
                        error=str(e))
            raise
    
    async def check_status(self) -> DeviceStatus:
        """Check OPC UA server status"""
        if self.connected and self.client:
            try:
                # Try to read server status
                server_state = await self.client.get_server_node().get_child("0:ServerStatus").read_value()
                if server_state:
                    return DeviceStatus.ONLINE
                else:
                    return DeviceStatus.ERROR
            except Exception:
                return DeviceStatus.ERROR
        return DeviceStatus.OFFLINE

# Composite Pattern for Device Groups
class DeviceComponent(ABC):
    """Abstract component for device composite pattern"""
    
    @abstractmethod
    async def read_all_data(self) -> List[SensorReading]:
        """Read data from device(s)"""
        pass
    
    @abstractmethod
    async def send_command_to_all(self, command: DeviceCommand) -> List[Dict[str, Any]]:
        """Send command to device(s)"""
        pass
    
    @abstractmethod
    def get_device_count(self) -> int:
        """Get total number of devices"""
        pass

class SingleIoTDevice(DeviceComponent):
    """Single IoT device leaf in composite pattern"""
    
    def __init__(self, device: IoTDevice, protocol_proxy: IoTProtocolProxy):
        self.device = device
        self.protocol_proxy = protocol_proxy
        self._last_readings: List[SensorReading] = []
    
    async def read_all_data(self) -> List[SensorReading]:
        """Read data from single device"""
        try:
            read_config = {
                'device_id': self.device.device_id,
                'timeout': 30
            }
            
            # Add protocol-specific configuration
            if self.device.protocol == Protocol.MQTT:
                read_config['topics'] = self.device.metadata.get('topics', [])
            elif self.device.protocol == Protocol.MODBUS_TCP:
                read_config['registers'] = self.device.metadata.get('registers', [])
                read_config['unit_id'] = self.device.metadata.get('unit_id', 1)
            elif self.device.protocol == Protocol.OPC_UA:
                read_config['nodes'] = self.device.metadata.get('nodes', [])
            
            readings = await self.protocol_proxy.read_data(read_config)
            self._last_readings = readings
            
            # Update device status
            self.device.status = DeviceStatus.ONLINE
            self.device.last_heartbeat = datetime.utcnow()
            
            return readings
            
        except Exception as e:
            logger.error("Device data read failed",
                        device_id=self.device.device_id,
                        error=str(e))
            self.device.status = DeviceStatus.ERROR
            return []
    
    async def send_command_to_all(self, command: DeviceCommand) -> List[Dict[str, Any]]:
        """Send command to single device"""
        try:
            command.device_id = self.device.device_id
            result = await self.protocol_proxy.send_command(command)
            return [result]
        except Exception as e:
            logger.error("Device command failed",
                        device_id=self.device.device_id,
                        error=str(e))
            return [{'status': 'error', 'error': str(e)}]
    
    def get_device_count(self) -> int:
        """Get device count (always 1 for single device)"""
        return 1

class DeviceGroup(DeviceComponent):
    """Composite of multiple IoT devices"""
    
    def __init__(self, name: str):
        self.name = name
        self.devices: List[DeviceComponent] = []
    
    def add_device(self, device: DeviceComponent):
        """Add device to group"""
        self.devices.append(device)
    
    def remove_device(self, device: DeviceComponent):
        """Remove device from group"""
        if device in self.devices:
            self.devices.remove(device)
    
    async def read_all_data(self) -> List[SensorReading]:
        """Read data from all devices in group"""
        all_readings = []
        
        # Read data from all devices concurrently
        tasks = [device.read_all_data() for device in self.devices]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error("Device group read error", error=str(result))
            else:
                all_readings.extend(result)
        
        logger.info("Device group data read completed",
                   group=self.name,
                   devices_count=len(self.devices),
                   readings_count=len(all_readings))
        
        return all_readings
    
    async def send_command_to_all(self, command: DeviceCommand) -> List[Dict[str, Any]]:
        """Send command to all devices in group"""
        all_results = []
        
        # Send command to all devices concurrently
        tasks = [device.send_command_to_all(command) for device in self.devices]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error("Device group command error", error=str(result))
                all_results.append({'status': 'error', 'error': str(result)})
            else:
                all_results.extend(result)
        
        return all_results
    
    def get_device_count(self) -> int:
        """Get total device count in group"""
        return sum(device.get_device_count() for device in self.devices)

# Main IoT Service
class IoTService:
    """
    Main IoT service implementing device management, data collection,
    and command execution with protocol abstraction and fault tolerance.
    """
    
    def __init__(self):
        self.devices: Dict[str, IoTDevice] = {}
        self.protocol_proxies: Dict[str, IoTProtocolProxy] = {}
        self.device_components: Dict[str, DeviceComponent] = {}
        self.device_groups: Dict[str, DeviceGroup] = {}
        self.alert_thresholds: Dict[str, Dict[str, float]] = {}
        self.active_alerts: Dict[str, IoTAlert] = {}
        
        logger.info("IoT service initialized")
    
    async def initialize(self):
        """Initialize IoT service"""
        # Initialize protocol proxies
        self.protocol_proxies = {
            Protocol.MQTT.value: MQTTProtocolProxy(),
            Protocol.MODBUS_TCP.value: ModbusProtocolProxy(),
            Protocol.OPC_UA.value: OPCUAProtocolProxy()
        }
        
        # Load default alert thresholds
        self.alert_thresholds = {
            DataType.TEMPERATURE.value: {'min': -20.0, 'max': 150.0},
            DataType.PRESSURE.value: {'min': 0.0, 'max': 1000.0},
            DataType.FLOW_RATE.value: {'min': 0.0, 'max': 10000.0},
            DataType.LEVEL.value: {'min': 0.0, 'max': 100.0},
            DataType.VIBRATION.value: {'min': 0.0, 'max': 50.0}
        }
        
        # Load and register devices (mock data)
        await self._load_devices()
        
        logger.info("IoT service initialization completed")
    
    async def shutdown(self):
        """Graceful shutdown of IoT service"""
        # Disconnect all protocol proxies
        for proxy in self.protocol_proxies.values():
            try:
                await proxy.disconnect()
            except Exception as e:
                logger.error("Protocol proxy disconnect error", error=str(e))
        
        logger.info("IoT service shutdown completed")
    
    async def _load_devices(self):
        """Load IoT devices configuration"""
        # Mock device configurations - in production would load from database
        mock_devices = [
            IoTDevice(
                name="Oil Rig Alpha - Main Control",
                device_type=DeviceType.OIL_RIG,
                protocol=Protocol.OPC_UA,
                connection_string="opc.tcp://oilrig-alpha.example.com:4840",
                location={"lat": 25.2048, "lon": 55.2708},
                metadata={
                    'nodes': [
                        {'node_id': 'ns=2;i=2', 'sensor_name': 'wellhead_pressure', 'data_type': 'pressure', 'unit': 'psi'},
                        {'node_id': 'ns=2;i=3', 'sensor_name': 'flow_rate', 'data_type': 'flow_rate', 'unit': 'bbl/day'},
                        {'node_id': 'ns=2;i=4', 'sensor_name': 'temperature', 'data_type': 'temperature', 'unit': 'C'}
                    ]
                }
            ),
            IoTDevice(
                name="Pipeline Sensor Station 1",
                device_type=DeviceType.PIPELINE,
                protocol=Protocol.MODBUS_TCP,
                connection_string="192.168.1.100:502",
                location={"lat": 25.1234, "lon": 55.3456},
                metadata={
                    'unit_id': 1,
                    'registers': [
                        {'address': 0, 'count': 2, 'type': 'holding', 'data_type': 'float32', 'sensor_name': 'pressure', 'sensor_type': 'pressure', 'unit': 'bar'},
                        {'address': 2, 'count': 2, 'type': 'holding', 'data_type': 'float32', 'sensor_name': 'flow', 'sensor_type': 'flow_rate', 'unit': 'm3/h'},
                        {'address': 4, 'count': 1, 'type': 'holding', 'data_type': 'int16', 'sensor_name': 'temperature', 'sensor_type': 'temperature', 'unit': 'C'}
                    ]
                }
            ),
            IoTDevice(
                name="Renewable Farm Weather Station",
                device_type=DeviceType.RENEWABLE_FARM,
                protocol=Protocol.MQTT,
                connection_string="mqtt://weather.renewables.example.com:1883",
                location={"lat": 25.5678, "lon": 55.7890},
                metadata={
                    'topics': ['weather/temperature', 'weather/wind_speed', 'weather/solar_radiation'],
                    'use_tls': False
                }
            )
        ]
        
        for device in mock_devices:
            self.devices[device.device_id] = device
            
            # Create device component
            protocol = device.protocol.value
            if protocol in self.protocol_proxies:
                device_component = SingleIoTDevice(device, self.protocol_proxies[protocol])
                self.device_components[device.device_id] = device_component
        
        # Create device groups
        oil_rigs = DeviceGroup("Oil Rigs")
        pipelines = DeviceGroup("Pipelines")
        renewables = DeviceGroup("Renewable Farms")
        
        for device_id, component in self.device_components.items():
            device = self.devices[device_id]
            if device.device_type == DeviceType.OIL_RIG:
                oil_rigs.add_device(component)
            elif device.device_type == DeviceType.PIPELINE:
                pipelines.add_device(component)
            elif device.device_type == DeviceType.RENEWABLE_FARM:
                renewables.add_device(component)
        
        self.device_groups = {
            "oil_rigs": oil_rigs,
            "pipelines": pipelines,
            "renewables": renewables
        }
        
        logger.info("Devices loaded",
                   devices_count=len(self.devices),
                   groups_count=len(self.device_groups))
    
    async def register_device(self, device: IoTDevice) -> bool:
        """Register a new IoT device"""
        try:
            self.devices[device.device_id] = device
            
            # Create protocol proxy connection
            protocol = device.protocol.value
            if protocol in self.protocol_proxies:
                proxy = self.protocol_proxies[protocol]
                connection_config = self._parse_connection_string(device.connection_string, protocol)
                
                # Test connection
                if await proxy.connect(connection_config):
                    device.status = DeviceStatus.ONLINE
                    device.last_heartbeat = datetime.utcnow()
                    
                    # Create device component
                    device_component = SingleIoTDevice(device, proxy)
                    self.device_components[device.device_id] = device_component
                    
                    logger.info("Device registered successfully",
                               device_id=device.device_id,
                               protocol=protocol)
                    return True
                else:
                    device.status = DeviceStatus.OFFLINE
                    return False
            else:
                logger.error("Unsupported protocol", protocol=protocol)
                return False
                
        except Exception as e:
            logger.error("Device registration failed",
                        device_id=device.device_id,
                        error=str(e))
            return False
    
    def _parse_connection_string(self, connection_string: str, protocol: str) -> Dict[str, Any]:
        """Parse device connection string into configuration"""
        config = {}
        
        if protocol == Protocol.MQTT.value:
            # Parse MQTT connection string: mqtt://host:port or mqtts://host:port
            if connection_string.startswith('mqtts://'):
                config['use_tls'] = True
                connection_string = connection_string[8:]
            elif connection_string.startswith('mqtt://'):
                config['use_tls'] = False
                connection_string = connection_string[7:]
            
            if ':' in connection_string:
                host, port = connection_string.split(':')
                config['host'] = host
                config['port'] = int(port)
            else:
                config['host'] = connection_string
                config['port'] = 1883
                
        elif protocol == Protocol.MODBUS_TCP.value:
            # Parse Modbus TCP connection string: host:port
            if ':' in connection_string:
                host, port = connection_string.split(':')
                config['host'] = host
                config['port'] = int(port)
            else:
                config['host'] = connection_string
                config['port'] = 502
                
        elif protocol == Protocol.OPC_UA.value:
            # OPC UA connection string is already in correct format
            config['url'] = connection_string
        
        return config
    
    async def read_device_data(self, device_id: str) -> List[SensorReading]:
        """Read data from specific device"""
        if device_id not in self.device_components:
            raise ValueError(f"Device not found: {device_id}")
        
        device_component = self.device_components[device_id]
        readings = await device_component.read_all_data()
        
        # Check for alerts
        for reading in readings:
            await self._check_alert_thresholds(reading)
        
        return readings
    
    async def read_group_data(self, group_name: str) -> List[SensorReading]:
        """Read data from all devices in a group"""
        if group_name not in self.device_groups:
            raise ValueError(f"Device group not found: {group_name}")
        
        device_group = self.device_groups[group_name]
        readings = await device_group.read_all_data()
        
        # Check for alerts
        for reading in readings:
            await self._check_alert_thresholds(reading)
        
        return readings
    
    async def send_device_command(self, device_id: str, command: DeviceCommand) -> Dict[str, Any]:
        """Send command to specific device"""
        if device_id not in self.device_components:
            raise ValueError(f"Device not found: {device_id}")
        
        device_component = self.device_components[device_id]
        results = await device_component.send_command_to_all(command)
        
        return results[0] if results else {'status': 'error', 'message': 'No result'}
    
    async def _check_alert_thresholds(self, reading: SensorReading) -> None:
        """Check if reading exceeds alert thresholds"""
        data_type = reading.data_type.value
        
        if data_type not in self.alert_thresholds:
            return
        
        thresholds = self.alert_thresholds[data_type]
        min_threshold = thresholds.get('min')
        max_threshold = thresholds.get('max')
        
        alert_message = None
        severity = AlertSeverity.INFO
        
        if min_threshold is not None and reading.value < min_threshold:
            alert_message = f"{reading.sensor_name} below minimum threshold: {reading.value} < {min_threshold}"
            severity = AlertSeverity.WARNING
        elif max_threshold is not None and reading.value > max_threshold:
            alert_message = f"{reading.sensor_name} above maximum threshold: {reading.value} > {max_threshold}"
            severity = AlertSeverity.CRITICAL if reading.value > max_threshold * 1.5 else AlertSeverity.WARNING
        
        if alert_message:
            alert = IoTAlert(
                device_id=reading.device_id,
                severity=severity,
                message=alert_message,
                alert_type='threshold_violation',
                sensor_reading=reading,
                threshold_value=min_threshold if reading.value < min_threshold else max_threshold
            )
            
            self.active_alerts[alert.alert_id] = alert
            
            logger.warning("IoT alert generated",
                          alert_id=alert.alert_id,
                          device_id=reading.device_id,
                          sensor=reading.sensor_name,
                          value=reading.value,
                          severity=severity.value)
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status and health information"""
        if device_id not in self.devices:
            raise ValueError(f"Device not found: {device_id}")
        
        device = self.devices[device_id]
        
        # Check protocol status
        protocol_status = DeviceStatus.UNKNOWN
        if device_id in self.device_components:
            device_component = self.device_components[device_id]
            if isinstance(device_component, SingleIoTDevice):
                protocol_status = await device_component.protocol_proxy.check_status()
        
        return {
            'device_id': device_id,
            'name': device.name,
            'device_type': device.device_type.value,
            'protocol': device.protocol.value,
            'status': protocol_status.value,
            'last_heartbeat': device.last_heartbeat.isoformat() if device.last_heartbeat else None,
            'location': device.location,
            'firmware_version': device.firmware_version
        }
    
    async def get_active_alerts(self, device_id: Optional[str] = None) -> List[IoTAlert]:
        """Get active alerts, optionally filtered by device"""
        if device_id:
            return [alert for alert in self.active_alerts.values() 
                   if alert.device_id == device_id and not alert.acknowledged]
        else:
            return [alert for alert in self.active_alerts.values() 
                   if not alert.acknowledged]
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an active alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info("Alert acknowledged", alert_id=alert_id)
            return True
        return False
    
    async def handle_websocket_message(self, message: str) -> str:
        """Handle WebSocket messages for real-time IoT updates"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'read_device':
                device_id = data.get('device_id')
                readings = await self.read_device_data(device_id)
                
                return json.dumps({
                    'type': 'device_readings',
                    'device_id': device_id,
                    'readings': [
                        {
                            'sensor_name': r.sensor_name,
                            'data_type': r.data_type.value,
                            'value': r.value,
                            'unit': r.unit,
                            'timestamp': r.timestamp.isoformat()
                        }
                        for r in readings
                    ]
                })
            
            elif message_type == 'get_alerts':
                device_id = data.get('device_id')
                alerts = await self.get_active_alerts(device_id)
                
                return json.dumps({
                    'type': 'active_alerts',
                    'alerts': [
                        {
                            'alert_id': alert.alert_id,
                            'device_id': alert.device_id,
                            'severity': alert.severity.value,
                            'message': alert.message,
                            'created_at': alert.created_at.isoformat()
                        }
                        for alert in alerts
                    ]
                })
            
            elif message_type == 'send_command':
                device_id = data.get('device_id')
                command_data = data.get('command', {})
                
                command = DeviceCommand(
                    device_id=device_id,
                    command_type=command_data.get('type', ''),
                    parameters=command_data.get('parameters', {})
                )
                
                result = await self.send_device_command(device_id, command)
                
                return json.dumps({
                    'type': 'command_result',
                    'command_id': command.command_id,
                    'result': result
                })
            
            else:
                return json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                })
                
        except Exception as e:
            logger.error("IoT WebSocket message handling error", error=str(e))
            return json.dumps({
                'type': 'error',
                'message': 'Message processing failed'
            })