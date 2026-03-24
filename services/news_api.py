import requests
import os
import time

NEWS_API_KEY = "pub_df2aa48b954644b89117a95390c07b4f"

BASE_URL = "https://newsdata.io/api/1/news"

# ===== Phase 5: In-Memory Cache (TTL = 30 minutes) =====
_news_cache = {}
CACHE_TTL = 30 * 60  # 30 minutes in seconds


def fetch_latest_news(page=None, page_size=10, category="top"):
    """
    Fetch news from NewsData.io (Indian news).
    Category for free tier is usually 'top' or 'world'.
    Results are cached in-memory for 30 minutes per category+page key.
    """
    cache_key = f"{category}_{page}"
    now = time.time()

    # Return from cache if fresh
    if cache_key in _news_cache:
        cached_at, cached_data = _news_cache[cache_key]
        if now - cached_at < CACHE_TTL:
            return cached_data

    params = {
        "apikey": NEWS_API_KEY,
        "country": "in",
        "language": "en,hi,gu",
        "category": category if category in ["business", "entertainment", "health", "science", "sports", "technology", "politics", "world"] else "top"
    }

    # newsdata.io uses nextPage token, handle string or int (if coming from old logic)
    if page and str(page).strip() != "1":
        params["page"] = page

    try:
        response = requests.get(BASE_URL, params=params)

        if response.status_code != 200:
            print(f"NEWS DATA API ERROR ({response.status_code}): {response.text}")
            return {"results": [], "nextPage": None}

        data = response.json()
        articles = data.get("results", [])
        next_page = data.get("nextPage")

        for a in articles:
            a['url'] = a.get('link')
            a['urlToImage'] = a.get('image_url')
            a['publishedAt'] = a.get('pubDate')

        result = {"results": articles, "nextPage": next_page}
        # Store in cache
        _news_cache[cache_key] = (now, result)
        return result

    except Exception as e:
        print(f"Exception fetching news: {e}")
        return {"results": [], "nextPage": None}
