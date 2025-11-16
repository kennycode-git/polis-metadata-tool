"""
Generic news/blog scraper using newspaper3k with requests-html fallback
Enhanced with Substack engagement metrics via API
Returns dual-CSV structure (Post data and OP data)

FIXED VERSION: 
- Asyncio event loop handling for Streamlit compatibility
- Enhanced Substack Reader URL resolution
"""
from typing import Dict, Tuple, Optional
from datetime import datetime
from .base_extractor import BaseExtractor
from config.settings import KNOWN_NEWS_DOMAINS
from urllib.parse import urlparse, quote_plus, urljoin
import re
import traceback
import asyncio

try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False

try:
    from requests_html import HTMLSession
    REQUESTS_HTML_AVAILABLE = True
except ImportError:
    REQUESTS_HTML_AVAILABLE = False


class NewsExtractor(BaseExtractor):
    """
    Extract metadata from news articles and blog posts
    
    Extraction Strategy:
    1. Try newspaper3k first (fast, works for traditional sites)
    2. If JavaScript detected, fallback to requests-html (cloud-friendly)
    
    Works for: News sites, Medium, Substack, personal blogs, etc.
    Enhanced: Substack/Medium posts include engagement metrics
    Returns: Tuple of (post_data, op_data) for dual-CSV output
    """
    
    def get_platform_name(self) -> str:
        return 'news'
    
    def validate_url(self) -> bool:
        """
        Validate that URL is from a recognized news/blog domain
        or looks like a blog/news site
        """
        try:
            parsed = urlparse(self.url.lower())
            domain = parsed.netloc
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check against known news domains
            for news_domain in KNOWN_NEWS_DOMAINS:
                if news_domain in domain:
                    return True
            
            # Check for blog/news patterns
            if any(pattern in domain for pattern in ['.blog', 'blog.', 'news.', '.news']):
                return True
            
            # Check for common blogging platforms
            blogging_platforms = ['medium.com', 'substack.com', 'wordpress.com', 
                                'blogger.com', 'tumblr.com', 'ghost.io']
            if any(platform in domain for platform in blogging_platforms):
                return True
            
            # If not recognized, return False
            return False
            
        except:
            return False
        
    def extract_metadata(self) -> Dict:
        """Stub - not used since we override extract() directly"""
        pass

    def extract(self) -> Tuple[Dict, Dict]:
        """
        Extract metadata using newspaper3k with requests-html fallback
        
        Returns:
            Tuple of (post_data, op_data) dictionaries for dual-CSV output
        """
        
        print("\n" + "="*80)
        print("NEWS EXTRACTOR - DEBUG MODE")
        print("="*80)
        print(f"📍 URL: {self.url}")
        print(f"📦 Newspaper3k available: {NEWSPAPER_AVAILABLE}")
        print(f"📦 requests-html available: {REQUESTS_HTML_AVAILABLE}")
        
        if not NEWSPAPER_AVAILABLE:
            raise Exception("Newspaper3k library not installed. Run: pip install newspaper3k")
        
        # 🔧 SPECIAL CASE: Normalise Substack Reader URLs
        if 'substack.com' in self.url.lower():
            print("\n" + "-"*80)
            print("[PRE-STEP] SUBSTACK URL NORMALISATION")
            print("-"*80)
            original_url = self.url
            self.url = self._resolve_substack_publication_url(self.url)
            print(f"  🌐 Original URL: {original_url}")
            print(f"  🎯 Normalised URL: {self.url}")
        
        # STEP 1: Try newspaper3k
        print("\n" + "-"*80)
        print("[STEP 1] NEWSPAPER3K EXTRACTION")

        print("-"*80)
        post_data, op_data = self._extract_with_newspaper3k()
        
        # STEP 2: Check for JavaScript blocking
        print("\n" + "-"*80)
        print("[STEP 2] JAVASCRIPT DETECTION")
        print("-"*80)
        content = post_data.get('Post_caption', '')
        print(f"  📏 Content length: {len(content)} chars")
        print(f"  📝 Content preview (first 150 chars):")
        print(f"     '{content[:150]}'")
        
        is_js_blocked = self._is_javascript_blocked(content)
        print(f"  🚫 JavaScript blocked: {is_js_blocked}")
        
        if is_js_blocked:
            print("\n" + "-"*80)
            print("[STEP 3] REQUESTS-HTML FALLBACK")
            print("-"*80)
            
            if not REQUESTS_HTML_AVAILABLE:
                print("  ❌ requests-html NOT AVAILABLE")
                print("  💡 Install with: pip install requests-html")
                print("  ⚠️  Continuing with limited data...")
                post_data['Post_caption'] = f"[JS-Required Site - Install requests-html for full extraction] {content[:200]}"
            else:
                print("  ✓ requests-html is available")
                print("  🔄 Attempting JavaScript rendering...")
                try:
                    post_data, op_data = self._extract_with_requests_html()
                    print("  ✅ requests-html extraction SUCCESSFUL")
                except Exception as e:
                    print(f"  ❌ requests-html extraction FAILED")
                    print(f"     🐛 Error type: {type(e).__name__}")
                    print(f"     💬 Error message: {e}")
                    print(f"     📋 Full traceback:")
                    print(traceback.format_exc())
                    print("  ⚠️  Keeping newspaper3k data with warning...")
                    post_data['Post_caption'] = f"[JS-Required Site - Limited Extraction] {content[:200]}"
        else:
            print("\n" + "-"*80)
            print("[STEP 3] SKIPPED (No JS blocking detected)")
            print("-"*80)
        
        # STEP 4: Platform-specific enhancements
        if 'substack.com' in self.url.lower():
            print("\n" + "-"*80)
            print("[STEP 4] SUBSTACK API ENHANCEMENT")
            print("-"*80)
            engagement = self._get_substack_engagement()
            
            if engagement:
                print("  ✅ Substack API returned data:")
                print(f"     👍 Likes: {engagement.get('likes')}")
                print(f"     💬 Comments: {engagement.get('comments')}")
                print(f"     🔄 Shares: {engagement.get('shares')}")
                print(f"     👤 Author bio: {'✓ Available' if engagement.get('author_bio') else '✗ Not available'}")
                
                post_data['Post_likes'] = engagement.get('likes')
                post_data['Post_comments'] = engagement.get('comments')
                post_data['Post_shares'] = engagement.get('shares')
                
                if engagement.get('author_bio'):
                    op_data['OP_bio'] = engagement.get('author_bio')
            else:
                print("  ℹ️  Substack engagement data not available")
        
        elif 'medium.com' in self.url.lower():
            print("\n" + "-"*80)
            print("[STEP 4] MEDIUM API ENHANCEMENT")
            print("-"*80)
            engagement = self._get_medium_engagement()
            
            if engagement:
                print("  ✅ Medium API returned data:")
                print(f"     👏 Claps: {engagement.get('claps')}")
                print(f"     💬 Responses: {engagement.get('responses')}")
                print(f"     👤 Author bio: {'✓ Available' if engagement.get('author_bio') else '✗ Not available'}")
                print(f"     👥 Author followers: {engagement.get('author_followers') or 'N/A'}")
                
                post_data['Post_likes'] = engagement.get('claps')
                post_data['Post_comments'] = engagement.get('responses')
                
                if engagement.get('author_bio'):
                    op_data['OP_bio'] = engagement.get('author_bio')
                if engagement.get('author_followers'):
                    op_data['OP_followers'] = engagement.get('author_followers')
            else:
                print("  ℹ️  Medium engagement data not available")
        
        # STEP 5: Calculate engagement rate
        print("\n" + "-"*80)
        print("[STEP 5] ENGAGEMENT RATE CALCULATION")
        print("-"*80)
        if post_data.get('Post_views') and post_data.get('Post_views') > 0:
            views = post_data['Post_views']
            likes = post_data.get('Post_likes') or 0
            comments = post_data.get('Post_comments') or 0
            shares = post_data.get('Post_shares') or 0
            
            engagement_rate = ((likes + comments + shares) / views * 100)
            post_data['Post_engagement_rate'] = round(engagement_rate, 2) if engagement_rate > 0 else None
            print(f"  ✓ Engagement rate: {post_data['Post_engagement_rate']}%")
            print(f"    (Calculated from: {likes} likes + {comments} comments + {shares} shares / {views} views)")
        else:
            print(f"  ℹ️  Cannot calculate (Views: {post_data.get('Post_views')})")
        
        # FINAL SUMMARY
        print("\n" + "="*80)
        print("EXTRACTION COMPLETE - SUMMARY")
        print("="*80)
        print(f"  📝 Post_ID: {post_data.get('Post_ID')}")
        print(f"  📰 Post_title: {post_data.get('Post_title', '')[:60]}...")
        print(f"  📏 Post_caption: {len(post_data.get('Post_caption', ''))} chars")
        print(f"  👤 OP_username: {op_data.get('OP_username')}")
        print(f"  🆔 OP_ID: {op_data.get('OP_ID')}")
        print(f"  📅 Post_date: {post_data.get('Post_date')}")
        print(f"  🌐 Post_language: {post_data.get('Post_language')}")
        print(f"  👍 Engagement metrics:")
        print(f"     - Views: {post_data.get('Post_views')}")
        print(f"     - Likes: {post_data.get('Post_likes')}")
        print(f"     - Comments: {post_data.get('Post_comments')}")
        print(f"     - Shares: {post_data.get('Post_shares')}")
        print("="*80 + "\n")
        
        return (post_data, op_data)
    
    def _is_javascript_blocked(self, content: str) -> bool:
        """Check if content indicates JavaScript is required or content is clearly missing."""
        
        js_indicators = [
            'requires javascript',
            'enable javascript',
            'turn on javascript',
            'javascript is disabled',
            'unblock scripts',
            'please enable javascript',
            'checking your browser before accessing',
            'enable cookies and javascript',
        ]
        
        # Also treat our own internal warnings as JS-blocked
        internal_indicators = [
            'may require javascript or authentication',
            'unable to extract content - may require javascript',
        ]
        
        content_lower = (content or '').lower()
        matched_indicators = [ind for ind in js_indicators + internal_indicators 
                              if ind in content_lower]
        
        if matched_indicators:
            print(f"  🔍 Matched JS indicators: {matched_indicators}")
            return True
        
        # Heuristic: Substack + very short content = probably JS-only shell
        if 'substack.com' in self.url.lower() and len(content) < 200:
            print("  🔍 Heuristic: Substack + very short content → treating as JS-blocked")
            return True
        
        return False

    
    def _extract_with_requests_html(self) -> Tuple[Dict, Dict]:
        """
        Extract article content using requests-html for JavaScript-heavy sites
        Cloud-friendly alternative to Selenium
        
        FIX: Handles Streamlit's asyncio event loop conflict
        
        Returns:
            Tuple of (post_data, op_data) dictionaries
        """
        
        print("  🌐 Creating HTML session...")
        session = None
        try:
            # FIX FOR STREAMLIT: Create/get event loop in this thread
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Loop is closed")
                print("  ✓ Using existing event loop")
            except RuntimeError:
                print("  🔧 Creating new event loop for this thread (Streamlit fix)...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                print("  ✓ Event loop created and set")
            
            session = HTMLSession()
            
            print(f"  📡 Fetching URL: {self.url}")
            response = session.get(
                self.url,
                timeout=30,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-GB,en;q=0.9",
                }
            )
            print(f"  ✓ Response status: {response.status_code}")
            
            print(f"  🎬 Rendering JavaScript (this may take 10-20 seconds)...")
            response.html.render(timeout=20, sleep=2)
            print(f"  ✓ JavaScript rendered successfully")
            
            # Extract data
            print(f"  🔍 Extracting metadata...")
            title = self._requests_html_get_title(response)
            author = self._requests_html_get_author(response)
            date = self._requests_html_get_date(response)
            content = self._requests_html_get_content(response)
            language = self._requests_html_get_language(response)
            
            print(f"  📊 Extraction results:")
            print(f"     Title: {title[:60]}...")
            print(f"     Author: {author}")
            print(f"     Date: {date}")
            print(f"     Content: {len(content)} chars")
            print(f"     Language: {language}")
            
            # Generate IDs
            post_id = BaseExtractor.generate_post_id()
            op_id = BaseExtractor.generate_op_id(author)
            
            # Build dictionaries
            post_data = {
                'Post_ID': post_id,
                'Post_title': title,
                'Post_caption': content[:5000] if content else 'Content extraction incomplete',
                'Post_hashtags': None,
                'Post_type': 'article',
                'Post_date': date,
                'Post_extracted_date': datetime.now().isoformat(),
                'Post_platform': 'news',
                'Post_views': None,
                'Post_likes': None,
                'Post_shares': None,
                'Post_comments': None,
                'Post_saves': None,
                'Post_reposts': None,
                'Post_engagement_rate': None,
                'Post_url': self.url,
                'Post_language': language,
                'OP_username': author,
                'OP_ID': op_id
            }
            
            op_data = {
                'OP_username': author,
                'OP_ID': op_id,
                'OP_bio': None,
                'OP_followers': None,
                'OP_following': None,
                'OP_post': None,
                'OP_platform': 'news'
            }
            
            return (post_data, op_data)
            
        except Exception as e:
            print(f"  ❌ Exception in requests-html extraction:")
            print(f"     Type: {type(e).__name__}")
            print(f"     Message: {e}")
            raise
        finally:
            if session:
                print(f"  🔒 Closing session...")
                session.close()
    
    def _requests_html_get_title(self, response) -> str:
        """Extract title using requests-html"""
        
        try:
            selectors = ['h1', 'article h1', '.post-title', '.entry-title']
            
            for selector in selectors:
                elements = response.html.find(selector)
                if elements:
                    title = elements[0].text.strip()
                    if title and len(title) > 5:
                        print(f"       ✓ Found title via selector: {selector}")
                        return title
            
            # Fallback to page title
            title_elements = response.html.find('title')
            if title_elements:
                print(f"       ✓ Using page title as fallback")
                return title_elements[0].text.strip()
            
            print(f"       ⚠ No title found")
            return "No title found"
            
        except Exception as e:
            print(f"       ❌ Error extracting title: {e}")
            return "No title found"
    
    def _requests_html_get_author(self, response) -> str:
        """Extract author using requests-html"""
        
        try:
            selectors = [
                "[rel='author']",
                '.author-name',
                '.by-author',
                "[class*='author']",
            ]
            
            for selector in selectors:
                elements = response.html.find(selector)
                if elements:
                    author = elements[0].text.strip()
                    if author and len(author) > 2 and len(author) < 100:
                        print(f"       ✓ Found author via selector: {selector}")
                        return author
            
            # Try meta tags
            meta_author = response.html.find("meta[name='author']", first=True)
            if meta_author:
                author = meta_author.attrs.get('content', '')
                if author:
                    print(f"       ✓ Found author in meta tag")
                    return author
            
            # Special handling for Substack
            if 'substack.com' in self.url.lower():
                from urllib.parse import urlparse
                parsed = urlparse(self.url)
                if '.substack.com' in parsed.netloc:
                    username = parsed.netloc.split('.substack.com')[0]
                    if username and username != 'www':
                        print(f"       ✓ Extracted Substack author from domain")
                        return username
            
            print(f"       ⚠ No author found, using default")
            return "Editorial Team"
            
        except Exception as e:
            print(f"       ❌ Error extracting author: {e}")
            return "Editorial Team"
    
    def _requests_html_get_date(self, response) -> Optional[str]:
        """Extract publish date using requests-html"""
        
        try:
            # Try time elements
            time_elements = response.html.find('time')
            for element in time_elements:
                date_str = element.attrs.get('datetime', '')
                if date_str:
                    print(f"       ✓ Found date in time element")
                    return date_str
            
            # Try meta tags
            meta_selectors = [
                "meta[property='article:published_time']",
                "meta[name='publication_date']",
                "meta[name='datePublished']",
            ]
            
            for selector in meta_selectors:
                meta = response.html.find(selector, first=True)
                if meta:
                    date_str = meta.attrs.get('content', '')
                    if date_str:
                        print(f"       ✓ Found date in meta: {selector}")
                        return date_str
            
            print(f"       ⚠ No date found")
            return None
            
        except Exception as e:
            print(f"       ❌ Error extracting date: {e}")
            return None
    
    def _requests_html_get_content(self, response) -> str:
        """Extract article content using requests-html"""
        
        try:
            selectors = [
                'article',
                '.post-content',
                '.entry-content',
                '.article-content',
                'main',
            ]
            
            for selector in selectors:
                elements = response.html.find(selector)
                if elements:
                    paragraphs = elements[0].find('p')
                    content_parts = [p.text.strip() for p in paragraphs if p.text.strip()]
                    
                    if content_parts:
                        content = ' '.join(content_parts)
                        if len(content) > 100:
                            print(f"       ✓ Found content via selector: {selector}")
                            return content
            
            # Last resort
            all_paragraphs = response.html.find('p')
            content_parts = [p.text.strip() for p in all_paragraphs if p.text.strip() and len(p.text.strip()) > 20]
            if content_parts:
                print(f"       ✓ Using all paragraphs as fallback")
                return ' '.join(content_parts[:20])
            
            print(f"       ⚠ Content extraction incomplete")
            return "Content extraction incomplete"
            
        except Exception as e:
            print(f"       ❌ Error extracting content: {e}")
            return "Content extraction incomplete"
    
    def _requests_html_get_language(self, response) -> str:
        """Extract language using requests-html"""
        
        try:
            html_elements = response.html.find('html')
            if html_elements:
                lang = html_elements[0].attrs.get('lang', '')
                if lang:
                    return lang.split('-')[0]
            
            return 'unknown'
            
        except:
            return 'unknown'
    
    def _resolve_substack_publication_url(self, url: str) -> str:
        """
        Normalise Substack Reader URLs (substack.com/home/post/...)
        to real publication URLs (username.substack.com/p/slug).

        This runs BEFORE newspaper3k so it sees real article HTML.
        """
        if 'substack.com/home/post/' not in url:
            return url

        import requests
        import re
        from urllib.parse import urlparse

        print("  🔍 Normalising Substack Reader URL before extraction...")
        try:
            resp = requests.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/120.0.0.0 Safari/537.36'
                },
                timeout=10,
                allow_redirects=True
            )
            html = resp.text
            final_url = resp.url
            print(f"  📍 Reader final URL: {final_url}")

            # Strategy 1: redirect already gave us a /p/ URL
            if '/p/' in final_url and 'substack.com/home/post/' not in final_url:
                print("  ✅ Strategy 1: redirect already resolved to publication URL")
                return final_url

            # Strategy 2: <link rel="canonical">
            m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
            if m:
                canonical_url = m.group(1)
                print(f"  🔍 Found canonical: {canonical_url}")
                if '/p/' in canonical_url:
                    print("  ✅ Strategy 2: using canonical URL")
                    return canonical_url

            # Strategy 3: <meta property="og:url">
            m = re.search(r'<meta property="og:url" content="([^"]+)"', html)
            if m:
                og_url = m.group(1)
                print(f"  🔍 Found og:url: {og_url}")
                if '/p/' in og_url:
                    print("  ✅ Strategy 3: using og:url")
                    return og_url

            # Strategy 4: any .substack.com/p/ link in HTML
            m = re.search(r'href="(https://[^"]+\.substack\.com/p/[^"]+)"', html)
            if m:
                link_url = m.group(1)
                print(f"  🔍 Found publication link: {link_url}")
                print("  ✅ Strategy 4: using publication link")
                return link_url

            print("  ⚠️ Could not normalise Reader URL; using original")
            return url

        except Exception as e:
            print(f"  ❌ Error normalising Substack Reader URL: {type(e).__name__}: {e}")
            return url


    def _parse_substack_title_and_pub(self, html: str):
        """
        From Reader HTML, extract:
          - full <title> text
          - publication name (heuristic: part after last ' - ')
        Returns: (full_title, publication_name) or (None, None)
        """
        try:
            m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            if not m:
                return None, None
            full_title = m.group(1).strip()
            publication_name = None

            # Example: "Nov7, 2025 | The Tongyi Weekly - Tongyi Lab"
            if ' - ' in full_title:
                publication_name = full_title.split(' - ')[-1].strip()

            return full_title, publication_name
        except Exception as e:
            print(f"  ❌ Error parsing Substack <title>: {type(e).__name__}: {e}")
            return None, None

    def _lookup_publication_hostname(self, publication_name: str) -> Optional[str]:
        """
        Resolve a human-readable publication name to its hostname, e.g.
        'Tongyi Lab' -> 'https://tongyilab.substack.com'

        Strategy:
        1) Try Substack's publication search API.
        2) If that fails / returns no items, slugify the name and probe
           https://{slug}.substack.com directly.
        """
        import requests
        import re

        # ---------- STEP 1: Try Substack search API ----------
        try:
            search_url = (
                "https://substack.com/api/v1/publication/search"
                f"?query={quote_plus(publication_name)}&page=0&limit=5&skipExplanation=true"
            )
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Origin": "https://substack.com",
                "Referer": "https://substack.com/discover",
            }
            print(f"  [Substack][Helper] Publication search API: {search_url}")
            resp = requests.get(search_url, headers=headers, timeout=10)
            print(f"  [Substack][Helper] Publication search status: {resp.status_code}")

            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception as e:
                    print(f"  [Substack][Helper] Failed to parse publication search JSON: {e}")
                    data = None

                if data is not None:
                    # Response shape can be array or object with 'publications'/'items'
                    if isinstance(data, list):
                        items = data
                    else:
                        items = data.get("publications") or data.get("items") or []

                    if items:
                        best = items[0]
                        host_key = (
                            best.get("subdomain")
                            or best.get("slug")
                            or best.get("handle")
                        )
                        if host_key:
                            publication_url = f"https://{host_key}.substack.com"
                            print(
                                f"  [Substack][Helper] Resolved hostname via search API: "
                                f"{publication_url}"
                            )
                            return publication_url
                    else:
                        print("  [Substack][Helper] No publications found in search API")
                else:
                    print("  [Substack][Helper] Empty/invalid JSON from search API")
            else:
                print(
                    f"  [Substack][Helper] Publication search API non-200: "
                    f"{resp.status_code}"
                )

        except Exception as e:
            print(f"  [Substack][Helper] Error in publication search API: {type(e).__name__}: {e}")

        # ---------- STEP 2: Slugify the name as a fallback ----------
        try:
            print("  [Substack][Helper] Falling back to slugified hostname guess...")
            # lower, remove non-alphanumerics
            slug = re.sub(r'[^a-z0-9]+', '', publication_name.lower())
            if not slug:
                print("  [Substack][Helper] Slugified name is empty; cannot guess hostname")
                return None

            candidate_url = f"https://{slug}.substack.com"
            print(f"  [Substack][Helper] Probing candidate: {candidate_url}")

            # HEAD first (cheaper), then GET if needed
            try:
                probe = requests.head(
                    candidate_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    allow_redirects=True,
                    timeout=5,
                )
            except Exception as e:
                print(f"  [Substack][Helper] HEAD probe failed: {e}")
                probe = None

            if not probe or probe.status_code >= 400:
                # Try GET in case HEAD is not supported properly
                try:
                    probe = requests.get(
                        candidate_url,
                        headers={"User-Agent": "Mozilla/5.0"},
                        allow_redirects=True,
                        timeout=5,
                    )
                except Exception as e:
                    print(f"  [Substack][Helper] GET probe failed: {e}")
                    probe = None

            if not probe:
                print("  [Substack][Helper] No response probing candidate hostname")
                return None

            print(
                f"  [Substack][Helper] Probe status: {probe.status_code}, "
                f"final URL: {probe.url}"
            )

            if 200 <= probe.status_code < 400:
                # Normalise to scheme+netloc of the final URL
                parsed_final = urlparse(probe.url)
                publication_url = f"{parsed_final.scheme}://{parsed_final.netloc}"
                print(
                    f"  [Substack][Helper] Hostname guess SUCCESS: {publication_url}"
                )
                return publication_url

            print("  [Substack][Helper] Candidate hostname did not resolve cleanly")
            return None

        except Exception as e:
            print(
                f"  [Substack][Helper] Error in slugified hostname fallback: "
                f"{type(e).__name__}: {e}"
            )
            return None


    def _find_post_slug_via_list(self, publication_url: str, article_title: str) -> Optional[str]:
        """
        Call {publication}/api/v1/posts?limit=50 and find the slug
        that best matches the article title from the Reader page.
        """
        import requests

        try:
            api_url = urljoin(publication_url, "/api/v1/posts?limit=50&offset=0")
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            }
            print(f"  📡 Posts list API: {api_url}")
            resp = requests.get(api_url, headers=headers, timeout=10)
            print(f"  ✓ Posts list status: {resp.status_code}")

            if resp.status_code != 200:
                return None

            data = resp.json()
            if isinstance(data, dict):
                posts = data.get("posts") or data.get("items") or data.get("data") or []
            else:
                posts = data

            if not posts:
                print("  ⚠️ Posts list empty")
                return None

            title_full = (article_title or "").strip()
            # Use the part before the final ' - ' for matching (publication often added there)
            title_base = title_full.split(' - ')[0].strip().lower()

            best_slug = None
            best_score = 0

            for post in posts:
                p_title = (post.get("title") or "").strip()
                if not p_title:
                    continue
                p_lower = p_title.lower()
                p_base = p_lower.split(' - ')[0].strip()

                score = 0
                if p_lower == title_full.lower():
                    score = 3
                elif p_base == title_base:
                    score = 2
                elif title_base in p_lower or p_lower in title_base:
                    score = 1

                if score > best_score:
                    best_score = score
                    best_slug = post.get("slug")

            if best_slug:
                print(f"  ✅ Matched post slug via list API: {best_slug} (score={best_score})")
            else:
                print("  ⚠️ Could not match post in posts list API")

            return best_slug

        except Exception as e:
            print(f"  ❌ Error in posts list API: {type(e).__name__}: {e}")
            return None

    def _fetch_substack_post_stats(self, publication_url: str, slug: str) -> Optional[Dict]:
        """
        IMPROVED: Fetch post stats with HTML scraping fallback
        """
        import time
        from bs4 import BeautifulSoup
        
        try:
            # Create session with better headers if not exists
            if not self._substack_session:
                import requests
                self._substack_session = requests.Session()
                self._substack_session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                })
            
            # STRATEGY 1: Try API first (might still work sometimes)
            api_url = urljoin(publication_url, f"/api/v1/posts/{slug}")
            print(f"  📡 Trying API: {api_url}")
            
            time.sleep(1)  # Be polite
            
            try:
                resp = self._substack_session.get(api_url, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    result = {
                        'likes': data.get('reaction_count') or data.get('likes'),
                        'comments': data.get('comment_count'),
                        'shares': data.get('restack_count'),
                    }
                    
                    if 'authors' in data and data['authors']:
                        author = data['authors'][0]
                        if author.get('bio'):
                            result['author_bio'] = author['bio']
                    
                    if result['likes'] or result['comments'] or result['shares']:
                        print(f"  ✅ API worked! likes={result['likes']}, comments={result['comments']}")
                        return result
            except Exception as api_error:
                print(f"  ⚠️ API failed: {type(api_error).__name__}")
            
            # STRATEGY 2: HTML Scraping fallback (more reliable)
            print(f"  📄 Falling back to HTML scraping...")
            post_url = f"{publication_url}/p/{slug}"
            
            time.sleep(1)
            
            resp = self._substack_session.get(post_url, timeout=15)
            
            if resp.status_code != 200:
                print(f"  ❌ HTML scraping failed: HTTP {resp.status_code}")
                return None
            
            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')
            
            result = {
                'likes': None,
                'comments': None,
                'shares': None,
                'author_bio': None,
            }
            
            # Extract from HTML using regex
            like_patterns = [
                r'(\d+)\s*like',
                r'(\d+)\s*reaction',
                r'"reaction_count":(\d+)',
            ]
            
            for pattern in like_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    result['likes'] = int(match.group(1))
                    print(f"  ✓ Found likes: {result['likes']}")
                    break
            
            comment_patterns = [
                r'(\d+)\s*comment',
                r'"comment_count":(\d+)',
            ]
            
            for pattern in comment_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    result['comments'] = int(match.group(1))
                    print(f"  ✓ Found comments: {result['comments']}")
                    break
            
            restack_patterns = [
                r'(\d+)\s*restack',
                r'"restack_count":(\d+)',
            ]
            
            for pattern in restack_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    result['shares'] = int(match.group(1))
                    print(f"  ✓ Found restacks: {result['shares']}")
                    break
            
            # Author bio
            author_meta = soup.find('meta', property='article:author')
            if author_meta:
                result['author_bio'] = author_meta.get('content')
            
            if result['likes'] or result['comments'] or result['shares']:
                print(f"  ✅ HTML scraping SUCCESS")
                return result
            
            print(f"  ⚠️ No engagement found")
            return None
            
        except Exception as e:
            print(f"  ❌ Error: {type(e).__name__}: {e}")
            return None


    def _get_substack_engagement(self) -> Optional[Dict]:
        """
        Get Substack engagement metrics and author data from API

        ENHANCED: Better handling of Reader URLs with multiple fallback strategies,
        including JSON APIs for publication + posts when HTML doesn't expose them.
        """
        try:
            import requests

            parsed = urlparse(self.url)

            publication_url = None
            post_slug = None

            # HANDLE READER URLs (substack.com/home/post/...)
            if 'substack.com/home/post/' in self.url:
                print("  🔍 Detected Reader URL, resolving to publication URL...")

                try:
                    # Fetch the Reader page HTML once
                    print("  📡 Fetching Reader page HTML...")
                    response = requests.get(
                        self.url,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        },
                        timeout=10,
                        allow_redirects=True
                    )

                    print(f"  ✓ Response status: {response.status_code}")
                    print(f"  📍 Final URL after redirects: {response.url}")

                    html = response.text

                    # Strategy 1: Redirect gave us publication URL (rare now)
                    final_url = response.url
                    if '/p/' in final_url and 'substack.com/home/post/' not in final_url:
                        parsed_final = urlparse(final_url)
                        publication_url = f"{parsed_final.scheme}://{parsed_final.netloc}"
                        post_slug = parsed_final.path.split('/p/')[-1].split('?')[0]
                        print(f"  ✅ Strategy 1 SUCCESS - Redirect gave publication URL")
                        print(f"     Publication: {parsed_final.netloc}")
                        print(f"     Slug: {post_slug}")

                    # Strategy 2: canonical URL (still often just Reader URL)
                    if not publication_url:
                        print("  🔍 Strategy 2 - Searching for canonical URL...")
                        canonical_match = re.search(
                            r'<link rel="canonical" href="([^"]+)"', html
                        )
                        if canonical_match:
                            canonical_url = canonical_match.group(1)
                            print(f"     Found canonical: {canonical_url}")

                            if '/p/' in canonical_url:
                                parsed_canonical = urlparse(canonical_url)
                                publication_url = f"{parsed_canonical.scheme}://{parsed_canonical.netloc}"
                                post_slug = parsed_canonical.path.split('/p/')[-1].split('?')[0]
                                print(f"  ✅ Strategy 2 SUCCESS")
                                print(f"     Publication: {parsed_canonical.netloc}")
                                print(f"     Slug: {post_slug}")

                    # Strategy 3: og:url
                    if not publication_url:
                        print("  🔍 Strategy 3 - Searching for og:url...")
                        og_url_match = re.search(
                            r'<meta property="og:url" content="([^"]+)"', html
                        )
                        if og_url_match:
                            og_url = og_url_match.group(1)
                            print(f"     Found og:url: {og_url}")

                            if '/p/' in og_url:
                                parsed_og = urlparse(og_url)
                                publication_url = f"{parsed_og.scheme}://{parsed_og.netloc}"
                                post_slug = parsed_og.path.split('/p/')[-1].split('?')[0]
                                print(f"  ✅ Strategy 3 SUCCESS")
                                print(f"     Publication: {parsed_og.netloc}")
                                print(f"     Slug: {post_slug}")

                    # Strategy 4: any .substack.com/p/ link
                    if not publication_url:
                        print("  🔍 Strategy 4 - Searching for any .substack.com/p/ link...")
                        link_match = re.search(
                            r'href="(https://[^"]+\.substack\.com/p/[^"]+)"', html
                        )
                        if link_match:
                            link_url = link_match.group(1)
                            print(f"     Found link: {link_url}")

                            parsed_link = urlparse(link_url)
                            publication_url = f"{parsed_link.scheme}://{parsed_link.netloc}"
                            post_slug = parsed_link.path.split('/p/')[-1].split('?')[0]
                            print(f"  ✅ Strategy 4 SUCCESS")
                            print(f"     Publication: {parsed_link.netloc}")
                            print(f"     Slug: {post_slug}")

                    # Strategy 5: Use JSON APIs if HTML doesn't expose publication URL
                    if not publication_url or not post_slug:
                        print("  🔍 Strategy 5 - Resolving via Substack search + posts API...")
                        full_title, publication_name = self._parse_substack_title_and_pub(html)
                        if publication_name and full_title:
                            print(f"     Parsed title: {full_title}")
                            print(f"     Parsed publication name: {publication_name}")

                            pub_api_url = self._lookup_publication_hostname(publication_name)
                            if pub_api_url:
                                publication_url = pub_api_url
                                slug_candidate = self._find_post_slug_via_list(publication_url, full_title)
                                if slug_candidate:
                                    post_slug = slug_candidate
                                    print("  ✅ Strategy 5 SUCCESS - Publication + slug via JSON APIs")

                    # If still nothing, log HTML snippet and give up
                    if not publication_url or not post_slug:
                        print("  ❌ All strategies FAILED to find publication URL and slug")
                        print("  💡 HTML preview (first 1000 chars):")
                        print(f"     {html[:1000]}")
                        return None

                except Exception as e:
                    print(f"  ❌ Error resolving Reader URL: {type(e).__name__}: {e}")
                    return None

            # HANDLE DIRECT PUBLICATION URLs (username.substack.com/p/...)
            elif '/p/' in self.url:
                publication_url = f"{parsed.scheme}://{parsed.netloc}"
                post_slug = parsed.path.split('/p/')[-1].split('?')[0]
                print(f"  ✓ Direct publication URL")
                print(f"     Publication: {parsed.netloc}")
                print(f"     Slug: {post_slug}")

            # Call API if we have both publication_url and post_slug
            if not publication_url or not post_slug:
                print("  ❌ Missing publication_url or post_slug - cannot call API")
                return None

            # Use helper to fetch stats & author bio
            stats = self._fetch_substack_post_stats(publication_url, post_slug)
            if not stats:
                print("  ⚠️ Substack post stats not available")
                return None

            return stats

        except Exception as e:
            print(f"  ❌ Substack API error: {type(e).__name__}: {e}")
            return None

    
    # [Continue with _get_medium_engagement and _extract_with_newspaper3k methods...]
    # [Copy from your original working code]
    
        """
    COMPLETE FIX for news_extractor.py - newspaper3k 403 errors

    This fixes the core issue: newspaper3k's default headers get blocked.

    APPROACH: Pre-download HTML with requests (good headers), then parse with newspaper3k
    """

    def _extract_with_newspaper3k(self) -> Tuple[Dict, Dict]:
        """
        Extract article using newspaper3k with anti-detection measures
        
        FIX: Downloads HTML with proper browser headers BEFORE giving to newspaper3k
        This prevents 403 errors from newspaper3k's basic requests
        """
        
        try:
            from newspaper import Article, Config
            import requests
            import time
            from bs4 import BeautifulSoup
            
            print(f"\nDEBUG - News Extraction for: {self.url}")
            
            # STEP 1: Download HTML ourselves with proper headers
            print(f"  📡 Downloading with browser-like headers...")
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            })
            
            # Be polite
            time.sleep(1)
            
            try:
                response = session.get(self.url, timeout=20, allow_redirects=True)
                
                if response.status_code == 403:
                    print(f"  ⚠️ 403 Forbidden - triggering JS fallback")
                    # Set a flag that will trigger requests-html fallback
                    return self._create_empty_article_with_js_flag()
                
                if response.status_code != 200:
                    print(f"  ⚠️ HTTP {response.status_code}")
                    raise Exception(f"HTTP {response.status_code} error")
                
                print(f"  ✓ Downloaded {len(response.text)} chars")
                
            except requests.exceptions.RequestException as req_error:
                print(f"  ❌ Request error: {req_error}")
                return self._create_empty_article_with_js_flag()
            
            # STEP 2: Parse with newspaper3k (using our pre-downloaded HTML)
            print(f"  🔍 Parsing with newspaper3k...")
            
            config = Config()
            config.browser_user_agent = session.headers['User-Agent']
            config.request_timeout = 20
            
            article = Article(self.url, config=config)
            
            # Give newspaper3k the HTML we downloaded (bypass its download)
            article.download_state = 2  # Mark as already downloaded
            article.html = response.text
            
            # Parse the article
            article.parse()
            
            print(f"  Title: {article.title}")
            print(f"  Authors: {article.authors}")
            print(f"  Date: {article.publish_date}")
            print(f"  Text length: {len(article.text) if article.text else 0} chars")

            # Detect if the main text is just a "enable JavaScript" placeholder
            raw_text = article.text or ''
            if self._is_javascript_blocked(raw_text):
                print("  ⚠️ Detected JS placeholder text - forcing fallback")
                return self._create_empty_article_with_js_flag()
            
            # STEP 3: Try NLP (with error suppression)
            try:
                import sys
                import io
                import warnings
                
                old_stderr = sys.stderr
                sys.stderr = io.StringIO()
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    article.nlp()
                
                sys.stderr = old_stderr
            except Exception:
                if 'old_stderr' in locals():
                    sys.stderr = old_stderr
                pass
            
            # STEP 4: Extract metadata (your existing code)
            authors = article.authors if article.authors else []
            author_name = authors[0] if authors else 'Editorial Team'
            
            # Substack author extraction from URL
            if 'substack.com' in self.url.lower():
                from urllib.parse import urlparse
                parsed = urlparse(self.url)
                
                if '/@' in parsed.path:
                    username = parsed.path.split('/@')[1].split('/')[0]
                    if username:
                        author_name = username
                        print(f"  Found Substack author from URL: {username}")
                elif parsed.netloc != 'substack.com' and '.substack.com' in parsed.netloc:
                    username = parsed.netloc.split('.substack.com')[0]
                    if username and username != 'www':
                        author_name = username
                        print(f"  Found Substack author from subdomain: {username}")
            
            # Fallback to meta tags for author
            if author_name == 'Editorial Team' and hasattr(article, 'meta_data'):
                for key in ['author', 'article:author', 'twitter:creator', 'og:author', 'parsely-author']:
                    val = article.meta_data.get(key, '')
                    if val:
                        author_name = val
                        print(f"  Found author in meta: {key} = {val}")
                        break
            
            # Publish date
            publish_date = None
            if article.publish_date:
                publish_date = article.publish_date.isoformat()
            elif hasattr(article, 'meta_data'):
                for key in ['article:published_time', 'published_time', 'publication_date', 
                        'datePublished', 'parsely-pub-date', 'article:modified_time',
                        'og:article:published_time', 'sailthru.date']:
                    val = article.meta_data.get(key, '')
                    if val:
                        publish_date = val
                        print(f"  Found date in meta: {key} = {val}")
                        break
            
            # Content extraction
            content = ''
            
            if raw_text and len(raw_text.strip()) > 50:
                content = raw_text[:5000]
                print(f"  Got {len(raw_text)} chars of text content")
            elif hasattr(article, 'meta_data'):
                for key in ['description', 'og:description', 'twitter:description', 'parsely-description']:
                    val = article.meta_data.get(key, '')
                    if val and len(val) > 20:
                        content = val[:5000]
                        print(f"  Using meta description from: {key}")
                        break
            
            if not content and hasattr(article, 'summary'):
                content = article.summary[:5000]
                print(f"  Using summary")
            
            if not content:
                content = 'Unable to extract content - may require JavaScript or authentication'
                print(f"  ⚠️ Content extraction failed")
            
            # Substack Notes handling
            if 'substack.com' in self.url.lower() and '/note/' in self.url.lower() and len(content) < 200:
                content = f"[Substack Note - Short Post] {content}"
                print(f"  ℹ️ This is a Substack Note")
            
            # Hashtags
            hashtags = []
            
            # Media URLs
            media_urls = []
            if article.top_image:
                media_urls.append(article.top_image)
            elif hasattr(article, 'meta_data'):
                og_img = article.meta_data.get('og:image', '')
                if og_img:
                    media_urls.append(og_img)
            
            if article.images:
                for img in list(article.images)[:5]:
                    if img not in media_urls:
                        media_urls.append(img)
            
            # Language
            language = 'unknown'
            if hasattr(article, 'meta_lang') and article.meta_lang:
                language = article.meta_lang
            elif hasattr(article, 'meta_data'):
                lang = article.meta_data.get('og:locale') or article.meta_data.get('language')
                if lang:
                    language = lang.split('_')[0]
            
            # Generate IDs
            post_id = BaseExtractor.generate_post_id()
            op_id = BaseExtractor.generate_op_id(author_name)
            
            # Build dictionaries
            post_data = {
                'Post_ID': post_id,
                'Post_title': article.title or 'No title found',
                'Post_caption': content,
                'Post_hashtags': ', '.join(hashtags) if hashtags else None,
                'Post_type': 'article',
                'Post_date': publish_date,
                'Post_extracted_date': datetime.now().isoformat(),
                'Post_platform': 'news',
                'Post_views': None,
                'Post_likes': None,
                'Post_shares': None,
                'Post_comments': None,
                'Post_saves': None,
                'Post_reposts': None,
                'Post_engagement_rate': None,
                'Post_url': self.url,
                'Post_language': language,
                'OP_username': author_name,
                'OP_ID': op_id
            }
            
            op_data = {
                'OP_username': author_name,
                'OP_ID': op_id,
                'OP_bio': None,
                'OP_followers': None,
                'OP_following': None,
                'OP_post': None,
                'OP_platform': 'news'
            }
            
            print(f"  ✓ Extraction complete\n")
            return (post_data, op_data)
            
        except Exception as e:
            error_msg = str(e)
            print(f"  ✗ Exception: {error_msg}\n")
            
            if 'ConnectionError' in error_msg or 'timeout' in error_msg.lower():
                raise Exception("Unable to connect to website. It may be blocking automated access.")
            elif '403' in error_msg or 'Forbidden' in error_msg:
                raise Exception("Website blocked access (403 Forbidden). May require browser access.")
            elif '404' in error_msg:
                raise Exception("Article not found (404). Check if URL is correct.")
            else:
                raise Exception(f"Failed to extract article content: {error_msg}")


    def _create_empty_article_with_js_flag(self) -> Tuple[Dict, Dict]:
        """
        Helper method: Create empty article data that triggers JS fallback
        """
        post_id = BaseExtractor.generate_post_id()
        
        post_data = {
            'Post_ID': post_id,
            'Post_title': '',
            'Post_caption': 'Requires JavaScript or authentication',  # This triggers JS detection
            'Post_hashtags': None,
            'Post_type': 'article',
            'Post_date': None,
            'Post_extracted_date': datetime.now().isoformat(),
            'Post_platform': 'news',
            'Post_views': None,
            'Post_likes': None,
            'Post_shares': None,
            'Post_comments': None,
            'Post_saves': None,
            'Post_reposts': None,
            'Post_engagement_rate': None,
            'Post_url': self.url,
            'Post_language': 'unknown',
            'OP_username': 'Editorial Team',
            'OP_ID': BaseExtractor.generate_op_id('Editorial Team')
        }
        
        op_data = {
            'OP_username': 'Editorial Team',
            'OP_ID': BaseExtractor.generate_op_id('Editorial Team'),
            'OP_bio': None,
            'OP_followers': None,
            'OP_following': None,
            'OP_post': None,
            'OP_platform': 'news'
        }
        
        return (post_data, op_data)
