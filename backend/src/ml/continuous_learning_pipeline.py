"""
Continuous Learning Pipeline for ETRM Models

This module implements a continuous learning workflow that includes:
- Scheduled retraining on new data
- Automated model evaluation and validation
- Safe deployment with rollback capabilities
- Performance monitoring and alerting
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from synthetic_data_generator import SyntheticETRMDataGenerator, ETRMDataConfig
from drift_detection_service import ModelMonitoringService, DriftType, AlertLevel
from model_fine_tuning import ETRMLanguageModel, ModelConfig, ETRMTokenizer

logger = logging.getLogger(__name__)


@dataclass
class RetrainingConfig:
    """Configuration for model retraining"""
    model_name: str
    retrain_schedule: str  # cron-like schedule
    data_window_days: int = 30
    min_samples_threshold: int = 1000
    performance_threshold: float = 0.05  # Max performance drop allowed
    drift_threshold: float = 0.25
    validation_split: float = 0.2
    max_retrain_attempts: int = 3
    auto_deploy: bool = False
    rollback_on_failure: bool = True


@dataclass
class RetrainingJob:
    """Retraining job status"""
    job_id: str
    model_name: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    trigger_reason: str = ""
    old_performance: Dict[str, float] = None
    new_performance: Dict[str, float] = None
    model_version: Optional[int] = None
    error_message: Optional[str] = None
    artifacts_path: Optional[str] = None


@dataclass
class ModelVersion:
    """Model version information"""
    version: int
    model_path: str
    performance_metrics: Dict[str, float]
    created_at: datetime
    is_active: bool = False
    is_champion: bool = False
    validation_results: Dict[str, Any] = None


class ContinuousLearningPipeline:
    """Main continuous learning pipeline orchestrator"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.monitoring_service = ModelMonitoringService()
        self.retrain_configs = {}
        self.active_jobs = {}
        self.model_versions = {}
        self.job_history = []
        
        # Paths
        self.models_base_path = Path(self.config.get('models_path', './models'))
        self.data_path = Path(self.config.get('data_path', './training_data'))
        self.artifacts_path = Path(self.config.get('artifacts_path', './artifacts'))
        
        # Ensure paths exist
        for path in [self.models_base_path, self.data_path, self.artifacts_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def _default_config(self) -> Dict[str, Any]:
        """Default pipeline configuration"""
        return {
            'check_interval': 3600,  # 1 hour
            'models_path': './models',
            'data_path': './training_data',
            'artifacts_path': './artifacts',
            'max_concurrent_jobs': 2,
            'notification_webhook': None,
            'model_registry_url': None,
            'performance_tracking_days': 30
        }
    
    def register_model_for_retraining(self, config: RetrainingConfig):
        """Register a model for continuous learning"""
        self.retrain_configs[config.model_name] = config
        
        # Initialize model versions tracking
        self.model_versions[config.model_name] = []
        
        # Register with monitoring service
        self.monitoring_service.register_model(config.model_name)
        
        logger.info(f"Registered model '{config.model_name}' for continuous learning")
    
    def collect_training_data(self, model_name: str, days: int = 30) -> Optional[pd.DataFrame]:
        """Collect new training data for model retraining"""
        try:
            # In a real implementation, this would query your data warehouse
            # For demo, we generate synthetic data
            logger.info(f"Collecting training data for {model_name} (last {days} days)")
            
            config = ETRMDataConfig(
                num_trades=2000,
                num_risk_reports=50,
                start_date=datetime.now() - timedelta(days=days),
                end_date=datetime.now()
            )
            
            generator = SyntheticETRMDataGenerator(config)
            dataset = generator.generate_complete_dataset()
            
            # Save data
            data_file = self.data_path / f"{model_name}_training_data_{datetime.now().strftime('%Y%m%d')}.csv"
            
            # Combine different data types for training
            combined_data = []
            for text in dataset['text_descriptions']:
                combined_data.append({
                    'text': text,
                    'timestamp': datetime.now(),
                    'model_name': model_name
                })
            
            df = pd.DataFrame(combined_data)
            df.to_csv(data_file, index=False)
            
            logger.info(f"Collected {len(df)} training samples for {model_name}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to collect training data for {model_name}: {e}")
            return None
    
    def evaluate_retrain_trigger(self, model_name: str) -> Tuple[bool, str]:
        """Evaluate if model needs retraining"""
        if model_name not in self.retrain_configs:
            return False, "Model not registered"
        
        config = self.retrain_configs[model_name]
        
        # Check drift
        monitoring_summary = self.monitoring_service.get_monitoring_summary(model_name)
        if model_name in monitoring_summary:
            summary = monitoring_summary[model_name]
            
            # Check for critical alerts
            if summary.get('critical_alerts', 0) > 0:
                return True, "Critical drift alerts detected"
            
            # Check performance degradation
            if 'latest_metrics' in summary:
                current_accuracy = summary['latest_metrics'].get('accuracy', 1.0)
                if current_accuracy < (1.0 - config.performance_threshold):
                    return True, f"Performance dropped below threshold: {current_accuracy:.3f}"
        
        # Check scheduled retraining
        # For simplicity, trigger every 7 days
        last_retrain = self._get_last_retrain_time(model_name)
        if last_retrain and (datetime.now() - last_retrain).days >= 7:
            return True, "Scheduled retraining"
        
        return False, "No retraining needed"
    
    def _get_last_retrain_time(self, model_name: str) -> Optional[datetime]:
        """Get last retraining time for model"""
        versions = self.model_versions.get(model_name, [])
        if versions:
            return max(v.created_at for v in versions)
        return None
    
    async def retrain_model(self, model_name: str, trigger_reason: str = "") -> RetrainingJob:
        """Retrain a specific model"""
        job_id = f"retrain_{model_name}_{int(datetime.now().timestamp())}"
        
        job = RetrainingJob(
            job_id=job_id,
            model_name=model_name,
            status='pending',
            trigger_reason=trigger_reason
        )
        
        self.active_jobs[job_id] = job
        
        try:
            job.status = 'running'
            job.started_at = datetime.now()
            
            logger.info(f"Starting retraining job {job_id} for model {model_name}")
            
            # 1. Collect training data
            training_data = self.collect_training_data(
                model_name, 
                self.retrain_configs[model_name].data_window_days
            )
            
            if training_data is None or len(training_data) < self.retrain_configs[model_name].min_samples_threshold:
                raise Exception(f"Insufficient training data: {len(training_data) if training_data is not None else 0}")
            
            # 2. Get baseline performance
            job.old_performance = self._get_current_model_performance(model_name)
            
            # 3. Train new model
            new_model_path, performance_metrics = await self._train_new_model(
                model_name, 
                training_data
            )
            
            job.new_performance = performance_metrics
            job.artifacts_path = str(new_model_path)
            
            # 4. Validate new model
            validation_passed, validation_results = self._validate_new_model(
                model_name, 
                job.old_performance, 
                job.new_performance
            )
            
            if not validation_passed:
                raise Exception(f"Model validation failed: {validation_results}")
            
            # 5. Create new model version
            new_version = self._create_model_version(
                model_name,
                new_model_path,
                performance_metrics,
                validation_results
            )
            
            job.model_version = new_version.version
            
            # 6. Deploy if auto-deploy is enabled
            if self.retrain_configs[model_name].auto_deploy:
                self._deploy_model_version(model_name, new_version.version)
                logger.info(f"Auto-deployed model {model_name} version {new_version.version}")
            
            job.status = 'completed'
            job.completed_at = datetime.now()
            
            logger.info(f"Retraining job {job_id} completed successfully")
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now()
            
            logger.error(f"Retraining job {job_id} failed: {e}")
            
            # Rollback if needed
            if self.retrain_configs[model_name].rollback_on_failure:
                self._rollback_model(model_name)
        
        finally:
            # Move job to history
            self.job_history.append(job)
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            # Send notification
            await self._send_notification(job)
        
        return job
    
    async def _train_new_model(self, model_name: str, training_data: pd.DataFrame) -> Tuple[Path, Dict[str, float]]:
        """Train a new model version"""
        logger.info(f"Training new model for {model_name}")
        
        # Prepare text data
        texts = training_data['text'].tolist()
        
        # Split data
        train_texts, val_texts = train_test_split(texts, test_size=0.2, random_state=42)
        
        # Build tokenizer
        tokenizer = ETRMTokenizer(vocab_size=5000)
        tokenizer.build_vocab(train_texts)
        
        # Create model config
        model_config = ModelConfig(
            vocab_size=tokenizer.vocab_size,
            max_length=256,
            batch_size=16,
            epochs=3,  # Fewer epochs for continuous learning
            hidden_dim=128
        )
        
        # Train model
        model = ETRMLanguageModel(model_config, tokenizer)
        history = model.train(train_texts, validation_split=0.2)
        
        # Evaluate on validation set
        eval_results = model.evaluate_model(val_texts)
        
        # Save model
        model_dir = self.models_base_path / model_name / f"v{int(datetime.now().timestamp())}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model.save_model(str(model_dir))
        
        # Performance metrics
        performance_metrics = {
            'accuracy': eval_results['accuracy'],
            'loss': eval_results['loss'],
            'perplexity': eval_results['perplexity'],
            'training_samples': len(train_texts),
            'validation_samples': len(val_texts)
        }
        
        return model_dir, performance_metrics
    
    def _get_current_model_performance(self, model_name: str) -> Dict[str, float]:
        """Get current model performance metrics"""
        monitoring_summary = self.monitoring_service.get_monitoring_summary(model_name)
        
        if model_name in monitoring_summary and 'latest_metrics' in monitoring_summary[model_name]:
            latest = monitoring_summary[model_name]['latest_metrics']
            return {
                'accuracy': latest.get('accuracy', 0.0),
                'precision': latest.get('precision', 0.0),
                'recall': latest.get('recall', 0.0),
                'f1_score': latest.get('f1_score', 0.0)
            }
        
        return {'accuracy': 0.0, 'precision': 0.0, 'recall': 0.0, 'f1_score': 0.0}
    
    def _validate_new_model(self, model_name: str, old_perf: Dict[str, float], 
                           new_perf: Dict[str, float]) -> Tuple[bool, Dict[str, Any]]:
        """Validate new model against current model"""
        config = self.retrain_configs[model_name]
        
        validation_results = {
            'performance_comparison': {},
            'drift_tests': {},
            'business_validation': {}
        }
        
        # Performance validation
        for metric in ['accuracy', 'loss', 'perplexity']:
            old_val = old_perf.get(metric, 0.0)
            new_val = new_perf.get(metric, 0.0)
            
            if metric == 'loss' or metric == 'perplexity':
                # Lower is better for loss and perplexity
                improvement = old_val - new_val
            else:
                # Higher is better for accuracy
                improvement = new_val - old_val
            
            validation_results['performance_comparison'][metric] = {
                'old_value': old_val,
                'new_value': new_val,
                'improvement': improvement,
                'passed': improvement >= -config.performance_threshold
            }
        
        # Overall validation
        accuracy_passed = validation_results['performance_comparison']['accuracy']['passed']
        loss_passed = validation_results['performance_comparison']['loss']['passed']
        
        overall_passed = accuracy_passed and loss_passed
        
        validation_results['overall_passed'] = overall_passed
        validation_results['validation_timestamp'] = datetime.now().isoformat()
        
        return overall_passed, validation_results
    
    def _create_model_version(self, model_name: str, model_path: Path, 
                             performance_metrics: Dict[str, float],
                             validation_results: Dict[str, Any]) -> ModelVersion:
        """Create a new model version"""
        versions = self.model_versions.get(model_name, [])
        new_version_num = len(versions) + 1
        
        version = ModelVersion(
            version=new_version_num,
            model_path=str(model_path),
            performance_metrics=performance_metrics,
            created_at=datetime.now(),
            validation_results=validation_results
        )
        
        versions.append(version)
        self.model_versions[model_name] = versions
        
        logger.info(f"Created model version {new_version_num} for {model_name}")
        return version
    
    def _deploy_model_version(self, model_name: str, version: int):
        """Deploy a specific model version"""
        versions = self.model_versions.get(model_name, [])
        
        # Deactivate current active version
        for v in versions:
            v.is_active = False
            v.is_champion = False
        
        # Activate new version
        for v in versions:
            if v.version == version:
                v.is_active = True
                v.is_champion = True
                break
        
        logger.info(f"Deployed model {model_name} version {version}")
    
    def _rollback_model(self, model_name: str):
        """Rollback to previous model version"""
        versions = self.model_versions.get(model_name, [])
        
        if len(versions) < 2:
            logger.warning(f"Cannot rollback {model_name}: No previous version available")
            return
        
        # Deactivate current version and activate previous
        current_active = None
        previous_version = None
        
        for i, v in enumerate(sorted(versions, key=lambda x: x.version, reverse=True)):
            if v.is_active:
                current_active = v
                if i + 1 < len(versions):
                    previous_version = sorted(versions, key=lambda x: x.version, reverse=True)[i + 1]
                break
        
        if current_active and previous_version:
            current_active.is_active = False
            current_active.is_champion = False
            previous_version.is_active = True
            previous_version.is_champion = True
            
            logger.info(f"Rolled back {model_name} from v{current_active.version} to v{previous_version.version}")
    
    async def _send_notification(self, job: RetrainingJob):
        """Send notification about job completion"""
        notification = {
            'job_id': job.job_id,
            'model_name': job.model_name,
            'status': job.status,
            'trigger_reason': job.trigger_reason,
            'duration': (job.completed_at - job.started_at).total_seconds() if job.completed_at and job.started_at else None,
            'performance_improvement': None,
            'error_message': job.error_message
        }
        
        if job.old_performance and job.new_performance:
            old_acc = job.old_performance.get('accuracy', 0.0)
            new_acc = job.new_performance.get('accuracy', 0.0)
            notification['performance_improvement'] = new_acc - old_acc
        
        # In a real implementation, send to webhook or messaging system
        logger.info(f"Notification: {json.dumps(notification, indent=2, default=str)}")
    
    async def run_continuous_learning_loop(self):
        """Main continuous learning loop"""
        logger.info("Starting continuous learning pipeline...")
        
        while True:
            try:
                # Check each registered model
                for model_name in self.retrain_configs.keys():
                    # Skip if already retraining
                    active_jobs_for_model = [
                        job for job in self.active_jobs.values() 
                        if job.model_name == model_name
                    ]
                    
                    if active_jobs_for_model:
                        continue
                    
                    # Check if retraining is needed
                    needs_retrain, reason = self.evaluate_retrain_trigger(model_name)
                    
                    if needs_retrain:
                        logger.info(f"Triggering retraining for {model_name}: {reason}")
                        await self.retrain_model(model_name, reason)
                    
                    # Limit concurrent jobs
                    if len(self.active_jobs) >= self.config['max_concurrent_jobs']:
                        break
                
                # Wait before next check
                await asyncio.sleep(self.config['check_interval'])
                
            except Exception as e:
                logger.error(f"Error in continuous learning loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return {
            'active_jobs': len(self.active_jobs),
            'registered_models': list(self.retrain_configs.keys()),
            'recent_jobs': [asdict(job) for job in self.job_history[-10:]],
            'model_versions': {
                name: [{'version': v.version, 'is_active': v.is_active, 'performance': v.performance_metrics}
                       for v in versions]
                for name, versions in self.model_versions.items()
            }
        }


# Example usage
async def main():
    """Example usage of continuous learning pipeline"""
    pipeline = ContinuousLearningPipeline()
    
    # Register models for continuous learning
    risk_config = RetrainingConfig(
        model_name="etrm_risk_model",
        retrain_schedule="0 2 * * 0",  # Weekly at 2 AM Sunday
        data_window_days=30,
        auto_deploy=False,
        rollback_on_failure=True
    )
    
    pipeline.register_model_for_retraining(risk_config)
    
    # Manual retrain trigger
    job = await pipeline.retrain_model("etrm_risk_model", "Manual trigger")
    print(f"Retraining job status: {job.status}")
    
    # Get pipeline status
    status = pipeline.get_pipeline_status()
    print(f"Pipeline status: {json.dumps(status, indent=2, default=str)}")


if __name__ == "__main__":
    asyncio.run(main())