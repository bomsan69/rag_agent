# API Contract Specification – Medicare AI Chatbot (Production)

## 1. Agent Orchestrator API

### POST /agent/chat
**Purpose:** Process user query and orchestrate retrieval, generation, verification.

**Request**
```json
{
  "session_id": "string",
  "user_query": "string",
  "doc_version": "2026",
  "stream": true
}
```

**Response (streamed or final)**
```json
{
  "answer": "string",
  "citations": [
    {
      "section": "Part B > Enrollment",
      "page": 27,
      "doc_version": "2026"
    }
  ],
  "confidence": "high|medium|low"
}
```

---

## 2. Retrieval Service API

### POST /retrieve
```json
{
  "queries": ["string"],
  "filters": {
    "doc_version": "2026",
    "chunk_type": "penalty"
  },
  "top_k": 10
}
```

Returns ranked evidence chunks with metadata.

---

## 3. Verifier Service API

### POST /verify
```json
{
  "draft_answer": "string",
  "citations": [ { "chunk_id": "string" } ]
}
```

Returns:
- approved: boolean
- revised_answer (if modified)
- issues[]

---