# backend/core/config.py
import os
from typing import List
from pathlib import Path

# Path Calculation (Backend/ เป็น Project Root)
# config.py อยู่ที่ Backend/core/config.py
BACKEND_ROOT = Path(__file__).resolve().parent.parent 
CKPT_DIR = BACKEND_ROOT / "ckpt"

class Settings:
    # ------------------------------------
    # ⚠️ 1. FIREBASE SETTINGS (ต้องแทนที่ URL และชื่อไฟล์คีย์)
    # ------------------------------------
    FIREBASE_CREDENTIALS: str = os.getenv(
        "FIREBASE_CREDENTIALS", 
        str(BACKEND_ROOT / "app" / "pattern-3d1a8-firebase-adminsdk-fbsvc-2eb3bbf92d.json")
    )
    FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL", "https://pattern-3d1a8-default-rtdb.asia-southeast1.firebasedatabase.app/") 
    
    # ------------------------------------
    # 2. MODEL PATHS
    # ------------------------------------
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(CKPT_DIR / "best_model.pt"))
    THRESH_PATH: str = os.getenv("THRESHOLD_PATH", str(CKPT_DIR / "threshold.json"))
    
    # ------------------------------------
    # 3. MODEL HYPERPARAMETERS (ค่าที่จำเป็นต้องใช้ในการสร้างโมเดล)
    # ------------------------------------
    LOWERCASE      = True
    MAX_LEN        = 256
    PAD_IDX        = 0

    EMB_DIM        = 200
    CNN_CHANNELS   = 128
    KERNEL_SIZES   = [3, 4, 5]
    LSTM_HIDDEN    = 128
    LSTM_LAYERS    = 1
    BIDIR          = True
    DROPOUT        = 0.3
    NUM_CLASSES    = 2

    # ------------------------------------
    # 4. FASTAPI / CORS Settings
    # ------------------------------------
    PROJECT_NAME: str = "Real-Fake News Detector API"
    VERSION: str = "1.0.0"
    ALLOW_ORIGINS: List[str] = [
        os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
    ]
    
settings = Settings()