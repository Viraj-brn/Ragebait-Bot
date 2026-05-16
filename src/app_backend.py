"""
Master-Baiter Chatbot — FastAPI Backend
========================================
Serves both the chat API and the frontend UI.
Uses a local GGUF model via llama-cpp-python and
retrieves sarcastic context from PGVector (RAG).

Cloud-ready with:
  • Supabase Postgres (pgvector)
  • asyncio.Semaphore concurrency control
  • Clerk JWT authentication
"""

import os
import sys
import asyncio
import urllib.parse
import traceback
import warnings

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware


# Suppress noisy LangChain pending-deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", message=".*pending deprecation.*")
warnings.filterwarnings("ignore", message=".*Please use JSONB.*")
warnings.filterwarnings("ignore", module="langchain.*")

# ---------------------------------------------------------------------------
# 1. Environment & Configuration
# ---------------------------------------------------------------------------

# Resolve paths relative to the project root (one level up from src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
MODEL_PATH = os.path.join(BASE_DIR, "models", "ragebait_model.gguf")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Load .env from the project root so it works regardless of CWD
load_dotenv(dotenv_path=ENV_PATH)

app = FastAPI(title="Master-Baiter", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows your Vercel URL to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS, images)
#app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Jinja2 templates (for the chat HTML)
#templates = Jinja2Templates(directory=TEMPLATE_DIR)

# ---------------------------------------------------------------------------
# 2. Concurrency Control — The "Bouncer" (asyncio.Semaphore)
# ---------------------------------------------------------------------------
# Limits how many LLM requests can run at the same time.
# If the GPU can't handle 5 simultaneous requests, the semaphore
# puts overflow users in a queue instead of crashing with OOM.

MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_REQUESTS", "2"))
inference_semaphore = asyncio.Semaphore(MAX_CONCURRENT)

# Track how many requests are currently queued for UX feedback
_active_requests = 0
_active_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# 3. Clerk Authentication — JWT Verification
# ---------------------------------------------------------------------------

CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")

# We'll lazily fetch Clerk's JWKS (JSON Web Key Set) for token verification
_clerk_jwks = None
_clerk_jwks_lock = asyncio.Lock()


async def _get_clerk_jwks():
    """Fetch Clerk's JWKS for JWT signature verification (cached)."""
    global _clerk_jwks
    if _clerk_jwks is not None:
        return _clerk_jwks

    async with _clerk_jwks_lock:
        if _clerk_jwks is not None:
            return _clerk_jwks

        try:
            import httpx
            # Extract the Clerk frontend API domain from the publishable key
            # pk_test_xxx.clerk.accounts.dev → xxx.clerk.accounts.dev
            if CLERK_PUBLISHABLE_KEY.startswith("pk_test_") or CLERK_PUBLISHABLE_KEY.startswith("pk_live_"):
                clerk_domain = CLERK_PUBLISHABLE_KEY.split("_", 2)[2]
                jwks_url = f"https://{clerk_domain}/.well-known/jwks.json"
            else:
                print("[WARN] Invalid Clerk publishable key format. Auth disabled.")
                return None

            async with httpx.AsyncClient() as client:
                resp = await client.get(jwks_url)
                resp.raise_for_status()
                _clerk_jwks = resp.json()
                print(f"[OK] Clerk JWKS loaded from {jwks_url}")
                return _clerk_jwks
        except Exception as exc:
            print(f"[WARN] Failed to fetch Clerk JWKS: {exc}")
            return None


def _auth_enabled():
    """Check if Clerk auth is properly configured."""
    return (
        CLERK_PUBLISHABLE_KEY
        and not CLERK_PUBLISHABLE_KEY.startswith("pk_test_REPLACE")
        and CLERK_SECRET_KEY
        and not CLERK_SECRET_KEY.startswith("sk_test_REPLACE")
    )


async def verify_clerk_token(request: Request) -> dict | None:
    """
    Verify the Clerk JWT from the Authorization header.
    Returns the decoded payload or None if auth is disabled.
    Raises HTTPException(401) if token is invalid.
    """
    if not _auth_enabled():
        # Auth not configured — allow all requests (local dev mode)
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = auth_header.split(" ", 1)[1]

    try:
        import jwt
        from jwt import PyJWKClient

        jwks = await _get_clerk_jwks()
        if jwks is None:
            # Can't verify — fail open in dev, fail closed in prod
            return None

        # Build a PyJWKClient from the cached JWKS
        jwk_client = PyJWKClient("")
        jwk_client.jwk_set = jwt.api_jwk.PyJWKSet.from_dict(jwks)

        # Get the signing key from the token header
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        # Decode and verify
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk doesn't set aud by default
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please sign in again.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
    except Exception as exc:
        print(f"[WARN] Token verification error: {exc}")
        raise HTTPException(status_code=401, detail="Authentication failed.")


# ---------------------------------------------------------------------------
# 4. Database Connection (with safety checks)
# ---------------------------------------------------------------------------

vector_store = None  # Will be set below if DB is reachable


