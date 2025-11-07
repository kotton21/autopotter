#!/usr/bin/env python3
"""
Minimal script to extract image metadata including dimensions, rotation, and thumbnail info.
"""

import os
from PIL import Image
from PIL.ExifTags import TAGS

def get_image_metadata(image_path):
    """Extract and print image metadata."""
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return
    
    try:
        with Image.open(image_path) as img:
            print(f"Image: {os.path.basename(image_path)}")
            print(f"Path: {image_path}")
            print("-" * 50)
            
            # Basic image info
            print(f"Format: {img.format}")
            print(f"Mode: {img.mode}")
            print(f"Dimensions: {img.size} (width x height)")
            
            # Check for EXIF data
            exif_data = img._getexif()
            if exif_data:
                print("\nEXIF Data:")
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ['Orientation', 'ImageWidth', 'ImageHeight', 'Thumbnail']:
                        print(f"  {tag}: {value}")
                
                # Check for orientation/rotation
                orientation = exif_data.get(274)  # Orientation tag
                if orientation:
                    orientation_map = {
                        1: "Normal (0°)",
                        2: "Mirrored horizontally",
                        3: "Rotated 180°",
                        4: "Mirrored vertically", 
                        5: "Mirrored horizontally, rotated 90° CCW",
                        6: "Rotated 90° CW",
                        7: "Mirrored horizontally, rotated 90° CW",
                        8: "Rotated 90° CCW"
                    }
                    print(f"\nRotation/Orientation: {orientation_map.get(orientation, f'Unknown ({orientation})')}")
                else:
                    print("\nNo rotation/orientation data found")
            else:
                print("\nNo EXIF data found")
            
            # Check for thumbnail
            try:
                if hasattr(img, 'thumbnail'):
                    print(f"\nThumbnail available: Yes")
                    # Try to get thumbnail size
                    thumb = img.copy()
                    thumb.thumbnail((100, 100))
                    print(f"Thumbnail size: {thumb.size}")
                else:
                    print(f"\nThumbnail available: No")
            except Exception as e:
                print(f"\nThumbnail check failed: {e}")
                
    except Exception as e:
        print(f"Error reading image: {e}")

if __name__ == "__main__":
    image_path = os.path.expanduser("~/Pottery/autopot1-sync/completed_works/sv24.jpg")
    get_image_metadata(image_path)
