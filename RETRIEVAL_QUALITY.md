# Retrieval Quality Improvement Guide

This guide explains how to improve retrieval quality (ability to find relevant information from the Medicare manual).

## Problem: Low Response Rate

If the system frequently says "I don't have enough information" for questions that ARE in the manual, you have a retrieval quality problem.

## Solutions Implemented

### 1. **Optimized Chunk Size**
- **Changed**: 1000 → 600 characters
- **Why**: Smaller chunks = more precise matching
- **Impact**: Better granularity, less noise per chunk

### 2. **Increased Chunk Overlap**
- **Changed**: 200 → 300 characters
- **Why**: Prevents information loss at chunk boundaries
- **Impact**: Context continuity across chunks

### 3. **Increased Top-K Retrieval**
- **Changed**: 10 → 20 chunks
- **Why**: Cast a wider net to catch relevant information
- **Impact**: Better recall (finding the right info)

### 4. **Increased Top-K Reranking**
- **Changed**: 5 → 8 chunks
- **Why**: More evidence for the generator to work with
- **Impact**: More comprehensive answers

### 5. **Enabled Query Expansion**
- **Changed**: false → true by default
- **Why**: Adds synonyms and related terms to search
- **Impact**: Better matching despite different wording

### 6. **Adjusted Hybrid Search Weights**
- **BM25 Weight**: 0.5 → 0.3 (keyword matching)
- **Vector Weight**: 0.5 → 0.7 (semantic matching)
- **Why**: Medicare questions are often semantic, not exact keyword matches
- **Impact**: Better semantic understanding

### 7. **Improved Generator Prompt**
- **Changed**: More explicit instructions to use evidence
- **Why**: Previous prompt was too conservative
- **Impact**: Generator uses evidence more confidently

### 8. **Enhanced Query Expansion**
- **Changed**: Simple rewrite → Synonym expansion
- **Why**: Better search term coverage
- **Impact**: Finds content with different terminology

## Configuration for Different Needs

### Maximum Recall (Find everything possible)
```env
CHUNK_SIZE=500
CHUNK_OVERLAP=350
TOP_K_RETRIEVAL=30
TOP_K_RERANK=12
ENABLE_QUERY_EXPANSION=true
BM25_WEIGHT=0.2
VECTOR_WEIGHT=0.8
```

**Use when**: Retrieval quality is poor
**Trade-off**: Slower, more expensive

### Balanced (Recommended)
```env
CHUNK_SIZE=600
CHUNK_OVERLAP=300
TOP_K_RETRIEVAL=20
TOP_K_RERANK=8
ENABLE_QUERY_EXPANSION=true
BM25_WEIGHT=0.3
VECTOR_WEIGHT=0.7
```

**Use when**: Normal operation
**Trade-off**: Good balance of speed and quality

### Maximum Precision (Exact matches only)
```env
CHUNK_SIZE=800
CHUNK_OVERLAP=200
TOP_K_RETRIEVAL=10
TOP_K_RERANK=5
ENABLE_QUERY_EXPANSION=false
BM25_WEIGHT=0.7
VECTOR_WEIGHT=0.3
```

**Use when**: You want only exact, high-confidence matches
**Trade-off**: May miss relevant information

## How to Rebuild Index with New Settings

After changing chunk size or overlap, you MUST rebuild the index:

```bash
# 1. Update .env with new settings
nano .env

# 2. Rebuild index
python scripts/build_index.py

# 3. Restart server
python main.py
```

**Note**: Rebuilding index may take 10-20 minutes due to embedding generation.

## Troubleshooting

### Still getting "I don't have enough information"

1. **Check if info is really in the manual**
   - Verify the content exists in `docs/medicare_manual.pdf`

2. **Try query expansion**
   ```env
   ENABLE_QUERY_EXPANSION=true
   ```

3. **Increase retrieval**
   ```env
   TOP_K_RETRIEVAL=30
   TOP_K_RERANK=12
   ```

4. **Adjust weights for semantic search**
   ```env
   BM25_WEIGHT=0.2
   VECTOR_WEIGHT=0.8
   ```

5. **Check query phrasing**
   - Try rephrasing the question
   - Use official Medicare terminology

### Getting wrong/irrelevant answers

1. **Increase precision with smaller chunks**
   ```env
   CHUNK_SIZE=500
   ```

2. **Increase BM25 weight for keyword matching**
   ```env
   BM25_WEIGHT=0.5
   VECTOR_WEIGHT=0.5
   ```

3. **Enable verification**
   ```env
   ENABLE_VERIFICATION=true
   ```

### Responses too slow after optimization

1. **Reduce retrieval**
   ```env
   TOP_K_RETRIEVAL=15
   TOP_K_RERANK=6
   ```

2. **Disable query expansion for speed**
   ```env
   ENABLE_QUERY_EXPANSION=false
   ```

## Monitoring Retrieval Quality

Track these metrics:

1. **Response Rate**: % of questions answered vs "no information"
2. **Citation Quality**: Are citations relevant?
3. **User Satisfaction**: Are users finding what they need?

## Best Practices

1. **Always enable query expansion** - Minimal speed impact, significant quality gain
2. **Use larger overlap** - Prevents context loss
3. **Start with semantic weights** - Vector 0.7, BM25 0.3
4. **Rebuild index after chunk changes** - Critical for consistency
5. **Test with real queries** - Validate improvements with actual use cases

## Technical Details

### How Retrieval Works

1. **Query Expansion**: Add synonyms and related terms
2. **BM25 Search**: Keyword-based matching (exact terms)
3. **Vector Search**: Semantic embedding similarity
4. **Hybrid Scoring**: Combine BM25 and vector scores with weights
5. **Filtering**: Apply metadata filters (doc_version, etc.)
6. **Reranking**: Select best evidence chunks
7. **Generation**: Create answer from top chunks

### Why Smaller Chunks Help

- **Precision**: Each chunk contains less noise
- **Granularity**: More focused information per chunk
- **Scoring**: Better score differentiation
- **Citation**: More accurate page references

### Why Overlap Matters

- **Context**: Prevents cutting mid-sentence
- **Completeness**: Ensures full concepts are captured
- **Recall**: Same info might be retrieved from multiple chunks

## Example Improvements

### Before Optimization
**Query**: "What is the Part B penalty?"
**Result**: "I don't have enough information"
**Reason**: Query too generic, not enough retrieval

### After Optimization
**Query**: "What is the Part B penalty?"
**Expanded**: "What is the Part B late enrollment penalty premium surcharge cost"
**Retrieved**: 20 chunks instead of 10
**Result**: Full answer with citations
**Reason**: Better query expansion + more retrieval

## Conclusion

The key to good retrieval quality is:
1. ✅ Small chunks (600 chars)
2. ✅ Large overlap (300 chars)
3. ✅ More retrieval (20 top-k)
4. ✅ Query expansion (enabled)
5. ✅ Semantic weights (0.7 vector, 0.3 BM25)

These settings significantly improve the system's ability to find and use information from the manual.
