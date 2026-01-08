# Medicare AI Chatbot

A production-grade, citation-first RAG (Retrieval-Augmented Generation) system for the Medicare Handbook 2026. Built with FastAPI, LangChain, LangGraph, and OpenAI.

## Features

- **Elderly-Friendly Design**: Designed for 60+ users with simple, clear language and friendly tone
- **Flexible Knowledge Base**: Prioritizes handbook, but uses general knowledge when handbook lacks info
- **Clear Source Attribution**: Clearly distinguishes between handbook citations and general knowledge
- **High-Quality Retrieval**: Optimized chunking and search for comprehensive coverage of manual content
- **Multi-language Support**: Ask in English or Korean (한국어) - responses match your language
- **Complete Answers**: No more "I don't have information" for common Medicare questions
- **Hybrid Search**: Combines BM25 (keyword) and vector search (semantic) for optimal retrieval
- **Web Search Integration**: Automatically searches the web (via Tavily) when manual lacks information
- **Query Expansion**: Automatically adds synonyms and related terms for better search coverage
- **Agent Orchestration**: LangGraph-based pipeline with intent classification, query expansion, retrieval, reranking, web search, generation, and verification
- **Streaming Responses**: Server-Sent Events (SSE) for real-time answer streaming

## Architecture

```
User Query
    ↓
Intent Classification
    ↓
Query Expansion (Medicare terminology)
    ↓
Hybrid Retrieval (BM25 + Vector)
    ↓
Reranking (select best evidence)
    ↓
Check if manual has sufficient information
    ├─ Yes → Skip web search
    └─ No → Web Search (Tavily)
         ↓
    Combine manual + web results
    ↓
Answer Generation (citation-first)
    ↓
Verification (accuracy + safety)
    ↓
Response (with citations + confidence)
```

## Technology Stack

### Backend
- **Framework**: FastAPI, Python 3.13+
- **AI/ML**: OpenAI GPT-4, LangChain, LangGraph
- **Search**: FAISS (vector), BM25 (keyword), Tavily (web search)
- **PDF Processing**: PyMuPDF
- **Streaming**: SSE-Starlette

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React

## Installation

### Backend Setup

#### 1. Prerequisites

- Python 3.13+
- Node.js 18+ (for frontend)
- OpenAI API key

#### 2. Install Backend Dependencies

```bash
# Install uv (if not already installed)
pip install uv

# Install project dependencies
uv pip install -e .
```

### 3. Set Up Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
OPENAI_API_KEY=your-openai-key-here
TAVILY_API_KEY=your-tavily-key-here
```

To get a Tavily API key (for web search):
1. Visit https://tavily.com/
2. Sign up for a free account
3. Copy your API key from the dashboard

### 4. Build Search Index

Before running the API, you need to build the search index from the Medicare PDF:

```bash
python scripts/build_index.py
```

This will:
1. Extract and chunk the Medicare PDF (`docs/medicare_manual.pdf`)
2. Generate embeddings using OpenAI
3. Build BM25 and vector indexes
4. Save indexes to `data/indexes/`

**Note**: This may take 10-20 minutes due to OpenAI API rate limits.

### Important: Retrieval Quality

⚠️ **For best results, use these optimized settings** in your `.env`:

```env
# Optimized for retrieval quality
CHUNK_SIZE=600
CHUNK_OVERLAP=300
TOP_K_RETRIEVAL=20
TOP_K_RERANK=8
ENABLE_QUERY_EXPANSION=true
BM25_WEIGHT=0.3
VECTOR_WEIGHT=0.7
```

These settings significantly improve the system's ability to find and answer questions from the manual. See `QUICKSTART_RETRIEVAL.md` for details.

### Frontend Setup

#### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

#### 2. Configure Environment

```bash
cp .env.local.example .env.local
```

The default configuration points to `http://localhost:8000/api/v1`. Update if your backend runs on a different port.

## Usage

### Start the Backend API Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn medicare_agent.app:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

