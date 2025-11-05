#!/usr/bin/env python3
"""
Script to fix image orientation by applying EXIF rotation and saving with orientation=1.
"""

import os
import sys
import argparse
import glob
from PIL import Image, ExifTags

def fix_image_orientation(input_path, output_suffix="_fixed", quality=95):
    """
    Fix image orientation by applying EXIF rotation and saving with orientation=1.
    
    Args:
        input_path: Path to input image
        output_suffix: Suffix to add to output filename (default: "_fixed")
        quality: JPEG quality (1-100, default 95)
    """
    if not os.path.exists(input_path):
        print(f"Error: Image file not found at {input_path}")
        return False
    
    # Generate output path using suffix
    name, ext = os.path.splitext(input_path)
    output_path = f"{name}{output_suffix}{ext}"
    
    try:
        with Image.open(input_path) as img:
            print(f"Processing: {os.path.basename(input_path)}")
            print(f"Original dimensions: {img.size}")
            
            # Get EXIF data
            exif_data = img._getexif()
            orientation = None
            
            if exif_data:
                orientation = exif_data.get(274)  # Orientation tag
                if orientation:
                    print(f"Original orientation: {orientation}")
                else:
                    print("No orientation data found - image is already normal")
                    orientation = 1
            
            # Apply rotation based on orientation
            if orientation == 1:
                # Already normal, just copy
                fixed_img = img.copy()
                print("No rotation needed")
            elif orientation == 2:
                # Mirrored horizontally
                fixed_img = img.transpose(Image.FLIP_LEFT_RIGHT)
                print("Applied: Horizontal flip")
            elif orientation == 3:
                # Rotated 180°
                fixed_img = img.rotate(180, expand=True)
                print("Applied: 180° rotation")
            elif orientation == 4:
                # Mirrored vertically
                fixed_img = img.transpose(Image.FLIP_TOP_BOTTOM)
                print("Applied: Vertical flip")
            elif orientation == 5:
                # Mirrored horizontally, rotated 90° CCW
                fixed_img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(90, expand=True)
                print("Applied: Horizontal flip + 90° CCW rotation")
            elif orientation == 6:
                # Rotated 90° CW
                fixed_img = img.rotate(-90, expand=True)
                print("Applied: 90° CW rotation")
            elif orientation == 7:
                # Mirrored horizontally, rotated 90° CW
                fixed_img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(-90, expand=True)
                print("Applied: Horizontal flip + 90° CW rotation")
            elif orientation == 8:
                # Rotated 90° CCW
                fixed_img = img.rotate(90, expand=True)
                print("Applied: 90° CCW rotation")
            else:
                # Unknown orientation, just copy
                fixed_img = img.copy()
                print(f"Unknown orientation {orientation}, no changes applied")
            
            print(f"New dimensions: {fixed_img.size}")
            
            # Save with orientation=1 (normal) by removing orientation tag
            # This effectively sets orientation to 1 (normal)
            fixed_img.save(output_path, quality=quality)
            print(f"Saved fixed image to: {output_path}")
            
            return True
            
    except Exception as e:
        print(f"Error processing image: {e}")
        return False

def process_folder(folder_path, output_suffix="_fixed", quality=95):
    """
    Process all images in a folder.
    
    Args:
        folder_path: Path to folder containing images
        output_suffix: Suffix to add to output filenames
        quality: JPEG quality (1-100)
    """
    if not os.path.isdir(folder_path):
        print(f"Error: Folder not found at {folder_path}")
        return False
    
    # Supported image extensions
    image_extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.png', '*.PNG', '*.tiff', '*.TIFF', '*.bmp', '*.BMP']
    
    # Find all image files in the folder
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder_path, ext)))
    
    if not image_files:
        print(f"No image files found in {folder_path}")
        return False
    
    print(f"Found {len(image_files)} image(s) to process in {folder_path}")
    print("-" * 60)
    
    success_count = 0
    failed_count = 0
    
    for image_path in sorted(image_files):
        print(f"\nProcessing: {os.path.basename(image_path)}")
        success = fix_image_orientation(image_path, output_suffix, quality)
        if success:
            success_count += 1
        else:
            failed_count += 1
    
    print("\n" + "=" * 60)
    print(f"Processing complete!")
    print(f"Successfully processed: {success_count} images")
    if failed_count > 0:
        print(f"Failed to process: {failed_count} images")
    
    return success_count > 0

def main():
    parser = argparse.ArgumentParser(
        description="Fix image orientation by applying EXIF rotation and saving with orientation=1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s photo.jpg
  %(prog)s photo.jpg -s _rotated
  %(prog)s photo.jpg -s _corrected -q 85
  %(prog)s photo.jpg --suffix _fixed --quality 80
  %(prog)s /path/to/folder
  %(prog)s /path/to/folder -s _fixed -q 85
        """
    )
    
    parser.add_argument('input_path', 
                       help='Path to input image file or folder containing images')
    
    parser.add_argument('-s', '--suffix', 
                       dest='output_suffix',
                       default='_fixed',
                       help='Suffix to add to output filename (default: "_fixed")')
    
    parser.add_argument('-q', '--quality', 
                       type=int, 
                       default=95,
                       choices=range(1, 101),
                       metavar='1-100',
                       help='JPEG quality setting (default: 95)')
    
    args = parser.parse_args()
    
    print(f"Using quality setting: {args.quality}%")
    
    # Check if input is a file or folder
    if os.path.isfile(args.input_path):
        # Process single file
        success = fix_image_orientation(args.input_path, args.output_suffix, args.quality)
        if success:
            print("Image orientation fixed successfully!")
        else:
            print("Failed to fix image orientation.")
            sys.exit(1)
    elif os.path.isdir(args.input_path):
        # Process folder
        success = process_folder(args.input_path, args.output_suffix, args.quality)
        if not success:
            sys.exit(1)
    else:
        print(f"Error: {args.input_path} is neither a file nor a directory")
        sys.exit(1)

if __name__ == "__main__":
    main()
