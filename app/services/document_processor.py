from typing import List, Dict, Any
import PyPDF2
import io
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from ..models import Document, DocumentChunk, DocumentEmbedding
from ..config import settings

class DocumentProcessor:
    def __init__(self, db: Session):
        """Initialize the document processor with database session."""
        print("Initializing DocumentProcessor...")
        self.db = db
        try:
            print("Loading sentence transformer model...")
            self.model = SentenceTransformer(settings.embedding_model)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            raise
        self.chunk_size = 500  # characters per chunk
        self.chunk_overlap = 50  # characters of overlap between chunks

    def process_document(self, document: Document):
        """Process a document by creating chunks and embeddings."""
        try:
            print(f"\nProcessing document: {document.title}")
            print(f"Document content length: {len(document.content) if document.content else 0} characters")
            
            if not document.content or not document.content.strip():
                print("Warning: Document has no content")
                return

            print("Creating chunks...")
            chunks = self._create_chunks(document.content)
            if not chunks:
                print("Warning: No chunks were created from the document")
                return
            print(f"Created {len(chunks)} chunks")

            print("\nGenerating embeddings...")
            try:
                embeddings = self.model.encode(chunks, show_progress_bar=True)
                print(f"Generated {len(embeddings)} embeddings")
            except Exception as e:
                print(f"Error generating embeddings: {str(e)}")
                raise

            print("\nStoring embeddings in database...")
            try:
                # Delete existing embeddings for this document
                self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
                print("Deleted existing chunks")

                # Create new embeddings
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    print(f"Storing chunk {i+1}/{len(chunks)} (length: {len(chunk)} chars)")
                    chunk_obj = DocumentChunk(
                        content=chunk,
                        embedding=embedding.astype(np.float32).tobytes(),
                        document_id=document.id,
                        chunk_index=i
                    )
                    self.db.add(chunk_obj)
                    
                    # Commit every 10 chunks to avoid memory issues
                    if (i + 1) % 10 == 0:
                        self.db.commit()
                        print(f"Committed chunks {i-8}-{i+1}")

                self.db.commit()
                print(f"Successfully processed document: {document.title}")

            except Exception as e:
                print(f"Error storing embeddings in database: {str(e)}")
                self.db.rollback()
                raise

        except Exception as e:
            print(f"Error processing document: {str(e)}")
            self.db.rollback()
            raise

    def _create_chunks(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks."""
        try:
            print("Starting text chunking...")
            if not text or not text.strip():
                print("Warning: Empty text received")
                return []

            chunks = []
            start = 0
            text_length = len(text)
            print(f"Text length: {text_length} characters")

            while start < text_length:
                # Print progress every few chunks
                if len(chunks) % 5 == 0:
                    print(f"Chunking progress: {start}/{text_length} characters processed")

                end = min(start + chunk_size, text_length)
                chunk = text[start:end]

                # If this is not the first chunk and we have overlap available
                if start > 0 and start >= overlap:
                    # Look for sentence boundaries in the overlap region
                    overlap_text = text[start - overlap:start]
                    best_boundary = -1
                    
                    for punct in ['. ', '! ', '? ', '\n\n']:
                        boundary = overlap_text.rfind(punct)
                        if boundary != -1 and boundary > best_boundary:
                            best_boundary = boundary
                    
                    if best_boundary != -1:
                        start = start - overlap + best_boundary + 2  # +2 for the punctuation mark and space
                        chunk = text[start:end]

                # If this is not the last chunk, try to end at a sentence boundary
                if end < text_length:
                    best_boundary = -1
                    for punct in ['. ', '! ', '? ', '\n\n']:
                        boundary = chunk.rfind(punct)
                        if boundary != -1 and boundary > best_boundary:
                            best_boundary = boundary
                    
                    if best_boundary != -1:
                        chunk = chunk[:best_boundary + 2]  # +2 for the punctuation mark and space

                # Only add non-empty chunks
                chunk = chunk.strip()
                if chunk:
                    chunks.append(chunk)
                    print(f"Created chunk {len(chunks)}: {len(chunk)} characters")

                # Move to next chunk, ensure we make progress
                new_start = start + len(chunk)
                if new_start <= start:  # Ensure we always make progress
                    new_start = start + chunk_size // 2
                start = new_start

                # Safety check to prevent infinite loops
                if len(chunks) > text_length // 50:  # Assuming average chunk size of 50 characters
                    print("Warning: Too many chunks created, breaking to prevent infinite loop")
                    break

            print(f"Chunking completed. Created {len(chunks)} chunks.")
            return chunks

        except Exception as e:
            print(f"Error creating chunks: {str(e)}")
            raise

    def process_text(self, text: str, document_id: int) -> List[Dict[str, Any]]:
        """Process a text string and return chunks with their embeddings."""
        chunks = self._create_chunks(text)
        processed_chunks = []
        
        for idx, chunk_text in enumerate(chunks):
            embedding = self.model.encode(chunk_text)
            processed_chunks.append({
                "text": chunk_text,
                "embedding": embedding,
                "chunk_index": idx,
                "document_id": document_id
            })
        
        return processed_chunks

    def process_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content."""
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ''
        
        for page in pdf_reader.pages:
            text += page.extract_text() + '\n'
            
        return text

    def generate_embeddings(self, chunks: List[str]) -> List[np.ndarray]:
        """Generate embeddings for text chunks."""
        return self.model.encode(chunks, convert_to_tensor=True).numpy()

    def process_document_content(self, content: bytes, mime_type: str) -> tuple[str, List[Dict[str, Any]]]:
        """Process document content and generate embeddings."""
        # Extract text based on mime type
        if mime_type == 'application/pdf':
            text = self.process_pdf(content)
        else:
            text = content.decode('utf-8')

        # Split into chunks
        chunks = self.process_text(text, 0)
        
        # Generate embeddings
        embeddings = self.generate_embeddings(text.split())
        
        # Prepare result
        chunk_embeddings = []
        for i, (chunk, embedding) in enumerate(zip(text.split(), embeddings)):
            chunk_embeddings.append({
                'chunk_index': i,
                'chunk_text': chunk,
                'embedding_vector': embedding.tolist()
            })
            
        return text, chunk_embeddings 