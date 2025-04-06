# Remove: from groq import Groq
# Remove: import os
# Remove: import json
# Remove: client = Groq(...)

from selenium import webdriver
from bs4 import BeautifulSoup
import time
import uuid
# Remove: from groq import Groq
# Remove: import os
# Remove: import json
from selenium import webdriver
from driver import setup_driver # Ensure this import is correct

# REMOVE the entire extract_location_and_crime_type function

def scrape_ndtv_news():
    driver = None # Initialize driver to None
    try:
        print("Initializing WebDriver...")
        driver = setup_driver()
        print("WebDriver initialized successfully.")
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        # Ensure driver is quit even if setup fails partially
        if driver:
             try: driver.quit()
             except: pass
        return {"data": []} # Return dict with data key

    url = "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation"
    try:
        print(f"Loading webpage: {url}")
        driver.get(url)
        print("Webpage loaded successfully.")
    except Exception as e:
        print(f"Error loading webpage: {e}")
        driver.quit()
        return {"data": []} # Return dict with data key

    print("Waiting for the page to load...")
    time.sleep(5) # Consider if this can be replaced with explicit waits

    try:
        print("Simulating scrolling to load more content...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10 # Prevent infinite loops
        while scroll_attempts < max_scroll_attempts:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) # Wait for content to potentially load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Scrolling reached the end.")
                break
            last_height = new_height
            scroll_attempts += 1
            print(f"Scroll attempt {scroll_attempts} completed.")
        if scroll_attempts == max_scroll_attempts:
            print("Max scroll attempts reached.")
        print("Scrolling completed or max attempts reached.")
    except Exception as e:
        print(f"Error during scrolling: {e}")
        # Continue processing with whatever content was loaded

    page_source = ""
    try:
        print("Extracting page source...")
        page_source = driver.page_source
        print("Page source extracted successfully.")
    except Exception as e:
        print(f"Error extracting page source: {e}")
        # Continue without page source if extraction fails? Or return empty?
        # Let's return empty for safety.
        driver.quit()
        return {"data": []} # Return dict with data key

    print("Closing WebDriver...")
    driver.quit()
    print("WebDriver closed.")

    if not page_source:
         print("No page source obtained, cannot parse.")
         return {"data": []}

    soup = None
    try:
        print("Parsing HTML with BeautifulSoup...")
        soup = BeautifulSoup(page_source, "html.parser")
        print("HTML parsed successfully.")
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return {"data": []} # Return dict with data key

    news_items = []
    try:
        print("Searching for news items...")
        # Make selector more robust if possible
        news_items = soup.find_all("div", class_="news_Itm") # Example: Adjust if needed
        # If the above doesn't work, revert to 'a', class_='NwsLstPg_img' but be aware it might change
        # news_items = soup.find_all("a", class_="NwsLstPg_img")
        print(f"Found {len(news_items)} potential news containers.")
    except Exception as e:
        print(f"Error finding news items containers: {e}")
        return {"data": []} # Return dict with data key

    raw_entries = []
    processed_links = set() # Avoid duplicates based on link

    for item in news_items:
        try:
            # Find link within the container first
            link_element = item.find("a", href=True)
            if not link_element: continue # Skip if no link found

            link = link_element['href']
            if link in processed_links: continue # Skip duplicate link
            processed_links.add(link)

            # Now find other elements relative to the container 'item'
            headline_element = item.find(['h2', 'h3'], class_='newsHdng') # Adjust tags/classes as needed
            headline = headline_element.get_text(strip=True) if headline_element else "N/A"
            if headline == "N/A": # Fallback using img title if heading not found
                 img_element = item.find("img", title=True)
                 headline = img_element.get("title", "N/A") if img_element else "N/A"

            if headline == "N/A" or not headline.strip(): continue # Skip if no headline

            img_element = item.find("img", src=True)
            image_url = img_element.get("src", "N/A") if img_element else "N/A"

            date_time_element = item.find("span", class_="posted-by") # Adjust class as needed
            date_time_text = date_time_element.get_text(strip=True) if date_time_element else "N/A"

            # --- Basic Date/Time Parsing (NEEDS ADJUSTMENT based on ACTUAL format) ---
            # This part is highly dependent on the website's current format
            # Example: "Updated: June 10, 2024 10:00 IST" or "Reported by ... | Monday June ..." etc.
            # You'll need to inspect the element and write robust parsing logic
            formatted_date = "N/A"
            formatted_time = "N/A"
            try:
                # Attempt a simple split if format is consistent
                parts = date_time_text.split('|')[-1].strip().split() # Example logic
                if len(parts) > 3:
                    formatted_date = " ".join(parts[:3]) # e.g., "June 10, 2024"
                    formatted_time = " ".join(parts[3:]) # e.g., "10:00 IST"
                else:
                    formatted_date = date_time_text # Fallback
            except Exception:
                 formatted_date = date_time_text # Fallback on error


            # REMOVE call to extract_location_and_crime_type
            # location = extracted_data.get("location", "N/A")
            # crime_type = extracted_data.get("crime_type", "N/A")

            # Create raw entry, location/type added later in app.py
            raw_entry = {
                "content": headline,
                "date": formatted_date,
                "id": str(uuid.uuid4()),
                "imageUrl": image_url,
                "readMoreUrl": link,
                "time": formatted_time,
                "url": link
                # REMOVE "type": crime_type,
                # REMOVE "location": location
            }
            raw_entries.append(raw_entry)
        except Exception as e:
            print(f"Error processing news item container: {e}")
            continue # Skip this item

    print(f"Successfully processed {len(raw_entries)} unique news items from NDTV.")
    return {"data": raw_entries}