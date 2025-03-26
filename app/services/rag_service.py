from typing import List, Dict, Any
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from openai import OpenAI
from ..models import Document, DocumentChunk
from ..config import settings
import os

class RAGService:
    def __init__(self, db: Session):
        self.db = db
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index_file = "./data/faiss_index.bin"
        self.chunk_ids = []  # Initialize chunk_ids list
        self.load_or_create_index()
        self.openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self._load_chunks_from_db()

    def _load_chunks_from_db(self):
        """Load all document chunks from the database and update the FAISS index."""
        try:
            # Get all chunks from the database
            chunks = self.db.query(DocumentChunk).all()
            if not chunks:
                print("No chunks found in database")
                # Initialize empty index
                embedding_size = 384
                self.index = faiss.IndexFlatL2(embedding_size)
                return

            # Prepare embeddings and chunk IDs
            embeddings = []
            self.chunk_ids = []  # Reset chunk_ids list

            print(f"Processing {len(chunks)} chunks from database...")
            for chunk in chunks:
                if chunk.embedding is not None:
                    try:
                        # Convert bytes to numpy array
                        embedding = np.frombuffer(chunk.embedding, dtype=np.float32)
                        if len(embedding) == 384:  # Verify embedding dimension
                            embeddings.append(embedding)
                            self.chunk_ids.append(chunk.id)
                        else:
                            print(f"Warning: Chunk {chunk.id} has wrong embedding dimension: {len(embedding)}")
                    except Exception as e:
                        print(f"Error processing chunk {chunk.id}: {str(e)}")
                        continue
                else:
                    print(f"Warning: Chunk {chunk.id} has no embedding")

            if embeddings:
                print(f"Found {len(embeddings)} valid embeddings")
                # Convert list of embeddings to numpy array
                embeddings_array = np.vstack(embeddings)
                print(f"Embeddings array shape: {embeddings_array.shape}")
                
                # Create new index with the correct dimension
                self.index = faiss.IndexFlatL2(embeddings_array.shape[1])
                
                # Add embeddings to the index
                self.index.add(embeddings_array)
                print(f"Added embeddings to FAISS index. Total vectors: {self.index.ntotal}")
                
                # Save the updated index
                os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
                faiss.write_index(self.index, self.index_file)
                print(f"Saved index with {len(embeddings)} chunks")
            else:
                print("No valid embeddings found in chunks")
                # Initialize empty index
                embedding_size = 384
                self.index = faiss.IndexFlatL2(embedding_size)

        except Exception as e:
            print(f"Error loading chunks from database: {str(e)}")
            import traceback
            traceback.print_exc()
            # Create empty index as fallback
            embedding_size = 384
            self.index = faiss.IndexFlatL2(embedding_size)
            self.chunk_ids = []

    def load_or_create_index(self):
        try:
            if os.path.exists(self.index_file):
                self.index = faiss.read_index(self.index_file)
            else:
                # Create a new index
                embedding_size = 384  # Size of embeddings from all-MiniLM-L6-v2
                self.index = faiss.IndexFlatL2(embedding_size)
                # Save the empty index
                os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
                faiss.write_index(self.index, self.index_file)
        except Exception as e:
            print(f"Error loading/creating index: {str(e)}")
            # Create in-memory index as fallback
            embedding_size = 384
            self.index = faiss.IndexFlatL2(embedding_size)

    def search_similar_chunks(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar chunks using the query."""
        try:
            if not self.chunk_ids:  # If no chunks are loaded
                print("No chunks available for search")
                return []

            print(f"\nSearching for query: {query}")
            print(f"Total chunks available: {len(self.chunk_ids)}")

            # Get query embedding
            query_embedding = self.model.encode([query])[0]
            
            # Search in the index
            D, I = self.index.search(np.array([query_embedding]).astype('float32'), min(k, len(self.chunk_ids)))
            
            results = []
            for idx, (distance, index) in enumerate(zip(D[0], I[0])):
                if index >= 0 and index < len(self.chunk_ids):  # Add bounds check
                    chunk_id = self.chunk_ids[index]
                    chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
                    if chunk:
                        similarity_score = float(1 / (1 + distance))
                        print(f"\nFound chunk with similarity score: {similarity_score:.3f}")
                        print(f"Chunk content preview: {chunk.content[:100]}...")
                        results.append({
                            "content": chunk.content,
                            "document_id": chunk.document_id,
                            "similarity_score": similarity_score
                        })
            
            # Sort results by similarity score
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            return results
        except Exception as e:
            print(f"Error searching similar chunks: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def get_answer(self, question: str) -> str:
        try:
            # Print available documents first
            docs = self.db.query(Document).all()
            print("\nAvailable documents:")
            for doc in docs:
                print(f"- {doc.title}: {doc.content[:100]}...")

            # Get relevant chunks
            relevant_chunks = self.search_similar_chunks(question, k=3)
            
            if not relevant_chunks:
                return "I couldn't find any relevant information in the documents. Here are the documents I have access to:\n" + \
                       "\n".join([f"- {doc.title}" for doc in docs])
            
            # Lower the similarity threshold to 0.2 (was 0.5)
            if all(chunk["similarity_score"] < 0.2 for chunk in relevant_chunks):
                return "While I found some documents, they don't seem to contain very relevant information about your question. Here's what I found:\n\n" + \
                       relevant_chunks[0]['content']
            
            # Prepare context from relevant chunks
            context = "\n\n".join([
                f"Relevant text (similarity: {chunk['similarity_score']:.2f}):\n{chunk['content']}"
                for chunk in relevant_chunks
            ])
            
            if self.openai_client:
                try:
                    return self._generate_answer_with_chatgpt(question, context)
                except Exception as e:
                    print(f"OpenAI API error: {str(e)}")
                    return f"I found some potentially relevant information, but couldn't generate a proper answer due to an API error. Here's the most relevant content I found:\n\n{relevant_chunks[0]['content']}"
            else:
                return f"I found some potentially relevant information, but the OpenAI API is not configured. Here's the most relevant content:\n\n{relevant_chunks[0]['content']}"
        except Exception as e:
            print(f"Error processing question: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error processing your question: {str(e)}"

    def _generate_answer_with_chatgpt(self, question: str, context: str) -> str:
        if not self.openai_client:
            return "OpenAI API key is not configured. Please set it up to get AI-generated answers."

        prompt = f"""You are a helpful AI assistant. Use the following information to answer the question naturally and conversationally, as if you're having a direct dialogue. Don't refer to "the context" or "the documents" in your response. If you can't find the answer in the provided information, simply say "I don't have enough information to answer this question."

Information:
{context}

Question: {question}

Remember to answer naturally and directly, without mentioning the source of your information."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides natural, conversational responses. Avoid phrases like 'Based on the context' or 'According to the documents'. Instead, answer directly and confidently when you have the information, and simply state when you don't have enough information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating answer: {str(e)}" 