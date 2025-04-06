from fastapi import FastAPI
from ndtv import scrape_ndtv_news
from aninews import scrape_ani_news
import time
import threading
import random
from groq import Groq
import os
import json
import logging

# --- Configuration ---
CACHE_UPDATE_INTERVAL_SECONDS = 600
GROQ_API_KEY = os.environ.get("api_key")
GROQ_MODEL = "llama3-8b-8192"
GROQ_REQUEST_DELAY_SECONDS = 2.2 # Safety buffer for 30 RPM

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Initialize Groq Client ---
groq_client = None
if not GROQ_API_KEY:
    logging.error("GROQ_API_KEY environment variable not set. Cannot analyze news.")
else:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY, timeout=30.0)
        logging.info("Groq client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Groq client: {e}")
        groq_client = None

# --- FastAPI App ---
app = FastAPI()
cached_news = None # Will store {"data": [...]}
cache_lock = threading.Lock()
fetch_lock = threading.Lock()

# --- Helper Function: Analyze Headline with Groq (Combined) ---
def analyze_headline_with_groq(headline: str, client: Groq) -> dict:
    """
    Uses Groq API to determine if headline is crime-related AND extracts location/type.
    Returns a dictionary: {"is_crime": bool, "location": str, "crime_type": str}
    Uses "N/A" for location/type if not applicable or not found.
    """
    # Default result ensures keys exist, uses "N/A" for non-crime/errors
    default_result = {"is_crime": False, "location": "N/A", "crime_type": "N/A"}
    if not client or not headline:
        logging.warning("Skipping Groq analysis: No client or empty headline.")
        return default_result

    # Updated prompt to clarify output expectations for non-crime cases
    prompt = f"""
    Analyze the following news headline. Determine if it is related to a CRIME (e.g., theft, assault, murder, scam, arrest, police investigation, illegal activity, court proceedings related to crime etc.).
    Also, extract the most precise LOCATION mentioned within the DELHI NCR area. If no specific Delhi NCR location is mentioned BUT the headline IS crime-related, use "Delhi".
    Strictly identify the CRIME TYPE if it is a crime-related headline.

    Headline: '{headline}'

    Return ONLY a valid JSON object with the following keys:
    - "is_crime": boolean (true if crime-related, false otherwise)
    - "location": string (extracted Delhi NCR location, or "Delhi" if crime-related but non-specific, otherwise "N/A")
    - "crime_type": string (identified crime type if is_crime is true, otherwise "N/A")

    Example 1 (Crime, Specific Loc): {{"is_crime": true, "location": "Rohini", "crime_type": "Murder"}}
    Example 2 (Not Crime): {{"is_crime": false, "location": "N/A", "crime_type": "N/A"}}
    Example 3 (Crime, Non-Specific Loc): {{"is_crime": true, "location": "Delhi", "crime_type": "Theft"}}

    Ensure the output is ONLY the JSON object. Do not include any explanations or surrounding text.
    """
    try:
        logging.debug(f"Calling Groq for analysis: '{headline[:50]}...'")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        result_content = response.choices[0].message.content.strip()
        logging.debug(f"Groq analysis raw response for '{headline[:50]}...': {result_content}")

        try:
            analysis_data = json.loads(result_content)
            # Basic validation
            if isinstance(analysis_data.get("is_crime"), bool) and \
               isinstance(analysis_data.get("location"), str) and \
               isinstance(analysis_data.get("crime_type"), str):
                 # Ensure consistency: if not crime, location/type should be N/A
                 if not analysis_data["is_crime"]:
                     analysis_data["location"] = "N/A"
                     analysis_data["crime_type"] = "N/A"
                 return analysis_data
            else:
                logging.warning(f"Groq response JSON has invalid structure/types: {result_content}")
                return default_result
        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON from Groq: {result_content}")
            return default_result

    except Exception as e:
        logging.error(f"Error during Groq analysis for '{headline[:50]}...': {e}", exc_info=False)
        return default_result

