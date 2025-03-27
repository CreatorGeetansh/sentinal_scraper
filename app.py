from fastapi import FastAPI
from ndtv import scrape_ndtv_news
import time
import threading

app = FastAPI()
cached_news = None
last_updated = 0
def update_news_cache():
    global cached_news, last_updated
    while True:
        cached_news = scrape_ndtv_news()
        last_updated = time.time()
        time.sleep(600)  # Update cache every 10 minutes

# Start background thread for cache update
thread = threading.Thread(target=update_news_cache, daemon=True)
thread.start()

@app.get("/new")
def get_news():
    return {"news_url": "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation", "news": cached_news}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)