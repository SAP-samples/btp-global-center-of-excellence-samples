from typing import List
from langchain_core.tools import tool
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from handle_db import get_conn
from webcrawler_tools import get_content, get_urls
import logging
from duckduckgo_search import DDGS
import streamlit as st

def init_remote():
    if 'init_remote' not in st.session_state:
        st.session_state.conn = get_conn()
        st.session_state.init_remote = True
    return st.session_state.conn
conn = init_remote()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
MAX_URL_RESULTS = 5

@tool
def search_web(query: str) -> List[str]:
    """Performs a web search using DuckDuckGo and returns a list of result URLs for competitor analysis.

        Use this tool for competitor research It can help find general news, blog posts, forum discussions,
        or the competitor's web presence via DuckDuckGo.
        Args:
            query (str): A search query focused on a competitor. Examples:
                         'CompetitorName news', 'Competitor Z company blog',
                         'customer reviews Competitor Y', 'Competitor X website'.

        Returns:
            List[str]: A list of URL strings found by DuckDuckGo, up to a maximum of 5 results.
                       Returns an empty list if the search fails or finds no results with URLs.
    """
    logger.info(f"Initiating DuckDuckGo URL search for query: '{query}'")
    urls = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=MAX_URL_RESULTS))
        if results:
            urls = [result['href'] for result in results if 'href' in result]
            logger.info(f"Found {len(urls)} URLs via DuckDuckGo for query: '{query}'")
        else:
            logger.warning(f"No results returned by DuckDuckGo for query: '{query}'")
    except Exception as e:
        logger.error(f"Error during DuckDuckGo URL search for query '{query}': {e}", exc_info=True)
    return urls



def rag(user_query : str) -> str:
    """Retrieves information that could be relevant to the users query from websites that were crawled in the past.
    Vector embeddings are used for similarity search.
    Results from the following query are returned: SELECT TOP 5 URL, PARENT_URL, LAST_UPDATED_AT, CONTENT
        FROM PAGES
        ORDER BY COSINE_SIMILARITY(
        VECTOR_EMBEDDING('user_query', 'QUERY', 'SAP_NEB.20240715'),
        EMBEDDING) DESC;
    """
    pass
    sql_retrieve_similar = f"""SELECT TOP 5 URL, PARENT_URL, LAST_UPDATED_AT, CONTENT 
        FROM PAGES
        ORDER BY COSINE_SIMILARITY(
        VECTOR_EMBEDDING('user_query', 'QUERY', 'SAP_NEB.20240715'),
        EMBEDDING) DESC;"""
    cursor = conn.cursor()
    cursor.execute(sql_retrieve_similar)
    result = cursor.fetchall()
    print(result)
    return result


MAIN_CONTENT_SELECTOR = 'body'
TAGS_TO_REMOVE = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'head', 'button', 'iframe', 'url', 'meta']

def extract_site_content(url: str, return_raw_html: bool):
    """
       Retrieves and processes a webpage to extract the main textual content AND a
       list of potential follow-up or related urls found within that content.
       When appropriate query relevant follow-up urls.

       This tool is useful when you need a comprehensive understanding of a specific
       webpage, including its primary information and pointers to related resources,
       for tasks like research, summarization, or answering questions based on the page.

       Args:
           url (str): The fully qualified URL of the webpage to fetch and process.
                      Example: "https://www.sap.com"
          return_raw_html (Boolean): If this parameter is set to true, the function returns the raw_html of the site.
                                    No follow-up links are returned.

       Returns:
           Tuple[str, List[str]]: A tuple containing two elements:
               1.  main_content (str): The cleaned text extracted from the identified
                                       main content area of the webpage. Boilerplate
                                       (like navigation, footers, scripts) is removed.
                                       On failure, this may contain an error message
                                       or be an empty string.
               2.  related_urls (List[str]): A list of absolute URLs found within or
                                              closely associated with the main content
                                              area, potentially representing follow-up
                                              reading, references, or next steps.
                                              Returns an empty list if no suitable
                                              urls are found or if processing fails.
    """
    html_content = None
    partially_cleaned_text = None
    print(f"Attempting to fetch URL: {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            page = browser.new_page(user_agent=user_agent)
            page.set_default_timeout(10000)  # 60 seconds
            print("Navigating to page...")
            # page.goto(url, wait_until='load')
            page.goto(url, wait_until='domcontentloaded')
            try:
                print(f"Waiting for selector: '{MAIN_CONTENT_SELECTOR}'")
                page.wait_for_selector(MAIN_CONTENT_SELECTOR, timeout=6000)
                print("Main content selector found.")
            except PlaywrightTimeoutError:
                print(
                    f"Warning: Main content selector '{MAIN_CONTENT_SELECTOR}' not found within timeout. Proceeding anyway.")
            # time.sleep(5) # Use cautiously, explicit waits are better
            print("Getting page content...")
            html_content = page.content()
            print(f"Successfully fetched HTML (length: {len(html_content)} characters)")
            browser.close()
    except PlaywrightTimeoutError:
        print(f"Error: Timeout while loading page {url}")
        return None
    except Exception as e:
        print(f"Error during Playwright operation: {e}")
        return None

    if return_raw_html:
        return html_content

    filter_prompt = f"""Analyze the following list of urls extracted from a webpage.
                    Identify which of these urls are likely 'follow-up urls'.
                    Definition of 'follow-up url': A url that likely leads the user to the next logical step, related content, further reading on the same topic, or a continuation of the current content (e.g., 'Next Page', 'Read More', urls within an article body discussing related concepts).
                    Exclude urls that appear to be primary navigation (even if missed by initial tag removal), advertisements, user profiles, login/logout urls, site structure urls (like 'Home'), or clearly unrelated content.
                    Base your judgment ONLY on the provided URL, url Text, and Surrounding Context for each candidate."""

    main_content = get_content(html_content)
    urls = get_urls(html_content, url, filter_prompt)
    return main_content, urls
#
# if __name__ == '__main__':
#     print(extract_site_content("https://www.test.de/Streaminganbieter-Verbraucherzentrale-mahnt-Disney-erfolgreich-ab-6220455-0/"))
