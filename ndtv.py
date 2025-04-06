from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup
import time
import uuid
from driver import setup_driver # Ensure this import is correct and driver.py works

# REMOVED Groq/JSON/OS imports

def scrape_ndtv_news():
    driver = None
    print("--- Starting NDTV Scraper ---")
    try:
        print("Initializing WebDriver for NDTV...")
        driver = setup_driver()
        print("WebDriver initialized successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR initializing WebDriver: {e}")
        return {"data": []}

    url = "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation"
    try:
        print(f"Loading webpage: {url}")
        driver.get(url)
        print("Webpage loaded successfully.")
    except WebDriverException as e:
        print(f"ERROR loading webpage: {e}")
        if driver: driver.quit()
        return {"data": []}
    except Exception as e:
        print(f"UNEXPECTED ERROR loading webpage: {e}")
        if driver: driver.quit()
        return {"data": []}

    print("Waiting for initial page load (5s)...")
    time.sleep(5)

    # --- Scrolling (Keep improved version) ---
    try:
        print("Attempting to scroll...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10
        while scroll_attempts < max_scroll_attempts:
            print(f"Scrolling down (Attempt {scroll_attempts + 1})...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            print(f"  Old height: {last_height}, New height: {new_height}")
            if new_height == last_height:
                print("Scrolling stopped, height didn't change.")
                break
            last_height = new_height
            scroll_attempts += 1
        if scroll_attempts == max_scroll_attempts: print("Max scroll attempts reached.")
        print("Scrolling finished.")
    except Exception as e:
        print(f"ERROR during scrolling: {e}. Proceeding with current content.")

    # --- Get Page Source ---
    page_source = ""
    try:
        print("Extracting page source...")
        page_source = driver.page_source
        if not page_source: print("WARNING: Page source is empty!")
        else: print(f"Page source extracted successfully (length: {len(page_source)}).")
    except Exception as e:
        print(f"ERROR extracting page source: {e}")
        if not page_source:
             if driver: driver.quit()
             return {"data": []}

    # --- Close WebDriver ---
    print("Closing WebDriver...")
    try:
        driver.quit()
        print("WebDriver closed.")
    except Exception as e: print(f"Error closing WebDriver: {e}")

    # --- Parse HTML ---
    if not page_source:
        print("Cannot parse, page source is empty.")
        return {"data": []}
    soup = None
    try:
        print("Parsing HTML with BeautifulSoup...")
        soup = BeautifulSoup(page_source, "html.parser")
        print("HTML parsed successfully.")
    except Exception as e:
        print(f"ERROR parsing HTML: {e}")
        return {"data": []}

    # --- Find News Item Containers (Using YOUR specific working selector) ---
    news_items = []
    try:
        print("Searching for news items using selector: 'a.NwsLstPg_img'...")
        news_items = soup.find_all("a", class_="NwsLstPg_img") # YOUR SELECTOR
        print(f"Found {len(news_items)} news items.")
        if not news_items:
             print("WARNING: No news items found with the selector 'a.NwsLstPg_img'!")
    except Exception as e:
        print(f"ERROR finding news items: {e}")
        return {"data": []} # Return the expected format on error

    if not news_items:
        print("Exiting scraper as no news items were found.")
        return {"data": []}

    # --- Process Each Item (Using YOUR specific working logic, NO Groq) ---
    raw_entries = []
    processed_links = set()
    print(f"Processing {len(news_items)} found items...")

    for index, item in enumerate(news_items):
        print(f"\n--- Processing Item {index + 1} ---")
        try:
            # --- Extract Data using YOUR specific logic ---
            date_time_element = item.find("span", class_="NwsLstPg_ovl-dt-nm")
            date_time = date_time_element.get_text(strip=True) if date_time_element else "N/A"
            print(f"  Raw Date/Time Text: {date_time}")

            img_element = item.find("img", class_="NwsLstPg_img-full")
            headline = img_element.get("title", "N/A") if img_element else "N/A"
            print(f"  Headline: {headline}")

            # Check if headline is valid before proceeding
            if not headline or headline == "N/A":
                 print(f"  WARNING: Skipping item {index+1} due to missing headline.")
                 continue

            link = item.get("href", "N/A") # Use .get for safety
            print(f"  Link: {link}")
            if link == "N/A":
                 print(f"  WARNING: Skipping item {index+1} due to missing link.")
                 continue

            # Skip duplicates based on link
            if link in processed_links:
                print(f"  Skipping duplicate link: {link}")
                continue
            processed_links.add(link)

            image_url = img_element.get("src", "N/A") if img_element else "N/A"
            print(f"  Image URL: {image_url}")

            news_id = str(uuid.uuid4()) # Generate ID here

            # REMOVED: extracted_data = extract_location_and_crime_type(headline)
            # REMOVED: location = extracted_data.get("location", "N/A")
            # REMOVED: crime_type = extracted_data.get("crime_type", "N/A")

            # --- Parse Date/Time using YOUR split logic ---
            formatted_date = "N/A"
            formatted_time = "N/A"
            if date_time != "N/A":
                try:
                    date_parts = date_time.split()
                    # Assuming format like "Month Day, Year | HH:MM AM/PM IST"
                    if len(date_parts) >= 5: # Need at least Month, Day, Year, Time, AM/PM
                         # Your original format: MonthDay,Year (e.g., Mar18,2025)
                         month = date_parts[0][:3] # Abbreviate month
                         day = date_parts[1].replace(',', '')
                         year = date_parts[2].replace(',', '')
                         formatted_date = f"{month}{day},{year}"

                         # Your original format: HH:MMam/pm (e.g., 12:45pm)
                         time_part = date_parts[4].lower() # Get the time part like '12:45pm'
                         formatted_time = time_part
                         print(f"  Parsed Date: {formatted_date}, Parsed Time: {formatted_time}")
                    else:
                         print(f"  WARNING: date_time string '{date_time}' doesn't have enough parts for expected split.")
                         formatted_date = date_time # Fallback
                except IndexError as e:
                     print(f"  ERROR parsing date/time string '{date_time}' using split: {e}. Falling back.")
                     formatted_date = date_time # Fallback
                except Exception as e:
                     print(f"  UNEXPECTED ERROR parsing date/time string '{date_time}': {e}. Falling back.")
                     formatted_date = date_time # Fallback
            else:
                 print("  WARNING: Raw date_time was N/A.")


            # --- Create Raw Entry dictionary (NO 'type', 'location') ---
            raw_entry = {
                "content": headline,
                "date": formatted_date, # Use parsed value
                "id": news_id,
                "imageUrl": image_url,
                "readMoreUrl": link,
                "time": formatted_time, # Use parsed value
                "url": link
            }
            raw_entries.append(raw_entry)
            print(f"  Successfully processed item {index + 1}")

        except Exception as e:
            # Log error for this specific item but continue with others
            print(f"ERROR processing item {index + 1} (Link: {item.get('href', 'N/A')}): {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging the item error
            continue # Skip this item

    print(f"\n--- NDTV Scraper Finished ---")
    print(f"Successfully processed {len(raw_entries)} unique news items.")
    # --- Return in the required {"data": [...]} format ---
    return {"data": raw_entries}