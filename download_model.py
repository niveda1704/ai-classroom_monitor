"""
Script to download the EmotionSense AI Classroom Monitor model from Hugging Face
and make it locally available.

Requirements:
- huggingface_hub
- transformers
- torch

Usage:
1. First, login to Hugging Face if the model is private:
   huggingface-cli login
   
2. Run this script:
   python download_model.py
"""

from huggingface_hub import snapshot_download, login, list_repo_files, hf_hub_download
import os

# Model repository on Hugging Face
MODEL_REPO = "AK97GAMERZ/emotionsense-ai-classroom-monitor"

# Local directory to save the model
LOCAL_MODEL_DIR = "./models/emotionsense-ai-classroom-monitor"

def download_model():
    """Download the model from Hugging Face to local directory."""
    
    print(f"Downloading model: {MODEL_REPO}")
    print(f"Saving to: {LOCAL_MODEL_DIR}")
    
    # Create the directory if it doesn't exist
    os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
    
    # First, list all files in the repository
    print("\n📁 Files in the repository:")
    try:
        files = list_repo_files(MODEL_REPO)
        for f in files:
            print(f"  - {f}")
    except Exception as e:
        print(f"Could not list files: {e}")
    
    try:
        # Download all files from the repository
        local_path = snapshot_download(
            repo_id=MODEL_REPO,
            local_dir=LOCAL_MODEL_DIR,
            local_dir_use_symlinks=False,  # Copy files instead of symlinks
        )
        
        print(f"\n✅ Model downloaded successfully to: {local_path}")
        print("\nDownloaded files:")
        for root, dirs, files in os.walk(local_path):
            for file in files:
                filepath = os.path.join(root, file)
                print(f"  - {filepath}")
                
        return local_path
        
    except Exception as e:
        print(f"\n❌ Error downloading model: {e}")
        print("\nIf the model is private, please login first:")
        print("  huggingface-cli login")
        print("\nOr set your token programmatically:")
        print("  from huggingface_hub import login")
        print("  login(token='your_hf_token')")
        return None

def login_to_huggingface(token=None):
    """Login to Hugging Face (required for private models)."""
    if token:
        login(token=token)
        print("✅ Logged in with provided token")
    else:
        print("Please enter your Hugging Face token when prompted...")
        login()
        print("✅ Logged in successfully")

if __name__ == "__main__":
    print("=" * 60)
    print("EmotionSense AI Classroom Monitor - Model Downloader")
    print("=" * 60)
    
    # Uncomment the next line and add your token if the model is private
    # login_to_huggingface(token="hf_your_token_here")
    
    # Or use interactive login (will prompt for token)
    # login_to_huggingface()
    
    download_model()
