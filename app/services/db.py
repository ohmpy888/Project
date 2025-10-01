# backend/app/services/db.py
import sys
from pathlib import Path # ⬅️ ต้องมีสำหรับจัดการ Path
from typing import Dict, Any
import firebase_admin
from firebase_admin import credentials, db
# -----------------------------------------------------------------
# ⚠️ FIX: เพิ่ม Project Root Path เพื่อให้ import 'core' ได้
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent 
sys.path.insert(0, str(PROJECT_ROOT)) 
# -----------------------------------------------------------------
from core.config import settings # ⬅️ ตอนนี้ import 'core' ได้แล้ว

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

def get_challenge_item(item_id: str) -> Dict[str, Any] | None:
    """Fetches a specific news item by its ID from the /items path (e.g., items/item1)."""
    
    # ตรวจสอบการเชื่อมต่อ
    if not firebase_admin._apps:
        return None
        
    try:
        # ดึงข้อมูลจากพาธ /items/{item_id}
        ref = db.reference(f'items/{item_id}')
        data = ref.get()
        
        if data:
            data['item_id'] = item_id
            
            # ⚠️ Logic สำคัญ: ตรวจสอบและเตรียม 'text' สำหรับโมเดล
            if 'text' not in data and 'content' not in data:
                 data['text'] = f"Mock news content for {item_id}. Full text is missing in Firebase."
            
            # ถ้ามี content ให้ย้ายไปไว้ที่คีย์ 'text' เพื่อใช้ในการวิเคราะห์
            if 'content' in data:
                data['text'] = data.pop('content') 
            
            return data
        else:
            return None
    except Exception as e:
        print(f"Error fetching Firebase item {item_id}: {e}")
        return None

# ⚠️ ฟังก์ชันนี้ถูกใช้โดย app/routes/analyze.py ของคุณ
def get_news_text_by_id(item_id: str) -> str:
    """Retrieves the news text content for analysis."""
    item = get_challenge_item(item_id)
    if item and item.get('text'):
        return item['text']
    raise Exception(f"Text not found for news ID: {item_id}")
