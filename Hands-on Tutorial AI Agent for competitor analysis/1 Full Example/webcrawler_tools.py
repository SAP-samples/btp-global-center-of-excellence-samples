import json
import sys
from urllib.parse import urljoin
import asyncio
from gen_ai_hub.proxy.langchain import init_llm
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup


MAIN_CONTENT_SELECTOR = 'body'
TAGS_TO_REMOVE = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'head', 'button', 'iframe', 'url', 'meta']

def get_content(html_content):
    if html_content:
        print("\n--- Starting BeautifulSoup Cleaning ---")
        soup = BeautifulSoup(html_content, 'html.parser')
        removed_count = 0
        for tag_name in TAGS_TO_REMOVE:
            for tag in soup.find_all(tag_name):
                tag.decompose()
                removed_count += 1
        print(f"Removed {removed_count} instances of specified tags ({', '.join(TAGS_TO_REMOVE)}).")
        main_content_area = soup.select_one(MAIN_CONTENT_SELECTOR)
        if not main_content_area:
            print(f"Warning: Main selector '{MAIN_CONTENT_SELECTOR}' not found in soup. Using entire body.")
            main_content_area = soup.body if soup.body else soup # Fallback
        if main_content_area:
            partially_cleaned_text = main_content_area.get_text(separator='\n', strip=True)
            print("Extracted text from main content area.")
        else:
            print("Error: Could not find main content area or body to extract text from.")
            partially_cleaned_text = "Error: Content extraction failed."
        print("--- BeautifulSoup Cleaning Finished ---")
        print("\n--- Partially Cleaned Text ---")
        print(partially_cleaned_text[:1000] + "..." if len(partially_cleaned_text) > 1000 else partially_cleaned_text) # Print preview
        print("-----------------------------")
    if partially_cleaned_text and "Error:" not in partially_cleaned_text:
        system_prompt = f"""
            From the following text extracted from a webpage after initial HTML tag removal,
            please identify and return *only* the core main content (e.g., the article body, the primary description).
            Exclude any remaining navigation text, comments, related urls, user interface elements, or boilerplate text that might still be present.
            Do not summarize, rephrase, or add any information not present in the input text. Preserve paragraph structure.
            Input Text:
            """
        out = llm.invoke([("system", system_prompt), ("user", partially_cleaned_text)])
        # print(out)
        return out.content

def get_urls(html_content, base_url, filter_prompt=None):
    url_candidates = []
    if html_content:
        print("\n--- Starting BeautifulSoup Processing for url Candidates ---")
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag_name in TAGS_TO_REMOVE:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        search_area = soup.select_one(MAIN_CONTENT_SELECTOR)
        if not search_area:
            print(f"Warning: Main selector '{MAIN_CONTENT_SELECTOR}' not found. Searching entire remaining body.")
            search_area = soup.body if soup.body else soup

        if search_area:
            print(f"Searching for urls within the selected area ('{MAIN_CONTENT_SELECTOR}')...")
            urls = search_area.find_all('a', href=True)
            print(f"Found {len(urls)} potential anchor tags.")
            for index, url in enumerate(urls):
                href = url.get('href', '').strip()
                if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                    continue
                try:
                    absolute_url = urljoin(base_url, href)
                except ValueError:
                    continue
                url_text = url.get_text(strip=True)
                context = ""
                parent = url.find_parent(['p', 'li', 'div', 'td'])
                if parent:
                    context = parent.get_text(strip=True, separator=' ')[:250]
                url_candidates.append({
                    'id': index + 1,
                    'url': absolute_url,
                    'text': url_text if url_text else '[No url Text]',
                    'context': context if context else '[No Parent Context Found]'
                })
        else:
            print("Error: Could not find main content area or body to search for urls.")
        print(f"--- Extracted {len(url_candidates)} url Candidates with Context ---")

        # --- Step 3: Construct LLM Prompt using a single f-string ---
        if not url_candidates:
            print("No url candidates found, cannot generate LLM prompt.")
            return [], "[]"
        candidate_details_str = "\n".join([
            f"\n{candidate['id']}. URL: {candidate['url']}\n"
            f"   url Text: {candidate['text']}\n"
            f"   Surrounding Context: {candidate['context']}"
            for candidate in url_candidates
        ])
        if filter:


            system_prompt =  f"""{filter_prompt} 
                            Instructions:
                            Return a comma-separated list containing ONLY the IDs (the numbers) of the urls you identify as 'follow-up urls' based on the definition and context provided above.
                            Do NOT add any URLs or IDs not present in the candidate list. Do not explain your reasoning, just provide the comma-separated list of IDs enclosed in [] brackets. Your return value has to be deserializable using json.loads().
                            Example Output Format: [1, 5, 12]
                            """
            user_text = f"Candidate urls: {candidate_details_str}"
            input = [("system", system_prompt), ("user", user_text)]
            out = llm.invoke(input)
            url_ids = out.content
            url_ids = json.loads(url_ids)
            try:
                urls = [url_candidates[i - 1] for i in url_ids]
            except Exception as e:
                print(e)
        else:
            urls = url_candidates
        return urls

    else:
        print("\nNo HTML content fetched, cannot extract urls.")
        return None

