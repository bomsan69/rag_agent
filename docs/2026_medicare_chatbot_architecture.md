
# 2026 Medicare Handbook AI Chatbot – Production Architecture Document

## 1. Project Overview
This document defines the **production‑grade architecture** for an AI chatbot built on the **2026 Medicare Handbook**.
The system is designed as a **regulation‑safe, citation‑first, agent‑based RAG platform**.

Primary goals:
- 100% citation‑based answers (page & section)
- Zero hallucinated numbers, dates, penalties, or eligibility rules
- Conservative, policy‑compliant language
- Auditability and version control

---

## 2. System Architecture (High Level)

Client → API Gateway → Agent Orchestrator  
→ Retrieval Service → Reranker → Generator  
→ Verifier → Client

---

## 3. Client Layer (Next.js)

### Responsibilities
- Chat interface with streaming responses
- Citation panel (page/section jump)
- Accessibility‑friendly UI (large text, clear spacing)
- User feedback collection (accuracy rating)

### Required UI Components
- Chat message view
- “Sources” expandable panel
- Disclaimer block (“General information only”)

---

## 4. API Gateway / BFF

### Responsibilities
- Authentication & rate limiting
- SSE / WebSocket streaming
- Request ID & audit log propagation
- Optional PII masking

---

## 5. Agent Orchestrator (Core Logic)

### Responsibilities
- Intent classification:
  - definition
  - eligibility
  - enrollment period
  - penalty
  - cost
  - coverage
  - comparison
  - procedure
  - exception
- Query rewriting into Medicare terminology
- Retrieval strategy selection
- Response format enforcement

### Mandatory Rules
- No numeric claims without citation
- No definitive language when rules are conditional
- Always prefer “may / depends on / generally”

---

## 6. Retrieval Service

### Search Strategy
- Hybrid search:
  - BM25 (terminology accuracy)
  - Vector search (semantic intent)
- Table‑first pipeline for:
  - costs
  - penalties
  - enrollment timelines

### Filters
- doc_version = 2026
- part = A | B | C | D
- chunk_type (penalty, cost, timeline, etc.)

---

## 7. Reranker

### Purpose
- Select top‑K evidence chunks (K = 4–8)
- Prioritize:
  - explicit conditions
  - tables with numbers
  - penalty definitions

This component is critical for accuracy.

---

## 8. Verifier Service (Mandatory)

### Responsibilities
- Validate answer ↔ citation alignment
- Remove unsupported numbers/dates
- Enforce conservative phrasing
- Trigger re‑retrieval if evidence is weak

Without this service, production deployment is **not recommended**.

---

## 9. Data Layer

### Document Store
- Original text
- Chunked sections
- Page mapping
- Tables (JSON)
- Version metadata

### Chunk Metadata Schema
- doc_version
- section_path
- page_start / page_end
- chunk_type
- effective_date
- keywords

### Optional Rule Store
Normalized policy rules:
- conditions
- outcomes
- exceptions
- citations

---

## 10. Runtime Request Flow

1. User submits question
2. Intent classification
3. Query rewrite & expansion
4. Hybrid retrieval + filters
5. Reranking
6. Answer generation (citation‑first)
7. Verification
8. Streaming response to client
9. Logging & evaluation capture

---

## 11. Evaluation & Quality Control

### Required Metrics
- Citation hit rate
- Hallucination rate
- Retrieval recall@K
- Latency (p50 / p95)

### Evaluation Dataset
- 150–300 curated Medicare questions
- Heavy focus on penalties, exceptions, timelines

Regression tests must run on:
- Document updates
- Model updates
- Index rebuilds

---

## 12. Compliance & Safety

- Strict document version isolation
- No legal/medical advice claims
- Clear disclaimers
- Full audit trail per response

---

## 13. Model Role Separation

- Embedding model: retrieval
- Reranker model: evidence quality
- Generator model: explanation
- Verifier model: safety & accuracy

Knowledge lives in RAG, not in the model.

---

## 14. Deployment Assumptions

- Containerized (Docker)
- Kubernetes‑ready
- Microservice architecture
- Future support for additional CMS documents

---

## 15. Key Principle (Summary)

This system is **not a creative chatbot**.  
It is a **policy interpretation engine with citations**.

Accuracy > Fluency  
Evidence > Eloquence  
Safety > Creativity
