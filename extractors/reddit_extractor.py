"""
Reddit metadata extractor using JSON endpoints
No API credentials needed!
"""
from typing import Dict
import re
from .base_extractor import BaseExtractor


class RedditExtractor(BaseExtractor):
    """
    Extract metadata from Reddit posts using JSON endpoints
    No authentication required - just add .json to any Reddit URL!
    """
    
    def get_platform_name(self) -> str:
        return 'reddit'
    
    def validate_url(self) -> bool:
        """Validate Reddit URL"""
        # Matches standard Reddit URLs and short links
        patterns = [
            r'reddit\.com/r/[\w]+/comments/',
            r'redd\.it/',  # Short URLs
            r'reddit\.com/user/[\w]+/comments/',  # User posts
        ]
        return any(re.search(pattern, self.url) for pattern in patterns)
    
    def extract_metadata(self) -> Dict:
        """Extract metadata using Reddit's public JSON endpoint"""
        
        try:
            import requests
            
            # Handle short URLs (redd.it)
            if 'redd.it' in self.url:
                print("  Expanding short URL...")
                response = requests.head(self.url, allow_redirects=True, timeout=10)
                self.url = response.url
                print(f"  Expanded to: {self.url}")
            
            # Remove any existing .json and query parameters
            clean_url = self.url.split('?')[0].rstrip('/')
            
            # Add .json extension
            json_url = f"{clean_url}.json"
            
            print(f"  Fetching: {json_url}")
            
            # Reddit requires a User-Agent header
            headers = {
                'User-Agent': 'Polis-Metadata-Tool/1.0 (Disinformation Research; Contact: your-email@example.com)'
            }
            
            # Fetch JSON data
            response = requests.get(json_url, headers=headers, timeout=15)
            
            if response.status_code == 403:
                raise Exception("Access forbidden - Reddit may be rate limiting. Wait a moment and try again.")
            elif response.status_code == 404:
                raise Exception("Post not found - URL may be invalid or post was deleted.")
            elif response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            
            # Parse JSON
            data = response.json()
            
            # Reddit returns: [post_data, comments_data]
            # We want the post data
            post_listing = data[0]['data']['children'][0]['data']
            
            # Extract metadata
            metadata = {
                'title': post_listing.get('title'),
                'author': post_listing.get('author', '[deleted]'),
                'author_id': post_listing.get('author_fullname'),
                'content': post_listing.get('selftext', ''),  # Text content (for text posts)
                'publish_date': self._format_timestamp(post_listing.get('created_utc')),
                'url': f"https://reddit.com{post_listing.get('permalink')}",
                
                # Engagement metrics (Reddit-specific)
                'views': None,  # Reddit doesn't expose view count publicly
                'likes': post_listing.get('ups', 0),  # Upvotes
                'score': post_listing.get('score', 0),  # Net score (upvotes - downvotes)
                'upvote_ratio': post_listing.get('upvote_ratio', 0),  # Percentage of upvotes
                'comments': post_listing.get('num_comments', 0),
                'shares': post_listing.get('num_crossposts', 0),  # Crossposts
                
                # Additional Reddit-specific data
                'subreddit': post_listing.get('subreddit'),
                'subreddit_subscribers': post_listing.get('subreddit_subscribers'),
                'awards': post_listing.get('total_awards_received', 0),
                'is_video': post_listing.get('is_video', False),
                'over_18': post_listing.get('over_18', False),
                'locked': post_listing.get('locked', False),
                'stickied': post_listing.get('stickied', False),
                
                # Flair as hashtags
                'hashtags': self._extract_flair(post_listing),
                
                # Media URLs
                'media_urls': self._extract_media_urls(post_listing),
                'thumbnail': post_listing.get('thumbnail') if post_listing.get('thumbnail') not in ['self', 'default', 'nsfw', 'spoiler'] else None,
            }
            
            # Log success
            print(f"  ✓ Title: {metadata['title'][:60]}...")
            print(f"  ✓ Subreddit: r/{metadata['subreddit']}")
            print(f"  ✓ Score: {metadata['score']} (↑{metadata['likes']}, {metadata['upvote_ratio']*100:.1f}% upvoted)")
            print(f"  ✓ Comments: {metadata['comments']}")
            if metadata['awards'] > 0:
                print(f"  ✓ Awards: {metadata['awards']}")
            
            return metadata
            
        except requests.exceptions.Timeout:
            raise Exception("Request timeout - Reddit took too long to respond")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - Could not reach Reddit")
        except KeyError as e:
            raise Exception(f"Unexpected Reddit JSON structure: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to extract Reddit metadata: {str(e)}")
    
    def _format_timestamp(self, unix_time: float) -> str:
        """Convert Unix timestamp to ISO format"""
        if not unix_time:
            return None
        
        from datetime import datetime
        return datetime.fromtimestamp(unix_time).isoformat()
    
    def _extract_flair(self, post_data: Dict) -> list:
        """Extract flair and convert to hashtag format"""
        hashtags = []
        
        # Link flair (post category)
        link_flair = post_data.get('link_flair_text')
        if link_flair:
            # Convert to hashtag format (remove spaces, add #)
            tag = link_flair.replace(' ', '_').replace('-', '_')
            hashtags.append(f"#{tag}")
        
        # Author flair (optional)
        author_flair = post_data.get('author_flair_text')
        if author_flair and author_flair != link_flair:
            tag = author_flair.replace(' ', '_').replace('-', '_')
            hashtags.append(f"#{tag}")
        
        return hashtags
    
    def _extract_media_urls(self, post_data: Dict) -> list:
        """Extract media URLs from Reddit post"""
        urls = []
        
        # Post URL (if it's a link post)
        post_url = post_data.get('url')
        is_self = post_data.get('is_self', False)  # Text post
        
        if post_url and not is_self:
            # External link or Reddit-hosted media
            urls.append(post_url)
        
        # Preview images
        if 'preview' in post_data:
            try:
                images = post_data['preview']['images']
                for img in images:
                    source = img.get('source', {})
                    if source.get('url'):
                        # Decode HTML entities in URL
                        import html
                        clean_url = html.unescape(source['url'])
                        urls.append(clean_url)
            except (KeyError, TypeError):
                pass
        
        # Reddit video
        if post_data.get('is_video'):
            try:
                video_url = post_data['media']['reddit_video']['fallback_url']
                urls.append(video_url)
            except (KeyError, TypeError):
                pass
        
        # Gallery images
        if 'gallery_data' in post_data:
            try:
                items = post_data['gallery_data']['items']
                media_metadata = post_data.get('media_metadata', {})
                
                for item in items:
                    media_id = item.get('media_id')
                    if media_id and media_id in media_metadata:
                        media_info = media_metadata[media_id]
                        if 's' in media_info and 'u' in media_info['s']:
                            import html
                            clean_url = html.unescape(media_info['s']['u'])
                            urls.append(clean_url)
            except (KeyError, TypeError):
                pass
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls