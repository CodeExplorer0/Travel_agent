import os
import json
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from data.reddit_scraper import scrape_relevant_data

import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini embedding model name (latest as of May 2025)
GEMINI_EMBED_MODEL = "models/embedding-001"  # or use "models/gemini-embedding-exp-03-07" if available

# Initialize Gemini client
genai.configure(api_key=GEMINI_API_KEY)
client = genai

# Pinecone setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "travel-recs"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=768,  # Gemini embeddings are 768-dim for "embedding-001"
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
index = pc.Index(index_name)

def get_gemini_embedding(text):
    """Get embedding vector from Gemini API."""
    result = client.embed_content(
        model=GEMINI_EMBED_MODEL,
        content=text
    )
    # REST API returns dict with 'embedding'
    if "embedding" in result:
        return result["embedding"]
    elif hasattr(result, "embedding"):
        return result.embedding
    raise RuntimeError("Unknown Gemini embedding response format")

def get_reddit_embeddings():
    """Convert Reddit posts to vectors using Gemini embeddings"""
    try:
        with open("data/relevant_posts.json") as f:
            posts = json.load(f)
        embeddings = []
        for post in posts:
            text = f"{post['title']} {post['selftext']}".replace("\n", " ")[:2000]
            emb = get_gemini_embedding(text)
            embeddings.append({
                "id": str(post['url']),
                "values": emb,
                "metadata": post
            })
        return embeddings
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

def upsert_reddit_data():
    """Store Reddit posts in Pinecone with embeddings"""
    if not os.path.exists("data/relevant_posts.json"):
        scrape_relevant_data()
    vectors = get_reddit_embeddings()
    if vectors:
        index.upsert(vectors)
        print(f"Upserted {len(vectors)} Reddit posts")

def get_similar_recommendations(user_prompt):
    """Retrieve relevant Reddit posts for a user query"""
    try:
        query_vec = get_gemini_embedding(user_prompt)
        results = index.query(vector=query_vec, top_k=5, include_metadata=True)
        return [match["metadata"] for match in results["matches"]]
    except Exception as e:
        print(f"Query error: {e}")
        return []

def store_itinerary(itinerary):
    """Store itinerary vector for future retrieval"""
    try:
        text = json.dumps(itinerary)
        emb = get_gemini_embedding(text)
        index.upsert([{
            "id": f"itinerary-{hash(text)}",
            "values": emb,
            "metadata": {"itinerary": itinerary}
        }])
    except Exception as e:
        print(f"Error storing itinerary: {e}")
