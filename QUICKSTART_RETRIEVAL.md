# Quick Start: Improving Retrieval Quality

If your system is saying "I don't have enough information" for questions that ARE in the manual, follow these steps:

## Step 1: Update Your .env File

```bash
# Edit your .env file
nano .env
```

Add or update these lines:

```env
# Chunk settings (MUST rebuild index after changing)
CHUNK_SIZE=600
CHUNK_OVERLAP=300

# Retrieval settings (no rebuild needed)
TOP_K_RETRIEVAL=20
TOP_K_RERANK=8
ENABLE_QUERY_EXPANSION=true

# Search weights (no rebuild needed)
BM25_WEIGHT=0.3
VECTOR_WEIGHT=0.7
```

## Step 2: Rebuild the Index

**IMPORTANT**: You must rebuild the index if you changed `CHUNK_SIZE` or `CHUNK_OVERLAP`:

```bash
python scripts/build_index.py
```

This will take 10-20 minutes. Wait for it to complete.

## Step 3: Restart the Server

```bash
python main.py
```

## Step 4: Test

Try questions that previously failed. You should see much better results!

## What Changed?

| Setting | Old Value | New Value | Impact |
|---------|-----------|-----------|--------|
| **Chunk Size** | 1000 | 600 | Smaller, more precise chunks |
| **Chunk Overlap** | 200 | 300 | Better context continuity |
| **Top-K Retrieval** | 10 | 20 | Retrieve more candidates |
| **Top-K Rerank** | 5 | 8 | Use more evidence |
| **Query Expansion** | false | true | Add synonyms to search |
| **Vector Weight** | 0.5 | 0.7 | Favor semantic matching |

## Still Having Issues?

See `RETRIEVAL_QUALITY.md` for advanced troubleshooting and configuration options.

## Don't Want to Rebuild?

You can improve retrieval WITHOUT rebuilding by only changing:

```env
# These don't require index rebuild
TOP_K_RETRIEVAL=20
TOP_K_RERANK=8
ENABLE_QUERY_EXPANSION=true
BM25_WEIGHT=0.3
VECTOR_WEIGHT=0.7
```

Then just restart:

```bash
python main.py
```

This will help, but rebuilding with new chunk settings is recommended for best results.
