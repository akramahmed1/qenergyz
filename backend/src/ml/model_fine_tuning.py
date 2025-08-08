"""
Fine-tuning Script for Generative Models on Synthetic ETRM Data

This script demonstrates how to fine-tune a small generative model (GPT-2 or similar)
on synthetic Energy Trading and Risk Management data.
"""

import os
import json
import pickle
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from synthetic_data_generator import SyntheticETRMDataGenerator, ETRMDataConfig, save_dataset


@dataclass
class ModelConfig:
    """Configuration for model training"""
    vocab_size: int = 10000
    embedding_dim: int = 128
    max_length: int = 512
    batch_size: int = 32
    epochs: int = 10
    learning_rate: float = 0.001
    dropout_rate: float = 0.1
    hidden_dim: int = 256
    num_heads: int = 8
    num_layers: int = 4


class ETRMTokenizer:
    """Simple tokenizer for ETRM text data"""
    
    def __init__(self, vocab_size: int = 10000):
        self.vocab_size = vocab_size
        self.word_to_idx = {'<PAD>': 0, '<UNK>': 1, '<START>': 2, '<END>': 3}
        self.idx_to_word = {0: '<PAD>', 1: '<UNK>', 2: '<START>', 3: '<END>'}
        self.vocab_built = False
    
    def build_vocab(self, texts: List[str]):
        """Build vocabulary from text data"""
        word_freq = {}
        for text in texts:
            words = self._tokenize_text(text)
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and take top vocab_size - 4 (reserved tokens)
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        for i, (word, freq) in enumerate(sorted_words[:self.vocab_size - 4]):
            idx = len(self.word_to_idx)
            self.word_to_idx[word] = idx
            self.idx_to_word[idx] = word
        
        self.vocab_built = True
        print(f"Built vocabulary with {len(self.word_to_idx)} tokens")
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Simple tokenization"""
        import re
        # Convert to lowercase and extract words/numbers
        text = text.lower()
        tokens = re.findall(r'\b\w+\b|\$[\d,]+\.?\d*', text)
        return tokens
    
    def encode(self, text: str, max_length: int = None) -> List[int]:
        """Encode text to token indices"""
        if not self.vocab_built:
            raise ValueError("Vocabulary not built. Call build_vocab first.")
        
        tokens = self._tokenize_text(text)
        indices = [self.word_to_idx.get(token, 1) for token in tokens]  # 1 is <UNK>
        
        if max_length:
            if len(indices) > max_length - 2:  # Account for START and END tokens
                indices = indices[:max_length - 2]
            indices = [2] + indices + [3]  # Add START and END tokens
            
            # Pad to max_length
            while len(indices) < max_length:
                indices.append(0)  # PAD token
        
        return indices
    
    def decode(self, indices: List[int]) -> str:
        """Decode token indices to text"""
        tokens = []
        for idx in indices:
            if idx == 0:  # PAD
                break
            elif idx in [2, 3]:  # START, END
                continue
            else:
                tokens.append(self.idx_to_word.get(idx, '<UNK>'))
        return ' '.join(tokens)
    
    def save(self, filepath: str):
        """Save tokenizer"""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'word_to_idx': self.word_to_idx,
                'idx_to_word': self.idx_to_word,
                'vocab_size': self.vocab_size,
                'vocab_built': self.vocab_built
            }, f)
    
    def load(self, filepath: str):
        """Load tokenizer"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.word_to_idx = data['word_to_idx']
            self.idx_to_word = data['idx_to_word']
            self.vocab_size = data['vocab_size']
            self.vocab_built = data['vocab_built']


