"""
PDF Viewer module for displaying manhwa chapters using PyMuPDF (fitz)
"""

import os
import tempfile
import shutil
import platform
import subprocess
import io
from PIL import Image
import time
# Fix the import for PyMuPDF
try:
    import fitz  
except ImportError:
    try:
        from PyMuPDF import fitz  
    except ImportError:
        raise ImportError("PyMuPDF not found. Please install it with 'pip install PyMuPDF'")
from rich.console import Console
from rich.progress import Progress

console = Console()

def create_pdf_from_images(images, title):
    """
    Create a PDF from a list of image data
    
    Args:
        images (list): List of image data bytes
        title (str): Title of the chapter for the PDF
        
    Returns:
        str: Path to the created PDF file or None if failed
    """
    try:
        # Create a temporary directory for the PDF
        temp_dir = tempfile.mkdtemp(prefix="manhwa_pdf_")
        pdf_path = os.path.join(temp_dir, f"{title.replace(' ', '_')}.pdf")
        
        # Create a new PDF document with A4 portrait size
        doc = fitz.open()
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Creating PDF...", total=len(images))
            
            # Add each image as a page
            for idx, img_data in enumerate(images):
                try:
                    # Process image with PIL first to ensure compatibility
                    pil_img = Image.open(io.BytesIO(img_data))
                    
                    # Convert to RGB if needed (PDF doesn't support RGBA)
                    if pil_img.mode == 'RGBA':
                        pil_img = pil_img.convert('RGB')
                    
                    # Save as temporary JPEG for better compression
                    temp_img_path = os.path.join(temp_dir, f"temp_img_{idx}.jpg")
                    pil_img.save(temp_img_path, "JPEG", quality=90)
                    
                    # Get the dimensions of the image
                    width, height = pil_img.size
                    
                    # Create a new page with the image dimensions (to avoid scaling)
                    page = doc.new_page(width=width, height=height)
                    
                    # Insert the image into the page
                    rect = fitz.Rect(0, 0, width, height)
                    page.insert_image(rect, filename=temp_img_path)
                    
                    # Clean up the temporary image
                    os.remove(temp_img_path)
                    
                    # Update progress
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not add image {idx+1}: {str(e)}[/]")
            
            # Set PDF metadata
            doc.set_metadata({
                "title": title,
                "subject": "Manhwa Chapter",
                "author": "Manhwa CLI",
                "creator": "Manhwa CLI using PyMuPDF",
            })
            
            # Save the PDF
            doc.save(pdf_path)
            doc.close()
            
            console.print(f"[green]PDF created successfully at {pdf_path}[/]")
            return pdf_path, temp_dir
            
    except Exception as e:
        console.print(f"[red]Error creating PDF: {str(e)}[/]")
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir)
        return None, None

def open_pdf_with_system_viewer(pdf_path):
    """
    Open PDF with the system's default PDF viewer
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        system = platform.system()
        
        # Open PDF based on the operating system
        if system == "Darwin":  # macOS
            # Use 'open' command on macOS
            subprocess.run(["open", pdf_path], check=True)
        elif system == "Linux":
            # Use 'xdg-open' on Linux
            subprocess.run(["xdg-open", pdf_path], check=True)
        else:
            # Use os.startfile on Windows
            os.startfile(pdf_path)
        
        return True
    except Exception as e:
        console.print(f"[red]Error opening PDF: {str(e)}[/]")
        return False

def view_manhwa_as_pdf(images, title):
    """
    Create PDF from images and open in default viewer
    
    Args:
        images (list): List of image data bytes
        title (str): Title of the chapter
        
    Returns:
        tuple: (bool, str) - Success status and temp directory path
    """
    # Create PDF file
    pdf_path, temp_dir = create_pdf_from_images(images, title)
    
    if pdf_path:
        # Write a small marker file to help track when it's safe to delete
        if temp_dir:
            marker_path = os.path.join(temp_dir, ".manhwa_cli_marker")
            try:
                with open(marker_path, 'w') as f:
                    f.write(f"PDF created at: {os.path.basename(pdf_path)}\n")
                    f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Auto-cleanup enabled\n")
            except Exception:
                pass  # Ignore error if marker can't be written
        
        # Open PDF with system viewer
        console.print("[cyan]Opening PDF with your default PDF viewer...[/]")
        success = open_pdf_with_system_viewer(pdf_path)
        
        if success:
            console.print("[green]PDF opened successfully![/]")
            console.print("[dim]Note: Temporary files will be automatically cleaned up when you close the PDF viewer.[/]")
            return True, temp_dir
    
    # Clean up on failure
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    return False, None 