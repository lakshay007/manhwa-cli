"""
Local viewer for downloaded manhwa chapters
"""

import os
import tempfile
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import io
import threading
import platform
from rich.console import Console
from rich.progress import Progress
from bs4 import BeautifulSoup

console = Console()

# Special handling for macOS scroll events
def _create_macos_scroll_handler(canvas):
    """Create a scroll handler specifically for macOS trackpads"""
    def _scroll_handler(event):
        # Get scrolling units based on the platform and event type
        if hasattr(event, 'delta'):
            # Convert macOS delta to scroll units (with direction handling)
            units = -1 if event.delta > 0 else 1
            canvas.yview_scroll(units, "units")
        return "break"  # Prevent event from propagating
    return _scroll_handler

class ManhwaViewer:
    """
    A simple viewer for displaying manhwa chapters locally
    """
    def __init__(self, title, images):
        """
        Initialize the viewer

        Args:
            title (str): Title of the chapter
            images (list): List of image data (bytes)
        """
        self.title = title
        self.images = images
        self.img_objects = []  # To prevent garbage collection
        
        # Track zoom level
        self.zoom_level = 1.0  # 1.0 = 100% (no zoom)
        self.zoom_step = 0.1   # 10% zoom change per step
        self.min_zoom = 0.5    # 50% minimum zoom
        self.max_zoom = 2.0    # 200% maximum zoom
        
        # Create temporary directory for images
        self.temp_dir = tempfile.mkdtemp(prefix="manhwa_viewer_")
        
        # Setup UI
        self.root = tk.Tk()
        self.root.title(f"Manhwa Viewer - {title}")
        # Set rectangular shape better suited for manhwas (taller than wide)
        self.root.geometry("800x1000")
        
        # Set a background color for better contrast
        self.bg_color = "#2A2A2A"  # Dark background color
        self.root.configure(background=self.bg_color)
        
        # Configure the root window grid for proper centering
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create outer frame that will expand in all directions
        outer_frame = ttk.Frame(self.root, style="BG.TFrame")
        outer_frame.grid(row=0, column=0, sticky="nsew")
        outer_frame.grid_rowconfigure(0, weight=1)
        outer_frame.grid_columnconfigure(0, weight=1)
        
        # Create a style for the frames to match the background
        style = ttk.Style()
        style.configure("BG.TFrame", background=self.bg_color)
        style.configure("BG.TLabel", background=self.bg_color, foreground="white")
        
        # Create a canvas with scrollbar in the outer frame
        self.canvas = tk.Canvas(outer_frame, background=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        # Position canvas and scrollbar in the outer frame
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure the canvas
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create the content frame that will hold all our widgets
        self.content_frame = ttk.Frame(self.canvas, style="BG.TFrame")
        
        # Center the content frame in the canvas
        self.canvas_window = self.canvas.create_window(
            (0, 0), 
            window=self.content_frame, 
            anchor="nw",
            tags="content"
        )
        
        # Add control panel at the bottom
        control_frame = ttk.Frame(self.root, style="BG.TFrame")
        control_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # Add zoom controls
        zoom_frame = ttk.Frame(control_frame, style="BG.TFrame")
        zoom_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(zoom_frame, text="Zoom In (+)", command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        self.zoom_label = ttk.Label(zoom_frame, text="100%", style="BG.TLabel")
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(zoom_frame, text="Zoom Out (-)", command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        
        # Add chapter indicator
        self.chapter_indicator = ttk.Label(control_frame, text=f"{title}", style="BG.TLabel")
        self.chapter_indicator.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(control_frame, text="Close", command=self.close).pack(side=tk.RIGHT, padx=5)
        
        # Bind events for various inputs
        self._bind_events()
        
        # Fullscreen state tracking
        self.is_fullscreen = False
        
        # Configure canvas resize behavior
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.content_frame.bind("<Configure>", self._on_content_configure)
        
        # Set minimum window size
        self.root.minsize(600, 800)
        
        # Load all images at once
        self.load_all_images()
    
    def _bind_events(self):
        """Bind all event handlers for mouse and keyboard"""
        # Platform-specific scrolling setup
        if platform.system() == "Darwin":
            # For macOS we need special handling due to trackpads
            self.macos_scroll_handler = _create_macos_scroll_handler(self.canvas)
            
            # Bind to the main canvas and its container
            self.canvas.bind("<MouseWheel>", self.macos_scroll_handler)
            self.root.bind_all("<MouseWheel>", self.macos_scroll_handler)
            
            # Bind Control/Command for zooming
            self.root.bind("<Control-MouseWheel>", self._on_ctrl_mousewheel)
            self.root.bind("<Command-MouseWheel>", self._on_ctrl_mousewheel)
        elif platform.system() == "Linux":
            # For Linux
            self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
            self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        else:
            # For Windows
            self.canvas.bind("<MouseWheel>", self._on_mousewheel_windows)
        
        # Universal keyboard shortcuts
        self.root.bind("<Down>", lambda e: self._scroll_down())
        self.root.bind("<Up>", lambda e: self._scroll_up())
        self.root.bind("<space>", lambda e: self._page_down())
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.bind("<f>", lambda e: self._toggle_fullscreen())
        
        # Zoom bindings
        self.root.bind("<plus>", lambda e: self.zoom_in())
        self.root.bind("<minus>", lambda e: self.zoom_out())
        self.root.bind("=", lambda e: self.zoom_in())  # = is on the same key as + on most keyboards
        self.root.bind("-", lambda e: self.zoom_out())
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize events"""
        # Update the width of the content window to match the canvas
        self.canvas.itemconfig("content", width=event.width)
        
        # Center the content in the canvas
        self._center_content()
    
    def _on_content_configure(self, event):
        """Update the scrollregion to encompass the content frame"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Center the content in the canvas
        self._center_content()
    
    def _center_content(self):
        """Center the content in the canvas"""
        canvas_width = self.canvas.winfo_width()
        content_width = self.content_frame.winfo_reqwidth()
        
        # If the content is narrower than the canvas, center it
        if content_width < canvas_width:
            # Calculate the centered x position
            centered_x = (canvas_width - content_width) / 2
            self.canvas.coords("content", centered_x, 0)
        else:
            # If content is wider, align to left
            self.canvas.coords("content", 0, 0)
    
    def load_all_images(self):
        """Load all images at once for continuous scrolling"""
        # Clear previous content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Reset the img_objects list
        self.img_objects = []
        
        try:
            # Get available width in window
            window_width = self.canvas.winfo_width() - 30  # Subtract some padding
            if window_width < 100:
                window_width = 700  # Default width if window not fully loaded
            
            # Set a maximum width to prevent excessive scaling in fullscreen
            max_display_width = min(window_width, 1000)  # Limit maximum width
            
            # Create a container frame for all images
            container = ttk.Frame(self.content_frame, style="BG.TFrame")
            container.pack(fill=tk.BOTH, expand=True)
            
            # Process each image
            console.print(f"[cyan]Loading {len(self.images)} images for the chapter...[/]")
            
            for idx, img_data in enumerate(self.images):
                try:
                    # Create a separator between images
                    if idx > 0:
                        separator = ttk.Frame(container, height=2, style="Separator.TFrame")
                        separator.pack(fill=tk.X, padx=10, pady=5)
                        
                        # Configure the separator style
                        style = ttk.Style()
                        style.configure("Separator.TFrame", background="#555555")
                    
                    # Open image using PIL
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Get original dimensions
                    orig_width, orig_height = img.size
                    
                    # Calculate new dimensions while maintaining aspect ratio
                    # Only scale down if image is larger than available space
                    # Only scale up if image is tiny (less than 300px wide)
                    if orig_width > max_display_width:
                        # Scale down case
                        scale_factor = max_display_width / orig_width
                        new_width = max_display_width
                        new_height = int(orig_height * scale_factor)
                    elif orig_width < 300:
                        # Scale up case for very small images
                        scale_factor = 300 / orig_width
                        new_width = 300
                        new_height = int(orig_height * scale_factor)
                    else:
                        # Use original size
                        new_width = orig_width
                        new_height = orig_height
                    
                    # Apply zoom level
                    final_width = int(new_width * self.zoom_level)
                    final_height = int(new_height * self.zoom_level)
                    
                    # Resize image
                    img = img.resize((final_width, final_height), Image.LANCZOS)
                    
                    # Convert to Tkinter format
                    photo = ImageTk.PhotoImage(img)
                    self.img_objects.append(photo)  # Prevent garbage collection
                    
                    # Create a frame for centering this image
                    img_frame = ttk.Frame(container, style="BG.TFrame")
                    img_frame.pack(fill=tk.X, expand=True, pady=5)
                    
                    # Create a label to display the image
                    label = ttk.Label(img_frame, image=photo, background=self.bg_color, style="BG.TLabel")
                    label.pack(anchor=tk.CENTER)
                    
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not load image {idx+1}: {str(e)}[/]")
                    # Add a placeholder for the failed image
                    error_label = ttk.Label(
                        container, 
                        text=f"Image {idx+1} could not be loaded: {str(e)}", 
                        style="BG.TLabel"
                    )
                    error_label.pack(pady=20)
            
            # Update title to show current image
            self.root.title(f"Manhwa Viewer - {self.title}")
            
            # Update zoom indicator
            self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
            
            # Reset scrollbar to top
            self.canvas.yview_moveto(0)
            
            # Center the content
            self.root.update_idletasks()  # Force geometry update
            self._center_content()
            
        except Exception as e:
            console.print(f"[red]Error loading images: {str(e)}[/]")
            error_label = ttk.Label(self.content_frame, text=f"Error loading images: {str(e)}", style="BG.TLabel")
            error_label.pack(pady=20)
    
    def zoom_in(self):
        """Increase zoom level"""
        if self.zoom_level < self.max_zoom:
            self.zoom_level += self.zoom_step
            self.zoom_level = min(self.zoom_level, self.max_zoom)  # Enforce max zoom
            self.load_all_images()
    
    def zoom_out(self):
        """Decrease zoom level"""
        if self.zoom_level > self.min_zoom:
            self.zoom_level -= self.zoom_step
            self.zoom_level = max(self.zoom_level, self.min_zoom)  # Enforce min zoom
            self.load_all_images()
    
    def _on_mousewheel_windows(self, event):
        """Handle mousewheel scrolling on Windows"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_mousewheel_mac(self, event):
        """Handle mousewheel/trackpad scrolling on macOS"""
        # macOS deltaY values are different
        # For trackpad events
        if hasattr(event, 'delta'):
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        # For button events
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        # Fallback method
        else:
            self.canvas.yview_scroll(-1, "units")
    
    def _on_ctrl_mousewheel(self, event):
        """Handle Ctrl+mousewheel for zooming"""
        if hasattr(event, 'delta'):
            # Direction is different on different platforms
            if platform.system() == "Darwin":
                # macOS
                if event.delta > 0:
                    self.zoom_out()
                else:
                    self.zoom_in()
            else:
                # Windows/Linux
                if event.delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
    
    def _scroll_down(self):
        """Scroll down on down arrow key"""
        self.canvas.yview_scroll(3, "units")
    
    def _scroll_up(self):
        """Scroll up on up arrow key"""
        self.canvas.yview_scroll(-3, "units")
    
    def _page_down(self):
        """Page down on space key"""
        self.canvas.yview_scroll(10, "units")
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        
        # After toggling, force a redraw to adjust everything
        self.root.update_idletasks()
        self._center_content()
        
        # Reload all images to adjust scaling
        self.root.after(200, self.load_all_images)
    
    def close(self):
        """Close the viewer and clean up temporary files"""
        self.root.destroy()
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove temporary directory: {str(e)}[/]")
    
    def start(self):
        """Start the viewer"""
        # Center window on screen 
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        self.root.mainloop()


def download_chapter_images(chapter_url, chapter_title):
    """
    Download all images for a chapter
    
    Args:
        chapter_url (str): URL of the chapter
        chapter_title (str): Title of the chapter
        
    Returns:
        list: List of image data (bytes)
    """
    from manhwa_cli.scraper import scraper
    
    images = []
    
    with Progress() as progress:
        task = progress.add_task(f"[cyan]Downloading {chapter_title}...", total=None)
        
        try:
            # Get the chapter page
            response = scraper.get(chapter_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the reader container
            reader_container = soup.select_one('#reader-content') or soup.select_one('.reading-content')
            
            if not reader_container:
                console.print("[red]Could not find reader container[/]")
                # Try to find any large images on the page
                all_images = soup.select('img')
                image_urls = []
                
                for img in all_images:
                    src = img.get('src', '')
                    data_src = img.get('data-src', '')
                    data_lazy_src = img.get('data-lazy-src', '')
                    
                    # Use whichever attribute contains the image URL
                    img_url = data_src or data_lazy_src or src
                    
                    # Only include likely chapter images (filter out small icons, etc.)
                    if img_url and ('chapter' in img_url or 'manga' in img_url or 'comic' in img_url):
                        image_urls.append(img_url)
            else:
                # Find all images in the reader container
                image_elements = reader_container.select('img')
                console.print(f"[green]Found {len(image_elements)} images[/]")
                
                image_urls = []
                for img in image_elements:
                    src = img.get('src', '')
                    data_src = img.get('data-src', '')
                    data_lazy_src = img.get('data-lazy-src', '')
                    
                    # Use whichever attribute contains the image URL
                    img_url = data_src or data_lazy_src or src
                    
                    if img_url:
                        image_urls.append(img_url)
            
            # Update progress bar with total count
            progress.update(task, total=len(image_urls))
            progress.update(task, completed=0)
            
            # Download all images
            for i, img_url in enumerate(image_urls):
                try:
                    # Add referer header to avoid being blocked
                    headers = {
                        'Referer': chapter_url,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    img_response = scraper.get(img_url, headers=headers, timeout=15)
                    img_response.raise_for_status()
                    
                    images.append(img_response.content)
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not download image {i+1}: {str(e)}[/]")
                    
            if not images:
                console.print("[red]No images found or downloaded[/]")
                return None
                
            console.print(f"[green]Successfully downloaded {len(images)} images[/]")
            return images
            
        except Exception as e:
            console.print(f"[red]Error downloading chapter: {str(e)}[/]")
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/]")
            return None


def open_chapter_in_viewer(chapter_url, chapter_title):
    """
    Download chapter images and open in local viewer
    
    Args:
        chapter_url (str): URL of the chapter
        chapter_title (str): Title of the chapter
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        console.print(f"[cyan]Downloading chapter: {chapter_title}[/]")
        images = download_chapter_images(chapter_url, chapter_title)
        
        if not images:
            console.print("[red]Failed to download chapter images[/]")
            return False
            
        console.print(f"[green]Opening viewer with {len(images)} images[/]")
        viewer = ManhwaViewer(chapter_title, images)
        viewer.start()
        
        return True
    except Exception as e:
        console.print(f"[red]Error opening chapter in viewer: {str(e)}[/]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/]")
        return False 