class ETRMLanguageModel:
    """Simple Transformer-based language model for ETRM text"""
    
    def __init__(self, config: ModelConfig, tokenizer: ETRMTokenizer):
        self.config = config
        self.tokenizer = tokenizer
        self.model = None
        self.history = None
    
    def build_model(self):
        """Build transformer model"""
        # Input layer
        inputs = keras.layers.Input(shape=(self.config.max_length,))
        
        # Embedding layer
        embeddings = keras.layers.Embedding(
            self.tokenizer.vocab_size, 
            self.config.embedding_dim,
            mask_zero=True
        )(inputs)
        
        # Positional encoding (simple)
        positions = tf.range(start=0, limit=self.config.max_length, delta=1)
        position_embeddings = keras.layers.Embedding(
            self.config.max_length, 
            self.config.embedding_dim
        )(positions)
        
        x = embeddings + position_embeddings
        
        # Transformer blocks
        for _ in range(self.config.num_layers):
            # Multi-head attention
            attention = keras.layers.MultiHeadAttention(
                num_heads=self.config.num_heads,
                key_dim=self.config.embedding_dim // self.config.num_heads,
                dropout=self.config.dropout_rate
            )(x, x)
            
            x = keras.layers.LayerNormalization(epsilon=1e-6)(x + attention)
            
            # Feed forward
            ff = keras.layers.Dense(self.config.hidden_dim, activation='relu')(x)
            ff = keras.layers.Dropout(self.config.dropout_rate)(ff)
            ff = keras.layers.Dense(self.config.embedding_dim)(ff)
            
            x = keras.layers.LayerNormalization(epsilon=1e-6)(x + ff)
        
        # Output layer
        outputs = keras.layers.Dense(self.tokenizer.vocab_size, activation='softmax')(x)
        
        self.model = keras.Model(inputs=inputs, outputs=outputs)
        
        # Compile model
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.config.learning_rate),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        print(f"Model built with {self.model.count_params():,} parameters")
        return self.model
    
    def prepare_training_data(self, texts: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for next-token prediction"""
        print("Preparing training data...")
        
        sequences = []
        for text in texts:
            encoded = self.tokenizer.encode(text, max_length=self.config.max_length)
            sequences.append(encoded)
        
        # Convert to numpy arrays
        X = np.array(sequences)
        
        # Create targets (next token prediction)
        y = np.roll(X, -1, axis=1)  # Shift by 1 position
        y[:, -1] = 0  # Last position gets PAD token
        
        print(f"Training data shape: X={X.shape}, y={y.shape}")
        return X, y
    
    def train(self, texts: List[str], validation_split: float = 0.2):
        """Train the model"""
        if self.model is None:
            self.build_model()
        
        X, y = self.prepare_training_data(texts)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42
        )
        
        # Reshape y for sparse categorical crossentropy
        y_train = y_train[..., np.newaxis]
        y_val = y_val[..., np.newaxis]
        
        # Callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=2),
            keras.callbacks.ModelCheckpoint(
                'best_etrm_model.h5', 
                save_best_only=True, 
                save_weights_only=False
            )
        ]
        
        print("Starting training...")
        self.history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            batch_size=self.config.batch_size,
            epochs=self.config.epochs,
            callbacks=callbacks,
            verbose=1
        )
        
        return self.history
    
    def generate_text(self, prompt: str, max_new_tokens: int = 100, temperature: float = 0.7) -> str:
        """Generate text from a prompt"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Encode prompt
        input_ids = self.tokenizer.encode(prompt, max_length=self.config.max_length)
        input_ids = np.array([input_ids])
        
        generated_tokens = []
        
        for _ in range(max_new_tokens):
            # Predict next token
            predictions = self.model.predict(input_ids, verbose=0)
            next_token_logits = predictions[0, -1, :] / temperature
            
            # Apply softmax and sample
            probabilities = tf.nn.softmax(next_token_logits).numpy()
            next_token = np.random.choice(len(probabilities), p=probabilities)
            
            generated_tokens.append(next_token)
            
            # Add to input for next iteration
            input_ids = np.roll(input_ids, -1, axis=1)
            input_ids[0, -1] = next_token
            
            # Stop if we generate END token
            if next_token == 3:  # END token
                break
        
        # Decode generated tokens
        generated_text = self.tokenizer.decode(generated_tokens)
        return generated_text
    
    def evaluate_model(self, test_texts: List[str]) -> Dict[str, float]:
        """Evaluate model on test data"""
        X_test, y_test = self.prepare_training_data(test_texts)
        
        # Reshape for evaluation
        y_test_reshaped = y_test[..., np.newaxis]
        
        # Evaluate
        loss, accuracy = self.model.evaluate(X_test, y_test_reshaped, verbose=0)
        
        # Calculate perplexity
        perplexity = np.exp(loss)
        
        return {
            'loss': loss,
            'accuracy': accuracy,
            'perplexity': perplexity
        }
    
    def save_model(self, model_dir: str):
        """Save model and tokenizer"""
        os.makedirs(model_dir, exist_ok=True)
        
        # Save model
        if self.model:
            self.model.save(f"{model_dir}/model.h5")
        
        # Save tokenizer
        self.tokenizer.save(f"{model_dir}/tokenizer.pkl")
        
        # Save config
        with open(f"{model_dir}/config.json", 'w') as f:
            json.dump(self.config.__dict__, f, indent=2)
        
        # Save training history
        if self.history:
            with open(f"{model_dir}/history.json", 'w') as f:
                history_dict = {k: [float(x) for x in v] for k, v in self.history.history.items()}
                json.dump(history_dict, f, indent=2)
        
        print(f"Model saved to {model_dir}")
    
    @classmethod
    def load_model(cls, model_dir: str):
        """Load saved model"""
        # Load config
        with open(f"{model_dir}/config.json", 'r') as f:
            config_dict = json.load(f)
        
        config = ModelConfig(**config_dict)
        
        # Load tokenizer
        tokenizer = ETRMTokenizer()
        tokenizer.load(f"{model_dir}/tokenizer.pkl")
        
        # Create model instance
        model = cls(config, tokenizer)
        
        # Load trained model
        if os.path.exists(f"{model_dir}/model.h5"):
            model.model = keras.models.load_model(f"{model_dir}/model.h5")
        
        return model


def main():
    """Main fine-tuning pipeline"""
    print("=== ETRM Generative Model Fine-tuning ===\n")
    
    # 1. Generate synthetic data
    print("1. Generating synthetic ETRM data...")
    config = ETRMDataConfig(
        num_trades=2000,
        num_risk_reports=100,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 6, 30)
    )
    
    generator = SyntheticETRMDataGenerator(config)
    dataset = generator.generate_complete_dataset()
    
    # Save dataset
    save_dataset(dataset, "fine_tuning_data")
    
    # 2. Prepare text data
    print("\n2. Preparing text data...")
    texts = dataset['text_descriptions']
    print(f"Total text samples: {len(texts)}")
    
    # Split data
    train_texts, test_texts = train_test_split(texts, test_size=0.2, random_state=42)
    print(f"Training samples: {len(train_texts)}")
    print(f"Test samples: {len(test_texts)}")
    
    # 3. Build tokenizer
    print("\n3. Building tokenizer...")
    tokenizer = ETRMTokenizer(vocab_size=5000)
    tokenizer.build_vocab(train_texts)
    
    # 4. Create and train model
    print("\n4. Creating model...")
    model_config = ModelConfig(
        vocab_size=tokenizer.vocab_size,
        max_length=256,  # Shorter for demo
        batch_size=16,   # Smaller batch size
        epochs=5,        # Fewer epochs for demo
        hidden_dim=128   # Smaller model for demo
    )
    
    model = ETRMLanguageModel(model_config, tokenizer)
    
    print("\n5. Training model...")
    history = model.train(train_texts, validation_split=0.2)
    
    # 6. Evaluate model
    print("\n6. Evaluating model...")
    eval_results = model.evaluate_model(test_texts)
    print(f"Test Loss: {eval_results['loss']:.4f}")
    print(f"Test Accuracy: {eval_results['accuracy']:.4f}")
    print(f"Perplexity: {eval_results['perplexity']:.2f}")
    
    # 7. Generate sample text
    print("\n7. Generating sample text...")
    sample_prompts = [
        "Trade Analysis:",
        "Position Report:",
        "Risk Alert:",
        "Daily trading summary shows"
    ]
    
    for prompt in sample_prompts:
        generated = model.generate_text(prompt, max_new_tokens=50)
        print(f"\nPrompt: {prompt}")
        print(f"Generated: {generated}")
    
    # 8. Save model
    print("\n8. Saving model...")
    model.save_model("etrm_fine_tuned_model")
    
    print("\n=== Fine-tuning Complete ===")
    print("Model and artifacts saved to 'etrm_fine_tuned_model/'")
    print("Training data saved to 'fine_tuning_data/'")


if __name__ == "__main__":
    # Import here to avoid issues if running as module
    from datetime import datetime
    main()