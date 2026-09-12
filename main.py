from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector
import os
import torch



app = FastAPI(title="Amazon Software Reviews Semantic Search")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


model = SentenceTransformer('all-MiniLM-L6-v2')

conn = psycopg2.connect(
    host="aws-0-eu-west-2.pooler.supabase.com",
    port=5432,
    dbname="postgres",
    user="postgres.kogrntulmflvtfgbbiqz",
    password=os.environ.get("DB_PASSWORD")
)
register_vector(conn)
class SearchQuery(BaseModel):
    query: str
    top_k: int = 5

@app.post("/search")
def search(payload: SearchQuery):
    query_embedding = model.encode(payload.query).tolist()
    cur = conn.cursor()
    cur.execute("""
        SELECT asin, title, review_text, rating,
               1 - (embedding <=> %s::vector) AS similarity
        FROM reviews
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """, (query_embedding, query_embedding, payload.top_k))
    results = cur.fetchall()
    cur.close()


    return [
        {"asin": r[0], "title": r[1], "text": r[2], "rating":[3], "similarity": round(r[4], 3)}
        for r in results
    ]
