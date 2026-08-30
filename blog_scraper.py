import re
import time
import requests
import psycopg2
from bs4 import BeautifulSoup

BASE_URL = "https://blog.python.org"
LIST_URL = f"{BASE_URL}/blog"
MAX_POSTS = 10  # keep it small for testing; raise this once it works

POST_LINK_RE = re.compile(r"^/\d{4}/\d{2}/[\w\-]+/?$")
DATE_RE = re.compile(r"[A-Z][a-z]+ \d{1,2}, \d{4}")

BORING_PHRASES = [
    "subscribe", "related links", "python.org", "python discourse",
    "developer's guide", "rss feed", "browse by tag", "cc by-nc-sa",
]


def get_with_retry(url, retries=3, delay=3):
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return requests.get(url, timeout=10)
        except requests.exceptions.ConnectionError as exc:
            last_exc = exc
            print(f"  Attempt {attempt} failed ({exc.__class__.__name__}), retrying in {delay}s...")
            time.sleep(delay)
    raise last_exc


def get_post_links():
    res = get_with_retry(LIST_URL)
    soup = BeautifulSoup(res.content, "html5lib")
    links = set()
    for a in soup.find_all("a", href=True):
        if POST_LINK_RE.match(a["href"]):
            links.add(BASE_URL + a["href"])
    return list(links)[:MAX_POSTS]


def scrape_post(url):
    res = get_with_retry(url)
    soup = BeautifulSoup(res.content, "html5lib")

    title = soup.find("h1").text.strip() if soup.find("h1") else ""

    page_text = soup.get_text(" ", strip=True)
    date_match = DATE_RE.search(page_text)
    published_date = date_match.group(0) if date_match else None

    author = None
    author_link = soup.find("a", href=re.compile(r"^/authors/"))
    if author_link:
        author = author_link.text.strip()

    paragraphs = []
    for p in soup.find_all("p"):
        text = p.text.strip()
        if not text:
            continue
        if any(phrase in text.lower() for phrase in BORING_PHRASES):
            continue
        paragraphs.append(text)
    content = "\n\n".join(paragraphs)

    return {
        "title": title,
        "url": url,
        "author": author,
        "published_date": published_date,
        "content": content,
    }


def save_to_db(posts):
    conn = psycopg2.connect(
        host="psql-db",
        port=5432,
        dbname="postgres",
        user="postgres",
        password="123456",
    )
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blog_posts (
            id SERIAL PRIMARY KEY,
            title TEXT,
            url TEXT UNIQUE,
            author TEXT,
            published_date TEXT,
            content TEXT
        );
    """)
    for post in posts:
        cur.execute("""
            INSERT INTO blog_posts (title, url, author, published_date, content)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING;
        """, (post["title"], post["url"], post["author"], post["published_date"], post["content"]))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Saved {len(posts)} posts to the database.")


if __name__ == "__main__":
    links = get_post_links()
    print(f"Found {len(links)} post links.")
    scraped = []
    for link in links:
        print("Scraping:", link)
        scraped.append(scrape_post(link))
        time.sleep(1)  # be polite to the server
    save_to_db(scraped)
