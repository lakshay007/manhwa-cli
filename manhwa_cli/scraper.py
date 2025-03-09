"""
Scraper module for toonily.com
"""

import requests
import cloudscraper
from bs4 import BeautifulSoup
from rich.console import Console
import time
import random
from urllib.parse import urljoin, quote_plus
from rich.progress import Progress


BASE_URL = "https://toonily.com"
SEARCH_URL = f"{BASE_URL}/wp-admin/admin-ajax.php"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

console = Console()


scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'darwin',
        'desktop': True
    }
)

def search_manhwa(query, limit=10):
    """
    Search for manhwas on toonily.com
    
    Args:
        query (str): Search query
        limit (int): Maximum number of results to return
        
    Returns:
        list: List of dictionaries containing manhwa info
    """
    try:
    
        encoded_query = quote_plus(query)
        search_url = f"{BASE_URL}/search/{encoded_query}"
        console.print(f"[yellow]Trying exact search URL: {search_url}[/]")
        
        results = []
        
        try:
       
            response = scraper.get(search_url, timeout=15)
            console.print(f"[yellow]Search page response: {response.status_code}[/]")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
            
                result_count_el = soup.select_one('h1.h4') or soup.select_one('h1.archive-title')
                if result_count_el:
                    count_text = result_count_el.text.strip()
                    console.print(f"[yellow]Search results heading: {count_text}[/]")
                
               
                result_container = soup.select_one('.page-listing-item')
                if result_container:
                  
                    manga_items = result_container.select('.page-item-detail.manga')
                    console.print(f"[green]Found {len(manga_items)} manga items in search results[/]")
                    
                 
                    for item in manga_items:
                     
                        
                   
                        title_el = item.select_one('.post-title h3 a')
                        if title_el:
                            title = title_el.text.strip()
                            url = title_el.get('href')
                            
                            console.print(f"[green]Found manhwa: {title}[/]")
                            
                      
                            img_el = item.select_one('.img-responsive')
                            image_url = img_el.get('src') or img_el.get('data-src') if img_el else None
                            
                          
                            rating_el = item.select_one('#averagerate')
                            rating = rating_el.text.strip() if rating_el else "N/A"
                            
                          
                            views_el = item.select_one('.item:has(.icon.ion-md-eye)')
                            views = views_el.text.strip() if views_el else "N/A"
                            
                         
                            if not any(r.get('title') == title for r in results):
                                results.append({
                                    'title': title,
                                    'url': url,
                                    'image_url': image_url,
                                    'rating': rating,
                                    'views': views
                                })
                else:
                    console.print("[yellow]Could not find the result container, trying alternate method[/]")
                    # Try a more general approach - find all .page-item-detail.manga elements
                    manga_items = soup.select('.page-item-detail.manga')
                    console.print(f"[yellow]Found {len(manga_items)} manga items with alternate method[/]")
                    
                    for item in manga_items:
                        title_el = item.select_one('.post-title h3 a')
                        if title_el:
                            title = title_el.text.strip()
                            url = title_el.get('href')
                            
                            console.print(f"[green]Found manhwa: {title}[/]")
                            
                         
                            img_el = item.select_one('.img-responsive')
                            image_url = img_el.get('src') if img_el else None
                            
                            rating_el = item.select_one('#averagerate')
                            rating = rating_el.text.strip() if rating_el else "N/A"
                            
                          
                            if not any(r.get('title') == title for r in results):
                                results.append({
                                    'title': title,
                                    'url': url,
                                    'image_url': image_url,
                                    'rating': rating
                                })
                
        
                if not results:
                    console.print("[yellow]No results found with primary method, trying alternate URL...[/]")
                    alt_search_url = f"{BASE_URL}/?s={encoded_query}&post_type=wp-manga"
                    console.print(f"[yellow]Trying alternate search URL: {alt_search_url}[/]")
                    
                    alt_response = scraper.get(alt_search_url, timeout=15)
                    if alt_response.status_code == 200:
                        alt_soup = BeautifulSoup(alt_response.text, 'html.parser')
                        
                     
                        alt_items = alt_soup.select('.page-item-detail.manga')
                        
                        console.print(f"[yellow]Found {len(alt_items)} items with alternate method[/]")
                        
                        for item in alt_items:
                            title_el = item.select_one('.post-title h3 a')
                            
                            if title_el:
                                title = title_el.text.strip()
                                url = title_el.get('href')
                                
                                console.print(f"[green]Found manhwa with alternate method: {title}[/]")
                      
                                img_el = item.select_one('.img-responsive')
                                image_url = img_el.get('src') if img_el else None
                                
                                rating_el = item.select_one('#averagerate')
                                rating = rating_el.text.strip() if rating_el else "N/A"
                                
                           
                                if not any(r.get('title') == title for r in results):
                                    results.append({
                                        'title': title,
                                        'url': url,
                                        'image_url': image_url,
                                        'rating': rating
                                    })
            
        except Exception as e:
            console.print(f"[red]Error with search: {str(e)}[/]")
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/]")
        
     
        if not results:
            console.print("[yellow]No results found with direct methods, trying API...[/]")
            try:
              
                search_params = {
                    "action": "madara_load_more",
                    "page": 0,
                    "template": "madara-core/content/content-search",
                    "vars[s]": query,
                    "vars[orderby]": "relevance",
                    "vars[paged]": 1,
                    "vars[template]": "search",
                    "vars[post_type]": "wp-manga",
                    "vars[post_status]": "publish",
                }
                
                api_response = scraper.post(SEARCH_URL, data=search_params, timeout=15)
                if api_response.status_code == 200:
                    api_soup = BeautifulSoup(api_response.text, 'html.parser')
                    api_items = api_soup.select('.page-item-detail.manga')
                    
                    console.print(f"[yellow]API search found {len(api_items)} items[/]")
                    
                    for item in api_items:
                        title_el = item.select_one('.post-title h3 a')
                        if title_el:
                            title = title_el.text.strip()
                            url = title_el.get('href')
                            
                         
                            if not any(r.get('title') == title for r in results):
                                console.print(f"[green]Found manhwa with API: {title}[/]")
                                
                                img_el = item.select_one('.img-responsive')
                                image_url = img_el.get('src') if img_el else None
                                
                                rating_el = item.select_one('#averagerate')
                                rating = rating_el.text.strip() if rating_el else "N/A"
                                
                                results.append({
                                    'title': title,
                                    'url': url,
                                    'image_url': image_url,
                                    'rating': rating
                                })
            except Exception as e:
                console.print(f"[red]Error with API search: {str(e)}[/]")
        
     
        if results:
            console.print(f"[green]Found a total of {len(results)} results[/]")
            return results[:limit]
        else:
            console.print("[red]No manhwas found with that query.[/]")
            return []
    
    except Exception as e:
        console.print(f"[red]Error searching for manhwas: {str(e)}[/]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/]")
        return []

