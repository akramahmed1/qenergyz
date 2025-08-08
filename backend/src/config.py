"""
Qenergyz Configuration Management

Implements Singleton pattern for application configuration with 
region-specific settings, structured logging, internationalization,
and enterprise security features.
"""

import os
import json
import gettext
from enum import Enum
from typing import Dict, Any, Optional, List
from functools import lru_cache
from pydantic import BaseSettings, Field, validator
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration

class Region(str, Enum):
    """Supported regional configurations"""
    MIDDLE_EAST = "middle_east"
    USA = "usa" 
    UK = "uk"
    EUROPE = "europe"
    GUYANA = "guyana"

class Environment(str, Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class ComplianceFramework(str, Enum):
    """Supported compliance frameworks"""
    SHARIA = "sharia"
    US_CFTC = "us_cftc"
    EU_MIFID = "eu_mifid" 
    UK_FCA = "uk_fca"
    GUYANA_EPA = "guyana_epa"

class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Settings(BaseSettings):
    """
    Application settings with region-specific configurations
    Implements enterprise-grade configuration management
    """
    
    # Basic Application Settings
    app_name: str = Field(default="Qenergyz ETRM Platform", env="APP_NAME")
    version: str = Field(default="1.0.0", env="VERSION")
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    region: Region = Field(default=Region.MIDDLE_EAST, env="REGION")
    
    # Security Settings
    secret_key: str = Field(..., env="SECRET_KEY")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Database Configuration
    database_url: str = Field(..., env="DB_URL")
    test_database_url: Optional[str] = Field(None, env="TEST_DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # Cache Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    
    # Message Queue Configuration
    kafka_bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", env="RABBITMQ_URL")
    
    # External API Keys
    nymex_api_key: Optional[str] = Field(None, env="NYMEX_API_KEY")
    nymex_api_secret: Optional[str] = Field(None, env="NYMEX_API_SECRET")
    icis_api_key: Optional[str] = Field(None, env="ICIS_API_KEY")
    icis_api_secret: Optional[str] = Field(None, env="ICIS_API_SECRET")
    openweather_api_key: Optional[str] = Field(None, env="OPENWEATHER_API_KEY")
    exxon_api_key: Optional[str] = Field(None, env="EXXON_API_KEY")
    exxon_api_secret: Optional[str] = Field(None, env="EXXON_API_SECRET")
    
    # AI/ML Configuration
    grok_api_key: Optional[str] = Field(None, env="GROK_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    qiskit_ibm_token: Optional[str] = Field(None, env="QISKIT_IBM_TOKEN")
    tensorflow_serving_url: str = Field(default="http://localhost:8501", env="TENSORFLOW_SERVING_URL")
    
    # Monitoring and Analytics
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    analytics_key: Optional[str] = Field(None, env="ANALYTICS_KEY")
    new_relic_license_key: Optional[str] = Field(None, env="NEW_RELIC_LICENSE_KEY")
    
    # IoT Configuration
    mqtt_broker_host: str = Field(default="localhost", env="MQTT_BROKER_HOST")
    mqtt_broker_port: int = Field(default=1883, env="MQTT_BROKER_PORT")
    mqtt_username: Optional[str] = Field(None, env="MQTT_USERNAME")
    mqtt_password: Optional[str] = Field(None, env="MQTT_PASSWORD")
    opcua_server_url: str = Field(default="opc.tcp://localhost:4840", env="OPC_UA_SERVER_URL")
    modbus_tcp_host: str = Field(default="localhost", env="MODBUS_TCP_HOST")
    modbus_tcp_port: int = Field(default=502, env="MODBUS_TCP_PORT")
    
    # Blockchain Configuration
    web3_provider_url: Optional[str] = Field(None, env="WEB3_PROVIDER_URL")
    web3_private_key: Optional[str] = Field(None, env="WEB3_PRIVATE_KEY")
    blockchain_network: str = Field(default="testnet", env="BLOCKCHAIN_NETWORK")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=3600, env="RATE_LIMIT_PER_HOUR")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # WebSocket Configuration
    ws_max_connections: int = Field(default=1000, env="WS_MAX_CONNECTIONS")
    ws_heartbeat_interval: int = Field(default=30, env="WS_HEARTBEAT_INTERVAL")
    ws_message_size_limit: int = Field(default=1048576, env="WS_MESSAGE_SIZE_LIMIT")
    
    # Compliance Configuration  
    aml_api_key: Optional[str] = Field(None, env="AML_API_KEY")
    kyc_api_key: Optional[str] = Field(None, env="KYC_API_KEY")
    compliance_webhook_url: Optional[str] = Field(None, env="COMPLIANCE_WEBHOOK_URL")
    sharia_compliance_api: Optional[str] = Field(None, env="SHARIA_COMPLIANCE_API")
    
    # Feature Flags
    enable_quantum_computing: bool = Field(default=False, env="ENABLE_QUANTUM_COMPUTING")
    enable_ai_esg_scoring: bool = Field(default=True, env="ENABLE_AI_ESG_SCORING")
    enable_advanced_analytics: bool = Field(default=True, env="ENABLE_ADVANCED_ANALYTICS")
    enable_iot_integration: bool = Field(default=True, env="ENABLE_IOT_INTEGRATION")
    enable_blockchain_auditing: bool = Field(default=True, env="ENABLE_BLOCKCHAIN_AUDITING")
    
    # Logging Configuration
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_json_format: bool = Field(default=True, env="LOG_JSON_FORMAT")
    
    # Multi-tenancy
    default_tenant: str = Field(default="qenergyz_main", env="DEFAULT_TENANT")
    tenant_isolation: str = Field(default="strict", env="TENANT_ISOLATION")
    
    # Performance Settings
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    connection_pool_size: int = Field(default=20, env="CONNECTION_POOL_SIZE")
    query_timeout: int = Field(default=30, env="QUERY_TIMEOUT")
    
    # Development/Testing
    mock_mode: bool = Field(default=False, env="MOCK_MODE")
    test_mode: bool = Field(default=False, env="TEST_MODE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @validator("environment", pre=True)
    def validate_environment(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v
        
    @validator("region", pre=True) 
    def validate_region(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

class RegionalConfig:
    """Region-specific configuration settings"""
    
    REGIONAL_SETTINGS = {
        Region.MIDDLE_EAST: {
            "timezone": "Asia/Dubai",
            "currency": "AED", 
            "locale": "ar_AE",
            "compliance_frameworks": [ComplianceFramework.SHARIA],
            "trading_hours": {"start": "08:00", "end": "16:00"},
            "weekend_days": [5, 6],  # Friday, Saturday
            "regulatory_authorities": ["ADGM", "DFSA", "CMA"],
            "supported_languages": ["ar", "en"],
            "prayer_time_adjustments": True,
            "islamic_calendar": True
        },
        Region.USA: {
            "timezone": "America/New_York",
            "currency": "USD",
            "locale": "en_US", 
            "compliance_frameworks": [ComplianceFramework.US_CFTC],
            "trading_hours": {"start": "09:30", "end": "16:00"},
            "weekend_days": [0, 6],  # Sunday, Saturday
            "regulatory_authorities": ["CFTC", "FERC", "SEC"],
            "supported_languages": ["en", "es"],
            "tax_reporting": True,
            "dodd_frank_compliance": True
        },
        Region.UK: {
            "timezone": "Europe/London",
            "currency": "GBP",
            "locale": "en_GB",
            "compliance_frameworks": [ComplianceFramework.UK_FCA],
            "trading_hours": {"start": "08:00", "end": "16:30"},
            "weekend_days": [0, 6],
            "regulatory_authorities": ["FCA", "Ofgem", "PRA"],
            "supported_languages": ["en"],
            "brexit_compliance": True,
            "gdpr_compliance": True
        },
        Region.EUROPE: {
            "timezone": "Europe/Amsterdam", 
            "currency": "EUR",
            "locale": "en_EU",
            "compliance_frameworks": [ComplianceFramework.EU_MIFID],
            "trading_hours": {"start": "09:00", "end": "17:30"},
            "weekend_days": [0, 6],
            "regulatory_authorities": ["ESMA", "ECB", "EBA"],
            "supported_languages": ["en", "de", "fr", "es", "it"],
            "mifid_ii_compliance": True,
            "gdpr_compliance": True,
            "esg_reporting": True
        },
        Region.GUYANA: {
            "timezone": "America/Guyana",
            "currency": "GYD",
            "locale": "en_GY", 
            "compliance_frameworks": [ComplianceFramework.GUYANA_EPA],
            "trading_hours": {"start": "08:00", "end": "16:00"},
            "weekend_days": [0, 6],
            "regulatory_authorities": ["EPA", "GRA", "BOG"],
            "supported_languages": ["en"],
            "local_content_requirements": True,
            "environmental_compliance": True,
            "sovereignty_requirements": True
        }
    }
    
    @classmethod
    def get_regional_config(cls, region: Region) -> Dict[str, Any]:
        """Get configuration for specific region"""
        return cls.REGIONAL_SETTINGS.get(region, cls.REGIONAL_SETTINGS[Region.MIDDLE_EAST])

class ConfigurationSingleton:
    """
    Singleton pattern implementation for application configuration
    Ensures single source of truth for configuration across the application
    """
    _instance = None
    _settings: Settings = None
    _regional_config: Dict[str, Any] = None
    _i18n: Optional[gettext.GNUTranslations] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigurationSingleton, cls).__new__(cls)
        return cls._instance
    
    def initialize(self, settings: Settings = None):
        """Initialize the configuration singleton"""
        if self._settings is None:
            self._settings = settings or Settings()
            self._regional_config = RegionalConfig.get_regional_config(self._settings.region)
            self._setup_logging()
            self._setup_i18n()
            self._setup_monitoring()
    
    def _setup_logging(self):
        """Configure structured logging with region-specific settings"""
        log_level = getattr(structlog.stdlib.INFO, self._settings.log_level.value, structlog.stdlib.INFO)
        
        # Configure structlog for JSON logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
    def _setup_i18n(self):
        """Setup internationalization support"""
        try:
            locale_dir = os.path.join(os.path.dirname(__file__), '..', 'locale')
            language = self._regional_config.get('supported_languages', ['en'])[0]
            
            self._i18n = gettext.translation(
                'qenergyz',
                localedir=locale_dir,
                languages=[language],
                fallback=True
            )
        except Exception as e:
            # Fallback to NullTranslations if locale files not found
            self._i18n = gettext.NullTranslations()
            
    def _setup_monitoring(self):
        """Setup monitoring and error tracking"""
        if self._settings.sentry_dsn:
            sentry_sdk.init(
                dsn=self._settings.sentry_dsn,
                integrations=[
                    FastApiIntegration(auto_enable=True),
                    RedisIntegration()
                ],
                traces_sample_rate=0.1 if self._settings.environment == Environment.PRODUCTION else 1.0,
                environment=self._settings.environment.value,
                release=f"qenergyz@{self._settings.version}"
            )
    
    @property
    def settings(self) -> Settings:
        """Get application settings"""
        if self._settings is None:
            self.initialize()
        return self._settings
    
    @property  
    def regional_config(self) -> Dict[str, Any]:
        """Get regional configuration"""
        if self._regional_config is None:
            self.initialize()
        return self._regional_config
        
    def get_compliance_frameworks(self) -> List[ComplianceFramework]:
        """Get applicable compliance frameworks for current region"""
        return self._regional_config.get('compliance_frameworks', [])
    
    def get_supported_languages(self) -> List[str]:
        """Get supported languages for current region"""
        return self._regional_config.get('supported_languages', ['en'])
    
    def translate(self, message: str) -> str:
        """Translate message using i18n"""
        if self._i18n is None:
            self.initialize()
        return self._i18n.gettext(message)
    
    def get_timezone(self) -> str:
        """Get regional timezone"""
        return self._regional_config.get('timezone', 'UTC')
    
    def get_currency(self) -> str:
        """Get regional currency"""
        return self._regional_config.get('currency', 'USD')
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        # Implementation would check current time against regional trading hours
        # This is a placeholder for the actual implementation
        return True
    
    def get_weekend_days(self) -> List[int]:
        """Get weekend days for current region (0=Sunday, 6=Saturday)"""
        return self._regional_config.get('weekend_days', [0, 6])

# Global configuration singleton
config_singleton = ConfigurationSingleton()

@lru_cache()
def get_settings() -> Settings:
    """
    Dependency function to get application settings
    Uses LRU cache for performance optimization
    """
    config_singleton.initialize()
    return config_singleton.settings

def get_regional_config() -> Dict[str, Any]:
    """Get regional configuration"""
    config_singleton.initialize()
    return config_singleton.regional_config

def get_compliance_frameworks() -> List[ComplianceFramework]:
    """Get applicable compliance frameworks"""
    config_singleton.initialize()
    return config_singleton.get_compliance_frameworks()

# Privacy and Security Configuration Notes
"""
PRIVACY & SECURITY IMPLEMENTATION NOTES:

1. SOC 2 Type II Compliance:
   - Access controls implemented via JWT and MFA
   - Audit logging for all data access and modifications
   - Encryption at rest and in transit
   - Regular security assessments and penetration testing
   - Vendor management and third-party risk assessments

2. ISO 27001 Information Security Management:
   - Information security policy and procedures
   - Risk assessment and treatment processes
   - Security incident management
   - Business continuity and disaster recovery
   - Regular security awareness training

3. Zero Trust Architecture:
   - Never trust, always verify principle
   - Multi-factor authentication for all users
   - Least privilege access controls
   - Continuous monitoring and verification
   - Encrypted communications

4. Data Protection (GDPR/CCPA):
   - Data minimization and purpose limitation
   - Right to access, rectification, and erasure
   - Data portability and consent management
   - Privacy by design and default
   - Data breach notification procedures

5. Hardware Security Module (HSM) Integration:
   - Cryptographic key generation and storage
   - Digital signing and certificate management  
   - Tamper-resistant hardware protection
   - FIPS 140-2 Level 3 compliance
   - High availability and performance

6. Regulatory Compliance Monitoring:
   - Real-time compliance checking
   - Automated regulatory reporting
   - Change management for regulatory updates
   - Multi-jurisdiction compliance tracking
   - Audit trail maintenance

7. API Security:
   - Rate limiting and DDoS protection
   - Input validation and sanitization
   - OAuth 2.0 and JWT token management
   - API versioning and deprecation policies
   - Comprehensive logging and monitoring
"""