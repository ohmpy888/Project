# app/routes/analyze.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel 
from typing import List, Dict, Any, Optional

# === Import Dependencies & Logic ===
from app.schemas import ChallengeSubmission, AnalyzeOut  # นำเข้า Schema ที่ปรับปรุงแล้ว
from app.services.model import predict_challenge          # Logic การทำนายและ Flagging
from app.services.db import get_challenge_items_for_today, get_item_by_path # Logic DB
from inference.flags_and_suggestions import (
    extract_signals, run_logic_flags, build_suggestions, compare_reasoning
)

router = APIRouter()

# ----------------------------------------------------
# ⚠️ Utility Function 
# ----------------------------------------------------
def band_from_proba(p: float, t: float) -> str:
    """คำนวณ Band ความแตกต่างของคะแนนโมเดลกับค่า Threshold"""
    d = abs(p - t)
    if d >= 0.35: return "high"
    if d >= 0.15: return "medium"
    return "low"

# ----------------------------------------------------
# 🟢 1. Analysis Submission Endpoint
# ----------------------------------------------------
@router.post("/analyze", tags=["analysis"], response_model=AnalyzeOut)
async def analyze_submission(submission: ChallengeSubmission):
    """
    Endpoint สำหรับรับ submission ข้อมูลครบชุด และส่งต่อให้ Model วิเคราะห์ (รวมถึง Logic Flagging และ DB Save)
    """
    
    news_text = submission.news_text # ใช้ชื่อ field จาก Pydantic
    news_date_key = submission.date_key
    
    if not news_text:
        raise HTTPException(status_code=400, detail="Content text is missing from submission.")

    try:
        # 🤖 เรียกใช้ Service Logic ที่รวมการทำนายและ Logic Flags แล้ว
        # NOTE: predict_challenge() ใน app/services/model.py ต้องรับผิดชอบการบันทึกข้อมูลลง Firebase
        analysis_result = predict_challenge(
            text=news_text, 
            user_reasoning=submission.user_reasoning,
            user_label=submission.user_label,
            urls=submission.user_urls, # ใช้ชื่อ field จาก Pydantic
            user_id="anonymous", # ⚠️ ต้องส่ง user_id จริงเข้ามาจาก Frontend/Auth
            news_id=submission.news_id,
        )
        
        # เพิ่ม Metadata กลับเข้าไปในผลลัพธ์ (สำหรับตอบกลับ Frontend)
        # item_id ต้องถูกแยกจาก news_id (เช่น dailyChallenges/2024-01-01/items/news_123)
        analysis_result["item_id"] = submission.news_id.split('/')[-1] if submission.news_id and '/' in submission.news_id else submission.news_id 
        analysis_result["date_key"] = news_date_key
        
        return AnalyzeOut(
            status="success",
            data=analysis_result
        )
    
    except HTTPException as http_e:
        # ส่งต่อ error จาก Service 
        raise http_e
    except Exception as e:
        print(f"UNHANDLED MODEL/LOGIC ERROR: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal Logic Error during analysis: {type(e).__name__}. Check Uvicorn console for detailed traceback."
        )
        
# ----------------------------------------------------
# 🟢 2. Challenges Today Endpoint
# ----------------------------------------------------
@router.get("/challenges/today", response_model=List[Dict[str, Any]], tags=["challenges"])
def get_today_challenges():
    """
    ดึงรายการโจทย์ทั้งหมดสำหรับวันปัจจุบันจาก Firebase 
    """
    try:
        challenges = get_challenge_items_for_today()
        if not challenges:
            raise HTTPException(status_code=404, detail="No daily challenges found for today.")
        
        return challenges 
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching daily challenges: {e}")
        raise HTTPException(status_code=500, detail="Internal error during challenge fetch.")

# ----------------------------------------------------
# 🟢 3. Debug Database Endpoint
# ----------------------------------------------------
@router.get("/debug-db/{path:path}", tags=["debug"])
def debug_db(path: str):
    """
    Endpoint สำหรับดึงข้อมูลดิบจาก Firebase ตามพาธที่ระบุ
    """
    data = get_item_by_path(path)
    
    if data is None:
        raise HTTPException(status_code=404, detail=f"Data not found at path: {path}") 
    
    return data
