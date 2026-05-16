import modal
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to the cloud drive you created earlier
model_volume = modal.Volume.from_name("ragebait-weights")
HF_TOKEN = os.environ.get("HF_TOKEN")
app = modal.App("download-model-app")

# Tell Modal to install the Hugging Face library
image = modal.Image.debian_slim().pip_install("huggingface_hub")

@app.function(
    image=image, 
    volumes={"/root/models": model_volume},
    secrets=[modal.Secret.from_dotenv()]
)
def download_model():
    from huggingface_hub import hf_hub_download
    import os
    
    print("Starting high-speed cloud download...")
    
    # 1. PASTE YOUR DETAILS HERE
    HF_TOKEN = os.environ.get("HF_TOKEN")
    REPO_ID = "virtive2003/frie-nemy_model" # Example: "johndoe/frien-emy-model"
    FILENAME = "ragebait_model.gguf"
    
    # Download directly to the mounted Modal volume
    file_path = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        token=HF_TOKEN,
        local_dir="/root/models"
    )
    
    # Lock the changes into the cloud drive
    model_volume.commit()
    print(f"Success! Model securely downloaded to volume at: {file_path}")

@app.local_entrypoint()
def main():
    download_model.remote()