from fastapi import APIRouter

from app.api.v1 import analytics, attempts, auth, materials, practice, quizzes, summaries, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(materials.router)
api_router.include_router(quizzes.router)
api_router.include_router(attempts.router)
api_router.include_router(summaries.router)
api_router.include_router(analytics.router)
api_router.include_router(practice.router)