# --- Core Logic: Fetch, Analyze, Filter News ---
def fetch_analyze_and_filter_news():
    """Fetches raw news, analyzes with Groq, filters for crime, returns structured data."""
    logging.info("Starting news fetch, analysis, and filter process...")
    # ... (Scraping logic for raw_ndtv_data and raw_ani_data remains the same) ...
    raw_ndtv_data = []
    raw_ani_data = []
    try:
        logging.info("Scraping NDTV...")
        raw_ndtv_data = scrape_ndtv_news().get("data", [])
        logging.info(f"Scraped {len(raw_ndtv_data)} raw items from NDTV.")
    except Exception as e: logging.error(f"Error scraping NDTV: {e}", exc_info=True)
    try:
        logging.info("Scraping ANI News...")
        raw_ani_data = scrape_ani_news().get("data", [])
        logging.info(f"Scraped {len(raw_ani_data)} raw items from ANI News.")
    except Exception as e: logging.error(f"Error scraping ANI: {e}", exc_info=True)

    all_raw_data = raw_ndtv_data + raw_ani_data
    logging.info(f"Total raw items scraped: {len(all_raw_data)}")

    if not all_raw_data: return {"data": []} # Return correct empty structure
    if not groq_client:
        logging.warning("Groq client not available. Cannot provide analyzed news.")
        return {"data": []} # Return correct empty structure

    logging.info(f"Analyzing {len(all_raw_data)} headlines with Groq (delay: {GROQ_REQUEST_DELAY_SECONDS}s)...")
    filtered_news_items = []
    analysis_start_time = time.time()

    for i, raw_item in enumerate(all_raw_data):
        headline = raw_item.get("content")
        if not headline or not headline.strip(): continue

        logging.debug(f"Waiting {GROQ_REQUEST_DELAY_SECONDS}s before Groq call {i+1}/{len(all_raw_data)}")
        time.sleep(GROQ_REQUEST_DELAY_SECONDS)

        analysis_result = analyze_headline_with_groq(headline, groq_client)

        # *** Only include CRIME-related news in the final output ***
        if analysis_result.get("is_crime"):
            logging.info(f"CRIME DETECTED: '{headline[:80]}...' -> Type: {analysis_result.get('crime_type')}, Loc: {analysis_result.get('location')}")
            # Build the final dictionary matching the target format
            formatted_entry = {
                "content": raw_item.get("content", "N/A"),
                "date": raw_item.get("date", "N/A"), # Ensure scraper provides this format
                "id": raw_item.get("id", str(uuid.uuid4())), # Use ID from scraper
                "imageUrl": raw_item.get("imageUrl", "N/A"),
                "readMoreUrl": raw_item.get("readMoreUrl", "N/A"),
                "time": raw_item.get("time", "N/A"), # Ensure scraper provides this format
                "url": raw_item.get("url", "N/A"),
                # Get type/location from analysis, defaulting to "N/A"
                "type": analysis_result.get("crime_type", "N/A"),
                "location": analysis_result.get("location", "N/A")
            }
            filtered_news_items.append(formatted_entry)
        # else: # No need to log non-crime here if only crime items are kept
            # logging.debug(f"NON-CRIME: '{headline[:80]}...'")


    analysis_end_time = time.time()
    logging.info(f"Groq analysis complete ({analysis_end_time - analysis_start_time:.2f}s). Found {len(filtered_news_items)} crime items.")

    random.shuffle(filtered_news_items)

    # *** Return the dictionary with the 'data' key ***
    return {"data": filtered_news_items}


# --- Background Thread for Cache Updates ---
def update_news_cache():
    global cached_news
    while True:
        logging.info("Background task: Attempting fetch_lock for cache update...")
        acquired = fetch_lock.acquire(blocking=True)
        if acquired:
            logging.info("Background task: fetch_lock acquired. Updating cache...")
            start_time = time.time()
            try:
                # Fetch, analyze, filter, get data in {"data": [...]} format
                news_data_dict = fetch_analyze_and_filter_news()
                with cache_lock:
                    cached_news = news_data_dict # Store the whole dict {"data": ...}
                item_count = len(news_data_dict.get("data", []))
                duration = time.time() - start_time
                logging.info(f"Background task: Cache updated ({item_count} items) in {duration:.2f}s.")
            except Exception as e:
                duration = time.time() - start_time
                logging.error(f"Background task: Cache update failed ({duration:.2f}s): {e}", exc_info=True)
            finally:
                logging.info("Background task: Releasing fetch_lock.")
                fetch_lock.release()
        # else: # Should not happen with blocking=True

        logging.info(f"Background task: Sleeping for {CACHE_UPDATE_INTERVAL_SECONDS}s.")
        time.sleep(CACHE_UPDATE_INTERVAL_SECONDS)

# --- Start Background Thread ---
thread = threading.Thread(target=update_news_cache, daemon=True)
thread.start()

# --- API Endpoints ---
@app.get("/ping")
def ping():
    return {"status": "alive"}

@app.get("/new")
def get_news():
    """Returns crime-related news in the specified format: {"data": [...]}."""
    global cached_news
    news_list = [] # Default to empty list

    with cache_lock:
        current_cache = cached_news # Expecting {"data": [...]} or None

    if current_cache is None:
        logging.warning("API Request: Cache empty. Trying non-blocking fetch_lock...")
        acquired = fetch_lock.acquire(blocking=False)
        if acquired:
            logging.info("API Request: fetch_lock acquired. Performing sync fetch...")
            sync_start_time = time.time()
            try:
                news_data_dict = fetch_analyze_and_filter_news()
                with cache_lock:
                    cached_news = news_data_dict
                    current_cache = news_data_dict # Use newly fetched data
                duration = time.time() - sync_start_time
                logging.info(f"API Request: Sync fetch success ({duration:.2f}s).")
            except Exception as e:
                duration = time.time() - sync_start_time
                logging.error(f"API Request: Sync fetch error ({duration:.2f}s): {e}", exc_info=True)
                fetch_lock.release() # Release lock on error
                logging.info("API Request: fetch_lock released (sync error).")
                # Return error structure (or could return empty data as below)
                # Consider what the client expects on failure
                return {"error": "Could not fetch news", "details": str(e)} # Or just {"data": []}
            finally:
                # Release lock if acquired and still held (success case)
                if acquired and fetch_lock.locked():
                    logging.info("API Request: Releasing fetch_lock (sync success).")
                    fetch_lock.release()
        else:
            logging.warning("API Request: Fetch lock busy. Returning empty data.")
            # Return the desired structure but empty, maybe with a message
            return {"data": [], "message": "News update in progress"}

    # Extract the list from the cache (either existing or from sync fetch)
    if current_cache:
        news_list = current_cache.get("data", [])

    # *** Return the final structure ***
    return {"data": news_list}


# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    logging.info("Starting FastAPI application with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)