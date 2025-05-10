import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime, timedelta
import re
import webbrowser
import textwrap
import random
import json
import os

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
        
        # Dictionary to track enabled sources
        self.source_enabled = {source: tk.IntVar(value=1) for source in self.sources}
        
        # Store results
        self.results = []
        self.search_history = []
        
        # Load search history if exists
        self.history_file = "search_history.json"
        self.load_search_history()
        
        # Create GUI
        self.create_widgets()
    
    def create_widgets(self):
        # Search frame
        search_frame = tk.Frame(self.root, bg="#f0f0f0")
        search_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Search label
        search_label = tk.Label(search_frame, text="Enter search query:", bg="#f0f0f0", font=("Arial", 12))
        search_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Search entry with history dropdown
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Combobox(search_frame, textvariable=self.search_var, width=40, font=("Arial", 12))
        self.search_entry['values'] = self.search_history
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", self.start_search)
        
        # Search button
        self.search_button = tk.Button(search_frame, text="Search", command=self.start_search, bg="#4a7abc", fg="white", font=("Arial", 11, "bold"), padx=15)
        self.search_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Source filter frame
        filter_frame = tk.Frame(self.root, bg="#f0f0f0")
        filter_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        filter_label = tk.Label(filter_frame, text="Sources:", bg="#f0f0f0", font=("Arial", 11))
        filter_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Select/Deselect All
        self.filter_all = tk.IntVar(value=1)
        cb_all = tk.Checkbutton(filter_frame, text="All", variable=self.filter_all, bg="#f0f0f0", 
                                command=self.toggle_all_sources)
        cb_all.pack(side=tk.LEFT, padx=(0, 10))
        
        # Source checkboxes in a scrollable frame
        sources_container = tk.Frame(filter_frame, bg="#f0f0f0")
        sources_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create individual source checkboxes (two rows)
        row1 = tk.Frame(sources_container, bg="#f0f0f0")
        row1.pack(side=tk.TOP, fill=tk.X)
        row2 = tk.Frame(sources_container, bg="#f0f0f0")
        row2.pack(side=tk.TOP, fill=tk.X)
        
        # Distribute sources across two rows
        sources_list = list(self.sources.keys())
        half = len(sources_list) // 2 + len(sources_list) % 2  # Ceil division
        
        for i, source in enumerate(sources_list[:half]):
            cb = tk.Checkbutton(row1, text=source, variable=self.source_enabled[source], bg="#f0f0f0")
            cb.pack(side=tk.LEFT, padx=(0, 10))
            
        for i, source in enumerate(sources_list[half:]):
            cb = tk.Checkbutton(row2, text=source, variable=self.source_enabled[source], bg="#f0f0f0")
            cb.pack(side=tk.LEFT, padx=(0, 10))
        
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
        
        # Create toolbar for articles
        articles_toolbar = tk.Frame(self.results_frame, bg="#e0e0e0")
        articles_toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # Sort options
        sort_label = tk.Label(articles_toolbar, text="Sort by:", bg="#e0e0e0")
        sort_label.pack(side=tk.LEFT, padx=(5, 5))
        
        self.sort_var = tk.StringVar(value="Relevance")
        sort_options = ["Relevance", "Date", "Source"]
        sort_menu = tk.OptionMenu(articles_toolbar, self.sort_var, *sort_options, command=self.sort_results)
        sort_menu.config(bg="#e0e0e0")
        sort_menu.pack(side=tk.LEFT, padx=(0, 10))
        
        # Export button
        export_button = tk.Button(articles_toolbar, text="Export Results", command=self.export_results, bg="#e0e0e0")
        export_button.pack(side=tk.RIGHT, padx=(0, 5))
        
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
        
        # Right-click menu for the tree
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="Open in Browser", command=self.open_selected_in_browser)
        self.tree_menu.add_command(label="Copy URL", command=self.copy_url_to_clipboard)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="View Article Content", command=self.show_selected_article_content)
        
        self.tree.bind("<Button-3>", self.show_tree_menu)
        
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
        
        # Analytics tab
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="Analytics")
        
        # Simple analytics display
        self.analytics_text = scrolledtext.ScrolledText(self.analytics_frame, wrap=tk.WORD, font=("Arial", 11))
        self.analytics_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def toggle_all_sources(self):
        """Toggle all source checkboxes based on the 'All' checkbox"""
        all_value = self.filter_all.get()
        for source in self.sources:
            self.source_enabled[source].set(all_value)
    
    def start_search(self, event=None):
        """Start the search process"""
        query = self.search_var.get().strip()
        if not query:
            self.status_var.set("Please enter a search query")
            return
        
        # Add to search history if not already there
        if query not in self.search_history:
            self.search_history.append(query)
            if len(self.search_history) > 10:
                self.search_history.pop(0)  # Keep history to 10 items
            self.search_entry['values'] = self.search_history
            self.save_search_history()
        
        # Get selected sources
        selected_sources = {source: base_url for source, base_url in self.sources.items() 
                          if self.source_enabled[source].get() == 1}
        
        if not selected_sources:
            self.status_var.set("Please select at least one news source")
            return
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []
        self.article_text.delete(1.0, tk.END)
        self.current_url = None
        self.analytics_text.delete(1.0, tk.END)
        
        # Update status
        self.status_var.set(f"Searching for: {query}")
        self.search_button.config(state=tk.DISABLED)
        
        # Start progress bar
        self.progress.start()
        
        # Create and start the search thread
        search_thread = threading.Thread(target=self.search_news, args=(query, selected_sources))
        search_thread.daemon = True
        search_thread.start()
    
    def search_news(self, query, selected_sources):
        """Search for news across selected sources"""
        try:
            # Search each selected source
            for source, base_url in selected_sources.items():
                self.status_var.set(f"Searching {source}...")
                try:
                    # Construct search URL
                    search_url = base_url + query.replace(" ", "+")
                    
                    # Send request
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Cache-Control": "max-age=0"
                    }
                    response = requests.get(search_url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        # Parse the response
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract articles based on source-specific selectors
                        articles = self.extract_articles(soup, source, search_url, query)
                        
                        # Add to results
                        self.results.extend(articles)
                    
                except Exception as e:
                    print(f"Error searching {source}: {e}")
            
            # Sort results by relevance and date
            self.results.sort(key=lambda x: (x['relevance'], x['date_obj'] if x['date_obj'] else datetime.min), reverse=True)
            
            # Update the UI with results
            self.root.after(0, self.update_results)
            
            # Generate analytics
            self.root.after(0, self.generate_analytics)
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Error during search: {e}"))
        finally:
            self.root.after(0, self.search_complete)
    
    def extract_articles(self, soup, source, search_url, query):
        """Extract article information from search results"""
        articles = []
        
        # Source-specific extraction logic for modern webpage structures (2025)
        if source == "AP News":
            # AP News - Updated selectors for 2025
            try:
                # Try multiple possible selectors
                article_elements = soup.select(".CardList-items > div") or soup.select(".PagePromo") or soup.select("[data-key='card']")
                
                for article in article_elements[:5]:
                    try:
                        # Multiple potential selectors for title elements
                        title_elem = (article.select_one(".CardHeadline h3") or 
                                    article.select_one(".PagePromo-title") or 
                                    article.select_one("h3.Component-headline") or
                                    article.select_one("h2") or
                                    article.select_one("h3"))
                        
                        # Multiple potential selectors for links
                        link_elem = article.select_one("a")
                        
                        # Multiple potential selectors for dates
                        date_elem = (article.select_one("time") or 
                                    article.select_one(".PagePromo-timestamp") or
                                    article.select_one(".CardTime-time") or
                                    article.select_one("[data-key='timestamp']"))
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = "https://apnews.com" + link
                            
                            date_text = date_elem.text.strip() if date_elem else "Recent"
                            date_obj = self.parse_date(date_text)
                            
                            articles.append({
                                'source': source,
                                'title': title,
                                'url': link,
                                'date': date_text,
                                'date_obj': date_obj,
                                'relevance': self.calculate_relevance(title, query)
                            })
                    except Exception as e:
                        print(f"Error extracting AP News article: {e}")
            except Exception as e:
                print(f"Error in AP News extraction: {e}")
        
        elif source == "Reuters":
            # Reuters - Updated selectors for 2025
            try:
                article_elements = (soup.select("li.search-result") or 
                                  soup.select(".search-result__list-item") or
                                  soup.select("[data-testid='search-result']") or
                                  soup.select(".media-story-card"))
                
                for article in article_elements[:5]:
                    try:
                        title_elem = (article.select_one("h3.search-result-title") or
                                    article.select_one("[data-testid='heading']") or
                                    article.select_one("h3") or
                                    article.select_one(".media-story-card__heading"))
                        
                        date_elem = article.select_one("time") or article.select_one(".media-story-card__datetime")
                        link_elem = article.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = "https://www.reuters.com" + link
                            
                            date_text = date_elem.text.strip() if date_elem else "Recent"
                            date_obj = self.parse_date(date_text)
                            
                            articles.append({
                                'source': source,
                                'title': title,
                                'url': link,
                                'date': date_text,
                                'date_obj': date_obj,
                                'relevance': self.calculate_relevance(title, query)
                            })
                    except Exception as e:
                        print(f"Error extracting Reuters article: {e}")
            except Exception as e:
                print(f"Error in Reuters extraction: {e}")
        
        elif source == "BBC":
            # BBC - Updated selectors for 2025
            try:
                article_elements = (soup.select(".ssrcss-1020bd1-Stack") or
                                  soup.select(".ssrcss-1krxqkx-Stack") or
                                  soup.select("[data-testid='search-result']") or
                                  soup.select(".gs-c-promo"))
                
                for article in article_elements[:5]:
                    try:
                        # Try different possible title selectors
                        title_elem = (article.select_one("h3") or 
                                    article.select_one(".gs-c-promo-heading__title") or
                                    article.select_one("[data-testid='title']"))
                        
                        link_elem = article.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem['href']
                            if not link.startswith('http'):
                                if link.startswith('/'):
                                    link = "https://www.bbc.co.uk" + link
                                else:
                                    link = "https://www.bbc.co.uk/" + link
                            
                            # BBC doesn't always have clear date elements in search results
                            date_elem = article.select_one("time") or article.select_one("[data-testid='timestamp']")
                            date_text = date_elem.text.strip() if date_elem else "Recent"
                            date_obj = self.parse_date(date_text) if date_elem else (datetime.now() - timedelta(days=1))
                            
                            articles.append({
                                'source': source,
                                'title': title,
                                'url': link,
                                'date': date_text,
                                'date_obj': date_obj,
                                'relevance': self.calculate_relevance(title, query)
                            })
                    except Exception as e:
                        print(f"Error extracting BBC article: {e}")
            except Exception as e:
                print(f"Error in BBC extraction: {e}")
        
        elif source == "NPR":
            try:
                article_elements = (soup.select(".item-info") or 
                                  soup.select(".result-item") or 
                                  soup.select(".stories-list article"))
                
                for article in article_elements[:5]:
                    try:
                        title_elem = (article.select_one("h2") or 
                                     article.select_one("h3") or 
                                     article.select_one(".title"))
                        
                        link_elem = article.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = "https://www.npr.org" + link
                            
                            date_elem = article.select_one("time") or article.select_one(".date")
                            date_text = date_elem.text.strip() if date_elem else "Recent"
                            date_obj = self.parse_date(date_text)
                            
                            articles.append({
                                'source': source,
                                'title': title,
                                'url': link,
                                'date': date_text,
                                'date_obj': date_obj,
                                'relevance': self.calculate_relevance(title, query)
                            })
                    except Exception as e:
                        print(f"Error extracting NPR article: {e}")
            except Exception as e:
                print(f"Error in NPR extraction: {e}")
                
        elif source == "The Guardian":
            try:
                article_elements = (soup.select(".fc-item") or 
                                  soup.select(".search-results__item") or 
                                  soup.select(".u-faux-block-link"))
                
                for article in article_elements[:5]:
                    try:
                        title_elem = (article.select_one("h2") or 
                                     article.select_one("h3") or 
                                     article.select_one(".fc-item__title"))
                        
                        link_elem = article.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem['href']
                            
                            date_elem = article.select_one("time") or article.select_one(".fc-item__timestamp")
                            date_text = date_elem.text.strip() if date_elem else "Recent"
                            date_obj = self.parse_date(date_text)
                            
                            articles.append({
                                'source': source,
                                'title': title,
                                'url': link,
                                'date': date_text,
                                'date_obj': date_obj,
                                'relevance': self.calculate_relevance(title, query)
                            })
                    except Exception as e:
                        print(f"Error extracting Guardian article: {e}")
            except Exception as e:
                print(f"Error in Guardian extraction: {e}")
        
        elif source == "Al Jazeera":
            try:
                article_elements = soup.select(".gc__content") or soup.select(".article-card")
                
                for article in article_elements[:5]:
                    try:
                        title_elem = article.select_one("h3") or article.select_one(".gc__title")
                        link_elem = article.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = "https://www.aljazeera.com" + link
                            
                            date_elem = article.select_one("time") or article.select_one(".date-simple")
                            date_text = date_elem.text.strip() if date_elem else "Recent"
                            date_obj = self.parse_date(date_text)
                            
                            articles.append({
                                'source': source,
                                'title': title,
                                'url': link,
                                'date': date_text,
                                'date_obj': date_obj,
                                'relevance': self.calculate_relevance(title, query)
                            })
                    except Exception as e:
                        print(f"Error extracting Al Jazeera article: {e}")
            except Exception as e:
                print(f"Error in Al Jazeera extraction: {e}")
        
        elif source == "CNN":
            try:
                article_elements = soup.select(".cnn-search__result") or soup.select(".cnn-search__result-contents")
                
                for article in article_elements[:5]:
                    try:
                        title_elem = article.select_one("h3") or article.select_one(".cnn-search__result-headline")
                        link_elem = article.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = "https://www.cnn.com" + link
                            
                            date_elem = article.select_one("time") or article.select_one(".cnn-search__result-publish-date")
                            date_text = date_elem.text.strip() if date_elem else "Recent"
                            date_obj = self.parse_date(date_text)
                            
                            articles.append({
                                'source': source,
                                'title': title,
                                'url': link,
                                'date': date_text,
                                'date_obj': date_obj,
                                'relevance': self.calculate_relevance(title, query)
                            })
                    except Exception as e:
                        print(f"Error extracting CNN article: {e}")
            except Exception as e:
                print(f"Error in CNN extraction: {e}")
        
        elif source == "The New York Times":
            try:
                article_elements = soup.select(".css-1i8vfl5") or soup.select(".css-1l4w6pd") or soup.select("[data-testid='search-bodega-result']")
                
                for article in article_elements[:5]:
                    try:
                        title_elem = article.select_one("h4") or article.select_one("[data-testid='headline']")
                        link_elem = article.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = "https://www.nytimes.com" + link
                            
                            date_elem = article.select_one("time") or article.select_one("[data-testid='publication-date']")
                            date_text = date_elem.text.strip() if date_elem else "Recent"
                            date_obj = self.parse_date(date_text)
                            
                            articles.append({
                                'source': source,
                                'title': title,
                                'url': link,
                                'date': date_text,
                                'date_obj': date_obj,
                                'relevance': self.calculate_relevance(title, query)
                            })
                    except Exception as e:
                        print(f"Error extracting NYT article: {e}")
            except Exception as e:
                print(f"Error in NYT extraction: {e}")
                
        # Generic extraction for other sources or fallback
        if not articles:
            # Look for common article patterns
            # 1. Find all links that might be articles
            link_elements = soup.find_all('a', href=True)
            
            for link in link_elements[:30]:  # Check first 30 links
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
                                'relevance': self.calculate_relevance(title, query)
                            })
                except Exception as e:
                    print(f"Error in generic extraction for {source}: {e}")
        
        return articles

    def parse_date(self, date_text):
        """Parse various date formats into a datetime object"""
        try:
            # Clean the date text
            date_text = date_text.strip().replace('\n', '').replace('\t', '')
            
            # Handle relative dates
            if 'ago' in date_text.lower():
                now = datetime.now()
                if 'hour' in date_text.lower():
                    hours = int(re.search(r'(\d+)', date_text).group(1))
                    return now - timedelta(hours=hours)
                elif 'day' in date_text.lower():
                    days = int(re.search(r'(\d+)', date_text).group(1))
                    return now - timedelta(days=days)
                elif 'minute' in date_text.lower():
                    minutes = int(re.search(r'(\d+)', date_text).group(1))
                    return now - timedelta(minutes=minutes)
                return now  # Fallback for vague relative dates
            
            # Try common date formats
            formats = [
                '%Y-%m-%d', '%d %b %Y', '%B %d, %Y', '%m/%d/%Y', '%d/%m/%Y',
                '%Y.%m.%d', '%b %d, %Y', '%d %B %Y', '%Y-%m-%dT%H:%M:%S%z'
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_text, fmt)
                except ValueError:
                    continue
            
            # Fallback: assume recent if parsing fails
            return datetime.now() - timedelta(days=1)
        except Exception as e:
            print(f"Error parsing date '{date_text}': {e}")
            return datetime.now() - timedelta(days=1)

    def calculate_relevance(self, title, query):
        """Calculate relevance score based on query match in title"""
        try:
            title_lower = title.lower()
            query_lower = query.lower()
            score = 0
            
            # Exact matches
            if query_lower in title_lower:
                score += 10
            
            # Individual word matches
            query_words = query_lower.split()
            for word in query_words:
                if word in title_lower:
                    score += 2
            
            # Proximity bonus (if multiple query words are present)
            if len(query_words) > 1 and all(word in title_lower for word in query_words):
                score += 5
            
            return score
        except Exception as e:
            print(f"Error calculating relevance: {e}")
            return 0

    def is_likely_article_link(self, url, source):
        """Determine if a URL is likely an article link"""
        try:
            # Skip common non-article patterns
            exclude_patterns = [
                '/login', '/signin', '/subscribe', '/account', '/profile',
                '/video', '/gallery', '/podcast', '/newsletter', '/comment',
                '/tag/', '/category/', '/search', '/archive', '/about',
                '/contact', '/privacy', '/terms', '#', 'javascript:', '/home'
            ]
            if any(pattern in url.lower() for pattern in exclude_patterns):
                return False
            
            # Include likely article patterns
            include_patterns = [
                '/article', '/news', '/story', '/feature', '/report',
                '/opinion', '/analysis', '/world', '/politics', '/business',
                '/technology', '/health', '/science', '/sport', '/culture',
                r'/\d{4}/\d{2}/\d{2}/',  # Date-based URLs
                r'/\d{4}-\d{2}-\d{2}-'   # Alternate date format
            ]
            if any(re.search(pattern, url.lower()) for pattern in include_patterns):
                return True
            
            # Source-specific checks
            if source == "BBC" and url.startswith('/news/'):
                return True
            if source == "Reuters" and url.startswith('/world/'):
                return True
            if source == "The Guardian" and '/article/' in url:
                return True
            
            # Fallback: check if URL is long enough and not a top-level page
            return len(url.split('/')) > 3 and not url.endswith('/')
        except Exception as e:
            print(f"Error checking article link: {e}")
            return False

    def update_results(self):
        """Update the treeview with search results"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for article in self.results:
            self.tree.insert("", tk.END, values=(
                article['source'],
                article['title'],
                article['date'],
                article['relevance']
            ))
        
        self.status_var.set(f"Found {len(self.results)} articles")

    def sort_results(self, *args):
        """Sort results based on selected criteria"""
        sort_by = self.sort_var.get()
        
        if sort_by == "Relevance":
            self.results.sort(key=lambda x: x['relevance'], reverse=True)
        elif sort_by == "Date":
            self.results.sort(key=lambda x: x['date_obj'] if x['date_obj'] else datetime.min, reverse=True)
        elif sort_by == "Source":
            self.results.sort(key=lambda x: x['source'])
        
        self.update_results()

    def show_article_content(self, event):
        """Show article content on double-click"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            title = values[1]
            
            # Find the article
            for article in self.results:
                if article['title'] == title:
                    self.fetch_article_content(article['url'], article['title'])
                    self.current_url = article['url']
                    break

    def show_selected_article_content(self):
        """Show content of selected article from right-click menu"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            title = values[1]
            
            for article in self.results:
                if article['title'] == title:
                    self.fetch_article_content(article['url'], article['title'])
                    self.current_url = article['url']
                    break

    def fetch_article_content(self, url, title):
        """Fetch and display article content"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Clear previous content
            self.article_text.delete(1.0, tk.END)
            
            # Extract main content
            content = ""
            # Try common article content selectors
            article_elements = (
                soup.select("article p") or
                soup.select(".article-body p") or
                soup.select(".story-body p") or
                soup.select(".content p") or
                soup.select("main p")
            )
            
            for elem in article_elements:
                text = elem.get_text().strip()
                if text and len(text) > 20:  # Skip short fragments
                    content += text + "\n\n"
            
            if not content:
                content = "Could not extract article content. The website may use dynamic loading or have restricted access."
            
            # Format the content
            wrapped_content = textwrap.fill(content, width=80)
            self.article_text.insert(tk.END, f"{title}\n\n{wrapped_content}")
            
            # Switch to summary tab
            self.notebook.select(self.summary_frame)
            
        except Exception as e:
            self.article_text.delete(1.0, tk.END)
            self.article_text.insert(tk.END, f"Error loading article: {e}")
            self.current_url = None

    def open_in_browser(self):
        """Open the current article in the default web browser"""
        if self.current_url:
            webbrowser.open(self.current_url)
        else:
            messagebox.showinfo("Info", "No article URL available")

    def open_selected_in_browser(self):
        """Open selected article in browser from right-click menu"""
