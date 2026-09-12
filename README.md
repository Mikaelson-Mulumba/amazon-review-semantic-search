# Amazon Software Reviews — Semantic Search API

A full-stack semantic search engine over 45,000+ real Amazon software product reviews.
Search by *meaning*, not keywords — a query like "app keeps crashing after update" surfaces
relevant reviews even when they use completely different words ("frozen", "won't open",
"broken since latest version").

**Live demo:** https://mikaelson-mulumba.github.io/amazon-review-semantic-search/

**Live API:** https://amazon-review-semantic-search-api.onrender.com/docs

---

## Table of Contents

1. Overview
2. Why This Project
3. Architecture
4. Tech Stack
5. Dataset
6. Pipeline Walkthrough
7. Real Challenges Solved
8. Running It Locally
9. API Reference
10. Project Structure
11. Future Improvements
12. Acknowledgements

---

## 1. Overview

Traditional keyword search fails the moment a user describes a problem in their own words.
If someone searches "won't open after updating" but a review says "crashes on launch since
the patch," a keyword search finds nothing — even though both describe the exact same issue.

This project solves that by converting review text into numerical vector embeddings that
capture *meaning* rather than exact wording. Reviews that mean similar things end up
mathematically close to each other in vector space, regardless of the specific words used.
A search query is embedded the same way, and the system returns the reviews whose meaning
is closest to the query — genuine semantic search, not string matching.

## 2. Why This Project

This was built as a hands-on, end-to-end portfolio project during a transition toward data
science and AI engineering work. The goal was not just to train a model in a notebook, but
to build something that goes all the way from raw data to a live, publicly accessible product:

    raw data → cleaning → embeddings → vector database → API → frontend → deployment

Each of these stages surfaces genuinely different engineering skills, and the project was
deliberately built to touch all of them rather than stopping at "it works on my machine."

## 3. Architecture

    Raw dataset (570M Amazon reviews, McAuley Lab / UCSD)
        |  streamed, sampled, cleaned (pandas)
        v
    Cleaned dataset (45,121 reviews)
        |  embedded (sentence-transformers, all-MiniLM-L6-v2)
        v
    Vector embeddings (384-dimensional)
        |  stored in
        v
    PostgreSQL + pgvector (Supabase, managed cloud instance)
        |  queried via cosine similarity
        v
    FastAPI search endpoint (deployed on Render)
        |  consumed by
        v
    HTML / CSS / JS frontend

## 4. Tech Stack

Data processing:
  - Python, Pandas
  - Hugging Face `datasets` library (streaming mode, to avoid downloading the full
    570M-review dataset)

Embeddings:
  - sentence-transformers, model: all-MiniLM-L6-v2
  - 384-dimensional embeddings, CPU-only inference (no GPU required)

Vector storage:
  - PostgreSQL with the pgvector extension
  - Local development: Docker container (pgvector/pgvector:pg16)
  - Production: Supabase (managed Postgres, free tier)

API:
  - FastAPI
  - Pydantic request validation
  - psycopg2 + pgvector Python adapter for database access
  - Deployed on Render (free tier)

Frontend:
  - Vanilla HTML, CSS, and JavaScript (no framework, no build step)
  - Calls the live API directly via fetch()

## 5. Dataset

Source: Amazon Reviews 2023 (Software category)
Published by: McAuley Lab, UC San Diego
Full dataset size: ~570 million reviews across all categories
Used in this project: ~50,000 raw reviews from the Software category, streamed and sampled
  (not downloaded in full) to stay within local disk and memory constraints

After cleaning (deduplication and removal of near-empty reviews), the final working dataset
contains 45,121 reviews spanning January 2000 to March 2023.

Citation:
  McAuley Lab, "Amazon Reviews 2023"
  https://amazon-reviews-2023.github.io/

## 6. Pipeline Walkthrough

Step 1 — Data Acquisition & Cleaning
  - Streamed the Software category from Hugging Face (avoiding a full download of a
    570M-review dataset)
  - Saved a 50,000-review sample to a local Parquet file for fully offline development
  - Removed 65 exact-duplicate reviews and ~4,800 near-empty reviews (under 10 characters)
  - Cleaned text formatting: stripped HTML tags/entities, collapsed whitespace
  - Final dataset: 45,121 reviews

Step 2 — Exploratory Data Analysis
  - Rating distribution: heavily skewed toward 5-star (a well-known pattern in review data)
  - Review length distribution: right-skewed, median 79 characters, mean 173 characters
  - Visualizations saved for documentation (eda_overview.png)

Step 3 — Text Preprocessing
  - Combined review title + body into a single field before embedding, giving the model
    more context per review

