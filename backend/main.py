"""
Audio Intel — FastAPI Backend (Advanced RAG)
=============================================
• Supabase Authentication  (sign-up, sign-in, sign-out, get-current-user)
• Advanced RAG Chatbot:
    ① Query Rewriting   — Groq rewrites user query into search-optimised keywords
    ② Hybrid Search     — Semantic (ChromaDB) + Keyword (BM25) via Reciprocal Rank Fusion
    ③ LLM Re-ranking    — Groq scores each candidate's relevance, top-K selected
    ④ Generation        — Groq produces the final answer from re-ranked context
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# ─── Supabase SDK ────────────────────────────────────────────────────────────
from supabase import create_client, Client as SupabaseClient

# ─── Groq SDK (direct, no LangChain wrapper) ────────────────────────────────
from groq import Groq

# ─── LangChain only for ChromaDB retrieval ───────────────────────────────────
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

# ─── BM25 for keyword search ────────────────────────────────────────────────
from rank_bm25 import BM25Okapi

# ─────────────────────────────────────────────────────────────────────────────
# ENV VARIABLES
# ─────────────────────────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing from .env")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("SUPABASE_URL / SUPABASE_ANON_KEY missing from .env")

# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE CLIENT
# ─────────────────────────────────────────────────────────────────────────────
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ─────────────────────────────────────────────────────────────────────────────
# CHROMA VECTORSTORE (already persisted)
# ─────────────────────────────────────────────────────────────────────────────
CHROMA_DIR = str(Path(__file__).resolve().parent.parent / "chroma_db")
COLLECTION_NAME = "products_collection"

embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
vectorstore = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings,
    collection_name=COLLECTION_NAME,
)

# ─────────────────────────────────────────────────────────────────────────────
# BM25 INDEX (built once at startup from ChromaDB contents)
# ─────────────────────────────────────────────────────────────────────────────
print("⏳ Building BM25 index from ChromaDB collection …")

_collection = vectorstore._collection
_all_data   = _collection.get(include=["documents", "metadatas"])
_all_docs   = _all_data["documents"]   # list[str]
_all_metas  = _all_data["metadatas"]   # list[dict]
_all_ids    = _all_data["ids"]         # list[str]


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokeniser, lowercased."""
    return re.findall(r"\w+", text.lower())


_tokenized_corpus = [_tokenize(doc) for doc in _all_docs]
bm25_index = BM25Okapi(_tokenized_corpus)

print(f"✅ BM25 index ready — {len(_all_docs)} chunks indexed.")

# ─────────────────────────────────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_MODEL_FAST = "llama-3.1-8b-instant"  # lightweight model for rewrite + rerank


# ═══════════════════════════════════════════════════════════════════════════════
#  ADVANCED RAG PIPELINE COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════

# ──────────────── ① QUERY REWRITING ──────────────────────────────────────────

QUERY_REWRITE_PROMPT = """\
You are a search-query optimiser for an audio-products database.

Given the user's conversational question and optional filter preferences,
rewrite it into 2-3 short, keyword-rich search queries that would retrieve
the most relevant products from a vector database of headphones, earphones,
TWS, and neckbands.

Rules:
- Output ONLY a JSON array of strings, e.g. ["query1", "query2"]
- Include product attributes: type, brand, price range, use-case, connectivity
- Expand abbreviations (ANC → active noise cancellation)
- Do NOT include any explanation, only the JSON array.

User's filter context: {filters}
User's question: {question}
"""


def rewrite_query(question: str, filter_text: str) -> list[str]:
    """Use a fast LLM to expand the user question into search-optimised queries."""
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL_FAST,
            messages=[
                {
                    "role": "system",
                    "content": QUERY_REWRITE_PROMPT.format(
                        filters=filter_text, question=question
                    ),
                },
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=256,
        )
        raw = resp.choices[0].message.content.strip()
        # Parse the JSON array from the response
        # Handle cases where LLM wraps in ```json ... ```
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*$", "", raw)
        queries = json.loads(raw)
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            return queries
    except Exception:
        pass
    # Fallback: use original question
    return [question]


