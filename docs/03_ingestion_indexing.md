# Ingestion & Indexing Architecture – Medicare Handbook

## 1. Ingestion Pipeline
PDF → Structure Parser → Rule Extractor → Chunker → Index Builder

## 2. Chunking Rules
- One rule per chunk
- Preserve if/when/unless clauses
- Tables extracted as JSON

## 3. Index Strategy
- BM25 for terminology
- Vector index for semantic intent
- Metadata filters for doc_version, part, rule_type

## 4. Re-index Policy
- Any CMS update triggers full re-index
- Old versions remain queryable but inactive

---