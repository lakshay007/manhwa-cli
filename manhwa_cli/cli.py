#!/usr/bin/env python3
"""
Main CLI entry point for manhwa-cli
"""

import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from manhwa_cli.scraper import search_manhwa, get_chapters, get_chapter_url
from manhwa_cli.utils.display import display_search_results, display_chapters
from manhwa_cli.utils.browser import open_chapter

console = Console()

@click.command()
@click.argument('query_parts', nargs=-1)
@click.option('--limit', '-l', default=10, help='Limit the number of search results')
def main(query_parts, limit):
    """
    Browse and read manhwas from toonily.com directly from your terminal.
    
    Example: manhwa-cli solo leveling
    """
   
    query = ' '.join(query_parts) if query_parts else None
    
  
    if not query:
        welcome_text = Text("Welcome to Manhwa CLI!", style="bold magenta")
        welcome_text.append("\n\nTo get started, search for a manhwa:")
        welcome_text.append("\n\n    manhwa-cli solo leveling", style="green")
        welcome_text.append("\n\nYou can also limit the number of results:")
        welcome_text.append("\n\n    manhwa-cli martial peak --limit 5", style="green")
        
        console.print(Panel(welcome_text, box=box.ROUNDED, title="[bold cyan]Manhwa CLI", 
                           subtitle="[italic]Read manhwas from your terminal"))
        return

    try:
       
        console.print(f"[bold blue]Searching for: [/][cyan]{query}[/]")
        results = search_manhwa(query, limit)
        
        if not results:
            console.print("[bold red]No manhwas found with that query.[/]")
            return
        
       
        selected_idx = display_search_results(results)
        if selected_idx is None:
            return
        
        selected_manhwa = results[selected_idx]
        
       
        console.print(f"[bold blue]Fetching chapters for: [/][cyan]{selected_manhwa['title']}[/]")
        chapters = get_chapters(selected_manhwa['url'])
        
        if not chapters:
            console.print("[bold red]No chapters found for this manhwa.[/]")
            return
        
       
        while True:
          
            selected_chapter_idx = display_chapters(chapters)
            if selected_chapter_idx is None:
                
                break
            
            selected_chapter = chapters[selected_chapter_idx]
            
          
            chapter_url = get_chapter_url(selected_chapter['url'])
            if chapter_url:
                console.print(f"[bold green]Opening chapter: [/][cyan]{selected_chapter['title']}[/]")
                open_chapter(chapter_url, selected_chapter['title'])
                
               
                console.print()
                continue_reading = click.confirm("[yellow]Continue reading other chapters?[/]", default=True)
                if not continue_reading:
                    break
            else:
                console.print("[bold red]Failed to get chapter URL.[/]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/]")
        sys.exit(1)

if __name__ == '__main__':
    main() 