if sys.platform == 'win32':
    print("Setting asyncio event loop policy to ProactorEventLoop for Windows.")
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# def scrape_site(url, return_raw_html=True):
#     """
#        Retrieves and processes a webpage to extract the main textual content AND a
#        list of potential follow-up or related urls found within that content.
#        When appropriate query relevant follow-up urls.
#
#        This tool is useful when you need a comprehensive understanding of a specific
#        webpage, including its primary information and pointers to related resources,
#        for tasks like research, summarization, or answering questions based on the page.
#
#        Args:
#            url (str): The fully qualified URL of the webpage to fetch and process.
#                       Example: "https://investors.johnsoncontrols.com/news-and-events/press-releases/johnson-controls-international-plc/2025/02-05-2025-115534241" (Q1 Earnings Call)
#                                "https://www.sap.com/"
#
#        Returns:
#            Tuple[str, List[str]]: A tuple containing two elements:
#                1.  main_content (str): The cleaned text extracted from the identified
#                                        main content area of the webpage. Boilerplate
#                                        (like navigation, footers, scripts) is removed.
#                                        On failure, this may contain an error message
#                                        or be an empty string.
#                2.  related_urls (List[str]): A list of absolute URLs found within or
#                                               closely associated with the main content
#                                               area, potentially representing follow-up
#                                               reading, references, or next steps.
#                                               Returns an empty list if no suitable
#                                               urls are found or if processing fails.
#     """
#     html_content = None
#     partially_cleaned_text = None
#     print(f"Attempting to fetch URL: {url}")
#     try:
#         with sync_playwright() as p:
#             browser = p.chromium.launch(headless=True)
#             user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
#             page = browser.new_page(user_agent=user_agent)
#             page.set_default_timeout(10000) # 60 seconds
#             print("Navigating to page...")
#             # page.goto(url, wait_until='load')
#             page.goto(url, wait_until='domcontentloaded')
#             try:
#                 print(f"Waiting for selector: '{MAIN_CONTENT_SELECTOR}'")
#                 page.wait_for_selector(MAIN_CONTENT_SELECTOR, timeout=6000)
#                 print("Main content selector found.")
#             except PlaywrightTimeoutError:
#                 print(f"Warning: Main content selector '{MAIN_CONTENT_SELECTOR}' not found within timeout. Proceeding anyway.")
#             # time.sleep(5) # Use cautiously, explicit waits are better
#             print("Getting page content...")
#             html_content = page.content()
#             print(f"Successfully fetched HTML (length: {len(html_content)} characters)")
#             browser.close()
#     except PlaywrightTimeoutError:
#         print(f"Error: Timeout while loading page {url}")
#         return None, None
#     except Exception as e:
#         print(f"Error during Playwright operation: {e}")
#         return None, None
#
#     if return_raw_html:
#         return html_content
#
#     filter_prompt = f"""Analyze the following list of urls extracted from a webpage.
#                     Identify which of these urls are likely 'follow-up urls'.
#                     Definition of 'follow-up url': A url that likely leads the user to the next logical step, related content, further reading on the same topic, or a continuation of the current content (e.g., 'Next Page', 'Read More', urls within an article body discussing related concepts).
#                     Exclude urls that appear to be primary navigation (even if missed by initial tag removal), advertisements, user profiles, login/logout urls, site structure urls (like 'Home'), or clearly unrelated content.
#                     Base your judgment ONLY on the provided URL, url Text, and Surrounding Context for each candidate."""
#
#     main_content = get_content(html_content)
#     urls = get_urls(html_content, url, filter_prompt)
#
#     return main_content, urls