# ──────────────── ② HYBRID SEARCH ────────────────────────────────────────────

def _semantic_search(query: str, k: int = 10) -> list[Document]:
    """ChromaDB cosine-similarity search."""
    return vectorstore.similarity_search(query, k=k)


def _bm25_search(query: str, k: int = 10) -> list[Document]:
    """BM25 keyword search over the same corpus."""
    tokens = _tokenize(query)
    scores = bm25_index.get_scores(tokens)

    # Get top-k indices
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:  # skip zero-score results
            results.append(
                Document(
                    page_content=_all_docs[idx],
                    metadata=_all_metas[idx],
                )
            )
    return results


def reciprocal_rank_fusion(
    result_lists: list[list[Document]], k: int = 60
) -> list[Document]:
    """
    Reciprocal Rank Fusion (RRF) to merge multiple ranked result lists.
    Each document gets score = Σ 1/(k + rank_i) across all lists.
    De-duplicates by product_name.
    """
    doc_scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            # Use product_name as the unique key (more reliable than page_content hash)
            key = doc.metadata.get("product_name", doc.page_content[:80])
            if key not in doc_map:
                doc_map[key] = doc
                doc_scores[key] = 0.0
            doc_scores[key] += 1.0 / (k + rank + 1)

    # Sort by fused score descending
    ranked_keys = sorted(doc_scores, key=lambda x: doc_scores[x], reverse=True)
    return [doc_map[k] for k in ranked_keys]


def hybrid_search(queries: list[str], k_per_query: int = 10, final_k: int = 15) -> list[Document]:
    """
    Run semantic + BM25 for each rewritten query, then fuse all results.
    """
    all_result_lists = []

    for q in queries:
        sem_results = _semantic_search(q, k=k_per_query)
        bm25_results = _bm25_search(q, k=k_per_query)
        all_result_lists.append(sem_results)
        all_result_lists.append(bm25_results)

    fused = reciprocal_rank_fusion(all_result_lists)
    return fused[:final_k]


# ──────────────── ③ LLM RE-RANKING ───────────────────────────────────────────

RERANK_PROMPT = """\
You are a relevance judge for an audio-products recommendation system.

Given a user's QUERY and a list of CANDIDATE products, score each candidate's
relevance to the query on a scale of 0-10 (10 = perfect match).

Consider: product type match, connectivity match, budget fit, use-case match,
brand preference, and how well the product description answers the query.

Output ONLY a JSON array of objects: [{{"index": 0, "score": 8}}, ...]
No explanation, just the JSON array.

QUERY: {query}
FILTERS: {filters}

CANDIDATES:
{candidates}
"""


def rerank_documents(
    query: str, filter_text: str, docs: list[Document], top_k: int = 5
) -> list[Document]:
    """Use a fast LLM to score & re-rank the retrieved candidates."""
    if len(docs) <= top_k:
        return docs

    # Format candidates for the LLM
    candidates_text = ""
    for i, doc in enumerate(docs):
        meta = doc.metadata
        candidates_text += (
            f"[{i}] {meta.get('product_name', 'N/A')} | "
            f"Price: {meta.get('price', 'N/A')} | "
            f"Type: {meta.get('type', 'N/A')} | "
            f"Connectivity: {meta.get('connectivity', 'N/A')}\n"
            f"    {doc.page_content[:200]}\n\n"
        )

    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL_FAST,
            messages=[
                {
                    "role": "system",
                    "content": RERANK_PROMPT.format(
                        query=query,
                        filters=filter_text,
                        candidates=candidates_text,
                    ),
                },
                {"role": "user", "content": "Score each candidate now."},
            ],
            temperature=0.0,
            max_tokens=512,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*$", "", raw)
        scores = json.loads(raw)

        if isinstance(scores, list):
            # Build index→score map
            score_map = {}
            for item in scores:
                if isinstance(item, dict) and "index" in item and "score" in item:
                    score_map[item["index"]] = item["score"]

            # Sort docs by score descending
            indexed_docs = [(i, doc) for i, doc in enumerate(docs)]
            indexed_docs.sort(
                key=lambda x: score_map.get(x[0], 0), reverse=True
            )
            return [doc for _, doc in indexed_docs[:top_k]]

    except Exception:
        pass

    # Fallback: return first top_k (original RRF order)
    return docs[:top_k]


