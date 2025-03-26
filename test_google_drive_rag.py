from sqlalchemy.orm import Session
from app.database import SessionLocal, create_tables
from app.models import User, Document
from app.services.document_processor import DocumentProcessor
from app.services.rag_service import RAGService
from app.services.google_drive import GoogleDriveService
from app.config import settings
import os
import json

def create_test_document(db: Session, user_id: int) -> Document:
    """Create a test document with sample content."""
    content = """
    In a recent project, I had to persuade my team to adopt a new testing framework. 
    Initially, there was resistance because the team was comfortable with the existing tools. 
    I prepared a detailed presentation showing how the new framework would save time and improve code quality.
    I also created a small proof of concept demonstrating the benefits.
    After showing concrete examples and addressing their concerns one by one, the team agreed to try it.
    The transition was successful, and team productivity improved by 30%.

    Another situation involved convincing a senior developer to refactor a critical component.
    I documented the technical debt and potential risks of the current implementation.
    Through one-on-one discussions and by proposing a gradual transition plan,
    I was able to get buy-in for the refactoring project.
    """

    document = Document(
        title="Workplace Scenarios",
        content=content,
        mime_type="text/plain",
        google_file_id="test_id",
        owner_id=user_id
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

def setup_test_user(db: Session) -> User:
    """Create or get a test user with Google credentials."""
    user = db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(email="test@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Update user with Google credentials from env if available
    if settings.google_client_id and settings.google_client_secret:
        try:
            # Try to get tokens from environment variables
            access_token = settings.google_access_token
            refresh_token = settings.google_refresh_token
            
            if access_token and refresh_token:
                user.google_credentials = {
                    "token": access_token,
                    "refresh_token": refresh_token,
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "scopes": [
                        "https://www.googleapis.com/auth/drive.readonly",
                        "https://www.googleapis.com/auth/drive.metadata.readonly",
                        "https://www.googleapis.com/auth/userinfo.profile",
                        "https://www.googleapis.com/auth/userinfo.email"
                    ]
                }
                db.commit()
                db.refresh(user)
                print("\nGoogle credentials set up successfully.")
                return user, True
            else:
                print("\nMissing access token or refresh token.")
        except Exception as e:
            print(f"\nError setting up Google credentials: {str(e)}")
    else:
        print("\nMissing Google client ID or client secret.")
    
    return user, False

def sync_google_drive_documents(db: Session, user: User) -> bool:
    """Sync documents from Google Drive and process them."""
    try:
        if not user.google_credentials:
            print("\nNo valid Google credentials found. Skipping Google Drive sync.")
            return False

        # Initialize services
        print("\nInitializing Google Drive service...")
        drive_service = GoogleDriveService(user.google_credentials)
        doc_processor = DocumentProcessor(db)

        # List files from Google Drive
        print("\nFetching files from Google Drive...")
        mime_types = [
            'text/plain',
            'application/pdf',
            'application/vnd.google-apps.document'
        ]
        files = drive_service.list_files(mime_types)
        
        if not files:
            print("No files found in Google Drive.")
            return False
            
        print(f"Found {len(files)} files to process.")
        
        processed_count = 0
        for file in files:
            print(f"\nProcessing file: {file['name']} (ID: {file['id']})")
            try:
                # Check if document already exists
                existing_doc = db.query(Document).filter(
                    Document.google_file_id == file['id']
                ).first()

                # Download and process the file
                print(f"Downloading file content...")
                content, metadata = drive_service.download_file(file['id'])
                
                if content:
                    print("File content downloaded successfully.")
                    if existing_doc:
                        print("Updating existing document...")
                        # Update existing document
                        existing_doc.content = content
                        existing_doc.title = file['name']
                        existing_doc.mime_type = file['mimeType']
                        db.commit()
                        print("Processing updated document...")
                        doc_processor.process_document(existing_doc)
                    else:
                        print("Creating new document...")
                        # Create new document
                        new_doc = Document(
                            title=file['name'],
                            content=content,
                            mime_type=file['mimeType'],
                            google_file_id=file['id'],
                            owner_id=user.id
                        )
                        db.add(new_doc)
                        db.commit()
                        print("Processing new document...")
                        doc_processor.process_document(new_doc)
                    
                    processed_count += 1
                    print(f"Successfully processed file: {file['name']}")
                else:
                    print(f"Failed to download content for file: {file['name']}")
            except Exception as e:
                print(f"Error processing file {file['name']}: {str(e)}")
                continue

        print(f"\nProcessed {processed_count} documents from Google Drive")
        return processed_count > 0

    except Exception as e:
        print(f"Error syncing documents: {str(e)}")
        return False

def test_rag_question(db: Session):
    """Test the RAG pipeline with a specific question."""
    question = "give me a situation when you want to persuade someone at work. What did you do?"
    
    print("\nInitializing RAG service...")
    rag_service = RAGService(db)
    
    print(f"\nQuestion: {question}")
    result = rag_service.get_answer(question)
    
    print("\nAnswer:", result)

def main():
    # Ensure the data directory exists
    os.makedirs("./data", exist_ok=True)
    
    # Initialize database
    print("Creating database tables...")
    create_tables()

    # Get database session
    db = SessionLocal()

    try:
        # Setup test user
        print("\nSetting up test user...")
        user, has_google_creds = setup_test_user(db)

        # Try to sync with Google Drive if we have credentials
        sync_success = False
        if has_google_creds:
            print("\nAttempting to sync with Google Drive...")
            sync_success = sync_google_drive_documents(db, user)

        # Create a test document if Google Drive sync failed or no credentials
        if not sync_success:
            print("\nCreating test document...")
            test_doc = create_test_document(db, user.id)
            
            print("\nProcessing test document...")
            processor = DocumentProcessor(db)
            processor.process_document(test_doc)

        # Verify we have at least one document with embeddings
        doc_count = db.query(Document).count()
        print(f"\nNumber of documents in database: {doc_count}")
        
        if doc_count == 0:
            print("Error: No documents available for RAG pipeline.")
            return

        # Test RAG pipeline with specific question
        test_rag_question(db)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 