def get_chapters(manhwa_url):
    """
    Get all chapters for a specific manhwa
    
    Args:
        manhwa_url (str): URL of the manhwa
        
    Returns:
        list: List of dictionaries containing chapter info
    """
    try:
        console.print(f"[yellow]Fetching chapters from {manhwa_url} with cloudscraper...[/]")
        response = scraper.get(manhwa_url, timeout=15)
        console.print(f"[yellow]Response status: {response.status_code}[/]")
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        chapters = []
        
    
        chapter_selectors = [
            '.wp-manga-chapter',
            '.main.version-chap li',
            '.version-chap li',
            '.chapter-item',
            '.chapters li'
        ]
        
        chapter_items = []
        for selector in chapter_selectors:
            items = soup.select(selector)
            console.print(f"[yellow]Selector '{selector}' found {len(items)} items[/]")
            if items:
                chapter_items = items
                break
        
        if not chapter_items:
            console.print("[yellow]No chapters found with standard selectors. Trying alternative approach...[/]")
       
            all_links = soup.select('a')
            chapter_links = []
            for link in all_links:
                href = link.get('href', '')
                text = link.text.strip()
         
                if ('chapter' in href.lower() or 'chap-' in href.lower() or 
                    'chapter' in text.lower() or 'chap' in text.lower()):
                    chapter_links.append(link)
            
            if chapter_links:
                console.print(f"[yellow]Found {len(chapter_links)} potential chapter links[/]")
            
                for idx, link in enumerate(chapter_links):
                    title = link.text.strip()
                    url = link['href']
                    chapters.append({
                        'index': idx + 1,
                        'title': title,
                        'url': url,
                        'release_date': "N/A"
                    })
                
                return chapters
            
        for idx, item in enumerate(reversed(chapter_items)): 
            chapter_link = item.select_one('a')
            if chapter_link:
                title = chapter_link.text.strip()
                url = chapter_link['href']
                
         
                date_selectors = [
                    '.chapter-release-date', 
                    '.date', 
                    '.chapterdate',
                    'span.date'
                ]
                
                release_date = "N/A"
                for selector in date_selectors:
                    date_element = item.select_one(selector)
                    if date_element:
                        release_date = date_element.text.strip()
                        break
                
                chapters.append({
                    'index': idx + 1,
                    'title': title,
                    'url': url,
                    'release_date': release_date
                })
        
        return chapters
    except Exception as e:
        console.print(f"[red]Error getting chapters: {str(e)}[/]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/]")
        return []

