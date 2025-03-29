from fastapi import FastAPI
from ndtv import scrape_ndtv_news
from aninews import scrape_ani_news
import time
import threading
import random

app = FastAPI()
cached_news = None

def update_news_cache():
    global cached_news
    while True:
        try:
            # Scrape both news sources
            ndtv_data = scrape_ndtv_news().get("data", [])
            ani_data = scrape_ani_news().get("data", [])
            
            # Combine and shuffle the news items
            combined = ndtv_data + ani_data
            random.shuffle(combined)
            
            cached_news = {
                "combined": combined,
                "sources": {
                    "ndtv": ndtv_data,
                    "aninews": ani_data
                }
            }
        except Exception as e:
            print(f"Error updating news cache: {e}")
        time.sleep(600)  # Update cache every 10 minutes

# Start background thread
thread = threading.Thread(target=update_news_cache, daemon=True)
thread.start()


@app.get("/ping")
def ping():
    return {"status": "alive"}

@app.get("/new")
def get_news():
    global cached_news
    if cached_news is None:
        try:
            ndtv_data = scrape_ndtv_news().get("data", [])
            ani_data = scrape_ani_news().get("data", [])
            combined = ndtv_data + ani_data
            random.shuffle(combined)
            
            cached_news = {
                "combined": combined,
                "sources": {
                    "ndtv": ndtv_data,
                    "aninews": ani_data
                }
            }
        except Exception as e:
            return {"error": "Could not fetch news", "details": str(e)}
    
    return {
        "news": cached_news["combined"],
        "sources": {
            "ndtv": "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation",
            "aninews": "https://www.aninews.in/topic/delhi/page/1/"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



# @app.get("/new")
# def get_news():
#     global cached_news
#     if cached_news is None:
#         # If cache is empty, try to populate it immediately (first request)
#         try:
#             cached_news = scrape_ndtv_news()
#         except Exception as e:
#             return {"error": "Could not fetch news", "details": str(e)}
    
#     return {
#         "news_url": "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation", 
#         "news": cached_news
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)