Step 4 — Embedding Generation
  - Used sentence-transformers (all-MiniLM-L6-v2) to convert each review into a
    384-dimensional vector
  - Batched encoding (batch_size=64) for efficiency
  - Full 45,121-review batch encoded in a few minutes on CPU only

Step 5 — Vector Database Setup
  - Initially stood up PostgreSQL + pgvector locally via Docker
  - Created a `reviews` table storing review metadata alongside its embedding vector
  - Indexed the embedding column (ivfflat, cosine distance) for efficient similarity search

Step 6 — Semantic Search Logic
  - Query text is embedded using the same model
  - pgvector's `<=>` cosine distance operator ranks all reviews by similarity to the query
  - Returns the top-K most semantically similar reviews

Step 7 — API Layer
  - Wrapped the search logic in a FastAPI `/search` POST endpoint
  - Pydantic model validates incoming requests (query string + optional top_k)
  - CORS middleware enabled so the frontend can call the API directly from the browser

Step 8 — Frontend
  - Single-page HTML/JS interface: a search box, a results list, and similarity scores
    shown as percentage matches

Step 9 — Cloud Migration & Deployment
  - Migrated the local Docker database to Supabase (managed Postgres + pgvector)
  - Deployed the FastAPI backend to Render
  - Connected the frontend to the live, public API endpoint

## 7. Real Challenges Solved

This section documents actual problems encountered and fixed during development —
included deliberately, since working through real infrastructure issues is a core part
of what this project demonstrates.

  - Hugging Face's `datasets` library (v4.0+) dropped support for script-based dataset
    loading mid-project, breaking the originally documented way to load Amazon Reviews 2023.
    Fixed by pinning `datasets==2.21.0`, which still supports the legacy loading script.

  - PyTorch's default install pulls in NVIDIA CUDA/cuDNN packages (several GB) even on a
    machine with no GPU. Fixed by installing the CPU-only build via PyTorch's dedicated
    CPU package index.

  - Ran out of local disk space mid-install due to the above issue; resolved by clearing
    space and using `pip cache purge` before reinstalling with the correct CPU-only wheel.

  - A direct connection to Supabase failed with "Network is unreachable" — diagnosed as an
    IPv6-only connection attempt on a network without outbound IPv6 support. Fixed by
    switching to Supabase's Session Pooler, which proxies connections over IPv4.

  - GitHub rejected password-based authentication for git push (deprecated for security).
    Fixed by generating a Personal Access Token with `repo` scope and using it in place of
    a password.

  - The deployed API exceeded Render's free-tier 512MB memory limit when loading the
    embedding model alongside FastAPI and PyTorch. Fixed by calling
    `torch.set_num_threads(1)` before model load, reducing memory overhead enough to fit
    within the free tier.

  - A `pgvector` connection established via psycopg2 didn't automatically know how to
    serialize/deserialize vector types in a fresh process context, causing 500 errors that
    didn't appear in local testing. Fixed by explicitly calling
    `register_vector(conn)` after each new database connection.

## 8. Running It Locally

Prerequisites:
  - Python 3.10+
  - A PostgreSQL database with the pgvector extension enabled (local Docker or Supabase)

Setup:

    pip install -r requirements.txt
    export DB_PASSWORD="your_database_password"
    uvicorn main:app --reload

Then either:
  - Open index.html directly in a browser, or
  - Visit http://localhost:8000/docs for the interactive Swagger UI

## 9. API Reference

POST /search

Request body:

    {
      "query": "app keeps crashing after update",
      "top_k": 5
    }

Response:

    [
      {
        "asin": "B0094BB4TW",
        "title": "crashing",
        "text": "It worked fine until it updated.",
        "rating": 1.0,
        "similarity": 0.674
      },
      ...
    ]

## 10. Project Structure

    .
    ├── main.py                          FastAPI application (search API)
    ├── index.html                       Frontend (search interface)
    ├── requirements.txt                 Python dependencies
    ├── migrate_to_supabase.py           One-time script: local DB -> Supabase
    ├── amazon_software_reviews_analysis.ipynb   Data cleaning, EDA, embedding generation
    ├── eda_overview.png                 Saved exploratory analysis charts
    ├── .gitignore
    └── README.md

## 11. Future Improvements

  - Hybrid search combining keyword and semantic ranking
  - Filtering by rating, date range, or verified purchase status
  - A larger embedding model for improved semantic accuracy (tradeoff: slower, more memory)
  - Caching frequent queries to reduce repeated embedding computation
  - Upgrading the hosting tier to eliminate free-tier cold-start delays

## 12. Acknowledgements

  - Dataset: Amazon Reviews 2023, McAuley Lab, UC San Diego
  - Embedding model: sentence-transformers/all-MiniLM-L6-v2
  - Built by Mulumba Mikaelson Kalya Kiwanuka
