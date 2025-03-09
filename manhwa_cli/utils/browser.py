"""
Browser utilities for opening manhwa chapters
"""

import webbrowser
import platform
import subprocess
import os
import tempfile
import threading
import time
from rich.console import Console
import signal
import sys

# Import our PDF viewer
from manhwa_cli.utils.pdf_viewer import view_manhwa_as_pdf

console = Console()

# Track temporary directories for cleanup
temp_directories = []

# Add signal handlers for terminal exit
def signal_handler(sig, frame):
    """Handle terminal exit signals (Ctrl+C, etc.)"""
    console.print("\n[yellow]Detected exit signal. Cleaning up...[/]")
    cleanup_all_temp_dirs()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # termination request

def open_chapter(url, title="Chapter"):
    """
    Open a chapter in the PDF viewer or fallback to web browser
    
    Args:
        url (str): URL to open
        title (str): Title of the chapter
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Try to open in the PDF viewer
        console.print(f"[cyan]Opening chapter in PDF viewer...[/]")
        
        # Download the chapter images
        from manhwa_cli.scraper import download_chapter_images
        images = download_chapter_images(url, title)
        
        if images and len(images) > 0:
            # Use the PDF viewer
            success, temp_dir = view_manhwa_as_pdf(images, title)
            
            if success:
                # Schedule cleanup for when the application exits
                if temp_dir:
                    temp_directories.append(temp_dir)
                    # Start a cleanup thread that will monitor the PDF viewer
                    threading.Thread(
                        target=_cleanup_when_viewer_closes, 
                        args=(temp_dir,),
                        daemon=True
                    ).start()
                return True
        
        # If PDF viewer fails, fallback to browser
        console.print("[yellow]PDF viewer failed, falling back to browser...[/]")
        
        # Determine the operating system
        system = platform.system()
        
        # Open URL based on OS
        if system == "Darwin":  # macOS
            # On macOS, try to use Safari or default browser
            subprocess.run(["open", url], check=True)
        elif system == "Linux":
            # On Linux, use xdg-open
            subprocess.run(["xdg-open", url], check=True)
        else:
            # For other systems, use the Python webbrowser module
            webbrowser.open(url)
            
        return True
    except Exception as e:
        console.print(f"[red]Error opening chapter: {str(e)}[/]")
        # Fallback to Python's webbrowser module
        try:
            webbrowser.open(url)
            return True
        except:
            console.print(f"[red]Failed to open {url} in browser.[/]")
            return False

def _cleanup_when_viewer_closes(temp_dir, check_interval=5):
    """
    Wait for the viewer to close and then cleanup the temporary directory
    
    Args:
        temp_dir (str): Path to temporary directory
        check_interval (int): How often to check if we can clean up
    """
    try:
        # Wait for a bit to make sure the PDF is opened
        time.sleep(10)
        
        # Wait until the app is done with the file
        while True:
            # Check if the temp directory still exists
            if not os.path.exists(temp_dir):
                break
                
            # Try to determine if any PDF in the directory is still open
            pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
            
            if not pdf_files:
                break
                
            # Check if we can get exclusive access to the file (not open elsewhere)
            can_delete = True
            for pdf_file in pdf_files:
                pdf_path = os.path.join(temp_dir, pdf_file)
                try:
                    # Try to open the file in exclusive mode
                    with open(pdf_path, 'a+b') as f:
                        # If we can get here, the file is not in use
                        pass
                except:
                    # If we can't open it, it's probably still in use
                    can_delete = False
                    break
            
            if can_delete:
                break
                
            # Wait before checking again
            time.sleep(check_interval)
            
        # Clean up temp directory
        if os.path.exists(temp_dir):
            console.print(f"[dim]Cleaning up temporary files...[/]")
            try:
                # For macOS, extra check with lsof to ensure the file isn't still in use
                if platform.system() == "Darwin":
                    for pdf_file in [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]:
                        pdf_path = os.path.join(temp_dir, pdf_file)
                        # Try to get processes using this file
                        result = subprocess.run(["lsof", pdf_path], capture_output=True, text=True)
                        if result.stdout.strip():  # If any process is using the file
                            console.print(f"[yellow]Warning: File still in use by another process. Will retry cleanup later.[/]")
                            # Schedule another attempt later
                            threading.Thread(
                                target=_cleanup_when_viewer_closes, 
                                args=(temp_dir, check_interval),
                                daemon=True
                            ).start()
                            return

                # If all checks pass, delete the directory
                import shutil
                shutil.rmtree(temp_dir)
                # Remove from global tracking list
                if temp_dir in temp_directories:
                    temp_directories.remove(temp_dir)
                console.print(f"[green]Temporary files cleaned up successfully.[/]")
            except Exception as e:
                console.print(f"[yellow]Warning: Error during cleanup: {str(e)}[/]")
            
    except Exception as e:
        console.print(f"[yellow]Warning: Could not clean up temporary directory: {str(e)}[/]")

# Register cleanup at exit
import atexit

def cleanup_all_temp_dirs():
    """Cleanup all temporary directories at program exit"""
    import shutil
    
    if not temp_directories:
        return
        
    console.print(f"[dim]Cleaning up {len(temp_directories)} temporary directories...[/]")
    
    for temp_dir in list(temp_directories):
        if os.path.exists(temp_dir):
            try:
                # For macOS: Try to forcefully close any open PDF files
                if platform.system() == "Darwin":
                    # Find PDF files in the directory
                    pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
                    for pdf_file in pdf_files:
                        pdf_path = os.path.join(temp_dir, pdf_file)
                        # Try to kill processes using the PDF
                        try:
                            # Get PID of processes using this file
                            result = subprocess.run(
                                ["lsof", "-t", pdf_path], 
                                capture_output=True, 
                                text=True,
                                check=False
                            )
                            if result.stdout.strip():
                                pids = result.stdout.strip().split('\n')
                                for pid in pids:
                                    if pid:
                                        console.print(f"[yellow]Closing process using PDF: {pid}[/]")
                                        # Try to terminate nicely first
                                        try:
                                            subprocess.run(["kill", pid], check=False)
                                        except:
                                            pass
                        except:
                            pass
                
                # Give a moment for processes to close
                time.sleep(0.5)
                
                # Now try to delete the directory
                shutil.rmtree(temp_dir)
                console.print(f"[green]Cleaned up: {temp_dir}[/]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not clean up {temp_dir}: {str(e)}[/]")
            
    # Clear the list
    temp_directories.clear()

# Register the cleanup function to run at program exit
atexit.register(cleanup_all_temp_dirs) 