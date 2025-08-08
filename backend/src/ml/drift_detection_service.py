"""
Model Monitoring and Drift Detection Service

This service provides comprehensive model monitoring capabilities including
drift detection, performance monitoring, and alerting for ML models in production.
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class DriftType(Enum):
    """Types of drift that can be detected"""
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    PERFORMANCE_DRIFT = "performance_drift"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    """Drift detection alert"""
    alert_id: str
    timestamp: datetime
    model_name: str
    drift_type: DriftType
    alert_level: AlertLevel
    drift_score: float
    threshold: float
    message: str
    metrics: Dict[str, Any]
    recommendations: List[str]


@dataclass
class ModelMetrics:
    """Model performance metrics"""
    timestamp: datetime
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    prediction_count: int
    avg_confidence: float
    drift_scores: Dict[str, float]


class DriftDetector:
    """Statistical drift detection methods"""
    
    def __init__(self, reference_window: int = 1000, detection_window: int = 100):
        self.reference_window = reference_window
        self.detection_window = detection_window
        self.reference_data = None
        self.reference_stats = {}
        
    def set_reference_data(self, data: np.ndarray):
        """Set reference data for drift detection"""
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        self.reference_data = data[-self.reference_window:]
        
        # Calculate reference statistics
        self.reference_stats = {
            'mean': np.mean(self.reference_data, axis=0),
            'std': np.std(self.reference_data, axis=0),
            'quantiles': np.percentile(self.reference_data, [25, 50, 75], axis=0),
            'min': np.min(self.reference_data, axis=0),
            'max': np.max(self.reference_data, axis=0)
        }
        
        logger.info(f"Reference data set with {len(self.reference_data)} samples")
    
    def detect_data_drift_ks(self, new_data: np.ndarray, feature_names: List[str] = None) -> Dict[str, float]:
        """Detect data drift using Kolmogorov-Smirnov test"""
        if self.reference_data is None:
            raise ValueError("Reference data not set. Call set_reference_data() first.")
        
        if len(new_data.shape) == 1:
            new_data = new_data.reshape(-1, 1)
        
        drift_scores = {}
        n_features = min(self.reference_data.shape[1], new_data.shape[1])
        
        for i in range(n_features):
            feature_name = feature_names[i] if feature_names else f"feature_{i}"
            
            # Kolmogorov-Smirnov test
            ks_statistic, p_value = stats.ks_2samp(
                self.reference_data[:, i], 
                new_data[:, i]
            )
            
            # Use KS statistic as drift score (0-1, higher = more drift)
            drift_scores[feature_name] = {
                'ks_statistic': float(ks_statistic),
                'p_value': float(p_value),
                'drift_detected': p_value < 0.05
            }
        
        return drift_scores
    
    def detect_data_drift_psi(self, new_data: np.ndarray, feature_names: List[str] = None, n_bins: int = 10) -> Dict[str, float]:
        """Detect data drift using Population Stability Index (PSI)"""
        if self.reference_data is None:
            raise ValueError("Reference data not set. Call set_reference_data() first.")
        
        if len(new_data.shape) == 1:
            new_data = new_data.reshape(-1, 1)
        
        drift_scores = {}
        n_features = min(self.reference_data.shape[1], new_data.shape[1])
        
        for i in range(n_features):
            feature_name = feature_names[i] if feature_names else f"feature_{i}"
            
            ref_feature = self.reference_data[:, i]
            new_feature = new_data[:, i]
            
            # Create bins based on reference data
            _, bin_edges = np.histogram(ref_feature, bins=n_bins)
            
            # Calculate distributions
            ref_counts, _ = np.histogram(ref_feature, bins=bin_edges)
            new_counts, _ = np.histogram(new_feature, bins=bin_edges)
            
            # Avoid division by zero
            ref_props = (ref_counts + 1e-6) / (len(ref_feature) + n_bins * 1e-6)
            new_props = (new_counts + 1e-6) / (len(new_feature) + n_bins * 1e-6)
            
            # Calculate PSI
            psi = np.sum((new_props - ref_props) * np.log(new_props / ref_props))
            
            drift_scores[feature_name] = {
                'psi_score': float(psi),
                'drift_level': 'low' if psi < 0.1 else 'medium' if psi < 0.25 else 'high'
            }
        
        return drift_scores
    
    def detect_prediction_drift(self, ref_predictions: np.ndarray, new_predictions: np.ndarray) -> Dict[str, Any]:
        """Detect drift in model predictions"""
        # Statistical tests on prediction distributions
        ks_stat, ks_p = stats.ks_2samp(ref_predictions, new_predictions)
        
        # Compare means and variances
        ref_mean, new_mean = np.mean(ref_predictions), np.mean(new_predictions)
        ref_std, new_std = np.std(ref_predictions), np.std(new_predictions)
        
        mean_shift = abs(new_mean - ref_mean) / (ref_std + 1e-6)
        variance_ratio = new_std / (ref_std + 1e-6)
        
        return {
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_p),
            'mean_shift': float(mean_shift),
            'variance_ratio': float(variance_ratio),
            'ref_mean': float(ref_mean),
            'new_mean': float(new_mean),
            'ref_std': float(ref_std),
            'new_std': float(new_std)
        }


class ModelMonitoringService:
    """Comprehensive model monitoring service"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.drift_detectors = {}
        self.model_metrics_history = {}
        self.alerts = []
        self.performance_baseline = {}
        
        # Initialize drift thresholds
        self.drift_thresholds = {
            DriftType.DATA_DRIFT: {
                'psi': 0.25,
                'ks_p_value': 0.05
            },
            DriftType.PREDICTION_DRIFT: {
                'ks_p_value': 0.05,
                'mean_shift': 2.0
            },
            DriftType.PERFORMANCE_DRIFT: {
                'accuracy_drop': 0.05,
                'f1_drop': 0.1
            }
        }
    
    def _default_config(self) -> Dict[str, Any]:
        """Default monitoring configuration"""
        return {
            'reference_window_size': 1000,
            'detection_window_size': 100,
            'monitoring_interval': 3600,  # 1 hour
            'alert_cooldown': 7200,      # 2 hours
            'max_alerts_per_model': 10,
            'enable_auto_retraining': False,
            'drift_detection_methods': ['psi', 'ks_test'],
            'performance_metrics': ['accuracy', 'precision', 'recall', 'f1']
        }
    
    def register_model(self, model_name: str, reference_data: np.ndarray = None, 
                      reference_predictions: np.ndarray = None):
        """Register a model for monitoring"""
        self.drift_detectors[model_name] = DriftDetector(
            reference_window=self.config['reference_window_size'],
            detection_window=self.config['detection_window_size']
        )
        
        if reference_data is not None:
            self.drift_detectors[model_name].set_reference_data(reference_data)
        
        self.model_metrics_history[model_name] = []
        
        logger.info(f"Registered model '{model_name}' for monitoring")
    
    def update_reference_data(self, model_name: str, new_data: np.ndarray):
        """Update reference data for a model"""
        if model_name not in self.drift_detectors:
            raise ValueError(f"Model '{model_name}' not registered")
        
        self.drift_detectors[model_name].set_reference_data(new_data)
        logger.info(f"Updated reference data for model '{model_name}'")
    
    def detect_drift(self, model_name: str, new_data: np.ndarray, 
                    new_predictions: np.ndarray = None, 
                    feature_names: List[str] = None) -> List[DriftAlert]:
        """Comprehensive drift detection"""
        if model_name not in self.drift_detectors:
            raise ValueError(f"Model '{model_name}' not registered")
        
        detector = self.drift_detectors[model_name]
        alerts = []
        
        # Data drift detection
        if 'psi' in self.config['drift_detection_methods']:
            psi_results = detector.detect_data_drift_psi(new_data, feature_names)
            alerts.extend(self._check_psi_drift(model_name, psi_results))
        
        if 'ks_test' in self.config['drift_detection_methods']:
            ks_results = detector.detect_data_drift_ks(new_data, feature_names)
            alerts.extend(self._check_ks_drift(model_name, ks_results))
        
        # Prediction drift detection
        if new_predictions is not None and detector.reference_data is not None:
            # For prediction drift, we need reference predictions
            # This is a simplified version - in practice, you'd store reference predictions
            ref_predictions = np.random.normal(0.5, 0.2, len(detector.reference_data))
            pred_drift = detector.detect_prediction_drift(ref_predictions, new_predictions)
            alerts.extend(self._check_prediction_drift(model_name, pred_drift))
        
        # Store alerts
        self.alerts.extend(alerts)
        
        # Keep only recent alerts
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff_time]
        
        return alerts
    
    def _check_psi_drift(self, model_name: str, psi_results: Dict[str, Dict]) -> List[DriftAlert]:
        """Check PSI drift results and create alerts"""
        alerts = []
        threshold = self.drift_thresholds[DriftType.DATA_DRIFT]['psi']
        
        for feature, results in psi_results.items():
            psi_score = results['psi_score']
            
            if psi_score > threshold:
                alert_level = AlertLevel.CRITICAL if psi_score > 0.5 else AlertLevel.WARNING
                
                alert = DriftAlert(
                    alert_id=f"drift_{model_name}_{feature}_{int(time.time())}",
                    timestamp=datetime.now(),
                    model_name=model_name,
                    drift_type=DriftType.DATA_DRIFT,
                    alert_level=alert_level,
                    drift_score=psi_score,
                    threshold=threshold,
                    message=f"Data drift detected in feature '{feature}' using PSI method",
                    metrics={'psi_score': psi_score, 'drift_level': results['drift_level']},
                    recommendations=[
                        "Investigate data quality and preprocessing pipelines",
                        "Consider retraining the model with recent data",
                        "Monitor feature importance changes"
                    ]
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_ks_drift(self, model_name: str, ks_results: Dict[str, Dict]) -> List[DriftAlert]:
        """Check KS test drift results and create alerts"""
        alerts = []
        threshold = self.drift_thresholds[DriftType.DATA_DRIFT]['ks_p_value']
        
        for feature, results in ks_results.items():
            if results['drift_detected']:
                alert = DriftAlert(
                    alert_id=f"drift_{model_name}_{feature}_ks_{int(time.time())}",
                    timestamp=datetime.now(),
                    model_name=model_name,
                    drift_type=DriftType.DATA_DRIFT,
                    alert_level=AlertLevel.WARNING,
                    drift_score=results['ks_statistic'],
                    threshold=threshold,
                    message=f"Statistical drift detected in feature '{feature}' using KS test",
                    metrics={
                        'ks_statistic': results['ks_statistic'],
                        'p_value': results['p_value']
                    },
                    recommendations=[
                        "Analyze feature distribution changes",
                        "Check for seasonality or external factors",
                        "Validate data collection processes"
                    ]
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_prediction_drift(self, model_name: str, pred_drift: Dict[str, Any]) -> List[DriftAlert]:
        """Check prediction drift results"""
        alerts = []
        
        if pred_drift['ks_p_value'] < self.drift_thresholds[DriftType.PREDICTION_DRIFT]['ks_p_value']:
            alert = DriftAlert(
                alert_id=f"pred_drift_{model_name}_{int(time.time())}",
                timestamp=datetime.now(),
                model_name=model_name,
                drift_type=DriftType.PREDICTION_DRIFT,
                alert_level=AlertLevel.WARNING,
                drift_score=pred_drift['ks_statistic'],
                threshold=self.drift_thresholds[DriftType.PREDICTION_DRIFT]['ks_p_value'],
                message=f"Prediction distribution drift detected for model '{model_name}'",
                metrics=pred_drift,
                recommendations=[
                    "Review model behavior on recent data",
                    "Check for changes in input data patterns",
                    "Consider model recalibration"
                ]
            )
            alerts.append(alert)
        
        return alerts
    
    def log_model_performance(self, model_name: str, y_true: np.ndarray, 
                             y_pred: np.ndarray, y_proba: np.ndarray = None):
        """Log model performance metrics"""
        # Calculate metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted')
        
        avg_confidence = np.mean(np.max(y_proba, axis=1)) if y_proba is not None else 0.0
        
        metrics = ModelMetrics(
            timestamp=datetime.now(),
            model_name=model_name,
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            prediction_count=len(y_true),
            avg_confidence=float(avg_confidence),
            drift_scores={}
        )
        
        # Store metrics
        if model_name not in self.model_metrics_history:
            self.model_metrics_history[model_name] = []
        
        self.model_metrics_history[model_name].append(metrics)
        
        # Keep only recent metrics (last 30 days)
        cutoff_time = datetime.now() - timedelta(days=30)
        self.model_metrics_history[model_name] = [
            m for m in self.model_metrics_history[model_name] 
            if m.timestamp > cutoff_time
        ]
        
        # Check for performance drift
        alerts = self._check_performance_drift(model_name, metrics)
        self.alerts.extend(alerts)
        
        logger.info(f"Logged performance for model '{model_name}': Accuracy={accuracy:.3f}, F1={f1:.3f}")
        
        return metrics
    
    def _check_performance_drift(self, model_name: str, current_metrics: ModelMetrics) -> List[DriftAlert]:
        """Check for performance degradation"""
        alerts = []
        
        if model_name not in self.performance_baseline:
            # Set baseline if this is the first measurement
            self.performance_baseline[model_name] = current_metrics
            return alerts
        
        baseline = self.performance_baseline[model_name]
        
        # Check accuracy drift
        accuracy_drop = baseline.accuracy - current_metrics.accuracy
        if accuracy_drop > self.drift_thresholds[DriftType.PERFORMANCE_DRIFT]['accuracy_drop']:
            alert = DriftAlert(
                alert_id=f"perf_drift_acc_{model_name}_{int(time.time())}",
                timestamp=datetime.now(),
                model_name=model_name,
                drift_type=DriftType.PERFORMANCE_DRIFT,
                alert_level=AlertLevel.CRITICAL,
                drift_score=accuracy_drop,
                threshold=self.drift_thresholds[DriftType.PERFORMANCE_DRIFT]['accuracy_drop'],
                message=f"Significant accuracy drop detected for model '{model_name}'",
                metrics={
                    'baseline_accuracy': baseline.accuracy,
                    'current_accuracy': current_metrics.accuracy,
                    'accuracy_drop': accuracy_drop
                },
                recommendations=[
                    "Investigate recent data quality issues",
                    "Consider immediate model retraining",
                    "Review feature engineering pipeline",
                    "Check for concept drift in the problem domain"
                ]
            )
            alerts.append(alert)
        
        return alerts
    
    def get_monitoring_summary(self, model_name: str = None) -> Dict[str, Any]:
        """Get monitoring summary for models"""
        if model_name:
            models = [model_name] if model_name in self.model_metrics_history else []
        else:
            models = list(self.model_metrics_history.keys())
        
        summary = {}
        
        for model in models:
            recent_metrics = self.model_metrics_history[model][-10:]  # Last 10 measurements
            recent_alerts = [a for a in self.alerts if a.model_name == model]
            
            if recent_metrics:
                latest = recent_metrics[-1]
                avg_accuracy = np.mean([m.accuracy for m in recent_metrics])
                
                summary[model] = {
                    'latest_metrics': asdict(latest),
                    'avg_accuracy_recent': float(avg_accuracy),
                    'total_predictions': sum(m.prediction_count for m in recent_metrics),
                    'alert_count': len(recent_alerts),
                    'critical_alerts': len([a for a in recent_alerts if a.alert_level == AlertLevel.CRITICAL]),
                    'last_updated': latest.timestamp.isoformat()
                }
        
        return summary
    
    async def start_monitoring(self):
        """Start continuous monitoring loop"""
        logger.info("Starting model monitoring service...")
        
        while True:
            try:
                # This would typically fetch new data and run monitoring
                # For now, it's just a placeholder
                await asyncio.sleep(self.config['monitoring_interval'])
                
                # In a real implementation, you would:
                # 1. Fetch new prediction data
                # 2. Run drift detection
                # 3. Send alerts if needed
                # 4. Update dashboards
                
                logger.info("Monitoring cycle completed")
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying


# Example usage and testing
if __name__ == "__main__":
    # Create monitoring service
    monitoring = ModelMonitoringService()
    
    # Generate synthetic data for testing
    np.random.seed(42)
    reference_data = np.random.normal(0, 1, (1000, 5))
    new_data_normal = np.random.normal(0, 1, (200, 5))  # No drift
    new_data_drift = np.random.normal(0.5, 1.5, (200, 5))  # With drift
    
    # Register model
    monitoring.register_model("test_model", reference_data)
    
    # Test drift detection
    print("Testing drift detection...")
    
    # No drift case
    alerts_normal = monitoring.detect_drift("test_model", new_data_normal)
    print(f"Alerts for normal data: {len(alerts_normal)}")
    
    # Drift case
    alerts_drift = monitoring.detect_drift("test_model", new_data_drift)
    print(f"Alerts for drift data: {len(alerts_drift)}")
    
    for alert in alerts_drift:
        print(f"Alert: {alert.message} (Score: {alert.drift_score:.3f})")
    
    # Test performance monitoring
    y_true = np.random.randint(0, 2, 100)
    y_pred = np.random.randint(0, 2, 100)
    
    metrics = monitoring.log_model_performance("test_model", y_true, y_pred)
    print(f"Performance metrics: Accuracy={metrics.accuracy:.3f}")
    
    # Get summary
    summary = monitoring.get_monitoring_summary()
    print(f"Monitoring summary: {json.dumps(summary, indent=2, default=str)}")