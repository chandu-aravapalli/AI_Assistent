from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from ..database import get_db
from ..services.rag_service import RAGService

router = APIRouter(prefix="/qa", tags=["question-answering"])

class QuestionRequest(BaseModel):
    question: str

@router.post("/ask")
async def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ask a question about the content of your Google Drive documents.
    The answer will be generated based on the relevant content found in your documents.
    """
    try:
        rag_service = RAGService(db)
        result = rag_service.answer_question(request.question)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing question: {str(e)}"
        ) 