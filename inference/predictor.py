# inference/predictor.py
# -*- coding: utf-8 -*-
import os, json, math
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import torch
import torch.nn.functional as F

# ⚠️ Import settings และ Model Config
from core.config import settings 
from .model_def import CNN_BiLSTM_Attn
from .tokenizer import simple_tokenize

POS_LABEL = 1  # 1=จริง, 0=ปลอม

class Predictor:
    # ⚠️ ไม่จำเป็นต้องรับค่า default มาจาก param เพราะเราใช้ settings แล้ว
    def __init__(self, ckpt_path: str, threshold_path: str, device=None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        
        # 1. โหลด Checkpoint และ Stoi
        ckpt = torch.load(ckpt_path, map_location=self.device)
        self.stoi = ckpt.get("stoi")
        if self.stoi is None:
            raise RuntimeError(f"Checkpoint must include 'stoi' dict. Path: {ckpt_path}")

        cfg = ckpt.get("config", {})
        self.MAX_LEN = int(cfg.get("MAX_LEN", settings.MAX_LEN)) # ใช้ settings เป็น fallback
        vocab_size = len(self.stoi)
        
        # 2. สร้าง Model Instance โดยใช้ Config จาก Checkpoint หรือ Settings
        model = CNN_BiLSTM_Attn(
            vocab_size=vocab_size,
            emb_dim=int(cfg.get("EMB_DIM", settings.EMB_DIM)),
            cnn_channels=int(cfg.get("CNN_CHANNELS", settings.CNN_CHANNELS)),
            kernel_sizes=list(cfg.get("KERNEL_SIZES", settings.KERNEL_SIZES)),
            lstm_hidden=int(cfg.get("LSTM_HIDDEN", settings.LSTM_HIDDEN)),
            # ใช้ค่าจาก settings เป็น fallback สำหรับ Layers, Bidirectional, Dropout
            lstm_layers=int(cfg.get("LSTM_LAYERS", settings.LSTM_LAYERS)), 
            bidir=bool(cfg.get("BIDIR", settings.BIDIR)),
            dropout=float(cfg.get("DROPOUT", settings.DROPOUT)),
            num_classes=settings.NUM_CLASSES
        ).to(self.device)
        
        # 3. โหลด Weights
        state = ckpt["model_state"]
        model.load_state_dict(state)
        model.eval()
        self.model = model

        self.pad_idx = self.stoi.get("<pad>", settings.PAD_IDX)
        self.unk_idx = self.stoi.get("<unk>", 1)

        # 4. โหลด Threshold
        self.threshold = settings.DEFAULT_THRESHOLD # ใช้ค่า default จาก settings
        if threshold_path and Path(threshold_path).exists():
            try:
                # ⚠️ ต้องอ่านไฟล์ JSON ให้ถูกคีย์ (สมมติว่าคีย์คือ "t")
                data = json.load(open(threshold_path, "r"))
                if "t" in data and isinstance(data["t"], (float, int)):
                     self.threshold = float(data["t"])
            except Exception as e:
                print(f"Warning: Failed to load threshold from JSON. Using default {self.threshold}. Error: {e}")

        self.kernel_max = max(settings.KERNEL_SIZES) # ใช้ค่าจาก settings
    
    # ... (ส่วนอื่น ๆ เหมือนเดิม) ...
    # _encode, _pad, predict methods อยู่เหมือนเดิม
    # ⚠️ ตรวจสอบว่า `simple_tokenize` ใน `predict` ถูก Import จาก `.tokenizer` แล้ว