# ═══════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT FOR FINAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
You are **Audio Intel**, an expert AI assistant that recommends audio products \
(headphones, earphones, TWS, neckbands, etc.) to users.

## Rules
1. Answer ONLY about audio products. Politely decline unrelated questions.
2. Use the CONTEXT below (retrieved and re-ranked from the product database) as \
   your primary knowledge source. If the context is insufficient, say so — never \
   fabricate specs.
3. When recommending products always include:
   • Product name
   • Price (from metadata)
   • Type / Connectivity
   • A short reason why it suits the user
   • The product URL so the user can buy it.
4. If filter preferences (type, connectivity, budget, use-case, brand) are given \
   inside <filters>, incorporate them as hard constraints.
5. Keep answers concise, friendly, and well-formatted with markdown.
6. If multiple products match, provide a ranked list (top 3-5).

<filters>
{filters}
</filters>

<context>
{context}
</context>
"""


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: format retrieved docs for context
# ─────────────────────────────────────────────────────────────────────────────
def _format_docs(docs: list[Document]) -> str:
    formatted = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        formatted.append(
            f"[{i}] {meta.get('product_name', 'N/A')} | "
            f"Price: {meta.get('price', 'N/A')} | "
            f"Type: {meta.get('type', 'N/A')} | "
            f"Connectivity: {meta.get('connectivity', 'N/A')} | "
            f"URL: {meta.get('url', 'N/A')}\n"
            f"    {doc.page_content[:400]}"
        )
    return "\n\n".join(formatted)


def _build_filter_text(f: "ChatFilters | None") -> str:
    if f is None:
        return "No specific filters applied."
    parts = []
    if f.product_type and f.product_type != "all":
        parts.append(f"Product type: {f.product_type}")
    if f.connectivity and f.connectivity != "all":
        parts.append(f"Connectivity: {f.connectivity}")
    if f.budget is not None and f.budget < 500:
        parts.append(f"Max budget: ${f.budget}")
    if f.use_case and f.use_case != "general":
        parts.append(f"Use case: {f.use_case}")
    if f.brand and f.brand != "all":
        parts.append(f"Preferred brand: {f.brand}")
    return "\n".join(parts) if parts else "No specific filters applied."


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Audio Intel API",
    version="2.0.0",
    description="Supabase Auth + Advanced RAG Chatbot (Hybrid Search, Re-ranking, Query Rewriting)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────────────────────────

# --- Auth ---
class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    full_name: Optional[str] = None

# --- Chat ---
class ChatFilters(BaseModel):
    product_type: Optional[str] = "all"
    connectivity: Optional[str] = "all"
    budget: Optional[int] = 500
    use_case: Optional[str] = "general"
    brand: Optional[str] = "all"

class ChatRequest(BaseModel):
    message: str
    filters: Optional[ChatFilters] = None

class ChatResponse(BaseModel):
    reply: str
    sources: list[dict] = []
    debug: Optional[dict] = None   # optional: pipeline telemetry


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    return parts[1]


# ─────────────────────────────────────────────────────────────────────────────
# AUTH ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/auth/signup", response_model=AuthResponse, tags=["Authentication"])
async def sign_up(body: SignUpRequest):
    """Register a new user via Supabase email/password auth."""
    try:
        res = supabase.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
                "options": {
                    "data": {"full_name": body.full_name or ""},
                },
            }
        )
        session = res.session
        user = res.user

        if not session:
            return AuthResponse(
                access_token="",
                refresh_token="",
                user_id=user.id if user else "",
                email=body.email,
                full_name=body.full_name,
            )

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user_id=user.id,
            email=user.email,
            full_name=body.full_name,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/signin", response_model=AuthResponse, tags=["Authentication"])
async def sign_in(body: SignInRequest):
    """Sign in an existing user with email + password."""
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        session = res.session
        user = res.user
        user_meta = user.user_metadata or {}
        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user_id=user.id,
            email=user.email,
            full_name=user_meta.get("full_name"),
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/auth/signout", tags=["Authentication"])
async def sign_out(token: str = Depends(_extract_token)):
    """Sign out the current user."""
    try:
        supabase.auth.sign_out()
        return {"message": "Signed out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/me", tags=["Authentication"])
async def get_current_user(token: str = Depends(_extract_token)):
    """Return the currently authenticated user's profile."""
    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        user_meta = user.user_metadata or {}
        return {
            "user_id": user.id,
            "email": user.email,
            "full_name": user_meta.get("full_name"),
            "created_at": str(user.created_at),
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# CHATBOT ENDPOINT — ADVANCED RAG PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse, tags=["Chatbot"])
async def chat(body: ChatRequest):
    """
    Advanced RAG pipeline:
      ① Query Rewriting   → Groq rewrites user query into search keywords
      ② Hybrid Search     → Semantic (ChromaDB) + Keyword (BM25) + RRF
      ③ LLM Re-ranking    → Groq scores & sorts candidates by relevance
      ④ Generation        → Groq generates answer from top re-ranked context
    """
    try:
        filter_text = _build_filter_text(body.filters)

        # ─── ① QUERY REWRITING ───────────────────────────────────────────
        rewritten_queries = rewrite_query(body.message, filter_text)

        # ─── ② HYBRID SEARCH (Semantic + BM25 + RRF) ─────────────────────
        hybrid_results = hybrid_search(
            queries=rewritten_queries, k_per_query=10, final_k=15
        )

        # ─── ③ LLM RE-RANKING ────────────────────────────────────────────
        reranked_docs = rerank_documents(
            query=body.message,
            filter_text=filter_text,
            docs=hybrid_results,
            top_k=5,
        )

        # ─── ④ GENERATION ────────────────────────────────────────────────
        context_text = _format_docs(reranked_docs)

        system_msg = SYSTEM_PROMPT.format(
            context=context_text,
            filters=filter_text,
        )

        chat_completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": body.message},
            ],
            temperature=0.5,
            max_tokens=1024,
        )

        reply = chat_completion.choices[0].message.content

        # ─── Collect source metadata ─────────────────────────────────────
        sources = []
        seen = set()
        for doc in reranked_docs:
            name = doc.metadata.get("product_name", "")
            if name and name not in seen:
                seen.add(name)
                sources.append(
                    {
                        "product_name": name,
                        "price": doc.metadata.get("price"),
                        "type": doc.metadata.get("type"),
                        "connectivity": doc.metadata.get("connectivity"),
                        "url": doc.metadata.get("url"),
                    }
                )

        # ─── Debug telemetry (helpful for development) ────────────────────
        debug_info = {
            "rewritten_queries": rewritten_queries,
            "hybrid_candidates": len(hybrid_results),
            "reranked_top_k": len(reranked_docs),
        }

        return ChatResponse(reply=reply, sources=sources, debug=debug_info)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Audio Intel API",
        "version": "2.0 — Advanced RAG",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    count = vectorstore._collection.count()
    return {
        "status": "healthy",
        "rag_type": "Advanced RAG (Hybrid Search + Re-ranking + Query Rewriting)",
        "chroma_documents": count,
        "bm25_indexed": len(_all_docs),
        "llm_model_main": GROQ_MODEL,
        "llm_model_fast": GROQ_MODEL_FAST,
        "provider": "Groq",
    }


# ─────────────────────────────────────────────────────────────────────────────
# RUN WITH: uvicorn backend.main:app --reload --port 8000
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
