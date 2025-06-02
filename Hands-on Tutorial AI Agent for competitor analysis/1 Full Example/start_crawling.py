import hashlib
import time
from collections import deque
from datetime import date
from bs4 import BeautifulSoup
from url_normalize import url_normalize
from webcrawler_tools import get_urls, get_content, identify_static_site, generate_summary
from tools import extract_site_content
from handle_db import *

MAX_DEPTH = 1
TARGET_URL = "https://www.test.de"

def get_content_hash(html_content):
    if not html_content:
        return None
    return hashlib.sha256(html_content.encode('utf-8')).hexdigest()


def crawl_site(base_url):
    conn = get_conn()
    base_url = url_normalize(base_url)

    #child_url, parent_url, depth
    queue = deque([(base_url, None, 0)])

    visited = set([base_url])
    pages_processed = 0
    filter_prompt = """You are an expert system assisting a web scraper. 
    Your goal is to identify which of the provided candidate URLs should be designated as 'follow-up URLs'. 
    The scraper aims to hierarchically explore a website to discover and extract its main content and structure.

    **Definition of a 'Follow-up URL':**
    A 'follow-up URL' is a link that likely leads to:
    * A deeper level of the website's primary information hierarchy (e.g., sub-categories, specific item pages from a list).
    * New, relevant content sections (e.g., articles, product details, distinct informational pages).
    * The next part of a sequence of primary content (e.g., next page in an article or product listing).

    **Your Task:**
    Based on the provided URL, its anchor text ('URL Text'), and the 'Surrounding Context', identify which URLs are valuable 'follow-up URLs'.

    **Criteria for INCLUSION (these ARE likely 'Follow-up URLs'):**
    1.  **Primary Content Navigation:** Links whose text or context suggests they lead to main sections, articles, product pages, detailed information pages, or important sub-categories. (e.g., "Read More", "Product Details", "Next Page" of an article/listing, category names).
    2.  **Hierarchical Progression:** URLs that appear to navigate deeper into the site's specific content areas, rather than to general or auxiliary pages.
    3.  **Core Offerings:** Links directly related to the website's main purpose or the information it primarily offers.

    **Criteria for EXCLUSION (these are generally NOT 'Follow-up URLs'):**
    1.  **Auxiliary/Utility Links:** 'Privacy Policy', 'Terms of Service', 'Contact Us', 'About Us', 'Login', 'Register', 'My Account', 'Sitemap' (unless it's clearly a primary tool for finding main content sections), 'Cookie Policy', 'Accessibility Statement', 'Impressum', 'FAQ'.
    2.  **External & Ad Links:** Links pointing to a completely different domain or subdomain, or links that are clearly advertisements.
    3.  **Social Media:** Links to platforms like Facebook, Twitter, LinkedIn, Instagram, YouTube, etc.
    4.  **Non-Content Actions/Meta Links:** 'Share this page', 'Print version', 'Download PDF', 'Add to Cart' 'Back to top', 'Subscribe to newsletter'.
    5.  **Superficial or Repetitive Navigation:** Pagination for user comments, links that seem to cycle back without offering new primary content, or links to language/country selectors if not part of the core scraping task.
    6.  **Unlikely to be Content:** Links with generic text like "click here" *unless* the context strongly suggests it leads to relevant follow-up content.

    Focus on selecting URLs that will help the scraper efficiently map out and extract the website's significant content and structure."""

    while queue:
        current_url, parent_url, depth = queue.popleft()
        static = retrieve_page(conn, current_url, ['static'])
        print(f"Static: {static}")
        if static:
            continue

        html_content = extract_site_content(current_url, return_raw_html=True)

        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.body

        page_exists = retrieve_page(conn, current_url, ['id', 'content_hash']) #retrieve_id_hash(conn, current_url)
        new_content_hash = get_content_hash(body)

        if page_exists:
            id, old_content_hash = page_exists
            if new_content_hash != old_content_hash:
                content = get_content(html_content)
                update_page(conn, id, new_content_hash, content)
        else:
            content = get_content(html_content)
            static = identify_static_site(current_url, html_content)
            add_new_page(conn, current_url, parent_url, static, new_content_hash, content)

        pages_processed += 1

        if depth < MAX_DEPTH:
            follow_up_url = get_urls(html_content, current_url, filter_prompt)
            for url in follow_up_url:
                clean_url = url_normalize(url['url'])
                if clean_url not in visited:
                    visited.add(clean_url)
                    queue.append((clean_url, current_url, depth+1))

        time.sleep(2)

    conn.close()

def create_summary():
    today_date_str = date.today().isoformat()
    conn = get_conn()
    results = get_pages_by_date(conn, today_date_str)
    out = generate_summary(results)
    add_summary(conn, out)
    conn.close()

if __name__ == "__main__":
    print(f"Running Playwright HTML Cleaner (Current time: {time.strftime('%Y-%m-%d %H:%M:%S %Z')})")
    init_db()
    crawl_site(TARGET_URL)
    create_summary()
