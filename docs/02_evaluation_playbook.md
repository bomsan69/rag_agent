# Evaluation & QA Playbook – Medicare Chatbot

## 1. Core Metrics
- Citation Hit Rate
- Hallucination Rate
- Retrieval Recall@K
- Latency (p50 / p95)

## 2. Evaluation Dataset
Minimum 200 questions:
- Enrollment periods (IEP/GEP/SEP)
- Penalties (Part B/D)
- Costs & IRMAA
- Coverage exclusions
- Edge-case exceptions

## 3. Automated Regression Tests
Run on:
- Document update
- Index rebuild
- Model change

Fail build if:
- Citation hit rate < 95%
- Any hallucinated numeric value detected

---