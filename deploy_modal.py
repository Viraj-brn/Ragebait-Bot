import modal

# 1. Use an official NVIDIA image to guarantee CUDA 12 is present!
image = (
    modal.Image.from_registry("nvidia/cuda:12.1.1-runtime-ubuntu22.04", add_python="3.11")
    .apt_install("libpq-dev", "gcc") # Required system tools for the new base image
    .pip_install(
        "fastapi[standard]", 
        "langchain-huggingface", 
        "langchain-community", 
        "sentence-transformers", # <-- FIX 1: Added the missing package
        "psycopg2-binary", 
        "pgvector", 
        "pyjwt", 
        "cryptography", 
        "httpx"
    )
    # FIX 2: The pre-compiled wheel now perfectly matches the NVIDIA base image
    .run_commands("pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121")
    .add_local_dir("src", remote_path="/root/src") 
)

# 2. Connect the cloud drive
model_volume = modal.Volume.from_name("ragebait-weights")
app = modal.App("frien-emy-backend")

# 3. Define the serverless API function
@app.function(
    image=image,
    gpu="L4",
    volumes={"/root/models": model_volume},
    secrets=[modal.Secret.from_dotenv()]
)
@modal.asgi_app()
def run_api():
    import sys
    sys.path.append("/root")
    
    from src import app_backend
    
    app_backend.MODEL_PATH = "/root/models/ragebait_model.gguf"
    
    if app_backend.llm is None:
        print("Initializing LLM from cloud volume...")
        app_backend._init_llm()
        
    return app_backend.app