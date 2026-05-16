<div align="center">
  <h1>Frien-emy (formerly Ragebait Bot)</h1>
  <p><i>"Who needs enemies when you have friends like these? Make this bot your friend."</i></p>
</div>

## 🚀 Live Demo
**Experience the bot live:** [https://ragebot-ui.vercel.app/](https://ragebot-ui.vercel.app/)

## 📝 Overview
**Frien-emy** is an end-to-end, full-stack AI chat application designed to provide sarcastically entertaining responses. Powered by a customized Retrieval-Augmented Generation (RAG) pipeline and a locally-run LLM, this project demonstrates production-grade application development, scalable cloud-native containerization, and robust AI deployment strategies.

## ✨ Technical Highlights for Recruiters

- **Containerized Cloud Deployment (Hugging Face Spaces)**
  The backend is deployed as a custom Docker container on Hugging Face Spaces, ensuring 24/7 high-availability and zero queue times. Massive model weights (5GB) are securely and dynamically fetched into the container cache at runtime via the `huggingface_hub` API, keeping the codebase lightweight.

- **Highly Optimized CPU Inference**
  Employs `llama-cpp-python` to execute quantized GGUF open-source models. To bypass expensive and heavily-throttled free-tier cloud GPUs, the architecture is explicitly configured for high-performance CPU inference (`n_gpu_layers=0`). This demonstrates the ability to deploy capable LLMs efficiently on highly constrained, affordable hardware.

- **Cloud-Based RAG Pipeline (IPv4 Pooler Configured)**
  Integrates `langchain` and `sentence-transformers` (`all-MiniLM-L6-v2`) for real-time embedding generation. Context is retrieved via similarity search from a cloud-hosted Postgres database (**Supabase**) utilizing the **pgvector** extension. Network traffic is routed through a dedicated IPv4 Session Pooler (`port 6543`) to resolve complex cloud IPv6 routing limitations.

- **Robust Concurrency Control**
  To prevent CPU/RAM Out-of-Memory (OOM) crashes under high concurrent load, the backend implements `asyncio.Semaphore` (the "bouncer"). This manages concurrent inference requests and implements an asynchronous queueing system that provides real-time position feedback to end-users.

- **Enterprise-Grade Authentication**
  API endpoints are securely protected using [Clerk](https://clerk.dev/) in Production mode. The backend performs rigorous JWT validation by dynamically fetching and verifying RSA signatures against Clerk's live JSON Web Key Set (JWKS), ensuring secure, stateless session management.

## 🛠️ Tech Stack
- **Frontend / Hosting**: Vercel (Deployed UI)
- **Backend / Framework**: Python 3.11, FastAPI, Uvicorn, asyncio
- **AI / Machine Learning**: `llama-cpp-python` (Local GGUF Models), LangChain, HuggingFace Hub
- **Database / Vector Store**: Supabase (PostgreSQL) + `pgvector`
- **Infrastructure / Deployment**: Hugging Face Spaces, Docker (`python:3.11-slim` base)
- **Security / Auth**: Clerk (JWT Verification via PyJWT), CORS Middleware

## 📂 Architecture & Core Files
- `Dockerfile`: Defines the production container, including the installation of C++ build tools (`build-essential`, `cmake`) required to compile the LLM engine from scratch, and exposes port 7860.
- `src/app_backend.py`: The core FastAPI application featuring dynamic model downloading, JWT auth guards, semaphore-based queuing, and the RAG/LLM generation pipeline.
- `generate_train_data.py`: Local data ingestion script used to populate the Supabase pgvector store with contextual data.
- `requirements.txt`: Specifically configured to pull pre-compiled Linux wheels to drastically reduce container build times.

## 🚦 Local Development

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Viraj-brn/Ragebait-Bot.git](https://github.com/Viraj-brn/Ragebait-Bot.git)
   cd Ragebait-Bot

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the environment:**
   Create a `.env` file referencing `.env.example`. Make sure to provide the required Supabase and Clerk API keys.

4. **Prepare the Model:**
   Add a compatible GGUF model to the `models/` directory (e.g., `ragebait_model.gguf`).

5. **Run the local server:**
   ```bash
   python -m src.app_backend
   ```
   *The server will run on `http://127.0.0.1:5000`.*
