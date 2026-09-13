#!/usr/bin/env python3
"""
Script to resize and optimize screenshots on GitHub
Downloads each image, resizes it to 800px width, and re-uploads it
"""

import requests
import base64
from io import BytesIO
from PIL import Image
import os

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Get from environment variable
REPO = "Ange-duval/adk-purchase-request"
BRANCH = "main"
SCREENSHOTS_DIR = "adk_purchase_request/static/description/screenshots"

screenshots = [
    "01-droits-utilisateur.png",
    "02-creation-brouillon.png",
    "03-approbation-manager.png",
    "04-selection-fournisseur-rfq.png",
    "05-suivi-commandes.png",
    "06-tableau-bord-kanban.png",
    "07-tableau-croise-articles.png",
]

TARGET_WIDTH = 800

def get_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def download_image(path):
    """Download image from GitHub raw URL"""
    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))

def get_file_sha(path):
    """Get the SHA of an existing file"""
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        return response.json()['sha']
    return None

def resize_image(img):
    """Resize image to target width, maintaining aspect ratio"""
    original_width, original_height = img.size
    ratio = TARGET_WIDTH / original_width
    new_height = int(original_height * ratio)
    return img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)

def upload_image(path, img):
    """Upload resized image to GitHub"""
    # Save to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    img_bytes = buffer.read()
    
    # Encode to base64
    b64_content = base64.b64encode(img_bytes).decode('utf-8')
    
    # Get SHA if file exists
    sha = get_file_sha(path)
    
    # Upload
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    data = {
        "message": f"Resize {path.split('/')[-1]} to professional size (800px width)",
        "content": b64_content,
    }
    
    if sha:
        data["sha"] = sha
    
    response = requests.put(url, json=data, headers=get_headers())
    return response.status_code in [200, 201], response

# Main process
if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN environment variable not set")
    exit(1)

print(f"Resizing screenshots to {TARGET_WIDTH}px width...\n")

for screenshot in screenshots:
    path = f"{SCREENSHOTS_DIR}/{screenshot}"
    
    try:
        print(f"Processing {screenshot}...")
        
        # Download
        img = download_image(path)
        original_size = img.size
        
        # Resize
        img_resized = resize_image(img)
        new_size = img_resized.size
        
        # Upload
        success, response = upload_image(path, img_resized)
        
        if success:
            print(f"✓ {screenshot}")
            print(f"  Original: {original_size[0]}x{original_size[1]}")
            print(f"  Resized:  {new_size[0]}x{new_size[1]}\n")
        else:
            print(f"✗ Failed to upload {screenshot}")
            print(f"  Response: {response.json()}\n")
        
    except Exception as e:
        print(f"✗ Error processing {screenshot}: {e}\n")

print("Done!")
