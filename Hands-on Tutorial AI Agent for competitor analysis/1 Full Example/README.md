
# AI Agent for competitor analysis 
This system monitors competitor websites, extracts data, generates summaries, and offers an AI agent for analysis. It uses web crawling, a HANA database, LLMs, and a Streamlit frontend to automate competitor intelligence. Key functions include tracking site changes, identifying static content, creating "Competitor Intelligence Briefings," and enabling user queries via an AI agent with RAG and web search.
## Setup
### Prerequisites
* Python 3.12
* Access to a SAP HANA Cloud
* Access to the SAP Generative AI Hub 
### Installation & Configuration
1. Install Python dependencies: `pip install -r requirements.txt`
2. Create `.env` file with HANA DB details (`DB_ADDRESS`, `DB_USER`, `DB_PASSWORD`)
3. Configure Generative AI Hub access.
## Running the System

1. **Crawler & Summarizer (`start_crawling.py`):**

   * Handles DB init, crawls the target site, and generates summaries.

   * **Execute:** `python start_crawling.py`

   * **Note:** Schedule for incremental updates (e.g., daily). Configure `TARGET_URL` and `MAX_DEPTH` in the script.

2. **AI Analyst Frontend (`frontend.py`):**

   * Launches the Streamlit UI for the AI Analyst.

   * **Execute:** `streamlit run frontend.py`

   * Access via browser (typically `http://localhost:8501`). Relies on data from `start_crawling.py`.