def identify_static_site(url, content):
    prompt = """
    You are an intelligent assistant for a web scraping agent. Your task is to analyze a given URL and its associated HTML content (or a summary of its content) to determine if the page is "static."

    A "static" page, in this context, is one whose primary informational content was published at a specific point in time and is unlikely to receive significant updates or changes in the future. The scraper aims to avoid re-crawling such pages frequently.

    **Input you will receive:**
    1.  `page_url`: The full URL of the web page.
    2.  `page_content_summary`: Key textual content from the page, including titles, headings, visible publication dates, and representative paragraphs. (Alternatively, this could be the full HTML if you are processing that).

    **Your Goal:**
    Based on the `page_url` and `page_content_summary`, decide if the page should be classified as "static" or "dynamic."

    **Criteria for classifying a page as "STATIC":**
    * **URL Patterns:**
        * Contains clear dates (e.g., `/2023/`, `/archive/2022/`, `/news/05-26-2024/`).
        * Includes keywords like `press-release`, `news-item`, `article-id-[timestamp_or_old_id]`, `archived-post`.
    * **Content Clues:**
        * Explicit and past publication dates clearly visible (e.g., "Published on: January 15, 2023", "Posted: May 30, 2024").
        * Content primarily describes events or information fixed to a past point in time.
        * Absence of "Last Updated" timestamps, or "Last Updated" timestamps that are very old (e.g., more than a year ago, depending on site type).
        * Lack of interactive or frequently changing elements directly related to the main content (e.g., no active comment sections, no live data feeds integrated into the core information).
        * Titles or headings like "Press Release:", "Archived News:", "Event Recap from [Past Date]".
        * Legal documents like "Terms of Service from 2022", "Privacy Policy (Effective 2021)".

    **Criteria for classifying a page as "DYNAMIC" (i.e., NOT static):**
    * **URL Patterns:** Suggests overview pages, product listings, or sections that are regularly updated (e.g., `/products/`, `/latest-news/`, `/category/active-topic/`).
    * **Content Clues:**
        * "Last Updated: [Recent Date/Time]" is prominently displayed and recent.
        * Content is clearly about ongoing topics, live events, or information that is regularly refreshed (e.g., homepage displaying latest articles).
        * Pages that are clearly designed to aggregate or list frequently changing content.

    **Output**
    Your output can only be true or false. If the site is static return true else false.
    """
    llm_input = [("system", prompt), ("user", f"Url: {url} HTML-Content: {content}")]
    output = llm.invoke(llm_input)
    print(output)
    print(output.content)
    return 'true' in output.content

def generate_summary(updated_pages):
    #todo ground summary within the companies context
    competitor_analysis_system_prompt = """
    You are a senior strategic business analyst. Your task is to synthesize raw data from our competitor monitoring system into a concise, actionable intelligence report for our company's employees. You will be given a list of database entries for pages on a competitor's website that have been recently discovered or updated.

    Your analysis must go beyond simply listing changes. You need to identify patterns, infer strategic intent, and highlight what is most important for our team to know.

    **Input Data:**
    You will receive a JSON object containing a list of page records. Each record has the following keys: `url`, `discovered_at`, `last_updated_at`, `static` (a boolean), `content` (the current page content), and `previous_content` (the page content before the update, if available).

    **Analytical Instructions:**
    1.  **Synthesize, Don't List:** Do not simply list every updated URL. Group related changes into strategic themes (e.g., Product Updates, Marketing Campaigns, Pricing Changes, Content Strategy Shifts).
    2.  **Identify New vs. Updated:** Clearly distinguish between brand-new pages/sections (which indicate a new initiative) and significant updates to existing pages (which indicate a change in strategy or focus). Use the `discovered_at` and `last_updated_at` timestamps to help with this.
    3.  **Analyze the "Diff":** The `previous_content` field is your most powerful tool. When a page is updated, analyze the difference between the `content` and `previous_content` to describe the *specific* changes. For example, instead of "the pricing page was updated," state "the price for the 'Pro Plan' was lowered by 15% and a new 'Enterprise Tier' was added."
    4.  **Infer Strategic Intent:** What is the likely business reason behind these changes? Are they targeting a new customer segment? Responding to market pressure? Launching a new feature?
    5.  **Filter Out Noise:** Ignore minor, non-strategic changes (e.g., typo corrections, copyright year updates) and pages marked as `static` unless their initial discovery is itself a significant event (e.g., a new press release).
    6.  **Be as concise as possible** Your answer must be shorter than 1500 characters. 

    ---
    **Output Structure:**
    Generate the report in markdown format. It must follow this structure exactly:
    ### Executive Summary
    (A 2-3 sentence paragraph summarizing the most critical findings and strategic shifts from the reporting period. A busy executive should be able to read only this section and understand the key takeaways.)
    ---
    ### Key Intelligence Points
    * **[Theme 1]:** [Directly state the finding and its implication]. [Provide a concise, actionable recommendation for our team if applicable]. [Source](url)
    * **[Theme 2]:** [Directly state the finding and its implication]. [Provide a concise, actionable recommendation for our team if applicable]. [Source](url)
    * **(Continue for all major themes)**
    """
    output = llm.invoke([("system", competitor_analysis_system_prompt), ("user", f"New entries: {updated_pages}")])
    return output.content

llm = init_llm('gemini-2.0-flash', max_tokens=1024, temperature=0)


