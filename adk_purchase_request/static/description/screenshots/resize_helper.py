#!/usr/bin/env python3
"""
Helper script to resize images in bulk
Usage: python3 resize_helper.py
"""

import os
from PIL import Image

def resize_screenshot(filepath, target_width=800):
    """
    Resize a screenshot to target width while maintaining aspect ratio.
    Optimizes PNG compression.
    """
    try:
        img = Image.open(filepath)
        original_size = img.size
        
        # Calculate new height maintaining aspect ratio
        ratio = target_width / original_size[0]
        new_height = int(original_size[1] * ratio)
        
        # Resize with high-quality LANCZOS filter
        img_resized = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
        
        # Save with optimization
        img_resized.save(filepath, 'PNG', optimize=True)
        
        new_file_size = os.path.getsize(filepath)
        original_file_size = os.path.getsize(filepath)
        
        print(f"✓ {os.path.basename(filepath)}")
        print(f"  Size: {original_size[0]}x{original_size[1]} → {target_width}x{new_height}")
        return True
        
    except Exception as e:
        print(f"✗ Error processing {filepath}: {e}")
        return False

if __name__ == '__main__':
    screenshots_dir = 'adk_purchase_request/static/description/screenshots'
    
    if not os.path.exists(screenshots_dir):
        print(f"Directory {screenshots_dir} not found!")
        exit(1)
    
    # Process all PNG files
    for filename in sorted(os.listdir(screenshots_dir)):
        if filename.endswith('.png'):
            filepath = os.path.join(screenshots_dir, filename)
            resize_screenshot(filepath)
    
    print("\nAll screenshots resized!")
