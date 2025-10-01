# backend/app/services/model.py
import sys
from pathlib import Path # ⬅️ ต้องมี import นี้!
from functools import lru_cache
from typing import Dict, Any 

# Fix ModuleNotFoundError
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent 
sys.path.insert(0, str(PROJECT_ROOT)) 

from inference.predictor import Predictor
from core.config import settings

@lru_cache(maxsize=1)
def get_predictor() -> Predictor:
    """Returns a cached instance of the ML Predictor."""
    # โหลดครั้งแรก แล้วแคชไว้ (process-level singleton)
    return Predictor(
        ckpt_path=settings.MODEL_PATH,
        threshold_path=settings.THRESH_PATH
    )
