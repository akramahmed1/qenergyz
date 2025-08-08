# Machine Learning Pipeline Documentation

This document covers the ML features implemented in Qenergyz including synthetic data generation, model fine-tuning, drift detection, TensorFlow Serving integration, and continuous learning.

## Features Overview

### 1. Synthetic Data Generation
Generate realistic ETRM (Energy Trading and Risk Management) synthetic data for model training.

### 2. Generative Model Fine-tuning
Fine-tune language models on synthetic ETRM data for report generation and analysis.

### 3. Model Drift Detection
Monitor models for data drift, concept drift, and performance degradation.

### 4. TensorFlow Serving Integration
Deploy and serve ML models at scale using TensorFlow Serving.

### 5. Continuous Learning Pipeline
Automated model retraining, evaluation, and deployment workflow.

## Quick Start

### Generate Synthetic Data
```python
from ml.synthetic_data_generator import SyntheticETRMDataGenerator, ETRMDataConfig
from datetime import datetime

# Configure data generation
config = ETRMDataConfig(
    num_trades=5000,
    num_risk_reports=200,
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# Generate dataset
generator = SyntheticETRMDataGenerator(config)
dataset = generator.generate_complete_dataset()

print(f"Generated {len(dataset['trades'])} trades")
print(f"Generated {len(dataset['text_descriptions'])} text samples")
```

### Fine-tune a Model
```python
from ml.model_fine_tuning import main as run_fine_tuning

# Run the complete fine-tuning pipeline
run_fine_tuning()
```

### Start Drift Detection
```python
from ml.drift_detection_service import ModelMonitoringService
import numpy as np

# Initialize monitoring service
monitoring = ModelMonitoringService()

# Register a model
reference_data = np.random.normal(0, 1, (1000, 5))
monitoring.register_model("risk_model", reference_data)

# Detect drift on new data
new_data = np.random.normal(0.5, 1.5, (200, 5))  # Shifted data
alerts = monitoring.detect_drift("risk_model", new_data)

for alert in alerts:
    print(f"Alert: {alert.message}")
```

### Deploy with TensorFlow Serving
```bash
# Start TensorFlow Serving
cd infrastructure/tensorflow-serving
docker-compose up -d

# Test predictions
python -c "
from ml.tensorflow_serving_client import ETRMModelClient, TensorFlowServingClient

client = ETRMModelClient(TensorFlowServingClient())
result = client.predict_risk_score({'volume': 1000, 'price': 75.5})
print('Risk prediction:', result)
"
```

### Run Continuous Learning
```python
from ml.continuous_learning_pipeline import ContinuousLearningPipeline, RetrainingConfig
import asyncio

async def run_pipeline():
    pipeline = ContinuousLearningPipeline()
    
    # Configure model for continuous learning
    config = RetrainingConfig(
        model_name="risk_model",
        retrain_schedule="0 2 * * 0",  # Weekly
        auto_deploy=False
    )
    
    pipeline.register_model_for_retraining(config)
    
    # Start monitoring loop
    await pipeline.run_continuous_learning_loop()

# Run the pipeline
asyncio.run(run_pipeline())
```

## Detailed Documentation

### Synthetic Data Generation

**Purpose**: Generate realistic ETRM data for model training without using sensitive production data.

**Features**:
- Trading transactions with realistic price movements
- Risk reports with portfolio metrics
- Compliance data with regulatory scenarios
- Text descriptions for language model training

**Configuration**:
```python
@dataclass
class ETRMDataConfig:
    num_trades: int = 1000              # Number of trades to generate
    num_positions: int = 500            # Number of positions
    num_risk_reports: int = 100         # Number of risk reports
    start_date: datetime = datetime(2023, 1, 1)
    end_date: datetime = datetime(2024, 12, 31)
    commodities: List[str] = None       # Energy commodities
    regions: List[str] = None           # Trading regions
```

**Output Data**:
- `trades.csv`: Trading transaction data
- `positions.csv`: Portfolio position data
- `risk_reports.csv`: Risk analysis reports
- `text_descriptions.txt`: Natural language descriptions
- `price_series.npz`: Historical price data
- `metadata.json`: Dataset metadata

### Model Fine-tuning

**Purpose**: Fine-tune generative models for ETRM-specific text generation and analysis.

**Architecture**:
- Custom tokenizer for ETRM terminology
- Transformer-based language model
- Next-token prediction training
- Evaluation metrics and validation

**Model Configuration**:
```python
@dataclass
class ModelConfig:
    vocab_size: int = 10000           # Vocabulary size
    embedding_dim: int = 128          # Embedding dimensions
    max_length: int = 512             # Maximum sequence length
    batch_size: int = 32              # Training batch size
    epochs: int = 10                  # Training epochs
    learning_rate: float = 0.001      # Learning rate
    hidden_dim: int = 256             # Hidden layer size
    num_heads: int = 8                # Attention heads
    num_layers: int = 4               # Transformer layers
```

