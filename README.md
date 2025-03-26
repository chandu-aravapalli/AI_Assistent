# AI Assistant with RAG and Google Drive Integration

A powerful AI-powered document assistant that combines Retrieval-Augmented Generation (RAG) with Google Drive integration to provide intelligent answers to questions about your documents.

## Features

- **Document Integration**
  - Seamless Google Drive integration
  - Support for multiple document types (Google Docs, PDFs)
  - Automatic document synchronization
  - Background processing with Celery

- **Intelligent Question Answering**
  - Context-aware responses using RAG
  - Natural language processing with OpenAI's GPT-3.5
  - Vector similarity search using FAISS
  - Document chunking and embedding generation

- **Modern Web Interface**
  - Clean, responsive UI built with Next.js
  - Real-time chat interface
  - Dark mode support
  - Conversation history management

## Tech Stack

### Backend
- FastAPI (Python web framework)
- Celery (Task queue)
- Redis (Message broker)
- FAISS (Vector similarity search)
- Sentence Transformers (Text embeddings)
- SQLite (Database)

### Frontend
- Next.js
- TypeScript
- Tailwind CSS
- React Query
- Local Storage for persistence

## Architecture

The application follows a modern microservices architecture:
1. **Document Processing Pipeline**
   - Google Drive sync
   - Document chunking
   - Embedding generation
   - Vector storage

2. **Question Answering System**
   - RAG implementation
   - Context retrieval
   - Answer generation
   - Response optimization

3. **Task Management**
   - Asynchronous processing
   - Background tasks
   - Queue management

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- Redis
- Google Drive API credentials
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AI_Assistent.git
cd AI_Assistent
```

2. Set up the backend:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```

3. Set up the frontend:
```bash
cd frontend
npm install
```

4. Start the services:
```bash
# Start Redis
redis-server

# Start Celery worker
celery -A app.worker worker --loglevel=info

# Start backend server
uvicorn app.main:app --reload

# Start frontend (in a new terminal)
cd frontend
npm run dev
```

## Environment Variables

Create a `.env` file with the following variables:
