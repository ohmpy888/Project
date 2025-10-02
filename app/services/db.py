# app/services/db.py

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import date
import firebase_admin
# ⚠️ ลบ 'exceptions' ออก และใช้แค่ credentials, db
from firebase_admin import credentials, db 
from app.services.firebase_service import FirebaseService

# Fix ModuleNotFoundError for 'core'
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent 
sys.path.insert(0, str(PROJECT_ROOT)) 

from core.config import settings

firebase_service_instance: Optional[FirebaseService] = None

def get_firebase_service() -> FirebaseService:
    """
    Dependency สำหรับเชื่อมต่อ Firebase (โหลดครั้งเดียว/Singleton)
    ใช้เรียกใน FastAPI routes
    """
    global firebase_service_instance
    if firebase_service_instance is None:
        try:
            # ใช้อ้างอิงชื่อคลาสจริงจาก services.firebase_service 
            from app.services.firebase_service import FirebaseService as RealFirebaseService 
            firebase_service_instance = RealFirebaseService(settings)
        except Exception as e:
            # ควรจัดการ Error ที่นี่หาก Firebase Service เริ่มต้นไม่ได้
            print(f"ERROR: Failed to initialize Firebase Service: {e}")
            # ยกเว้น RuntimeError เพื่อให้ FastAPI จัดการ
            raise RuntimeError(f"Failed to initialize Firebase: {e}") 
    return firebase_service_instance

