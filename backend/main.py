"""
Audio Intel — FastAPI Backend
===============================
• Supabase Authentication  (sign-up, sign-in, sign-out, get-current-user)
• Groq-powered RAG Chatbot (groq SDK + ChromaDB vector search)
"""

import os
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
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})

# ─────────────────────────────────────────────────────────────────────────────
# GROQ CLIENT (direct SDK)
# ─────────────────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "openai/gpt-oss-120b"

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT FOR RAG
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are **Audio Intel**, an expert AI assistant that recommends audio products \
(headphones, earphones, TWS, neckbands, etc.) to users.

## Rules
1. Answer ONLY about audio products. Politely decline unrelated questions.
2. Use the CONTEXT below (retrieved from the product database) as your primary \
   knowledge source. If the context is insufficient, say so — never fabricate specs.
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
def _format_docs(docs) -> str:
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


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Audio Intel API",
    version="1.0.0",
    description="Supabase Auth + RAG Chatbot powered by Groq & ChromaDB",
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
# CHATBOT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_filter_text(f: ChatFilters | None) -> str:
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


def _build_search_query(message: str, f: ChatFilters | None) -> str:
    extras = []
    if f:
        if f.product_type and f.product_type != "all":
            extras.append(f.product_type)
        if f.connectivity and f.connectivity != "all":
            extras.append(f.connectivity)
        if f.use_case and f.use_case != "general":
            extras.append(f.use_case)
        if f.brand and f.brand != "all":
            extras.append(f.brand)
    if extras:
        return f"{message} {' '.join(extras)}"
    return message


# ─────────────────────────────────────────────────────────────────────────────
# CHATBOT ENDPOINT (RAG with Groq SDK)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse, tags=["Chatbot"])
async def chat(body: ChatRequest):
    """
    RAG chatbot endpoint.
    1. Build an enriched query from the user message + filters.
    2. Retrieve relevant product chunks from ChromaDB.
    3. Feed context + filters + question into Groq LLM (direct SDK).
    4. Return the LLM answer + source metadata.
    """
    try:
        # 1. Build search query
        search_query = _build_search_query(body.message, body.filters)

        # 2. Retrieve from vectorstore
        docs = retriever.invoke(search_query)

        # 3. Format context & filters
        context_text = _format_docs(docs)
        filter_text = _build_filter_text(body.filters)

        # 4. Build the system prompt with context injected
        system_msg = SYSTEM_PROMPT.format(
            context=context_text,
            filters=filter_text,
        )

        # 5. Call Groq directly
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

        # 6. Collect source metadata for the frontend
        sources = []
        seen = set()
        for doc in docs:
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

        return ChatResponse(reply=reply, sources=sources)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Audio Intel API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    count = vectorstore._collection.count()
    return {
        "status": "healthy",
        "chroma_documents": count,
        "llm_model": GROQ_MODEL,
        "provider": "Groq",
    }


# ─────────────────────────────────────────────────────────────────────────────
# RUN WITH: uvicorn backend.main:app --reload --port 8000
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
