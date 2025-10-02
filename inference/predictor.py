import os, json
from typing import List, Dict, Any, Optional, Tuple
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from scipy.interpolate import interp1d
import re
from functools import lru_cache

# Fix module import paths
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent 
sys.path.insert(0, str(PROJECT_ROOT)) 

from core.config import settings 
# 🟢 Import CNN_BiLSTM_Attn จาก model_def.py
from inference.model_def import CNN_BiLSTM_Attn 
# 🟢 Import simple_tokenize จาก tokenizer.py
from inference.tokenizer import simple_tokenize 

# Global constants
POS_LABEL = 1 
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
PAD_IDX = settings.PAD_IDX

# --------------------------------------------------------------------
# Predictor Class 
# --------------------------------------------------------------------

class Predictor:
    """
    Class สำหรับโหลดโมเดล, vocab, threshold และทำนายผล 
    """
    
    def __init__(self, model_path: str, vocab_path: str, threshold_path: str):
        # 1. Load Vocab (Logic from previous successful fix)
        print(f"Loading vocab from: {vocab_path}")
        with open(vocab_path, 'r', encoding='utf-8') as f:
            loaded_vocab = json.load(f)

        vocab_list = None
        
        if isinstance(loaded_vocab, list):
            vocab_list = loaded_vocab
            print("INFO: Vocab loaded as List. Using positional index.")
        elif isinstance(loaded_vocab, dict):
            if 'itos' in loaded_vocab and isinstance(loaded_vocab['itos'], list):
                vocab_list = loaded_vocab['itos']
                print(f"INFO: Vocab loaded as Dict containing 'itos' list with {len(vocab_list)} tokens.")
            elif all(isinstance(v, int) for v in loaded_vocab.values()):
                self.vocab = loaded_vocab
                self.idx_to_token = {idx: token for token, idx in self.vocab.items()}
                print(f"INFO: Vocab loaded as direct token:index map with {len(self.vocab)} tokens.")
                vocab_list = None 
            else:
                 raise ValueError("Vocabulary dictionary is not in the expected format (missing 'itos' key or values are not integers).")
        else:
            raise ValueError(f"Vocabulary file format is neither a list nor a dictionary: {type(loaded_vocab)}")

        if vocab_list is not None:
            self.vocab = {token: i for i, token in enumerate(vocab_list)}
            self.idx_to_token = {i: token for i, token in enumerate(vocab_list)}

        if not hasattr(self, 'vocab') or not self.vocab:
            raise RuntimeError("Failed to finalize vocabulary maps. Vocab is empty or incorrectly formatted.")
        
        # 2. Load Threshold
        try:
            print(f"Loading threshold from: {threshold_path}")
            with open(threshold_path, 'r', encoding='utf-8') as f:
                thresh_data = json.load(f)
            self.threshold = float(thresh_data.get("optimal_threshold", settings.DEFAULT_THRESHOLD))
        except Exception as e:
            print(f"Warning: Could not load threshold ({e}). Using default: {settings.DEFAULT_THRESHOLD}")
            self.threshold = settings.DEFAULT_THRESHOLD

        # 3. Initialize Model Structure
        self.model = CNN_BiLSTM_Attn(
            vocab_size=len(self.vocab), 
            emb_dim=settings.EMB_DIM, 
            cnn_channels=settings.CNN_CHANNELS, 
            kernel_sizes=settings.KERNEL_SIZES, 
            lstm_hidden=settings.LSTM_HIDDEN, 
            lstm_layers=settings.LSTM_LAYERS, 
            bidir=settings.BIDIR, 
            dropout=settings.DROPOUT
        )
        
        # 4. Load Model Weights
        print(f"Loading model weights from: {model_path}")
        
        # 🟢 FIX: โหลด Checkpoint และดึงเฉพาะ State Dict ที่ต้องการ
        checkpoint = torch.load(model_path, map_location=DEVICE)
        
        if isinstance(checkpoint, dict) and 'model_state' in checkpoint:
            # ถ้า Checkpoint เป็น Dictionary และมีคีย์ 'model_state' ให้ใช้ค่านั้น
            print("INFO: Extracting 'model_state' from Checkpoint dict.")
            state_dict = checkpoint['model_state']
        elif isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            # บางครั้งอาจใช้ 'state_dict' (เผื่อไว้)
            print("INFO: Extracting 'state_dict' from Checkpoint dict.")
            state_dict = checkpoint['state_dict']
        else:
            # ถ้า Checkpoint เป็น State Dict โดยตรง หรืออยู่ในรูปแบบอื่นที่ไม่รู้จัก
            print("INFO: Assuming Checkpoint is a raw State Dict.")
            state_dict = checkpoint
            
        self.model.load_state_dict(state_dict)
        self.model.to(DEVICE).eval()
        
        self.max_len = settings.MAX_LEN
        self.pad_idx = settings.PAD_IDX

    # ------------------------------------------------
    # Private Helpers (No change in logic here)
    # ------------------------------------------------
    
    def _encode_and_pad(self, text: str) -> Tuple[torch.Tensor, List[str]]:
        """ Tokenize, map to indices, and pad/truncate. """
        tokens = simple_tokenize(text) 
        unk_idx = self.vocab.get(settings.UNK_TOKEN, 1) 
        indices = [self.vocab.get(token, unk_idx) for token in tokens] 
        
        if len(indices) < self.max_len:
            padding = [self.pad_idx] * (self.max_len - len(indices))
            padded_indices = indices + padding
        else:
            padded_indices = indices[:self.max_len]
            tokens = tokens[:self.max_len]
            
        tensor = torch.LongTensor(padded_indices).unsqueeze(0).to(DEVICE)
        return tensor, tokens 

    def _extract_clues(self, alpha: torch.Tensor, actual_tokens: List[str], min_t: int) -> List[Dict[str, Any]]:
        """ Extracts top attention weights as clues. """
        alpha_np = alpha.squeeze(0).cpu().numpy()[:min_t]
        x_short = np.linspace(0, 1, len(alpha_np))
        f = interp1d(x_short, alpha_np, kind='linear', fill_value="extrapolate")
        x_long = np.linspace(0, 1, len(actual_tokens))
        stretched_alpha = f(x_long)
        sorted_indices = np.argsort(stretched_alpha)[::-1]
        
        clues_list = []
        seen_tokens = set()
        for i in range(len(actual_tokens)):
            idx = sorted_indices[i]
            token = actual_tokens[idx]
            weight = float(stretched_alpha[idx])
            
            if len(clues_list) >= 10: break
                
            if weight > 0.01 and len(token) > 1 and token not in seen_tokens:
                 clues_list.append({"span_tokens": [token], "weight": weight})
                 seen_tokens.add(token)
        return clues_list

    # ------------------------------------------------
    # Main Public Method 
    # ------------------------------------------------

    def predict(self, text: str) -> Dict[str, Any]:
        """ Main prediction function. Return prediction, score, clues. """
        if not text:
            return {"prediction": 0, "score": 0.0, "clues": []}

        input_tensor, actual_tokens = self._encode_and_pad(text)
        
        with torch.no_grad():
            logits, alpha, min_t = self.model(input_tensor)
        
        probs = F.softmax(logits, dim=1)
        score = probs[0, POS_LABEL].item() 
        prediction = 1 if score >= self.threshold else 0
        
        clues = self._extract_clues(alpha, actual_tokens, min_t)
        
        return {"prediction": prediction, "score": score, "clues": clues}


# --------------------------------------------------------------------
# Predictor Initialization (Singleton)
# --------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_predictor() -> Predictor:
    """ Returns a cached instance of the ML Predictor (Singleton). """
    print("INFO: Initializing ML Predictor...")
    try:
        predictor_instance = Predictor(
            model_path=settings.MODEL_PATH, 
            vocab_path=settings.VOCAB_PATH, 
            threshold_path=settings.THRESH_PATH
        )
        print("INFO: ML Predictor initialized successfully.")
        return predictor_instance
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize Predictor: {e}")
        # ⚠️ เปลี่ยนการ Raise เป็น RuntimeError เพื่อให้ Model Service ดักจับได้
        raise RuntimeError(f"Model initialization failed: {e}. Check model files and configuration.")
