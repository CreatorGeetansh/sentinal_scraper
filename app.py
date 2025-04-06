from fastapi import FastAPI
from ndtv import scrape_ndtv_news
from aninews import scrape_ani_news # Assuming this exists and works
import time
import threading
import random
from groq import Groq
import os
import json
import logging

# --- Configuration ---
CACHE_UPDATE_INTERVAL_SECONDS = 600 # Update cache every 10 minutes
GROQ_API_KEY = os.environ.get("api_key")
GROQ_MODEL = "llama3-8b-8192"
# Keep the delay needed for the rate limit
GROQ_REQUEST_DELAY_SECONDS = 2.2 # Or 2.2 for extra safety buffer

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Initialize Groq Client ---
# ... (Groq client initialization remains the same) ...
if not GROQ_API_KEY:
    logging.error("GROQ_API_KEY environment variable not set.")
    groq_client = None
else:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        logging.info("Groq client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Groq client: {e}")
        groq_client = None


# --- FastAPI App ---
app = FastAPI()
cached_news = None
cache_lock = threading.Lock() # To prevent race conditions when accessing cache variable
# ---- ADD A LOCK FOR THE FETCHING PROCESS ITSELF ----
fetch_lock = threading.Lock()
# ---- /ADD A LOCK ----


# --- Helper Function: Check if Headline is Crime Related ---
# ... (is_crime_related function remains the same) ...
def is_crime_related(headline: str, client: Groq) -> bool:
    # ... (implementation is unchanged) ...
    if not client or not headline:
        logging.warning("Skipping Groq check: No client or empty headline.")
        return False

    prompt = f"""
    Analyze the following news headline and determine if it is related to a CRIME (e.g., theft, assault, murder, scam, arrest, police investigation, illegal activity, court proceedings related to crime etc.).
    Headline: '{headline}'
    Respond with only 'true' if it IS crime-related, and 'false' otherwise.
    Do not include any other text, explanation, or formatting. Just the word 'true' or 'false'.
    """
    try:
        logging.debug(f"Calling Groq for headline: '{headline[:50]}...'")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.1
        )
        result = response.choices[0].message.content.strip().lower()
        logging.debug(f"Groq crime check for '{headline[:50]}...': Result='{result}'")
        return result == "true"
    except Exception as e:
        logging.error(f"Error checking crime status with Groq for headline '{headline[:50]}...': {e}", exc_info=False) # Can set exc_info=True for more detail if needed
        return False


# --- Core Logic: Fetch, Filter, and Structure News ---
# ... (fetch_and_filter_news function remains the same internally) ...
def fetch_and_filter_news():
    # ... (Its internal logic with time.sleep() is correct, the issue is concurrency) ...
    logging.info("Starting news fetch and filter process...")
    # ... (rest of the function as previously defined with delays) ...
    filtered_ndtv_data = []
    filtered_ani_data = []

    # Scrape NDTV
    try:
        logging.info("Scraping NDTV...")
        ndtv_data = scrape_ndtv_news().get("data", [])
        logging.info(f"Scraped {len(ndtv_data)} items from NDTV.")
    except Exception as e:
        logging.error(f"Error scraping NDTV news: {e}", exc_info=True)
        ndtv_data = []

    # Scrape ANI News
    try:
        logging.info("Scraping ANI News...")
        ani_data = scrape_ani_news().get("data", [])
        logging.info(f"Scraped {len(ani_data)} items from ANI News.")
    except Exception as e:
        logging.error(f"Error scraping ANI news: {e}", exc_info=True)
        ani_data = []

    if not groq_client:
        logging.warning("Groq client not available. Skipping crime filtering.")
        filtered_ndtv_data = ndtv_data
        filtered_ani_data = ani_data
    else:
        logging.info(f"Filtering news items for crime relevance using Groq (with {GROQ_REQUEST_DELAY_SECONDS}s delay between calls)...")
        # Filter NDTV
        logging.info(f"Processing {len(ndtv_data)} NDTV items for crime check...")
        for i, item in enumerate(ndtv_data):
            headline = item.get("content", "")
            if headline:
                logging.debug(f"Waiting {GROQ_REQUEST_DELAY_SECONDS}s before Groq call for NDTV item {i+1}/{len(ndtv_data)}")
                time.sleep(GROQ_REQUEST_DELAY_SECONDS)
                if is_crime_related(headline, groq_client):
                    logging.info(f"CRIME (NDTV): {headline[:80]}...")
                    filtered_ndtv_data.append(item)
                # else: # Optional: log non-crime only if needed
                #    logging.debug(f"NON-CRIME (NDTV): {headline[:80]}...")
            else:
                 logging.warning("Skipping NDTV item with empty headline.")
        # Filter ANI
        logging.info(f"Processing {len(ani_data)} ANI items for crime check...")
        for i, item in enumerate(ani_data):
            headline = item.get("content", "")
            if headline:
                logging.debug(f"Waiting {GROQ_REQUEST_DELAY_SECONDS}s before Groq call for ANI item {i+1}/{len(ani_data)}")
                time.sleep(GROQ_REQUEST_DELAY_SECONDS)
                if is_crime_related(headline, groq_client):
                    logging.info(f"CRIME (ANI): {headline[:80]}...")
                    filtered_ani_data.append(item)
                # else: # Optional: log non-crime only if needed
                #    logging.debug(f"NON-CRIME (ANI): {headline[:80]}...")
            else:
                logging.warning("Skipping ANI item with empty headline.")

        logging.info(f"Groq filtering complete. Found {len(filtered_ndtv_data)} crime items from NDTV, {len(filtered_ani_data)} from ANI.")

    combined_filtered = filtered_ndtv_data + filtered_ani_data
    random.shuffle(combined_filtered)
    logging.info(f"Total combined crime-related news items: {len(combined_filtered)}")

    return {
        "combined": combined_filtered,
        "sources": {
            "ndtv": filtered_ndtv_data,
            "aninews": filtered_ani_data
        }
    }