#At this point, the code is mostly complete, but I notice the `open_selected_in_browser` method is cut off. Let's complete it and ensure all remaining methods are implemented correctly to finalize the program.

#```python
    def open_selected_in_browser(self):
        """Open selected article in browser from right-click menu"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            title = values[1]
            
            for article in self.results:
                if article['title'] == title:
                    webbrowser.open(article['url'])
                    break

    def copy_url_to_clipboard(self):
        """Copy selected article URL to clipboard"""
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            title = values[1]
            
            for article in self.results:
                if article['title'] == title:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(article['url'])
                    messagebox.showinfo("Info", "URL copied to clipboard")
                    break

    def show_tree_menu(self, event):
        """Show right-click context menu for treeview"""
        # Select item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)

    def export_results(self):
        """Export search results to a text file"""
        if not self.results:
            messagebox.showinfo("Info", "No results to export")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_search_results_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"News Search Results - {self.search_var.get()}\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for article in self.results:
                    f.write(f"Source: {article['source']}\n")
                    f.write(f"Title: {article['title']}\n")
                    f.write(f"Date: {article['date']}\n")
                    f.write(f"URL: {article['url']}\n")
                    f.write(f"Relevance: {article['relevance']}\n")
                    f.write("-" * 50 + "\n\n")
            messagebox.showinfo("Success", f"Results exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {e}")

    def generate_analytics(self):
        """Generate basic analytics about search results"""
        self.analytics_text.delete(1.0, tk.END)
        
        if not self.results:
            self.analytics_text.insert(tk.END, "No results to analyze")
            return
        
        # Count articles by source
        source_counts = {}
        for article in self.results:
            source = article['source']
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Average relevance
        avg_relevance = sum(article['relevance'] for article in self.results) / len(self.results)
        
        # Date range
        dates = [article['date_obj'] for article in self.results if article['date_obj']]
        date_range = f"{min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}" if dates else "Unknown"
        
        # Generate analytics text
        analytics = f"Search Analytics\n\n"
        analytics += f"Total Articles: {len(self.results)}\n"
        analytics += f"Average Relevance Score: {avg_relevance:.2f}\n"
        analytics += f"Date Range: {date_range}\n\n"
        analytics += "Articles by Source:\n"
        for source, count in source_counts.items():
            analytics += f"  {source}: {count}\n"
        
        self.analytics_text.insert(tk.END, analytics)

    def search_complete(self):
        """Handle search completion"""
        self.progress.stop()
        self.search_button.config(state=tk.NORMAL)
        if not self.results:
            self.status_var.set("No results found")
        else:
            self.status_var.set(f"Search complete: {len(self.results)} articles found")

    def load_search_history(self):
        """Load search history from file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.search_history = json.load(f)
            except Exception as e:
                print(f"Error loading search history: {e}")
                self.search_history = []

    def save_search_history(self):
        """Save search history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.search_history, f)
        except Exception as e:
            print(f"Error saving search history: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsScraperApp(root)
    root.mainloop()