### Start the Frontend

In a separate terminal:

```bash
cd frontend
npm run dev
```

The chatbot UI will be available at:
- Frontend: http://localhost:3000

### Access the Application

1. Open http://localhost:3000 in your browser
2. Start asking questions about Medicare!
3. Answers will stream in real-time with citations
4. Click on citations to see source information

**Example questions:**

English:
- "What is the Part B late enrollment penalty?"
- "When can I enroll in Medicare?"
- "What does Medicare Part D cover?"

Korean (한국어):
- "Part B 늦은 등록 벌금은 무엇인가요?"
- "Medicare에 언제 등록할 수 있나요?"
- "Medicare Part D는 무엇을 보장하나요?"

### API Endpoints

#### 1. Chat with Agent (Main Endpoint)

**POST** `/api/v1/agent/chat`

```json
{
  "session_id": "user-123",
  "user_query": "What is the Part B late enrollment penalty?",
  "doc_version": "2026",
  "stream": true
}
```

Response:
```json
{
  "answer": "The Part B late enrollment penalty is generally calculated as 10% of the standard premium for each 12-month period you were eligible but didn't enroll [Part B > Enrollment > Page 27]...",
  "citations": [
    {
      "section": "Part B > Enrollment",
      "page": 27,
      "doc_version": "2026"
    }
  ],
  "confidence": "high"
}
```

#### 2. Retrieve Documents

**POST** `/api/v1/retrieve`

```json
{
  "queries": ["Part B enrollment penalty"],
  "filters": {
    "doc_version": "2026",
    "chunk_type": "penalty"
  },
  "top_k": 10
}
```

#### 3. Verify Answer

**POST** `/api/v1/verify`

```json
{
  "draft_answer": "The penalty is 10% per year...",
  "citations": [...]
}
```

## Project Structure

```
medicare_agent/
├── medicare_agent/          # Backend
│   ├── agents/              # LangGraph orchestration
│   │   └── orchestrator.py
│   ├── api/                 # FastAPI routes
│   │   └── routes.py
│   ├── models/              # Pydantic schemas
│   │   └── schemas.py
│   ├── services/            # Core services
│   │   ├── ingestion.py     # PDF processing
│   │   ├── retrieval.py     # Hybrid search
│   │   ├── reranker.py      # Evidence selection
│   │   ├── web_search.py    # Web search (Tavily)
│   │   ├── generator.py     # Answer generation
│   │   └── verifier.py      # Answer verification
│   ├── utils/               # Utilities
│   ├── app.py               # FastAPI app
│   └── config.py            # Configuration
├── frontend/                # Frontend (Next.js)
│   ├── src/
│   │   ├── app/            # Next.js App Router
│   │   ├── components/     # React components
│   │   ├── lib/            # API client & utils
│   │   └── types/          # TypeScript types
│   ├── package.json
│   └── tailwind.config.js
├── scripts/
│   └── build_index.py       # Index builder
├── docs/                    # Documentation + PDF
├── data/                    # Generated indexes
├── main.py                  # Backend entry point
└── pyproject.toml           # Backend dependencies
```

## Configuration

All configuration is in `.env`:

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Tavily (Web Search)
TAVILY_API_KEY=tvly-...
ENABLE_WEB_SEARCH=true
WEB_SEARCH_MAX_RESULTS=5

# Application
APP_ENV=development
LOG_LEVEL=INFO

# Document
MEDICARE_DOC_VERSION=2026
MEDICARE_PDF_PATH=./docs/medicare_manual.pdf

# Index
INDEX_PATH=./data/indexes
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=10
TOP_K_RERANK=5

# Performance (see PERFORMANCE.md for details)
ENABLE_QUERY_EXPANSION=false
ENABLE_INTENT_CLASSIFICATION=true
ENABLE_VERIFICATION=true
SKIP_VERIFICATION_ON_STREAM=true
USE_FAST_MODEL_FOR_CLASSIFICATION=true
FAST_MODEL=gpt-3.5-turbo

