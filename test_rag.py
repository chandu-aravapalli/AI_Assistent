from sqlalchemy.orm import Session
from app.database import SessionLocal, create_tables
from app.models import User, Document
from app.services.document_processor import DocumentProcessor
from app.services.rag_service import RAGService
import os

def create_test_document(db: Session) -> Document:
    """Create a test document with sample content."""
    content = """
    Artificial Intelligence (AI) is revolutionizing various industries. Machine learning, 
    a subset of AI, enables computers to learn from data without explicit programming. 
    Deep learning, a type of machine learning, uses neural networks with multiple layers 
    to process complex patterns.

    Natural Language Processing (NLP) is a branch of AI that helps computers understand 
    and interact with human language. Applications of NLP include machine translation, 
    sentiment analysis, and question answering systems.

    Computer Vision is another important field in AI. It enables machines to understand 
    and process visual information from the world. Applications include facial recognition, 
    object detection, and autonomous vehicles.
    """

    document = Document(
        title="Introduction to AI",
        content=content,
        mime_type="text/plain",
        google_file_id="test_id",
        owner_id=1
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

def main():
    # Ensure the data directory exists
    os.makedirs("./data", exist_ok=True)
    
    # Initialize database
    print("Creating database tables...")
    create_tables()

    # Get database session
    db = SessionLocal()

    try:
        # Create test user
        print("\nCreating test user...")
        user = User(email="test@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create and process test document
        print("\nCreating test document...")
        document = create_test_document(db)

        # Process document
        print("\nProcessing document...")
        processor = DocumentProcessor(db)
        processor.process_document(document)

        # Initialize RAG service
        print("\nInitializing RAG service...")
        rag_service = RAGService(db)

        # Test questions
        questions = [
            "What is machine learning?",
            "What are the applications of NLP?",
            "What is computer vision used for?",
        ]

        print("\nTesting RAG pipeline with questions:")
        for question in questions:
            print(f"\nQuestion: {question}")
            result = rag_service.answer_question(question)
            print(f"Answer: {result['answer']}")
            print("\nSources:")
            for source in result['sources']:
                print(f"- {source['document_name']} (Score: {source['similarity_score']:.2f})")

    finally:
        db.close()

if __name__ == "__main__":
    main() 