def _build_connection_string():
    """Build the SQLAlchemy connection string, or return None on failure."""
    raw_password = os.getenv("POSTGRES_PASSWORD")
    if raw_password is None:
        print("[WARN] POSTGRES_PASSWORD not set - vector store disabled.")
        return None

    encoded_password = urllib.parse.quote(raw_password, safe="")
    user = os.getenv("POSTGRES_USER", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB", "postgres")

    return (
        f"postgresql+psycopg2://{user}:{encoded_password}"
        f"@{host}:{port}/{db}"
    )


def _init_vector_store():
    """Try to connect to PGVector. Returns the store or None."""
    global vector_store
    conn_str = _build_connection_string()
    if conn_str is None:
        return

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import PGVector

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vector_store = PGVector(
            connection_string=conn_str,
            embedding_function=embeddings,
            collection_name="reddit_sarcasm",
        )
        print("[OK] Vector store connected!")
    except Exception as exc:
        print(f"[WARN] Vector store unavailable: {exc}")
        vector_store = None


_init_vector_store()

# ---------------------------------------------------------------------------
# 5. LLM Loading (with crash guard)
# ---------------------------------------------------------------------------

llm = None  # Will be set below if the model file exists


def _init_llm():
    """Load the GGUF model. Fails gracefully if file missing or OOM."""
    global llm
    if not os.path.isfile(MODEL_PATH):
        print(f"[WARN] Model not found at {MODEL_PATH} - LLM disabled.")
        return

    try:
        from llama_cpp import Llama

        print("Loading Model... (this may take a minute)")
        llm = Llama(
            model_path=MODEL_PATH,
            n_gpu_layers=10,   # Adjust down (e.g. 15) if you hit GPU OOM
            n_ctx=2048,
            verbose=False,
        )
        print("[OK] Model loaded!")
    except Exception as exc:
        print(f"[WARN] Model failed to load: {exc}")
        llm = None


_init_llm()

# ---------------------------------------------------------------------------
# 6. Request/Response Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    user_message: str


class ChatResponse(BaseModel):
    user: str
    rag_context: str
    bot_response: str
    queue_info: str | None = None


# ---------------------------------------------------------------------------
# 7. Routes
# ---------------------------------------------------------------------------
'''
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the chat frontend."""
    return templates.TemplateResponse(
        request=request,         # <--- Explicitly passing the request first
        name="index.html",       # <--- Explicitly naming the template
        context={                # <--- Explicitly naming the dictionary
            "request": request,
            "clerk_publishable_key": CLERK_PUBLISHABLE_KEY if _auth_enabled() else "",
            "auth_enabled": _auth_enabled(),
        }
    )
'''

@app.get("/favicon.ico")
async def favicon():
    """Serve a favicon to prevent 404 noise in logs."""
    return Response(status_code=204)


@app.get("/health")
async def health():
    """Quick health-check endpoint."""
    return {
        "status": "ok",
        "llm_loaded": llm is not None,
        "vector_store_connected": vector_store is not None,
        "auth_enabled": _auth_enabled(),
        "max_concurrent_requests": MAX_CONCURRENT,
    }


@app.post("/chat")
async def chat(body: ChatRequest, request: Request):
    """
    Accepts JSON  {"user_message": "..."}
    Returns JSON  {"user": "...", "rag_context": "...", "bot_response": "...", "queue_info": "..."}

    Protected by:
      1. Clerk JWT auth (if configured)
      2. asyncio.Semaphore (limits concurrent GPU usage)
    """
    # --- Auth Check ---
    await verify_clerk_token(request)

    user_text = body.user_message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Empty message.")

    # --- Concurrency: acquire the semaphore (the "bouncer") ---
    global _active_requests
    async with _active_lock:
        _active_requests += 1
        position = _active_requests

    queue_info = None
    if position > MAX_CONCURRENT:
        queue_info = f"You're #{position - MAX_CONCURRENT} in the queue. Hang tight!"

    try:
        async with inference_semaphore:
            # Run the blocking LLM + RAG work in a thread pool
            # so we don't block the async event loop
            import asyncio
            result = await asyncio.to_thread(_process_chat, user_text)
            return result | {"queue_info": queue_info}
    finally:
        async with _active_lock:
            _active_requests -= 1


def _process_chat(user_text: str) -> dict:
    """
    Synchronous chat processing (runs in a thread via asyncio.to_thread).
    Handles RAG retrieval + LLM generation.
    """
    try:
        # --- Step A: RAG retrieval ------------------------------------------
        rag_context = "No specific snark found, just be generically mean."
        if vector_store is not None:
            try:
                docs = vector_store.similarity_search(user_text, k=1)
                if docs:
                    rag_context = docs[0].page_content
            except Exception as exc:
                print(f"RAG retrieval error: {exc}")

        # --- Step B: LLM generation ----------------------------------------
        if llm is None:
            bot_response = (
                "My brain is still loading (or missing). "
                "Try again later, if you dare."
            )
        else:
            prompt = (
                "Below is an instruction that describes a task, paired with "
                "an input that provides further context. Write a response "
                "that appropriately completes the request.\n\n"
                f"### Instruction:\n{user_text}\n\n"
                f"### Input:\n{rag_context}\n\n"
                "### Response:\n"
            )

            output = llm(
                prompt,
                max_tokens=150,
                stop=["###", "\n\n"],
                temperature=0.7,
            )
            bot_response = output["choices"][0]["text"].strip()

        return {
            "user": user_text,
            "rag_context": rag_context,
            "bot_response": bot_response,
        }

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 8. Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    # Debug mode for local development; disable in production
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5000,
    )