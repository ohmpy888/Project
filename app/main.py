import os
import sys
from pathlib import Path

# ตั้งค่า PYTHONPATH เพื่อให้สามารถ import modules ภายในได้
# PROJECT_ROOT ควรชี้ไปที่โฟลเดอร์หลักของ Backend (e.g., app/../)
PROJECT_ROOT = Path(__file__).resolve().parent.parent 
sys.path.insert(0, str(PROJECT_ROOT))

# ----------------------------------------------------
# 1. IMPORTS & CONFIGURATION
# ----------------------------------------------------
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import torch.nn as nn

# Internal imports
from core.config import settings
from app.routes import analyze as analyze_router # Router สำหรับ /analyze
from app.routes import daily as daily_challenges # Router สำหรับ /challenges/today

# ----------------------------------------------------
# 2. MODEL & PREDICTOR INITIALIZATION (Singleton)
# ----------------------------------------------------
try:
    # ⚠️ ตรวจสอบว่า Predictor ถูก import ถูกต้องตามโครงสร้างของคุณ (e.g., inference.predictor)
    from inference.predictor import Predictor 
    
    # Global instance สำหรับการโหลดโมเดลเพียงครั้งเดียว
    predictor: Predictor = None
    
    def get_predictor() -> Predictor:
        """Dependency function to get the initialized Predictor instance."""
        global predictor
        if predictor is None:
            predictor = Predictor(
                model_path=settings.MODEL_PATH,
                vocab_path=settings.VOCAB_PATH,
                thresh_path=settings.THRESH_PATH,
                config=settings,
                device=settings.DEVICE 
            )
            print(f"✅ Predictor initialized using model: {settings.MODEL_PATH.split('/')[-1]}")
        return predictor

except Exception as e:
    # หากโหลดโมเดลล้มเหลว (เช่น ไฟล์ .pt หรือ vocab.json หาย)
    print(f"🛑 CRITICAL ERROR: Could not initialize Predictor! Check model files and dependencies.")
    print(f"Error Detail: {e}")
    predictor = None

# ----------------------------------------------------
# 3. FASTAPI APP SETUP
# ----------------------------------------------------

app = FastAPI(
    title="Daily Challenge Fact-Checker API",
    description="API สำหรับระบบ Daily Challenge และการวิเคราะห์ข่าว",
    version="1.0.0",
)

# ----------------------------------------------------
# 4. MIDDLEWARE (CORS FIX)
# ----------------------------------------------------
# นี่คือส่วนที่สำคัญที่สุดในการแก้ไขปัญหา "Failed to fetch"
app.add_middleware(
    CORSMiddleware,
    # ⚠️ กำหนด Origin ของ React Frontend (Port 5173) และ Backend (Port 8000)
    # เพื่อป้องกันปัญหา CORS
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# 5. EXCEPTION HANDLERS
# ----------------------------------------------------

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """จับ Exception ทั่วไป เพื่อให้แน่ใจว่าได้ JSON response แทน HTML 500"""
    import traceback
    print(f"\n--- Internal Server Error (500) ---")
    print(f"Request Path: {request.url.path}")
    print(f"Error Message: {exc}")
    traceback.print_exc(limit=5)
    print(f"-----------------------------------\n")

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error_message": str(exc)},
    )


# ----------------------------------------------------
# 6. ROUTE REGISTRATION
# ----------------------------------------------------

@app.get("/")
def read_root():
    """Endpoint ต้อนรับสำหรับตรวจสอบสถานะของ API"""
    return {"message": "Daily Challenge API is running successfully!"}

@app.get("/health")
async def health_check():
    """Endpoint สำหรับตรวจสอบสถานะและสถานะโมเดล"""
    status = "running"
    model_loaded = predictor is not None
    return {"status": status, "model_loaded": model_loaded, "model_path": settings.MODEL_PATH}

# รวม Router เข้ากับ App ทั้งหมด
app.include_router(analyze_router.router, prefix="/api/v1")
app.include_router(daily_challenges.router, prefix="/api/v1")