# --- Background Thread for Cache Updates ---
def update_news_cache():
    """
    Periodically fetches, filters, and updates the news cache.
    Uses fetch_lock to prevent concurrent runs.
    """
    global cached_news
    while True:
        logging.info("Background task: Attempting to acquire fetch_lock to update news cache...")
        acquired = fetch_lock.acquire(blocking=True) # Block until lock is free
        if acquired:
            logging.info("Background task: fetch_lock acquired. Starting cache update.")
            try:
                news_data = fetch_and_filter_news() # This will now run exclusively
                with cache_lock:
                    cached_news = news_data
                logging.info(f"Background task: News cache updated successfully with {len(news_data.get('combined', []))} items.")
            except Exception as e:
                logging.error(f"Background task: Error during news fetch/cache update: {e}", exc_info=True)
            finally:
                logging.info("Background task: Releasing fetch_lock.")
                fetch_lock.release() # Ensure lock is always released
        else:
             # This case shouldn't happen with blocking=True, but good practice
             logging.warning("Background task: Failed to acquire fetch_lock (unexpected).")


        logging.info(f"Background task: Sleeping for {CACHE_UPDATE_INTERVAL_SECONDS} seconds before next attempt.")
        time.sleep(CACHE_UPDATE_INTERVAL_SECONDS)

# --- Start Background Thread ---
thread = threading.Thread(target=update_news_cache, daemon=True)
thread.start()


# --- API Endpoints ---
@app.get("/ping")
def ping():
    """Basic health check endpoint."""
    return {"status": "alive"}

@app.get("/new")
def get_news():
    """
    Returns the cached list of filtered (crime-related) news.
    If cache is empty, attempts a synchronous fetch ONLY IF not already fetching.
    """
    global cached_news
    with cache_lock: # Read cache safely
        current_cache = cached_news

    if current_cache is None:
        logging.warning("API Request: Cache is empty. Attempting to acquire fetch_lock for synchronous fetch...")
        # Try to acquire the lock WITHOUT blocking.
        # If the background thread has the lock, we won't wait and won't fetch here.
        acquired = fetch_lock.acquire(blocking=False)

        if acquired:
            logging.info("API Request: fetch_lock acquired. Performing synchronous fetch.")
            try:
                news_data = fetch_and_filter_news() # Run fetch exclusively
                with cache_lock: # Safely update cache
                    cached_news = news_data
                    current_cache = news_data # Use newly fetched data for this request
                logging.info("API Request: Synchronous fetch successful.")
            except Exception as e:
                logging.error(f"API Request: Error during synchronous fetch: {e}", exc_info=True)
                # Don't release lock here if error occurred during fetch_and_filter_news
                # because that function might not have completed.
                # Instead, ensure fetch_and_filter_news itself handles errors gracefully.
                # We *do* need to release the lock we acquired though.
                fetch_lock.release() # Release lock even if fetch failed
                logging.info("API Request: fetch_lock released after synchronous fetch attempt (error).")
                return {"error": "Could not fetch news at the moment.", "details": str(e)}
            finally:
                 # Ensure lock is released if fetch succeeded *or* if an error occurred *after* a successful fetch but before return
                 # The check 'if acquired and fetch_lock.locked()' might be needed if errors can occur between fetch and release
                 # Simpler: just release if acquired, assuming fetch_and_filter_news doesn't leave lock dangling
                 # Rechecking logic: release only if we successfully acquired it in this block
                 if fetch_lock.locked() and acquired: # Check if *we* still hold the lock
                     logging.info("API Request: Releasing fetch_lock after synchronous fetch attempt (success/finally).")
                     fetch_lock.release()

        else:
            # Fetch lock was held by the background thread. Don't fetch now.
            logging.warning("API Request: Fetch lock is busy (background update likely in progress). Returning empty/stale data.")
            # Return empty data or a specific message
            return {
                "news": [],
                "message": "News update in progress. Please try again shortly.",
                "sources_info": {
                    "ndtv": "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation",
                    "aninews": "https://www.aninews.in/topic/delhi/page/1/"
                }
            }

    # --- Return cached data (if it was populated either initially or by background) ---
    combined_news = current_cache.get("combined", []) if current_cache else []

    return {
        "news": combined_news,
        "sources_info": {
            "ndtv": "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation",
            "aninews": "https://www.aninews.in/topic/delhi/page/1/"
        }
    }

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    logging.info("Starting FastAPI application with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)