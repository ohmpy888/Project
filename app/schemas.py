# app/schemas.py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Any, Dict


class ChallengeSubmission(BaseModel):
    """
    Schema สำหรับรับข้อมูลครบชุดจาก Frontend (News Data + User Input)
    """
    news_text: str                       # เนื้อหาข่าว (Required)
    news_id: Optional[str] = None        # ID ข่าว (e.g., dailyChallenges/{dateKey}/items/{itemId})
    user_label: Optional[int] = -1       # คำตอบของผู้ใช้ (-1, 0=fake, 1=real)
    user_reasoning: Optional[str] = ""   # เหตุผลของผู้ใช้
    date_key: Optional[str] = None       # วันที่/Key สำหรับอ้างอิง (YYY-MM-DD)
    user_urls: Optional[List[str]] = []  # ลิงก์ที่ผู้ใช้อ้างอิง

    
class Challenge(BaseModel):
    id: str
    title: str
    content: str
    source: str
    domain: str
    publishDate: str
    difficulty: Literal["easy", "medium", "hard"]

class AnalyzeOut(BaseModel):
    """
    Schema สำหรับตอบกลับหลังจากวิเคราะห์เสร็จ (Strong Schema)
    """
    # === Metadata (ข้อมูลที่ส่งกลับไปเพื่อให้ Frontend อ้างอิง) ===
    news_id: Optional[str] = None
    news_text: Optional[str] = None
    user_label: Optional[int] = -1
    user_reasoning: Optional[str] = ""

    # === Model Prediction Results ===
    predicted_label: int
    probability: float
    model_clues: List[Dict[str, Any]]
    model_version: str

    # === Logic & Comparison Results ===
    evidence_match: Literal["low","partial","good"]
    overlap_ratio: float
    logic_flags: List[Dict[str, str]]
    suggestions: List[Dict[str, Any]]

class ClueWordAnalysis(BaseModel):
    """Schema สำหรับ Clue Word แต่ละคำ และการวิเคราะห์"""
    word: str = Field(..., description="คำสำคัญที่พบในเนื้อหาข่าว (จาก Attention Mechanism)")
    analysis: str = Field(..., description="คำอธิบายความสำคัญของคำนี้ในการตัดสินใจ (Rule-Based)")
    found_in_reason: bool = Field(False, description="True หากคำนี้ถูกกล่าวถึงในเหตุผลของผู้ใช้ (Substring Check)")

class SubmissionIn(BaseModel):
    """Schema สำหรับข้อมูลที่ผู้ใช้ส่งเข้ามา"""
    # ✅ เพิ่ม userId เข้ามาใน Schema
    userId: str = Field(..., description="ID ของผู้ใช้ที่ส่งคำตอบ")
    itemRef: str = Field(..., description="ID หรือ Ref ของ Challenge Item")
    userLabel: bool = Field(..., description="คำตอบของผู้ใช้ (True/False)")
    userReason: str = Field("", description="เหตุผลที่ผู้ใช้ป้อน")
    
class ChallengeFeedback(BaseModel):
    """Schema Feedback การส่งคำตอบสุดท้าย"""
    score: int = Field(..., description="คะแนน reasoning (จาก Confidence Score ของโมเดล)")
    correct: bool = Field(..., description="True ถ้าคำตอบของผู้ใช้ตรงกับโมเดล")
    explanation: str = Field(..., description="คำอธิบายที่ถูกต้อง/สรุปผลการวิเคราะห์")
    clue_words_analysis: List[ClueWordAnalysis] = Field([], description="รายการคำสำคัญและการวิเคราะห์เทียบกับเหตุผลผู้ใช้")
    suggestions: List[Dict[str, Any]] = Field([], description="คำแนะนำเพิ่มเติมจาก Logic Flags")