**Training Process**:
1. Generate synthetic ETRM data
2. Build domain-specific tokenizer
3. Prepare training sequences
4. Train transformer model
5. Evaluate on validation set
6. Save model and artifacts

### Drift Detection

**Purpose**: Monitor ML models for performance degradation and distribution shifts.

**Detection Methods**:
- **Population Stability Index (PSI)**: Measures distribution changes
- **Kolmogorov-Smirnov Test**: Statistical distribution comparison
- **Performance Monitoring**: Track accuracy, precision, recall
- **Prediction Drift**: Monitor output distribution changes

**Alert Types**:
- **Data Drift**: Input feature distributions change
- **Concept Drift**: Relationship between inputs/outputs change  
- **Prediction Drift**: Model output distributions change
- **Performance Drift**: Model accuracy degrades

**Configuration**:
```python
drift_thresholds = {
    DriftType.DATA_DRIFT: {
        'psi': 0.25,              # PSI threshold
        'ks_p_value': 0.05        # KS test p-value
    },
    DriftType.PERFORMANCE_DRIFT: {
        'accuracy_drop': 0.05,    # Max accuracy drop
        'f1_drop': 0.1           # Max F1 score drop
    }
}
```

### TensorFlow Serving

**Purpose**: Deploy and serve ML models at scale with high performance.

**Features**:
- Multiple model versions
- A/B testing with version labels
- REST and gRPC APIs
- Model monitoring and health checks
- Batch prediction support

**Model Configuration**:
```protobuf
model_config_list {
  config {
    name: "etrm_risk_model"
    base_path: "/models/etrm_risk_model"
    model_platform: "tensorflow"
    model_version_policy {
      latest { num_versions: 2 }
    }
    version_labels {
      key: "stable"
      value: 1
    }
  }
}
```

**Client Usage**:
```python
from ml.tensorflow_serving_client import ETRMModelClient, TensorFlowServingClient

# Initialize client
client = ETRMModelClient(TensorFlowServingClient())

# Predict risk score
risk_result = client.predict_risk_score({
    'volume': 1000.0,
    'price': 75.50,
    'volatility': 0.25
})

print(f"Risk Score: {risk_result['risk_score']}")
print(f"Risk Level: {risk_result['risk_level']}")
```

### Continuous Learning

**Purpose**: Automate model lifecycle management with retraining, validation, and deployment.

**Workflow**:
1. **Data Collection**: Gather new training data
2. **Drift Detection**: Check if retraining is needed
3. **Model Training**: Train new model version
4. **Validation**: Compare against current model
5. **Deployment**: Deploy if validation passes
6. **Monitoring**: Track performance and rollback if needed

**Configuration**:
```python
@dataclass
class RetrainingConfig:
    model_name: str                    # Model identifier
    retrain_schedule: str              # Cron-like schedule
    data_window_days: int = 30         # Training data window
    min_samples_threshold: int = 1000  # Minimum samples required
    performance_threshold: float = 0.05 # Max performance drop
    auto_deploy: bool = False          # Auto-deploy after validation
    rollback_on_failure: bool = True   # Rollback on failure
```

**Job Management**:
- Async job execution
- Job status tracking
- Error handling and retry logic
- Notification system integration

## Deployment Architecture

### Development Setup
```
┌─────────────────────────────────────────┐
│              Development                │
├─────────────────────────────────────────┤
│  • Jupyter notebooks                   │
│  • Local model training                │
│  • Synthetic data generation           │
│  • Model experimentation               │
└─────────────────────────────────────────┘
```

### Production Architecture
```
┌─────────────────────────────────────────┐
│            Data Pipeline                │
├─────────────────────────────────────────┤
│  • Real-time data ingestion            │
│  • Feature engineering                 │
│  • Data quality monitoring             │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│          ML Pipeline                    │
├─────────────────────────────────────────┤
│  • Model training                      │
│  • Hyperparameter tuning              │
│  • Model validation                    │
│  • Experiment tracking                 │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│        Model Registry                   │
├─────────────────────────────────────────┤
│  • Version management                  │
│  • Model metadata                      │
│  • Deployment artifacts               │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      TensorFlow Serving                 │
├─────────────────────────────────────────┤
│  • Model serving                       │
│  • A/B testing                         │
│  • Load balancing                      │
│  • Health monitoring                   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│        Monitoring                       │
├─────────────────────────────────────────┤
│  • Drift detection                     │
│  • Performance tracking               │
│  • Alert management                    │
│  • Dashboard and reports              │
└─────────────────────────────────────────┘
```

## Testing

### Unit Tests
```python
# Example test for synthetic data generator
def test_synthetic_data_generation():
    config = ETRMDataConfig(num_trades=100)
    generator = SyntheticETRMDataGenerator(config)
    dataset = generator.generate_complete_dataset()
    
    assert len(dataset['trades']) == 100
    assert 'text_descriptions' in dataset
    assert len(dataset['metadata']['commodities']) > 0
```

