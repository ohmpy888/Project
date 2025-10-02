# backend/services/firebase_service.py
# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional
from firebase_admin import db
from firebase_admin.db import Reference
from core.config import Settings
import datetime
import time

class FirebaseService:
    """
    Custom Service Class สำหรับจัดการการสื่อสารกับ Firebase Realtime Database (RTDB).
    อาศัย Firebase Admin SDK ที่ถูก Initialize ไว้แล้วใน services/db.py
    """

    def __init__(self, settings: Settings):
        """
        Constructor รับ settings และตั้งค่า database reference.
        """
        # settings ถูกส่งมาจาก get_firebase_service()
        self.settings = settings
        # Reference ไปยัง root ของ RTDB
        self.root_ref: Reference = db.reference()

    def get_data(self, path: str) -> Optional[Dict[str, Any]]:
        """
        ดึงข้อมูลจาก path ที่ระบุใน RTDB
        
        Args:
            path: Path ภายในฐานข้อมูล (เช่น "dailyChallenges/2024-05-15/items")
            
        Returns:
            ข้อมูลในรูปแบบ Dict หรือ None หากไม่พบ
        """
        try:
            data = self.root_ref.child(path).get()
            return data
        except Exception as e:
            print(f"Firebase read error at path '{path}': {e}")
            return None

    def set_data(self, path: str, data: Dict[str, Any]) -> bool:
        """
        บันทึกหรืออัปเดตข้อมูลที่ path ที่ระบุใน RTDB
        
        Args:
            path: Path ภายในฐานข้อมูล (เช่น "submissions/{user_id}/{timestamp}")
            data: ข้อมูลที่จะบันทึก (ต้องเป็น Dict ที่ serialize ได้)
            
        Returns:
            True หากสำเร็จ, False หากเกิดข้อผิดพลาด
        """
        try:
            self.root_ref.child(path).set(data)
            return True
        except Exception as e:
            print(f"Firebase write error at path '{path}': {e}")
            return False

    def get_server_timestamp(self) -> int:
        """
        คืนค่า Unix Timestamp ปัจจุบันในหน่วยมิลลิวินาที (ms)
        โดยจำลองการใช้ Server Timestamp หาก Firebase Admin SDK ไม่มีฟังก์ชันนี้โดยตรง
        NOTE: ในการใช้งานจริง, ควรใช้ db.ServerValue.TIMESTAMP ในการ set_data เพื่อให้ได้เวลาที่แม่นยำจากเซิร์ฟเวอร์
        แต่ในบริบทนี้ เราจะใช้เวลาปัจจุบันของ API Server แทน 
        """
        # ใช้เวลาปัจจุบันของ Python Server (ms)
        return int(time.time() * 1000)

    # NOTE: อาจเพิ่ม method อื่นๆ เช่น update_data, delete_data ในอนาคต
