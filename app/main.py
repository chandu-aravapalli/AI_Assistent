from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from .routers import auth, users, items, google_auth, qa
from .database import engine, SessionLocal, create_tables
from . import models
from app.services.rag_service import RAGService
from app.schemas import QuestionRequest, AnswerResponse

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Knowledge Assistant",
    description="AI-Powered Knowledge Assistant",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(items.router, prefix="/api/v1", tags=["items"])
app.include_router(google_auth.router, prefix="/api/v1", tags=["google"])
app.include_router(qa.router, prefix="/api/v1", tags=["question-answering"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Knowledge Assistant API",
        "status": "running"
    }

@app.post("/api/v1/qa/answer", response_model=AnswerResponse)
async def get_answer(request: QuestionRequest, db: Session = Depends(get_db)):
    try:
        rag_service = RAGService(db)
        answer = rag_service.get_answer(request.question)
        return {"answer": answer}
    except Exception as e:
        print(f"Error in get_answer: {str(e)}")  # Log the error
        return {"answer": f"I encountered an error while processing your request: {str(e)}"}

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    try:
        create_tables()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {str(e)}") 