### Integration Tests
```python
# Example test for drift detection
def test_drift_detection_integration():
    monitoring = ModelMonitoringService()
    reference_data = np.random.normal(0, 1, (1000, 5))
    monitoring.register_model("test_model", reference_data)
    
    # No drift data
    new_data = np.random.normal(0, 1, (200, 5))
    alerts = monitoring.detect_drift("test_model", new_data)
    assert len(alerts) == 0
    
    # Drift data
    drift_data = np.random.normal(2, 1, (200, 5))
    alerts = monitoring.detect_drift("test_model", drift_data)
    assert len(alerts) > 0
```

## Performance Optimization

### Training Optimization
- **Mixed Precision**: Use FP16 for faster training
- **Gradient Accumulation**: Handle large batch sizes
- **Distributed Training**: Multi-GPU/multi-node training
- **Efficient Data Loading**: Optimized data pipelines

### Serving Optimization
- **Model Optimization**: TensorRT, quantization
- **Batching**: Dynamic batching for throughput
- **Caching**: Response caching for repeated requests
- **Load Balancing**: Distribute load across replicas

### Memory Management
- **Model Pruning**: Remove unnecessary weights
- **Knowledge Distillation**: Create smaller models
- **Gradient Checkpointing**: Reduce memory usage
- **Efficient Storage**: Compressed model formats

## Monitoring and Alerting

### Key Metrics
- **Model Performance**: Accuracy, precision, recall, F1
- **Drift Scores**: PSI, KS statistic, distribution metrics
- **System Metrics**: Latency, throughput, error rates
- **Business Metrics**: Prediction quality, user satisfaction

### Alert Configuration
```python
# Alert configuration example
alert_rules = {
    'high_drift': {
        'condition': 'psi_score > 0.25',
        'severity': 'warning',
        'notification': ['email', 'slack']
    },
    'performance_drop': {
        'condition': 'accuracy < baseline_accuracy - 0.05',
        'severity': 'critical',
        'notification': ['email', 'slack', 'pager']
    }
}
```

### Dashboard Metrics
- Real-time model performance
- Drift detection status
- Training job progress
- System health indicators
- Prediction quality trends

## Security Considerations

### Data Security
- **Encryption**: Encrypt data at rest and in transit
- **Access Control**: Role-based access to models and data
- **Audit Logging**: Track all model access and modifications
- **Data Privacy**: Implement privacy-preserving techniques

### Model Security
- **Model Versioning**: Track all model changes
- **Signature Verification**: Verify model integrity
- **Access Logging**: Monitor model serving requests
- **Vulnerability Scanning**: Regular security assessments

## Troubleshooting

### Common Issues

1. **Model Training Fails**
   - Check data quality and format
   - Verify resource availability (CPU/Memory/GPU)
   - Review training logs for errors

2. **Drift Detection False Positives**
   - Adjust drift thresholds
   - Check for seasonal patterns
   - Validate reference data quality

3. **TensorFlow Serving Issues**
   - Verify model format and signatures
   - Check network connectivity
   - Review serving logs

4. **Continuous Learning Problems**
   - Monitor data pipeline health
   - Check training data availability
   - Verify model validation criteria

### Debug Commands
```bash
# Check model serving status
curl http://localhost:8501/v1/models

# View drift detection logs
docker logs qenergyz-drift-detector

# Monitor training job
docker logs qenergyz-training-job

# Check continuous learning pipeline
python -c "
from ml.continuous_learning_pipeline import ContinuousLearningPipeline
pipeline = ContinuousLearningPipeline()
print(pipeline.get_pipeline_status())
"
```

## Future Enhancements

### Short Term (3-6 months)
- Advanced drift detection algorithms
- AutoML for hyperparameter tuning
- Enhanced model explainability
- Multi-model ensemble support

### Medium Term (6-12 months)
- Federated learning capabilities
- Advanced A/B testing framework
- Custom model architectures
- Real-time feature engineering

### Long Term (12+ months)
- Edge deployment support
- Quantum ML integration
- Advanced privacy-preserving ML
- Cross-platform model compatibility

## Support and Resources

### Documentation Links
- [TensorFlow Serving Guide](https://www.tensorflow.org/tfx/guide/serving)
- [MLOps Best Practices](https://ml-ops.org/)
- [Model Monitoring Guide](https://christophergs.com/machine%20learning/2020/03/14/how-to-monitor-machine-learning-models/)

### Internal Resources
- ML Engineering Team: `ml-eng@qenergyz.com`
- Model Registry: `http://internal-registry:8080`
- Training Infrastructure: `http://internal-kubeflow:8080`
- Monitoring Dashboard: `http://internal-grafana:3000`

For technical support:
1. Check service logs and monitoring dashboards
2. Review troubleshooting guide
3. Contact ML engineering team with detailed error information
4. Create support ticket with reproduction steps