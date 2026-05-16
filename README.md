<div align="center">
  <h1>Frien-emy (formerly Ragebait Bot)</h1>
  <p><i>"Who needs enemies when you have friends like these? Make this bot your friend."</i></p>
</div>

## 🚀 Live Demo
**Experience the bot live:** [https://ragebot-ui.vercel.app/](https://ragebot-ui.vercel.app/)

## 📝 Overview
**Frien-emy** is an end-to-end, full-stack AI chat application designed to provide sarcastically entertaining responses. Powered by a customized Retrieval-Augmented Generation (RAG) pipeline and a locally-run LLM, this project demonstrates production-grade application development, scalable cloud-native architectures, and robust AI deployment strategies.

## ✨ Technical Highlights for Recruiters

- **Serverless GPU Computing (Modal)**
  The backend is deployed on [Modal](https://modal.com/), leveraging serverless T4 GPUs. This ensures cost-effective scaling with zero idle compute waste. Model weights are dynamically loaded from persistent cloud volumes (`modal.Volume`), optimizing container start times and reducing overhead.

- **Optimized LLM Inference**
  Employs `llama-cpp-python` to execute quantized GGUF models. The architecture intelligently delegates layers to the GPU (`n_gpu_layers=10`), carefully balancing VRAM constraints against inference speed to maximize throughput on affordable hardware.

- **Cloud-Based RAG Pipeline**
  Integrates `langchain` and `sentence-transformers` (`all-MiniLM-L6-v2`) for embedding generation. Context is retrieved via similarity search from a cloud-hosted Postgres database (**Supabase**) heavily utilizing the **pgvector** extension. 

- **Robust Concurrency Control**
  To prevent GPU Out-of-Memory (OOM) crashes under high concurrent load, the backend implements `asyncio.Semaphore` (the "bouncer"). This manages concurrent inference requests and implements an asynchronous queueing system that provides real-time position feedback to end-users.

- **Enterprise-Grade Authentication**
  API endpoints are securely protected using [Clerk](https://clerk.dev/). The backend performs rigorous JWT validation by dynamically fetching and verifying RSA signatures against Clerk's JSON Web Key Set (JWKS), ensuring secure, stateless session management.

## 🛠️ Tech Stack
- **Frontend / Hosting**: Vercel (Deployed UI)
- **Backend / Framework**: Python 3.11, FastAPI, Uvicorn, asyncio
- **AI / Machine Learning**: `llama-cpp-python` (Local GGUF Models), LangChain, HuggingFace
- **Database / Vector Store**: Supabase (PostgreSQL) + `pgvector`
- **Infrastructure / Deployment**: Modal Serverless, Docker (`nvidia/cuda:12.1.1-runtime-ubuntu22.04` base)
- **Security / Auth**: Clerk (JWT Verification via PyJWT), CORS Middleware

## 📂 Architecture & Core Files
- `src/app_backend.py`: The core FastAPI application featuring JWT auth guards, semaphore-based queuing, and the RAG/LLM generation pipeline.
- `deploy_modal.py`: Infrastructure-as-code for Modal, defining the CUDA environment, dependency installations, and volume mounts.
- `generate_train_data.py`: Local data ingestion script used to populate the Supabase pgvector store with contextual data.
- `.env`: Centralized environment configuration.

## 🚦 Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Viraj-brn/Ragebait-Bot.git
   cd Ragebait-Bot
   ```

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
