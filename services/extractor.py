import requests
from bs4 import BeautifulSoup
from newspaper import Article, Config

def extract_news_from_url(url):
    try:
        # Configuration to mimic a real browser to avoid 401: Unauthorized
        config = Config()
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        config.request_timeout = 15

        article = Article(url, config=config)
        article.download()
        article.parse()

        title = article.title.strip() if article.title else ""
        text = article.text.strip()

        # 🔥 FALLBACK: If text is too short or newspaper failed
        if len(text) < 200:
            res = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, "html.parser")

            # Try to find the title if missing
            if not title:
                og = soup.find("meta", property="og:title")
                if og and og.get("content"):
                    title = og["content"].strip()
                elif soup.title:
                    title = soup.title.text.strip()

            # Smart Fallback Extraction: Get all <p> tags from main content areas
            paragraphs = []
            # Common article containers
            for container in soup.find_all(['article', 'main', 'div'], class_=lambda x: x and ('content' in x or 'article' in x or 'post' in x or 'body' in x)):
                for p in container.find_all('p'):
                    p_text = p.get_text().strip()
                    if len(p_text) > 40:
                        paragraphs.append(p_text)

            # If still nothing, just grab every <p> on the page
            if not paragraphs:
                for p in soup.find_all('p'):
                    p_text = p.get_text().strip()
                    if len(p_text) > 40:
                        paragraphs.append(p_text)

            fallback_text = "\n".join(paragraphs)
            if len(fallback_text) > len(text):
                text = fallback_text

        if not title:
            title = "News Article"

        return {
            "title": title,
            "text": text
        }

    except Exception as e:
        print("Extractor Error:", e)
        return {
            "title": "News Article",
            "text": ""
        }
