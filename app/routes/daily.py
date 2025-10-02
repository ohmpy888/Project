# app/routes/daily.py
from fastapi import APIRouter
from typing import List
from app.schemas import Challenge
from app.services.db import get_challenge_items_for_today

router = APIRouter()

@router.get("/challenges", response_model=List[Challenge])
def daily_challenges():
    return get_challenge_items_for_today()