def get_chapter_url(chapter_url):
    """
    Get the actual URL to view the chapter
    
    Args:
        chapter_url (str): URL of the chapter
        
    Returns:
        str: URL to view the chapter
    """
    try:
       
        console.print(f"[yellow]Fetching chapter page from {chapter_url} with cloudscraper...[/]")
        
  
        time.sleep(random.uniform(0.5, 1.5))
        
        response = scraper.get(chapter_url, timeout=15)
        console.print(f"[yellow]Response status: {response.status_code}[/]")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
        
            reader_container = soup.select_one('#reader-content') or soup.select_one('.reading-content')
            
            if reader_container:
                console.print("[green]Found reader container[/]")

                reader_url = chapter_url
                
              
                reader_link = soup.select_one('a.reading-mode') or soup.select_one('a[href*="reader"]')
                if reader_link and 'href' in reader_link.attrs:
                    reader_url = reader_link['href']
                    console.print(f"[green]Found better reader URL: {reader_url}[/]")
                    return reader_url
            
      
            return chapter_url
        else:
            console.print(f"[red]Failed to get chapter page. Status code: {response.status_code}[/]")
            return chapter_url
    except Exception as e:
        console.print(f"[red]Error getting chapter URL: {str(e)}[/]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/]")
        return chapter_url

def download_chapter_images(chapter_url, chapter_title):
    """
    Download all images for a chapter
    
    Args:
        chapter_url (str): URL of the chapter
        chapter_title (str): Title of the chapter
        
    Returns:
        list: List of image data (bytes) or None if failed
    """
    images = []
    
    with Progress() as progress:
        task = progress.add_task(f"[cyan]Downloading {chapter_title}...", total=None)
        
        try:
      
            response = scraper.get(chapter_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
         
            reader_container = soup.select_one('#reader-content') or soup.select_one('.reading-content')
            
            if not reader_container:
                console.print("[red]Could not find reader container[/]")
       
                all_images = soup.select('img')
                image_urls = []
                
                for img in all_images:
                    src = img.get('src', '')
                    data_src = img.get('data-src', '')
                    data_lazy_src = img.get('data-lazy-src', '')
                    
            
                    img_url = data_src or data_lazy_src or src
                    
                   
                    if img_url and ('chapter' in img_url or 'manga' in img_url or 'comic' in img_url):
                        image_urls.append(img_url)
            else:
             
                image_elements = reader_container.select('img')
                console.print(f"[green]Found {len(image_elements)} images[/]")
                
                image_urls = []
                for img in image_elements:
                    src = img.get('src', '')
                    data_src = img.get('data-src', '')
                    data_lazy_src = img.get('data-lazy-src', '')
                    
                  
                    img_url = data_src or data_lazy_src or src
                    
                    if img_url:
                        image_urls.append(img_url)
            
          
            progress.update(task, total=len(image_urls))
            progress.update(task, completed=0)
            

            for i, img_url in enumerate(image_urls):
                try:
                   
                    headers = {
                        'Referer': chapter_url,
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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