from celery import shared_task
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .celery_app import celery_app
from ..database import SessionLocal
from ..models import User, Document, DocumentEmbedding
from ..services.google_drive import GoogleDriveService
from ..services.document_processor import DocumentProcessor

SUPPORTED_MIME_TYPES = [
    'text/plain',
    'text/markdown',
    'application/pdf',
    'application/vnd.google-apps.document'
]

@shared_task
def sync_user_documents(user_id: int):
    """
    Synchronize user's Google Drive documents and process them for the RAG pipeline.
    """
    db = SessionLocal()
    try:
        # Get user and their credentials
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.google_credentials:
            return {"status": "error", "message": "User not found or not authenticated"}

        # Initialize services
        drive_service = GoogleDriveService(user.google_credentials)
        doc_processor = DocumentProcessor(db)

        # List files from Google Drive
        mime_types = [
            'text/plain',
            'application/pdf',
            'application/vnd.google-apps.document'
        ]
        files = drive_service.list_files(mime_types)

        processed_count = 0
        for file in files:
            # Check if document already exists
            existing_doc = db.query(Document).filter(
                Document.google_file_id == file['id']
            ).first()

            # Download and process the file
            content, metadata = drive_service.download_file(file['id'])
            if content:
                if existing_doc:
                    # Update existing document
                    existing_doc.content = content
                    existing_doc.title = file['name']
                    existing_doc.mime_type = file['mimeType']
                    db.commit()
                    doc_processor.process_document(existing_doc)
                else:
                    # Create new document
                    new_doc = Document(
                        title=file['name'],
                        content=content,
                        mime_type=file['mimeType'],
                        google_file_id=file['id'],
                        owner_id=user_id
                    )
                    db.add(new_doc)
                    db.commit()
                    doc_processor.process_document(new_doc)
                
                processed_count += 1

        return {
            "status": "success",
            "message": f"Processed {processed_count} documents"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

def process_document(
    db: Session,
    drive_service: GoogleDriveService,
    doc_processor: DocumentProcessor,
    user_id: int,
    file_metadata: Dict[str, Any]
):
    """Process a single document and store its content and embeddings."""
    # Check if document exists and needs updating
    existing_doc = db.query(Document).filter(
        Document.file_id == file_metadata['id']
    ).first()

    if existing_doc and existing_doc.last_synced:
        modified_time = datetime.fromisoformat(file_metadata['modifiedTime'].replace('Z', '+00:00'))
        if existing_doc.last_synced >= modified_time:
            return  # Document is up to date

    # Download and process document
    content, metadata = drive_service.download_file(file_metadata['id'])
    if not content:
        return

    # Process document and generate embeddings
    full_text, chunk_embeddings = doc_processor.process_document(
        content.encode('utf-8'),
        file_metadata['mimeType']
    )

    # Create or update document
    if not existing_doc:
        existing_doc = Document(
            file_id=file_metadata['id'],
            name=file_metadata['name'],
            mime_type=file_metadata['mimeType'],
            content=full_text,
            owner_id=user_id,
            metadata=metadata
        )
        db.add(existing_doc)
    else:
        existing_doc.content = full_text
        existing_doc.metadata = metadata
        existing_doc.last_synced = datetime.utcnow()

    db.commit()
    db.refresh(existing_doc)

    # Update embeddings
    db.query(DocumentEmbedding).filter(
        DocumentEmbedding.document_id == existing_doc.id
    ).delete()

    for chunk_data in chunk_embeddings:
        embedding = DocumentEmbedding(
            document_id=existing_doc.id,
            chunk_index=chunk_data['chunk_index'],
            chunk_text=chunk_data['chunk_text'],
            embedding_vector=chunk_data['embedding_vector']
        )
        db.add(embedding)

    db.commit() 