"""
Utility helper functions
"""
from PIL import Image, ImageDraw, ImageFont
import io


def generate_placeholder_preview(original_filename: str) -> bytes:
    """Generate a white rectangle placeholder image for files without previews"""
    # Create a 512x512 white image
    img = Image.new('RGB', (512, 512), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add a light gray border
    draw.rectangle([0, 0, 511, 511], outline='lightgray', width=2)
    
    # Add text in the center
    try:
        # Try to use a default font
        font = ImageFont.load_default()
    except:
        font = None
    
    # Text to display
    text_lines = [
        "Preview Not Available",
        "",
        f"File: {original_filename}",
        "",
        "Preview generation in progress..."
    ]
    
    # Calculate text position (center)
    text_height = len(text_lines) * 20
    start_y = (512 - text_height) // 2
    
    for i, line in enumerate(text_lines):
        if line:  # Skip empty lines
            # Get text bounding box
            bbox = draw.textbbox((0, 0), line, font=font) if font else (0, 0, 100, 20)
            text_width = bbox[2] - bbox[0]
            text_x = (512 - text_width) // 2
            text_y = start_y + (i * 20)
            
            # Draw text in gray
            draw.text((text_x, text_y), line, fill='gray', font=font)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

