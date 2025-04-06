# from fastapi import FastAPI
# from ndtv import scrape_ndtv_news
# from aninews import scrape_ani_news
# import time
# import threading
# import random

# app = FastAPI()
# cached_news = None

# def update_news_cache():
#     global cached_news
#     while True:
#         try:
#             # Scrape both news sources
#             ndtv_data = scrape_ndtv_news().get("data", [])
#             ani_data = scrape_ani_news().get("data", [])
            
#             # Combine and shuffle the news items
#             combined = ndtv_data + ani_data
#             random.shuffle(combined)
            
#             cached_news = {
#                 "combined": combined,
#                 "sources": {
#                     "ndtv": ndtv_data,
#                     "aninews": ani_data
#                 }
#             }
#         except Exception as e:
#             print(f"Error updating news cache: {e}")
#         time.sleep(600)  # Update cache every 10 minutes

# # Start background thread
# thread = threading.Thread(target=update_news_cache, daemon=True)
# thread.start()


# @app.get("/ping")
# def ping():
#     return {"status": "alive"}

# @app.get("/new")
# def get_news():
#     global cached_news
#     if cached_news is None:
#         try:
#             ndtv_data = scrape_ndtv_news().get("data", [])
#             ani_data = scrape_ani_news().get("data", [])
#             combined = ndtv_data + ani_data
#             random.shuffle(combined)
            
#             cached_news = {
#                 "combined": combined,
#                 "sources": {
#                     "ndtv": ndtv_data,
#                     "aninews": ani_data
#                 }
#             }
#         except Exception as e:
#             return {"error": "Could not fetch news", "details": str(e)}
    
#     return {
#         "news": cached_news["combined"],
#         "sources": {
#             "ndtv": "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation",
#             "aninews": "https://www.aninews.in/topic/delhi/page/1/"
#         }
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)




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
GROQ_REQUEST_DELAY_SECONDS = 2.2 # Delay between Groq API calls to avoid rate limits

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Initialize Groq Client ---
if not GROQ_API_KEY:
    logging.error("GROQ_API_KEY environment variable not set.")
    # Depending on requirements, you might exit here or proceed without Groq filtering
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
cache_lock = threading.Lock() # To prevent race conditions when accessing cache

def is_crime_related(headline: str, client: Groq) -> bool:
    """
    Uses Groq API to determine if a news headline is crime-related.
    """
    if not client or not headline:
        logging.warning("Skipping Groq check: No client or empty headline.")
        return False # Cannot determine without client or headline

    prompt = f"""
    Analyze the following news headline and determine if it is related to a CRIME (e.g., theft, assault, murder, scam, arrest, police investigation, illegal activity, court proceedings related to crime etc.).
    Headline: '{headline}'
    Respond with only 'true' if it IS crime-related, and 'false' otherwise.
    Do not include any other text, explanation, or formatting. Just the word 'true' or 'false'.
    """
    try:
        # Add a small delay *before* making the API call
        # time.sleep(GROQ_REQUEST_DELAY_SECONDS) # Moved delay to fetch_and_filter_news

        logging.debug(f"Calling Groq for headline: '{headline[:50]}...'") # Log before call
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL,
            temperature=0.1 # Lower temperature for more deterministic classification
        )
        result = response.choices[0].message.content.strip().lower()
        logging.debug(f"Groq crime check for '{headline[:50]}...': Result='{result}'")
        return result == "true"
    except Exception as e:
        # Check if the exception is a rate limit error (needs Groq API specific exception if available,
        # otherwise check status code if the underlying HTTP library exposes it,
        # or just log the general error)
        # Example (pseudo-code, might need adjustment based on actual Groq library exceptions):
        # from groq.error import RateLimitError
        # if isinstance(e, RateLimitError):
        #    logging.warning(f"Rate limit hit for headline '{headline[:50]}...'. Will likely retry. Error: {e}")
        # else:
        logging.error(f"Error checking crime status with Groq for headline '{headline[:50]}...': {e}", exc_info=True) # Log full error details
        return False # Default to False in case of error