def initialize_firebase():
    """Initializes Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        try:
            # 1. ตรวจสอบ Path ของ Credentials
            if not Path(settings.FIREBASE_CREDENTIALS).exists():
                 print(f"ERROR: Firebase credentials file not found at {settings.FIREBASE_CREDENTIALS}")
                 return
                 
            # 2. Initialize
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred, {
                'databaseURL': settings.FIREBASE_DATABASE_URL
            })
            print("Firebase Admin SDK Initialized Successfully.")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")

# เรียก initialize เมื่อ Module โหลด
initialize_firebase()

def get_item_by_path(full_path: str) -> Dict[str, Any] | None:
    """Fetches a specific data object by its full path."""
    if not firebase_admin._apps: return None
    try:
        # 🟢 Clean Fetch Logic: ถ้าไม่มีข้อมูล จะได้ None อัตโนมัติ
        # 🟢 ไม่มี TOMBSTONE หรือ Exception ภายใน
        data = db.reference(full_path).get()
        
        if data is None:
            return None
            
        return data
        
    except Exception as e:
        # 🚨 Log Error ที่เหลืออยู่ (เช่น Network หรือ Key Errors อื่นๆ)
        print(f"🚨 FIREBASE FETCH ERROR (General): Could not fetch at {full_path}. Error: {e}")
        return None

def get_challenge_items_for_today() -> List[Dict[str, Any]] | None:
    """
    1. ดึง ID ของโจทย์ประจำวันจาก /dailyChallenges/{YYYY-MM-DD}/items
    2. ใช้ ID เหล่านี้ไปดึงรายละเอียดข่าวเต็มจาก /items/{id}
    """
    # ⚠️ ใช้ Hardcode Date ชั่วคราวเพื่อให้ Debug ง่ายขึ้น
    # เมื่อมั่นใจแล้ว ค่อยเปลี่ยนเป็น date.today().strftime('%Y-%m-%d')
    today_date_key = date.today().strftime('%Y-%m-%d') 
    
    challenge_path = f'dailyChallenges/{today_date_key}/items'
    
    print(f"DEBUG: Today's date key is: {today_date_key}")
    print(f"DEBUG: Trying to fetch challenge list from path: {challenge_path}")
    
    # 1. ดึงรายการ ID ของโจทย์ประจำวัน
    challenge_items_map = get_item_by_path(challenge_path) 
    
    if not challenge_items_map:
        print(f"DEBUG: Fetch failed or returned None/empty for path: {challenge_path}")
        return []
    
    if not isinstance(challenge_items_map, dict):
        print(f"DEBUG: Challenge data at {challenge_path} is not a dictionary. Data type: {type(challenge_items_map)}")
        return []


    print(f"DEBUG: Successfully fetched {len(challenge_items_map)} potential keys from daily challenges.")

    results = []
    
    # 2. Loop ผ่าน ID ที่ได้มาและ Join กับตาราง items
    for item_id, challenge_data in challenge_items_map.items():
        if item_id in ['count', 'createdAt', 'dateKey']: continue # ข้าม metadata
        
        # 🟢 ใช้ item_id เพื่อดึงข้อมูลข่าว
        item_detail_path = f'items/{item_id}'
        item_data = get_item_by_path(item_detail_path)
        
        if item_data:
            item_data['item_id'] = item_id
            item_data['date_key'] = today_date_key
            
            # จัดการ key 'content' -> 'text' 
            if 'text' not in item_data and 'content' in item_data:
                 item_data['text'] = item_data.pop('content') 
            
            # รวมข้อมูลจาก dailyChallenges เข้าไป
            if isinstance(challenge_data, dict):
                 item_data.update(challenge_data)
                 
            results.append(item_data)
        else:
            print(f"Warning: Item detail not found for {item_id} at {item_detail_path}")

    # จัดเรียงตาม 'order'
    if all('order' in item for item in results):
        results.sort(key=lambda x: x.get('order', float('inf')))

    return results

def get_challenge_item_by_ref(
    firebase_service: FirebaseService,
    item_ref: str
) -> Optional[Dict[str, Any]]:
    """
    ดึงข้อมูล Challenge Item จาก Firebase โดยใช้ itemRef ที่มาจาก Frontend
    
    Args:
        firebase_service: อินสแตนซ์ FirebaseService
        item_ref: ID อ้างอิงของ Challenge Item (e.g., 'news_123' หรือ 'items/news_123')
        
    Returns:
        ข้อมูล Dict ของ Challenge Item พร้อม True Label และ Content
    """
    if item_ref.startswith('items/'):
        item_id = item_ref.split('/')[-1]
    else:
        item_id = item_ref
        
    item_detail_path = f'items/{item_id}'
    
    # ⚠️ ใช้ instance ที่ได้รับมาในการเรียก get_data
    item_data = firebase_service.get_data(item_detail_path)
    
    if item_data:
        # จัดการ Key Name (ถ้า 'text' ไม่มี แต่มี 'content' ให้เปลี่ยน)
        if 'text' not in item_data and 'content' in item_data:
            item_data['text'] = item_data['content'] # เก็บ content ไว้ที่ text
            
        # ตรวจสอบ true_label (จำเป็นสำหรับคำนวณ 'correct' ใน model.py)
        if 'true_label' not in item_data:
            print(f"Warning: Missing 'true_label' for item {item_id}. Assuming 0.")
            item_data['true_label'] = 0 
            
        return item_data
        
    return None

# 🟢 ALIAS: สำหรับใช้ใน Depends() ใน FastAPI
get_db = get_firebase_service 

def save_submission(
    firebase_service: FirebaseService,
    user_id: str,
    date_key: str,
    submission_data: Dict[str, Any]
) -> bool:
    """
    บันทึกข้อมูลการตอบของผู้ใช้ลงใน Firebase Realtime Database
    ตามโครงสร้าง: submissions/{user_id}/{date_key}/{submission_id}
    """
    try:
        # สร้าง Path ไปยัง collection ของ user และ date นั้นๆ
        path = f'submissions/{user_id}/{date_key}'
        
        # ใช้ .push() เพื่อให้ Firebase สร้าง unique key (sub_id) ให้โดยอัตโนมัติ
        submission_ref = firebase_service.root_ref.child(path)
        submission_ref.push(submission_data)
        
        print(f"Successfully saved submission for user '{user_id}' on '{date_key}'.")
        return True
    except Exception as e:
        print(f"ERROR: Could not save submission for user '{user_id}'. Reason: {e}")
        return False
