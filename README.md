# Metadata Extraction Tool

Extract comprehensive metadata from social media posts for disinformation research and analysis.

## Features

- **Multi-Platform Support:** Facebook, YouTube, TikTok, Reddit, News articles
- **Comprehensive Data:** Engagement metrics, author info, content analysis
- **Dual CSV Export:** Separate Post and Original Poster (OP) data tables
- **Real-time Processing:** Instant metadata extraction via web interface

## Supported Platforms

| Platform | Metrics Extracted |
|----------|------------------|
| Facebook | Views, Likes, Comments, Shares, Author info |
| YouTube | Views, Likes, Comments, Channel data |
| Reddit (not fully tested) | Upvotes, Comments, Subreddit, Author karma |
| TikTok | Views, Likes, Comments, Shares, Author stats |

Coming soon:
| News/Blogs | Author, publish date, article content |

## Deployment

### Streamlit Cloud (Recommended)

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add secrets (YouTube API key) in dashboard settings
5. Deploy!

### Local Development

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/polis-metadata-tool.git
cd polis-metadata-tool

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
echo "YOUTUBE_API_KEY=your_key_here" > .env

# Run app
streamlit run app.py
```

## Configuration

### Required: YouTube API Key

1. Get a key from [Google Cloud Console](https://console.cloud.google.com)
2. Add to Streamlit Cloud secrets OR local `.env` file

### Optional: Facebook Cookies

For better Facebook extraction, provide cookies via the sidebar UI:
- Click "Facebook Authentication" in sidebar
- Paste your cookie string
- Format: `c_user=123456; xs=abcd...`

## Usage

1. Enter a social media URL
2. Click "Extract Metadata"
3. View results in dashboard
4. Download CSV files (Post + OP data)

## Data Output

### Post Data CSV
- Post ID, Caption, Hashtags
- Engagement metrics (views, likes, comments, shares)
- Publish date, platform, language

### Original Poster (OP) Data CSV
- Username, Bio
- Follower/Following counts
- Total post count

## Privacy & Security

- ✅ No data is stored permanently
- ✅ API keys kept in Streamlit secrets
- ✅ Facebook cookies used only during session
- ✅ All processing happens server-side

## License

MIT License - See LICENSE file for details

## Support

For issues or questions, open a GitHub issue.
