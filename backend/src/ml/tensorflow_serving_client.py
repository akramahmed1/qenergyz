"""
TensorFlow Serving Client for Qenergyz ML Models

This module provides a client interface for interacting with TensorFlow Serving
deployed models for risk management, pricing, and compliance predictions.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import numpy as np
import requests
import grpc
from tensorflow_serving.apis import predict_pb2, prediction_service_pb2_grpc
import tensorflow as tf

logger = logging.getLogger(__name__)


@dataclass
class ModelPredictionRequest:
    """Model prediction request"""
    model_name: str
    inputs: Dict[str, np.ndarray]
    model_version: Optional[int] = None
    signature_name: str = "serving_default"


@dataclass
class ModelPredictionResponse:
    """Model prediction response"""
    outputs: Dict[str, np.ndarray]
    model_name: str
    model_version: int
    prediction_time: float
    status: str = "success"
    error_message: Optional[str] = None


class TensorFlowServingClient:
    """Client for TensorFlow Serving REST API"""
    
    def __init__(self, host: str = "localhost", port: int = 8501, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        
    def predict(self, request: ModelPredictionRequest) -> ModelPredictionResponse:
        """Make prediction request via REST API"""
        start_time = time.time()
        
        # Prepare URL
        if request.model_version:
            url = f"{self.base_url}/v1/models/{request.model_name}/versions/{request.model_version}:predict"
        else:
            url = f"{self.base_url}/v1/models/{request.model_name}:predict"
        
        # Prepare request payload
        instances = []
        for key, value in request.inputs.items():
            if isinstance(value, np.ndarray):
                instances.append({key: value.tolist()})
        
        payload = {
            "instances": instances,
            "signature_name": request.signature_name
        }
        
        try:
            # Make request
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            prediction_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse predictions
                predictions = result.get("predictions", [])
                outputs = {}
                
                if predictions:
                    # Assume single instance prediction for simplicity
                    pred = predictions[0]
                    for key, value in pred.items():
                        outputs[key] = np.array(value)
                
                return ModelPredictionResponse(
                    outputs=outputs,
                    model_name=request.model_name,
                    model_version=result.get("model_version", -1),
                    prediction_time=prediction_time
                )
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Prediction failed: {error_msg}")
                
                return ModelPredictionResponse(
                    outputs={},
                    model_name=request.model_name,
                    model_version=-1,
                    prediction_time=prediction_time,
                    status="error",
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            
            return ModelPredictionResponse(
                outputs={},
                model_name=request.model_name,
                model_version=-1,
                prediction_time=time.time() - start_time,
                status="error",
                error_message=error_msg
            )
    
    def get_model_status(self, model_name: str) -> Dict[str, Any]:
        """Get model status and metadata"""
        try:
            url = f"{self.base_url}/v1/models/{model_name}"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def list_models(self) -> Dict[str, Any]:
        """List all available models"""
        try:
            url = f"{self.base_url}/v1/models"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}


class TensorFlowServingGRPCClient:
    """Client for TensorFlow Serving gRPC API (higher performance)"""
    
    def __init__(self, host: str = "localhost", port: int = 8500, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = prediction_service_pb2_grpc.PredictionServiceStub(self.channel)
    
    def predict(self, request: ModelPredictionRequest) -> ModelPredictionResponse:
        """Make prediction request via gRPC API"""
        start_time = time.time()
        
        # Create gRPC request
        grpc_request = predict_pb2.PredictRequest()
        grpc_request.model_spec.name = request.model_name
        grpc_request.model_spec.signature_name = request.signature_name
        
        if request.model_version:
            grpc_request.model_spec.version.value = request.model_version
        
        # Convert inputs to TensorProto
        for key, value in request.inputs.items():
            tensor_proto = tf.make_tensor_proto(value)
            grpc_request.inputs[key].CopyFrom(tensor_proto)
        
        try:
            # Make gRPC call
            response = self.stub.Predict(grpc_request, timeout=self.timeout)
            prediction_time = time.time() - start_time
            
            # Parse response
            outputs = {}
            for key, tensor_proto in response.outputs.items():
                outputs[key] = tf.make_ndarray(tensor_proto)
            
            return ModelPredictionResponse(
                outputs=outputs,
                model_name=request.model_name,
                model_version=response.model_spec.version.value,
                prediction_time=prediction_time
            )
            
        except grpc.RpcError as e:
            error_msg = f"gRPC error: {e.code()} - {e.details()}"
            logger.error(error_msg)
            
            return ModelPredictionResponse(
                outputs={},
                model_name=request.model_name,
                model_version=-1,
                prediction_time=time.time() - start_time,
                status="error",
                error_message=error_msg
            )
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            
            return ModelPredictionResponse(
                outputs={},
                model_name=request.model_name,
                model_version=-1,
                prediction_time=time.time() - start_time,
                status="error",
                error_message=error_msg
            )
    
    def close(self):
        """Close gRPC connection"""
        self.channel.close()


class ETRMModelClient:
    """High-level client for ETRM-specific models"""
    
    def __init__(self, client: Union[TensorFlowServingClient, TensorFlowServingGRPCClient]):
        self.client = client
    
    def predict_risk_score(self, position_data: Dict[str, float]) -> Dict[str, Any]:
        """Predict risk score for a trading position"""
        # Prepare input features
        features = np.array([[
            position_data.get('volume', 0.0),
            position_data.get('price', 0.0),
            position_data.get('volatility', 0.0),
            position_data.get('time_to_maturity', 0.0),
            position_data.get('correlation', 0.0)
        ]], dtype=np.float32)
        
        request = ModelPredictionRequest(
            model_name="etrm_risk_model",
            inputs={"input_features": features}
        )
        
        response = self.client.predict(request)
        
        if response.status == "success":
            risk_score = response.outputs.get("risk_score", np.array([0.0]))[0]
            confidence = response.outputs.get("confidence", np.array([0.0]))[0]
            
            return {
                "risk_score": float(risk_score),
                "confidence": float(confidence),
                "risk_level": self._categorize_risk(risk_score),
                "prediction_time": response.prediction_time
            }
        else:
            return {
                "error": response.error_message,
                "risk_score": None,
                "confidence": 0.0,
                "risk_level": "unknown"
            }
    
    def predict_price(self, market_data: Dict[str, float]) -> Dict[str, Any]:
        """Predict commodity price"""
        features = np.array([[
            market_data.get('current_price', 0.0),
            market_data.get('volume', 0.0),
            market_data.get('open_interest', 0.0),
            market_data.get('volatility', 0.0),
            market_data.get('time_trend', 0.0)
        ]], dtype=np.float32)
        
        request = ModelPredictionRequest(
            model_name="etrm_pricing_model",
            inputs={"market_features": features}
        )
        
        response = self.client.predict(request)
        
        if response.status == "success":
            predicted_price = response.outputs.get("predicted_price", np.array([0.0]))[0]
            price_confidence = response.outputs.get("price_confidence", np.array([0.0]))[0]
            
            return {
                "predicted_price": float(predicted_price),
                "confidence": float(price_confidence),
                "prediction_time": response.prediction_time
            }
        else:
            return {
                "error": response.error_message,
                "predicted_price": None,
                "confidence": 0.0
            }
    
    def check_compliance(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check trade compliance"""
        # Convert trade data to features
        features = np.array([[
            trade_data.get('trade_amount', 0.0),
            trade_data.get('counterparty_risk_score', 0.0),
            trade_data.get('region_code', 0.0),
            trade_data.get('commodity_type', 0.0),
            trade_data.get('regulatory_score', 0.0)
        ]], dtype=np.float32)
        
        request = ModelPredictionRequest(
            model_name="etrm_compliance_model",
            inputs={"trade_features": features}
        )
        
        response = self.client.predict(request)
        
        if response.status == "success":
            compliance_score = response.outputs.get("compliance_score", np.array([0.0]))[0]
            risk_flags = response.outputs.get("risk_flags", np.array([]))[0]
            
            return {
                "compliance_score": float(compliance_score),
                "is_compliant": compliance_score > 0.7,
                "risk_flags": risk_flags.tolist() if len(risk_flags) > 0 else [],
                "prediction_time": response.prediction_time
            }
        else:
            return {
                "error": response.error_message,
                "compliance_score": None,
                "is_compliant": False,
                "risk_flags": []
            }
    
    def generate_report_text(self, context_data: Dict[str, str]) -> Dict[str, Any]:
        """Generate report text using generative model"""
        # For text generation, we would typically use tokenized input
        # This is a simplified example
        prompt_text = context_data.get('prompt', '')
        
        # In practice, you'd tokenize the text input
        # For now, using dummy numerical input
        input_ids = np.array([[1, 2, 3, 4, 5]], dtype=np.int32)  # Dummy tokens
        
        request = ModelPredictionRequest(
            model_name="etrm_generative_model",
            inputs={"input_ids": input_ids}
        )
        
        response = self.client.predict(request)
        
        if response.status == "success":
            # In practice, you'd decode the output tokens back to text
            output_tokens = response.outputs.get("output_tokens", np.array([]))
            
            # Dummy text generation for demo
            generated_text = f"Generated report based on: {prompt_text[:100]}..."
            
            return {
                "generated_text": generated_text,
                "tokens_generated": len(output_tokens),
                "prediction_time": response.prediction_time
            }
        else:
            return {
                "error": response.error_message,
                "generated_text": None
            }
    
    @staticmethod
    def _categorize_risk(risk_score: float) -> str:
        """Categorize risk score"""
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.7:
            return "medium"
        else:
            return "high"


# Example usage and testing
def main():
    """Example usage of TensorFlow Serving client"""
    print("=== TensorFlow Serving Client Demo ===\n")
    
    # Initialize clients
    rest_client = TensorFlowServingClient()
    grpc_client = TensorFlowServingGRPCClient()
    
    # High-level ETRM client
    etrm_client = ETRMModelClient(rest_client)
    
    # Test model listing
    print("1. Available models:")
    models = rest_client.list_models()
    print(json.dumps(models, indent=2))
    
    # Test risk prediction
    print("\n2. Risk prediction:")
    position = {
        'volume': 1000.0,
        'price': 75.50,
        'volatility': 0.25,
        'time_to_maturity': 30.0,
        'correlation': 0.15
    }
    
    risk_result = etrm_client.predict_risk_score(position)
    print(f"Risk prediction: {json.dumps(risk_result, indent=2)}")
    
    # Test price prediction
    print("\n3. Price prediction:")
    market = {
        'current_price': 75.00,
        'volume': 50000,
        'open_interest': 25000,
        'volatility': 0.22,
        'time_trend': 1.5
    }
    
    price_result = etrm_client.predict_price(market)
    print(f"Price prediction: {json.dumps(price_result, indent=2)}")
    
    # Test compliance check
    print("\n4. Compliance check:")
    trade = {
        'trade_amount': 1000000.0,
        'counterparty_risk_score': 0.8,
        'region_code': 1.0,
        'commodity_type': 2.0,
        'regulatory_score': 0.9
    }
    
    compliance_result = etrm_client.check_compliance(trade)
    print(f"Compliance result: {json.dumps(compliance_result, indent=2)}")
    
    # Close gRPC connection
    grpc_client.close()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()