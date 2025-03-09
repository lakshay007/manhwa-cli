"""
Display utilities for presenting search results and chapters
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.prompt import IntPrompt

console = Console()

def display_search_results(results):
    """
    Display search results in a formatted table and prompt for selection
    
    Args:
        results (list): List of dictionaries containing manhwa info
        
    Returns:
        int or None: Index of selected manhwa or None if canceled
    """
    # Create a table for search results
    table = Table(title="Search Results", box=box.ROUNDED)
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Title", style="green")
    table.add_column("Rating", justify="center")
    table.add_column("Views/Info", justify="center")
    
    for idx, manhwa in enumerate(results):
        # Get the view count or latest chapter info
        info_text = manhwa.get('views', 'N/A')
        if not info_text or info_text == 'N/A':
            # Try to use latest_chapter if views is not available
            info_text = manhwa.get('latest_chapter', 'N/A')
        
        table.add_row(
            str(idx + 1),
            manhwa['title'],
            manhwa.get('rating', 'N/A'),
            info_text
        )
    
    console.print(table)
    
    # Prompt for selection
    try:
        selection = IntPrompt.ask(
            "Enter the number of the manhwa you want to read [b]([red]0 to cancel[/])[/]",
            default=0,
            show_default=True
        )
        
        if selection == 0:
            return None
        
        if 1 <= selection <= len(results):
            return selection - 1
        else:
            console.print("[bold red]Invalid selection. Please try again.[/]")
            return display_search_results(results)
    except KeyboardInterrupt:
        return None

def display_chapters(chapters):
    """
    Display chapters in a formatted table and prompt for selection
    
    Args:
        chapters (list): List of dictionaries containing chapter info
        
    Returns:
        int or None: Index of selected chapter or None if canceled
    """
    # If there are too many chapters, paginate the display
    chapters_per_page = 20
    total_pages = (len(chapters) + chapters_per_page - 1) // chapters_per_page
    current_page = 1
    
    while True:
        start_idx = (current_page - 1) * chapters_per_page
        end_idx = min(start_idx + chapters_per_page, len(chapters))
        page_chapters = chapters[start_idx:end_idx]
        
        # Create a table for chapters
        table = Table(
            title=f"Chapters (Page {current_page}/{total_pages})",
            box=box.ROUNDED
        )
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Chapter", style="green")
        table.add_column("Release Date", justify="center")
        
        for chapter in page_chapters:
            table.add_row(
                str(chapter['index']),
                chapter['title'],
                chapter['release_date']
            )
        
        console.print(table)
        
        # Show navigation options
        nav_text = Text()
        if current_page > 1:
            nav_text.append("P: Previous page | ", style="yellow")
        if current_page < total_pages:
            nav_text.append("N: Next page | ", style="yellow")
        nav_text.append("0: Cancel", style="red")
        
        console.print(nav_text)
        
        # Prompt for selection
        try:
            selection = console.input("[bold cyan]Enter chapter # or navigation option: [/]").strip().lower()
            
            if selection == "0":
                return None
            elif selection == "p" and current_page > 1:
                current_page -= 1
                continue
            elif selection == "n" and current_page < total_pages:
                current_page += 1
                continue
            
            try:
                chapter_idx = int(selection) - 1
                if 0 <= chapter_idx < len(chapters):
                    return chapter_idx
                else:
                    console.print("[bold red]Invalid chapter number. Please try again.[/]")
            except ValueError:
                console.print("[bold red]Invalid input. Please enter a number or navigation option.[/]")
        except KeyboardInterrupt:
            return None 