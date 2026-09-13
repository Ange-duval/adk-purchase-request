#!/usr/bin/env python3
"""
Script to resize screenshots to professional size
Reduces image dimensions and compresses them
"""
import os
import subprocess
import sys

# List of screenshots to resize
screenshots = [
    "adk_purchase_request/static/description/screenshots/01-droits-utilisateur.png",
    "adk_purchase_request/static/description/screenshots/02-creation-brouillon.png",
    "adk_purchase_request/static/description/screenshots/03-approbation-manager.png",
    "adk_purchase_request/static/description/screenshots/04-selection-fournisseur-rfq.png",
    "adk_purchase_request/static/description/screenshots/05-suivi-commandes.png",
    "adk_purchase_request/static/description/screenshots/06-tableau-bord-kanban.png",
    "adk_purchase_request/static/description/screenshots/07-tableau-croise-articles.png",
]

# Check if ImageMagick is installed
try:
    subprocess.run(["convert", "--version"], capture_output=True, check=True)
except (subprocess.CalledProcessError, FileNotFoundError):
    print("Error: ImageMagick is not installed.")
    print("Install it with:")
    print("  Ubuntu/Debian: sudo apt-get install imagemagick")
    print("  macOS: brew install imagemagick")
    print("  Windows: Download from https://imagemagick.org/script/download.php")
    sys.exit(1)

# Resize each screenshot
for screenshot in screenshots:
    if os.path.exists(screenshot):
        print(f"Resizing {screenshot}...")
        # Resize to 800px width, maintain aspect ratio, and compress
        subprocess.run([
            "convert",
            screenshot,
            "-resize", "800x",
            "-quality", "85",
            screenshot
        ])
        print(f"✓ Resized {screenshot}")
    else:
        print(f"Warning: {screenshot} not found")

print("\nAll screenshots have been resized!")