# API
API_HOST=0.0.0.0
API_PORT=8000
```

## Performance Optimization

The system includes several performance optimizations. See `PERFORMANCE.md` for detailed information.

### Quick Start (Recommended Settings)

For **balanced performance and accuracy**, use these settings:

```env
ENABLE_QUERY_EXPANSION=false            # Faster, minimal quality impact
ENABLE_INTENT_CLASSIFICATION=true       # Improves accuracy
ENABLE_VERIFICATION=true                # Ensures accuracy
SKIP_VERIFICATION_ON_STREAM=true        # Faster streaming
USE_FAST_MODEL_FOR_CLASSIFICATION=true  # 3-5x faster, 10x cheaper
FAST_MODEL=gpt-3.5-turbo               # Fast model for classification
```

**Performance:** ~4-6 seconds per query
**Cost:** ~$0.02 per query
**Accuracy:** 92-95%

### Key Optimizations

1. **Reranker**: Eliminated LLM calls, 10x faster
2. **Fast Model**: Uses GPT-3.5 for classification (optional)
3. **Optional Expansion**: Query expansion disabled by default
4. **Streaming Skip**: Verification skipped during streaming for speed

### Configuration Profiles

| Profile | Response Time | Cost/Query | Accuracy |
|---------|--------------|------------|----------|
| **Maximum Speed** | ~2-4s | ~$0.01 | 85-90% |
| **Balanced** ⭐ | ~4-6s | ~$0.02 | 92-95% |
| **Maximum Accuracy** | ~8-12s | ~$0.05 | 95-98% |

See `PERFORMANCE.md` for detailed configuration examples.

## Development

### Running in Development Mode

```bash
python main.py
```

This enables auto-reload on code changes.

### Rebuilding Index

If you update the Medicare PDF or change chunking parameters:

```bash
python scripts/build_index.py
```

### Testing the API

Use the interactive docs at http://localhost:8000/docs or:

```bash
curl -X POST "http://localhost:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "user_query": "What is Medicare Part B?",
    "doc_version": "2026",
    "stream": false
  }'
```

## Design Principles

1. **Accuracy > Fluency**: Correct information is more important than eloquent prose
2. **Evidence > Eloquence**: Every claim must be backed by citations
3. **Safety > Creativity**: Conservative language prevents misinterpretation
4. **Citation-First**: Never make claims without source references
5. **Verification Required**: All answers must pass verification before delivery

## Key Features

### 1. Hybrid Search

Combines BM25 (keyword matching) with vector search (semantic similarity) for optimal retrieval:
- BM25: Accurate for Medicare-specific terminology
- Vector: Captures semantic intent and synonyms

### 2. Intent Classification

Automatically classifies queries into categories:
- penalty, cost, enrollment, coverage, eligibility, comparison, procedure, exception, general

### 3. Query Expansion

Rewrites queries using official Medicare terminology for better retrieval.

### 4. Reranking

Selects top-K evidence chunks with priority for:
- Tables with numbers (for costs/penalties)
- Explicit conditions and exceptions
- Relevant section types

### 5. Web Search Integration

Automatically triggers web search when manual information is insufficient:
- Evaluates quality and quantity of retrieved chunks
- Searches the web via Tavily API for supplementary information
- Combines manual and web sources for comprehensive answers
- Clearly distinguishes between manual citations and web sources

### 6. Citation Enforcement

Generator is constrained to:
- Only use information from evidence
- Always cite sources [Section > Page X]
- Use conservative language
- Never hallucinate numbers/dates

### 7. Verification

Multi-stage verification checks for:
- Unsupported claims
- Missing citations
- Numeric errors
- Overly definitive language

## Compliance & Safety

- Strict document version isolation
- No legal/medical advice claims
- Clear disclaimers
- Full audit trail per response
- Conservative, policy-compliant language

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or questions, please refer to the documentation in `docs/`.