# --- Core Logic: Fetch, Filter, and Structure News ---
def fetch_and_filter_news():
    """
    Scrapes news from sources, filters for crime-related articles using Groq,
    and returns structured data. Includes delays between Groq calls.
    """
    logging.info("Starting news fetch and filter process...")
    all_scraped_data = [] # Keep this if needed for other purposes, otherwise remove
    filtered_ndtv_data = []
    filtered_ani_data = []

    # Scrape NDTV
    try:
        logging.info("Scraping NDTV...")
        ndtv_data = scrape_ndtv_news().get("data", [])
        logging.info(f"Scraped {len(ndtv_data)} items from NDTV.")
        # Removed extending all_scraped_data here, add back if needed elsewhere
    except Exception as e:
        logging.error(f"Error scraping NDTV news: {e}", exc_info=True)
        ndtv_data = []

    # Scrape ANI News
    try:
        logging.info("Scraping ANI News...")
        ani_data = scrape_ani_news().get("data", []) # Make sure this function exists and works
        logging.info(f"Scraped {len(ani_data)} items from ANI News.")
         # Removed extending all_scraped_data here, add back if needed elsewhere
    except Exception as e:
        logging.error(f"Error scraping ANI news: {e}", exc_info=True)
        ani_data = []

    if not groq_client:
        logging.warning("Groq client not available. Skipping crime filtering.")
        filtered_ndtv_data = ndtv_data
        filtered_ani_data = ani_data
    else:
        logging.info(f"Filtering news items for crime relevance using Groq (with {GROQ_REQUEST_DELAY_SECONDS}s delay between calls)...")

        # Filter NDTV Data
        logging.info(f"Processing {len(ndtv_data)} NDTV items for crime check...")
        for i, item in enumerate(ndtv_data):
            headline = item.get("content", "")
            if headline:
                 # --- ADD DELAY ---
                logging.debug(f"Waiting {GROQ_REQUEST_DELAY_SECONDS}s before Groq call for NDTV item {i+1}/{len(ndtv_data)}")
                time.sleep(GROQ_REQUEST_DELAY_SECONDS)
                 # --- /ADD DELAY ---
                if is_crime_related(headline, groq_client):
                    logging.info(f"CRIME (NDTV): {headline[:80]}...") # Log confirmation
                    filtered_ndtv_data.append(item)
                else:
                    logging.debug(f"NON-CRIME (NDTV): {headline[:80]}...") # Log non-crime status
            else:
                 logging.warning("Skipping NDTV item with empty headline.")


        # Filter ANI Data
        logging.info(f"Processing {len(ani_data)} ANI items for crime check...")
        for i, item in enumerate(ani_data):
            headline = item.get("content", "") # Ensure ANI data has 'content' key
            if headline:
                # --- ADD DELAY ---
                logging.debug(f"Waiting {GROQ_REQUEST_DELAY_SECONDS}s before Groq call for ANI item {i+1}/{len(ani_data)}")
                time.sleep(GROQ_REQUEST_DELAY_SECONDS)
                # --- /ADD DELAY ---
                if is_crime_related(headline, groq_client):
                    logging.info(f"CRIME (ANI): {headline[:80]}...") # Log confirmation
                    filtered_ani_data.append(item)
                else:
                    logging.debug(f"NON-CRIME (ANI): {headline[:80]}...") # Log non-crime status
            else:
                logging.warning("Skipping ANI item with empty headline.")


        logging.info(f"Groq filtering complete. Found {len(filtered_ndtv_data)} crime items from NDTV, {len(filtered_ani_data)} from ANI.")

    # Combine and shuffle the filtered news items
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
    """
    global cached_news # Declare global at the start of the function
    while True:
        logging.info("Attempting to update news cache...")
        try:
            news_data = fetch_and_filter_news()
            with cache_lock:
                # Now assign directly to the global variable
                cached_news = news_data
            logging.info(f"News cache updated successfully with {len(news_data.get('combined', []))} items.")
        except Exception as e:
            logging.error(f"Error updating news cache: {e}", exc_info=True)

        logging.info(f"Sleeping for {CACHE_UPDATE_INTERVAL_SECONDS} seconds before next cache update.")
        time.sleep(CACHE_UPDATE_INTERVAL_SECONDS)

# --- Start Background Thread ---
# Run initial fetch immediately if needed, or let the thread handle it first
# fetch_and_filter_news() # Optional: uncomment to prime cache on startup
thread = threading.Thread(target=update_news_cache, daemon=True)
thread.start()


# --- API Endpoints ---
@app.get("/ping")
def ping():
    """Basic health check endpoint."""
    return {"status": "alive"}

@app.get("/new")
def get_news():
    """Returns the cached list of filtered (crime-related) news."""
    global cached_news # Declare global at the start of the function
    with cache_lock: # Ensure thread-safe access
        # Read the global variable into a local one for processing
        current_cache = cached_news

    if current_cache is None:
        # Cache hasn't been populated yet (or failed). Try one synchronous fetch.
        logging.warning("Cache is empty. Attempting synchronous fetch...")
        try:
            news_data = fetch_and_filter_news()
            # Update global cache as well
            with cache_lock:
                # Assign the fetched data to the global variable
                cached_news = news_data
                # Also update the local variable for this request
                current_cache = news_data
            logging.info("Synchronous fetch successful.")
        except Exception as e:
            logging.error(f"Error during synchronous fetch: {e}", exc_info=True)
            return {"error": "Could not fetch news at the moment.", "details": str(e)}

    # Ensure we always return the expected structure, even if empty
    combined_news = current_cache.get("combined", []) if current_cache else []

    return {
        "news": combined_news, # Return only the combined, shuffled, filtered list
        "sources_info": { # Renamed to avoid confusion with data sources list
            "ndtv": "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation",
            "aninews": "https://www.aninews.in/topic/delhi/page/1/"
        },
        # Optionally, you could return the counts or the separated lists if needed
        # "filtered_sources": current_cache.get("sources", {})
    }

# --- Main Execution ---
# (Keep the rest of the file as it was, including imports, FastAPI app creation, etc.)
if __name__ == "__main__":
    import uvicorn
    logging.info("Starting FastAPI application with Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)