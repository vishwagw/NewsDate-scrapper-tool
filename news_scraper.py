import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime, timedelta
import re
import webbrowser
from newspaper import Article
import textwrap

class NewsScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("News Scraper")
        self.root.geometry("900x600")
        self.root.configure(bg="#f0f0f0")
        
        # Define credible news sources
        self.sources = {
            "AP News": "https://apnews.com/search?q=",
            "Reuters": "https://www.reuters.com/search/news?blob=",
            "BBC": "https://www.bbc.co.uk/search?q=",
            "NPR": "https://www.npr.org/search?query=",
            "The Guardian": "https://www.theguardian.com/search?q=",
            "Al Jazeera": "https://www.aljazeera.com/search/",
            "CNN": "https://www.cnn.com/search?q=",
            "The New York Times": "https://www.nytimes.com/search?query="
        }
        
        # Store results
        self.results = []
        
        # Create GUI
        self.create_widgets()
    
    def create_widgets(self):
        # Search frame
        search_frame = tk.Frame(self.root, bg="#f0f0f0")
        search_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Search label
        search_label = tk.Label(search_frame, text="Enter search query:", bg="#f0f0f0", font=("Arial", 12))
        search_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Search entry
        self.search_entry = tk.Entry(search_frame, width=40, font=("Arial", 12))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", self.start_search)
        
        # Search button
        self.search_button = tk.Button(search_frame, text="Search", command=self.start_search, bg="#4a7abc", fg="white", font=("Arial", 11, "bold"), padx=15)
        self.search_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        self.progress.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 10))
        
        # Results frame with tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Articles tab
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="Articles")
        
        # Create treeview for results
        columns = ("source", "title", "date", "relevance")
        self.tree = ttk.Treeview(self.results_frame, columns=columns, show="headings")
        
        # Configure columns
        self.tree.heading("source", text="Source")
        self.tree.heading("title", text="Title")
        self.tree.heading("date", text="Date")
        self.tree.heading("relevance", text="Relevance")
        
        self.tree.column("source", width=100)
        self.tree.column("title", width=400)
        self.tree.column("date", width=100)
        self.tree.column("relevance", width=80)
        
        # Add scrollbar to treeview
        scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double click to open article
        self.tree.bind("<Double-1>", self.show_article_content)
        
        # Summary tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Article Preview")
        
        # Article content display
        self.article_text = scrolledtext.ScrolledText(self.summary_frame, wrap=tk.WORD, font=("Arial", 11))
        self.article_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Open in browser button (initially hidden)
        self.open_button_frame = tk.Frame(self.summary_frame, bg="#f0f0f0")
        self.open_button_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        self.open_button = tk.Button(self.open_button_frame, text="Open in Browser", 
                                     command=self.open_in_browser, bg="#4a7abc", fg="white", 
                                     font=("Arial", 11))
        self.open_button.pack(side=tk.RIGHT)
        self.current_url = None
    
    def start_search(self, event=None):
        query = self.search_entry.get().strip()
        if not query:
            self.status_var.set("Please enter a search query")
            return
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []
        self.article_text.delete(1.0, tk.END)
        self.current_url = None
        
        # Update status
        self.status_var.set(f"Searching for: {query}")
        self.search_button.config(state=tk.DISABLED)
        
        # Start progress bar
        self.progress.start()
        
        # Create and start the search thread
        search_thread = threading.Thread(target=self.search_news, args=(query,))
        search_thread.daemon = True
        search_thread.start()
    
    def search_news(self, query):
        try:
            # Search each source
            for source, base_url in self.sources.items():
                self.status_var.set(f"Searching {source}...")
                try:
                    # Construct search URL
                    search_url = base_url + query.replace(" ", "+")
                    
                    # Send request
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    response = requests.get(search_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        # Parse the response
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract articles based on source-specific selectors
                        articles = self.extract_articles(soup, source, search_url)
                        
                        # Add to results
                        self.results.extend(articles)
                    
                except Exception as e:
                    print(f"Error searching {source}: {e}")
            
            # Sort results by date (newest first) and relevance
            self.results.sort(key=lambda x: (x['relevance'], x['date_obj'] if x['date_obj'] else datetime.min), reverse=True)
            
            # Update the UI with results
            self.root.after(0, self.update_results)
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Error during search: {e}"))
        finally:
            self.root.after(0, self.search_complete)
    
    def extract_articles(self, soup, source, search_url):
        articles = []
        
        # Different selectors based on the source
        if source == "AP News":
            article_elements = soup.select(".PagePromo")
            for article in article_elements[:5]:  # Limit to 5 articles
                try:
                    title_elem = article.select_one(".PagePromo-title")
                    date_elem = article.select_one(".PagePromo-timestamp")
                    link_elem = article.select_one("a")
                    
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        link = link_elem['href']
                        if not link.startswith('http'):
                            link = "https://apnews.com" + link
                        
                        date_text = date_elem.text.strip() if date_elem else ""
                        date_obj = self.parse_date(date_text)
                        
                        articles.append({
                            'source': source,
                            'title': title,
                            'url': link,
                            'date': date_text,
                            'date_obj': date_obj,
                            'relevance': self.calculate_relevance(title)
                        })
                except Exception as e:
                    print(f"Error extracting AP News article: {e}")
        
        elif source == "Reuters":
            article_elements = soup.select("li.search-result")
            for article in article_elements[:5]:
                try:
                    title_elem = article.select_one("h3.search-result-title")
                    date_elem = article.select_one("time")
                    link_elem = article.select_one("a")
                    
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        link = link_elem['href']
                        if not link.startswith('http'):
                            link = "https://www.reuters.com" + link
                        
                        date_text = date_elem.text.strip() if date_elem else ""
                        date_obj = self.parse_date(date_text)
                        
                        articles.append({
                            'source': source,
                            'title': title,
                            'url': link,
                            'date': date_text,
                            'date_obj': date_obj,
                            'relevance': self.calculate_relevance(title)
                        })
                except Exception as e:
                    print(f"Error extracting Reuters article: {e}")
        
        elif source == "BBC":
            article_elements = soup.select(".ssrcss-1020bd1-Stack")
            for article in article_elements[:5]:
                try:
                    title_elem = article.select_one("h3")
                    link_elem = article.select_one("a")
                    
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        link = link_elem['href']
                        if not link.startswith('http'):
                            link = "https://www.bbc.co.uk" + link
                        
                        # BBC doesn't always have clear date elements in search results
                        date_text = "Recent"
                        date_obj = datetime.now() - timedelta(days=1)  # Assume recent
                        
                        articles.append({
                            'source': source,
                            'title': title,
                            'url': link,
                            'date': date_text,
                            'date_obj': date_obj,
                            'relevance': self.calculate_relevance(title)
                        })
                except Exception as e:
                    print(f"Error extracting BBC article: {e}")
        
        elif source == "The Guardian":
            article_elements = soup.select(".fc-item")
            for article in article_elements[:5]:
                try:
                    title_elem = article.select_one(".fc-item__title")
                    link_elem = article.select_one("a")
                    
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        link = link_elem['href']
                        
                        # Guardian doesn't always have clear date elements in search results
                        date_text = "Recent"
                        date_obj = datetime.now() - timedelta(days=1)  # Assume recent
                        
                        articles.append({
                            'source': source,
                            'title': title,
                            'url': link,
                            'date': date_text,
                            'date_obj': date_obj,
                            'relevance': self.calculate_relevance(title)
                        })
                except Exception as e:
                    print(f"Error extracting Guardian article: {e}")
        
        # Generic extraction for other sources
        else:
            # Look for common article patterns
            # 1. Find all links that might be articles
            link_elements = soup.find_all('a', href=True)
            
            for link in link_elements[:20]:  # Check first 20 links
                try:
                    url = link['href']
                    
                    # Skip navigation, social media, etc.
                    if self.is_likely_article_link(url, source):
                        # Make URL absolute if it's relative
                        if not url.startswith('http'):
                            if url.startswith('/'):
                                base_domain = '/'.join(search_url.split('/')[:3])
                                url = base_domain + url
                            else:
                                url = '/'.join(search_url.split('/')[:-1]) + '/' + url
                        
                        # Get title from link text or contained heading
                        title = ""
                        heading = link.find(['h1', 'h2', 'h3', 'h4'])
                        if heading:
                            title = heading.get_text().strip()
                        else:
                            title = link.get_text().strip()
                        
                        # Skip if title is too short or contains unwanted elements
                        if len(title) > 10 and not any(x in title.lower() for x in ['sign in', 'log in', 'subscribe']):
                            date_text = "Recent"
                            date_obj = datetime.now() - timedelta(days=3)  # Assume recent
                            
                            # Look for date near the link
                            date_elem = link.find_next(['time', 'span', 'div'], class_=re.compile('(date|time|published)', re.I))
                            if date_elem:
                                date_text = date_elem.get_text().strip()
                                date_obj = self.parse_date(date_text)
                            
                            # Add if not duplicate
                            if not any(a['url'] == url for a in articles):
                                articles.append({
                                    'source': source,
                                    'title': title,
                                    'url': url,
                                    'date': date_text,
                                    'date_obj': date_obj,
                                    'relevance': self.calculate_relevance(title)
                                })
                            
                            # Limit to 5 articles per source
                            if len(articles) >= 5:
                                break
                except Exception as e:
                    print(f"Error extracting generic article: {e}")
        
        return articles
    
    def is_likely_article_link(self, url, source):
        # Basic heuristics to identify article links
        url_lower = url.lower()
        
        # Skip common non-article URLs
        skip_patterns = [
            'login', 'signin', 'signup', 'register', 'subscribe', 
            'account', 'help', 'contact', 'about', 'terms', 'policy',
            'javascript', 'mailto', 'tel:', 'whatsapp', 'facebook', 
            'twitter', 'instagram', 'youtube', '.jpg', '.png', '.gif'
        ]
        
        if any(pattern in url_lower for pattern in skip_patterns):
            return False
            
        # Look for positive indicators
        article_patterns = ['/article/', '/news/', '/story/', '/20', '/archive/', 
                           'html', '/world/', '/breaking-news/', '/politics/']
        
        # Source-specific patterns
        if source == "CNN":
            return '/20' in url or '/article/' in url_lower
        elif source == "The New York Times":
            return '/20' in url or '/article/' in url_lower
        elif source == "NPR":
            return '/20' in url or '/story/' in url_lower
        elif source == "Al Jazeera":
            return '/news/' in url_lower or '/20' in url
            
        # Generic check
        return any(pattern in url_lower for pattern in article_patterns)
    
    def parse_date(self, date_text):
        try:
            # Try some common date formats
            date_text = date_text.lower().strip()
            
            # Handle "X minutes/hours ago" format
            if 'ago' in date_text:
                if 'minute' in date_text:
                    minutes = int(re.search(r'(\d+)', date_text).group(1))
                    return datetime.now() - timedelta(minutes=minutes)
                elif 'hour' in date_text:
                    hours = int(re.search(r'(\d+)', date_text).group(1))
                    return datetime.now() - timedelta(hours=hours)
                elif 'day' in date_text:
                    days = int(re.search(r'(\d+)', date_text).group(1))
                    return datetime.now() - timedelta(days=days)
                elif 'week' in date_text:
                    weeks = int(re.search(r'(\d+)', date_text).group(1))
                    return datetime.now() - timedelta(weeks=weeks)
                elif 'month' in date_text:
                    months = int(re.search(r'(\d+)', date_text).group(1))
                    return datetime.now() - timedelta(days=months*30)
                else:
                    return datetime.now() - timedelta(days=1)  # Default to yesterday
            
            # Try different date formats
            formats = [
                '%B %d, %Y', '%b %d, %Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y',
                '%d-%m-%Y', '%d %B %Y', '%d %b %Y', '%B %d %Y', '%b %d %Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_text, fmt)
                except ValueError:
                    continue
            
            # If we can't parse, assume recent
            return datetime.now() - timedelta(days=7)
        except:
            return None
    
    def calculate_relevance(self, title):
        # Simple relevance score based on matching query terms
        query = self.search_entry.get().strip().lower()
        query_terms = set(query.split())
        title_lower = title.lower()
        
        # Count how many query terms appear in the title
        matches = sum(1 for term in query_terms if term in title_lower)
        
        # Calculate relevance as percentage of matched terms
        if query_terms:
            return int((matches / len(query_terms)) * 100)
        return 0
    
    def update_results(self):
        # Update the treeview with results
        for i, article in enumerate(self.results[:30]):  # Limit to 30 results
            date_display = article['date'] if article['date'] else "Unknown"
            relevance_display = f"{article['relevance']}%"
            
            self.tree.insert('', tk.END, values=(
                article['source'],
                article['title'],
                date_display,
                relevance_display
            ), tags=('odd' if i % 2 else 'even',))
        
        # Update status
        self.status_var.set(f"Found {len(self.results)} articles")
    
    def search_complete(self):
        # Stop progress bar and re-enable search button
        self.progress.stop()
        self.search_button.config(state=tk.NORMAL)
    
    def show_article_content(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        # Get the selected article index
        item_index = self.tree.index(selected_item[0])
        if item_index < len(self.results):
            article = self.results[item_index]
            url = article['url']
            self.current_url = url
            
            # Update status
            self.status_var.set(f"Loading article from {article['source']}...")
            self.progress.start()
            
            # Switch to summary tab
            self.notebook.select(1)
            
            # Clear previous content
            self.article_text.delete(1.0, tk.END)
            self.article_text.insert(tk.END, f"Loading article: {article['title']}...\n\n")
            
            # Start thread to fetch article content
            threading.Thread(target=self.fetch_article_content, args=(url, article['title'], article['source'])).start()
    
    def fetch_article_content(self, url, title, source):
        try:
            # Use newspaper library to extract article
            article = Article(url)
            article.download()
            article.parse()
            
            # Update the text widget with article content
            content = f"Title: {title}\nSource: {source}\nURL: {url}\n\n"
            
            if article.publish_date:
                content += f"Published: {article.publish_date.strftime('%Y-%m-%d %H:%M')}\n\n"
            
            if article.authors:
                content += f"Authors: {', '.join(article.authors)}\n\n"
            
            content += "Summary:\n"
            content += textwrap.fill(article.text[:1000], width=80)
            
            if len(article.text) > 1000:
                content += "\n\n[Article truncated. Click 'Open in Browser' to read full article]"
            
            self.root.after(0, lambda: self.update_article_text(content))
            
        except Exception as e:
            error_message = f"Error loading article: {str(e)}\n\nPlease try opening in browser instead."
            self.root.after(0, lambda: self.update_article_text(error_message))
        
        finally:
            self.root.after(0, self.article_fetch_complete)
    
    def update_article_text(self, content):
        self.article_text.delete(1.0, tk.END)
        self.article_text.insert(tk.END, content)
    
    def article_fetch_complete(self):
        self.progress.stop()
        self.status_var.set("Ready")
    
    def open_in_browser(self):
        if self.current_url:
            webbrowser.open(self.current_url)
            self.status_var.set(f"Opened article in browser")

def main():
    root = tk.Tk()
    app = NewsScraperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
