# app/routes/analyze.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel 
from typing import List, Dict, Any, Optional
from datetime import date, datetime

# === Import Dependencies & Logic ===
from app.schemas import ChallengeSubmission, AnalyzeOut, ChallengeFeedback, SubmissionIn  # นำเข้า Schema ที่ปรับปรุงแล้ว
from app.services.model import predict_challenge          # Logic การทำนายและ Flagging
from app.services.db import get_challenge_items_for_today, get_item_by_path, get_firebase_service, get_challenge_item_by_ref, save_submission
from app.services.firebase_service import FirebaseService
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
@router.post(
    "/analyze",
    response_model=ChallengeFeedback,
    tags=["challenges"],
    summary="Analyze a user's submission for a daily challenge"
)
def analyze_submission(
    submission: SubmissionIn,
    firebase_service: FirebaseService = Depends(get_firebase_service)
):
    """
    รับคำตอบจากผู้ใช้, วิเคราะห์ด้วยโมเดล, บันทึกผล, และส่ง Feedback กลับไป
    """
    print("\n--- ANALYZING SUBMISSION ---")
    print(f"Received submission data: {submission.dict()}")
    
    try:
        # 1. ดึงข้อมูลข่าวจาก DB
        item_data = get_challenge_item_by_ref(firebase_service, submission.itemRef)
        if not item_data:
            raise HTTPException(status_code=404, detail=f"Item with ref '{submission.itemRef}' not found.")

        news_text = item_data.get('text')
        if news_text is None:
            raise HTTPException(status_code=500, detail=f"Item '{submission.itemRef}' is missing 'text' data.")

        # 2. วิเคราะห์ด้วยโมเดล เพื่อเอาคำตอบของ AI และ Clue ที่ประมวลผลแล้ว
        analysis_data = predict_challenge(
            text=news_text,
            user_label=submission.userLabel,
            user_reasoning=submission.userReason,
            urls=[] 
        )

        # 3. ใช้ผลลัพธ์จากโมเดลเป็น "Source of Truth"
        model_prediction_bool = bool(analysis_data.get("predicted_label", 0))
        clues_from_model = analysis_data.get("clue_words_analysis", [])

        # 3.1 คำนวณความถูกต้อง (correct) โดยเทียบคำตอบผู้ใช้กับ "คำตอบของโมเดล"
        is_correct = (submission.userLabel == model_prediction_bool)

        # ✅ --- START: LOGIC การคำนวณคะแนนใหม่ ---
        final_score = 0
        
        # 1. ให้คะแนนพื้นฐาน 25 คะแนน ถ้าทาย Label ถูก
        if is_correct:
            final_score = 25
        
        # 2. คำนวณคะแนน Reasoning จาก 75 คะแนนที่เหลือ
        if clues_from_model:
            reasoning_points_pool = 75
            score_per_clue = reasoning_points_pool / len(clues_from_model)
            
            for clue in clues_from_model:
                if clue.get("found_in_reason", False):
                    if is_correct:
                        # ถ้า Label ถูก และ Clue ถูก -> ได้คะแนนเต็มส่วน
                        final_score += score_per_clue
                    else:
                        # ถ้า Label ผิด แต่ Clue ถูก -> ยังคงได้คะแนน 1/3 ของส่วนนั้น
                        final_score += (score_per_clue / 3)

        # 3. ตรวจสอบว่าคะแนนไม่เกิน 100 และปัดเป็นจำนวนเต็ม
        final_score = min(100, int(final_score))

        # ✅ --- END: LOGIC การคำนวณคะแนนใหม่ ---

        # 3.2 สร้างคำอธิบาย (explanation)
        if is_correct:
            explanation_text = f"คุณวิเคราะห์ได้ตรงกับ AI! โมเดลเห็นว่านี่คือ '{'ข่าวจริง' if model_prediction_bool else 'ข่าวปลอม'}'"
        else:
            explanation_text = f"มุมมองของคุณต่างจาก AI เล็กน้อย โมเดลวิเคราะห์ว่าเป็น '{'ข่าวจริง' if model_prediction_bool else 'ข่าวปลอม'}'"
        
        # 3.3 จัดรูปแบบ suggestions ให้ถูกต้อง
        suggestions_list = analysis_data.get("suggestions", [])
        formatted_suggestions = [{"text": s} for s in suggestions_list if isinstance(s, str)]

        # 3.4 รวบรวม Feedback ทั้งหมด
        final_feedback = {
            "score": final_score,
            "correct": is_correct,
            "explanation": explanation_text,
            "clue_words_analysis": clues_from_model,
            "suggestions": formatted_suggestions
        }

        # 4. เตรียมข้อมูลและบันทึกลง Firebase
        today_date_key = date.today().strftime('%Y-%m-%d')
        db_submission_data = {
            "createdAt": int(datetime.utcnow().timestamp() * 1000),
            "itemRef": f"items/{submission.itemRef}",
            "userLabel": submission.userLabel,
            "userReason": submission.userReason,
            "score": final_score 
        }
        save_submission(
            firebase_service=firebase_service,
            user_id=submission.userId,
            date_key=today_date_key,
            submission_data=db_submission_data
        )

        print("--- ANALYSIS COMPLETE ---")
        # 5. สร้าง Response กลับไปให้ Frontend
        return ChallengeFeedback(**final_feedback)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during analysis: {e}"
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
