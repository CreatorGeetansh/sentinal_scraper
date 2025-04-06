import time
import uuid
# Remove: import json
from bs4 import BeautifulSoup
from driver import setup_driver
# Remove: from groq import Groq
# Remove: import os
from selenium import webdriver

# REMOVE: client = Groq(...)
# REMOVE the entire extract_location_and_crime_type function

def scrape_ani_news_page(driver, page_num):
    url = f"https://www.aninews.in/topic/delhi/page/{page_num}/"
    raw_entries = []
    try:
        print(f"Loading page {page_num}: {url}")
        driver.get(url)
        time.sleep(3)  # Consider replacing with explicit waits

        # Simplified scroll, adjust if needed
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        except Exception as scroll_err:
             print(f"Warning: Scrolling failed on page {page_num}: {scroll_err}")


        soup = BeautifulSoup(driver.page_source, "html.parser")
        # Use a more specific selector if possible (inspect ANI page structure)
        cards = soup.find_all("div", class_="card") # Example: Adjust if this is the repeating card element
        if not cards: # Fallback if 'card' doesn't work
            cards = soup.find_all("div", class_="col-md-4") # Another common pattern

        print(f"Found {len(cards)} potential cards on page {page_num}.")

        processed_links = set()

        for card in cards:
            try:
                link_element = card.find("a", href=True)
                if not link_element: continue

                link = link_element['href']
                # Make link absolute if relative
                if not link.startswith("http"):
                    link = f"https://www.aninews.in{link}"

                if link in processed_links: continue
                processed_links.add(link)

                headline_element = card.find(['h6', 'h5'], class_='title') # Common headline tags/classes
                headline = headline_element.get_text(strip=True) if headline_element else "N/A"
                if headline == "N/A" or not headline.strip(): continue # Skip if no headline

                img_element = card.find("img", src=True)
                image_url = img_element['src'] if img_element else "N/A"

                time_element = card.find(class_="time") # Find time element by class
                date_time_text = time_element.get_text(strip=True).replace("IST","").strip() if time_element else "N/A"

                 # --- Basic Date/Time Parsing (NEEDS ADJUSTMENT based on ACTUAL format) ---
                formatted_date = "N/A"
                formatted_time = "N/A"
                try:
                     # Example: "Jun 10, 2024 15:30"
                     parts = date_time_text.split()
                     if len(parts) >= 4:
                          formatted_date = " ".join(parts[:3]) # Jun 10, 2024
                          formatted_time = parts[3] # 15:30
                     else:
                          formatted_date = date_time_text # Fallback
                except Exception:
                     formatted_date = date_time_text # Fallback

                # REMOVE call to extract_location_and_crime_type

                # Create raw entry
                raw_entry = {
                    "content": headline,
                    "date": formatted_date,
                    "id": str(uuid.uuid4()),
                    "imageUrl": image_url,
                    "readMoreUrl": link,
                    "time": formatted_time,
                    "url": link,
                    # REMOVE "type": ...,
                    # REMOVE "location": ...
                }
                raw_entries.append(raw_entry)
            except Exception as e:
                print(f"Error processing card on page {page_num}: {e}")
                continue

        print(f"Processed {len(raw_entries)} unique items from page {page_num}.")
        return raw_entries

    except Exception as e:
        print(f"Error scraping page {page_num}: {e}")
        return []

def scrape_ani_news():
    driver = None
    try:
        print("Initializing WebDriver for ANI...")
        driver = setup_driver()
        print("WebDriver initialized successfully.")

        all_entries = []
        total_pages = 7 # Number of pages to scrape (adjust as needed)

        for page_num in range(1, total_pages + 1):
            page_entries = scrape_ani_news_page(driver, page_num)
            if page_entries: # Only extend if list is not empty
                 all_entries.extend(page_entries)
            print(f"ANI Page {page_num} scraped. Total entries collected so far: {len(all_entries)}")
            # Consider adding a small delay between page loads if needed
            # time.sleep(1)

        print(f"ANI Scraping completed. Total raw entries: {len(all_entries)}")
        return {"data": all_entries} # Return dict with data key

    except Exception as e:
        print(f"Error in scrape_ani_news: {e}")
        return {"data": []} # Return dict with data key
    finally:
        if driver:
            print("Closing ANI WebDriver...")
            try:
                driver.quit()
                print("ANI WebDriver closed.")
            except Exception as e:
                print(f"Error closing ANI WebDriver: {e}")