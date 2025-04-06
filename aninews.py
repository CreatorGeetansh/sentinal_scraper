import time
import uuid
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from driver import setup_driver # Ensure driver.py is correct and accessible
from selenium import webdriver

# REMOVED Groq/JSON/OS imports

def scrape_ani_news_page(driver, page_num):
    """Scrapes a single page of ANI news using specific user logic and find_all."""
    url = f"https://www.aninews.in/topic/delhi/page/{page_num}/"
    print(f"\n--- Scraping ANI Page {page_num}: {url} ---")
    raw_entries = [] # Will hold dictionaries of scraped raw data
    try:
        print(f"  Requesting URL: {url}")
        driver.get(url)
        print(f"  Page {page_num} loaded.")
        # Wait for potential dynamic content loading
        time.sleep(3)

        # Optional scroll (keep it simple as per original logic implied)
        try:
             print("  Scrolling down once...")
             driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
             time.sleep(2) # Wait after scroll
        except Exception as scroll_e:
             # Non-critical error, log and continue
             print(f"  Warning: Scrolling failed on page {page_num}: {scroll_e}")

        # Get page source AFTER loading and scrolling
        page_source = driver.page_source
        if not page_source:
            print(f"  ERROR: Failed to get page source for page {page_num}. Skipping page.")
            return []

        print(f"  Parsing page source (length: {len(page_source)})...")
        soup = BeautifulSoup(page_source, "html.parser")

        # --- Find Item Containers (Using YOUR specific find_all logic) ---
        cards = []
        try:
            # *** Using your find_all call ***
            card_classes = "card"
            print(f"  Searching for cards using find_all('div', class_='{card_classes}')...")
            cards = soup.find_all("div", class_=card_classes)
            # ********************************

            print(f"  Found {len(cards)} potential cards on page {page_num}.")
            if not cards:
                print(f"  WARNING: No cards found on page {page_num} with classes '{card_classes}'!")
                 # Optional: Save page source for debugging if no cards found
                 # try:
                 #     debug_filename = f"ani_debug_page_{page_num}.html"
                 #     with open(debug_filename, "w", encoding="utf-8") as f:
                 #         f.write(page_source)
                 #     print(f"  Saved page source for debugging to {debug_filename}")
                 # except Exception as save_e:
                 #     print(f"  Error saving debug HTML: {save_e}")

        except Exception as e:
            print(f"  ERROR finding cards on page {page_num}: {e}")
            return [] # Return empty list for this page on find error

        if not cards:
             print(f"  No cards found, returning empty list for page {page_num}.")
             return [] # Return empty if no cards found

        # --- Process Each Card (Using YOUR specific working logic, NO Groq) ---
        print(f"  Processing {len(cards)} found cards...")
        for index, card in enumerate(cards):
            print(f"  -- Processing Card {index + 1} on page {page_num} --")
            # Initialize variables for each card
            image_url = "N/A"
            headline = "N/A"
            link = "N/A"
            date_time = "N/A" # Raw date_time string
            formatted_date = "N/A"
            formatted_time = "N/A"
            absolute_link = "N/A"

            try:
                # --- Extract Data using YOUR specific logic ---

                # Your logic for image:
                img_container = card.find("div", class_="img-container")
                if img_container:
                     img_element = img_container.find("img")
                     if img_element:
                         image_url = img_element.get("src", "N/A")
                         print(f"    Image URL (from img inside container): {image_url}")
                     else:
                         print(f"    WARNING: Found img-container but no img tag inside card {index+1}.")
                else:
                    print(f"    WARNING: 'div.img-container' not found in card {index + 1}.")
                    # Fallback: look for any img?
                    img_element = card.find("img")
                    if img_element:
                         image_url = img_element.get("src", "N/A")
                         print(f"    WARNING: Using direct img tag fallback for Image URL: {image_url}")

                # Your logic for headline/link/date:
                figcaption = card.find("figcaption")
                if figcaption:
                    title_element = figcaption.find("h6", class_="title")
                    headline = title_element.get_text(strip=True) if title_element else "N/A"

                    link_element = figcaption.find("a")
                    # Check link element exists and has href
                    if link_element and link_element.has_attr("href"):
                        link = link_element["href"]
                    # else: link remains "N/A"

                    time_element = figcaption.find("p", class_="time small")
                    if time_element:
                        time_red = time_element.find("span", class_="time-red")
                        if time_red:
                            date_time = time_red.get_text(strip=True).replace("IST", "").strip()
                        # else: date_time remains "N/A" (as per your original logic)
                    # else: date_time remains "N/A"
                else:
                    print(f"    WARNING: figcaption not found in card {index + 1}.")
                    # Fallback: Try finding link directly in card if figcaption fails
                    link_element = card.find("a", href=True)
                    if link_element and link_element.has_attr("href"):
                        link = link_element["href"]
                        print(f"    WARNING: Using direct link fallback: {link}")
                        # Maybe use link text as headline fallback?
                        headline_fallback = link_element.get_text(strip=True)
                        if headline_fallback:
                             headline = headline_fallback # Overwrite headline only if fallback exists
                             print(f"    WARNING: Using link text as fallback headline: {headline}")


                print(f"    Headline: {headline}")
                print(f"    Link: {link}")
                print(f"    Raw Date/Time Text: {date_time}")

                # Skip if essential info missing after attempting extraction
                if headline == "N/A" or not headline.strip():
                    print(f"    WARNING: Skipping card {index+1} due to missing/empty headline.")
                    continue
                if link == "N/A":
                    print(f"    WARNING: Skipping card {index+1} due to missing link.")
                    continue


                # --- Parse Date/Time using YOUR split logic ---
                if date_time != "N/A":
                    try:
                        date_parts = date_time.split()
                        # Your original logic: first 3 parts for date, rest for time
                        if len(date_parts) >= 3:
                             # Expect format like "Jun 10, 2024"
                             formatted_date = " ".join(date_parts[:3])
                             if len(date_parts) > 3:
                                 # Expect format like "15:30" or "8:29 AM"
                                 formatted_time = " ".join(date_parts[3:])
                             else:
                                 formatted_time = "N/A" # No time part found
                             print(f"    Parsed Date: {formatted_date}, Parsed Time: {formatted_time}")
                        else:
                            print(f"    WARNING: date_time string '{date_time}' doesn't have enough parts for date.")
                            formatted_date = date_time # Fallback to raw string if parsing fails
                    except Exception as e:
                        print(f"    ERROR parsing date/time string '{date_time}': {e}")
                        formatted_date = date_time # Fallback to raw string on error
                else:
                    print("    WARNING: Raw date_time was N/A, cannot parse.")

                # REMOVED: extracted_data = extract_location_and_crime_type(headline)

                # Make link absolute
                absolute_link = link if link.startswith("http") else f"https://www.aninews.in{link}"

                # --- Create Raw Entry dictionary (NO 'type', 'location') ---
                raw_entry = {
                    "content": headline,
                    "date": formatted_date, # Use parsed value or fallback
                    "id": str(uuid.uuid4()),
                    "imageUrl": image_url,
                    "readMoreUrl": absolute_link,
                    "time": formatted_time, # Use parsed value or N/A
                    "url": absolute_link,
                }
                raw_entries.append(raw_entry)
                print(f"    Successfully processed card {index + 1}.")

            except Exception as e:
                # Catch errors processing a single card, log, and continue
                print(f"ERROR processing card {index + 1} on page {page_num} (Link: {link}): {e}")
                import traceback
                traceback.print_exc() # Print full traceback for debugging
                continue # Skip this card

        # Finished processing all cards for this page
        print(f"  Finished processing page {page_num}. Extracted {len(raw_entries)} items from this page.")
        return raw_entries # Return list of dicts for this page

    except WebDriverException as e:
        print(f"WebDriver ERROR scraping page {page_num}: {e}")
        return [] # Return empty list for this page on critical WebDriver error
    except Exception as e:
        # Catch any other unexpected errors during page processing
        print(f"UNEXPECTED ERROR scraping page {page_num}: {e}")
        import traceback
        traceback.print_exc()
        return []


def scrape_ani_news():
    """Scrapes multiple pages of ANI news and returns combined raw data."""
    driver = None
    print("--- Starting ANI Scraper ---")
    try:
        print("Initializing WebDriver for ANI...")
        # Ensure setup_driver() is working correctly
        driver = setup_driver()
        print("WebDriver initialized successfully.")

        all_entries = []
        # Consider making total_pages configurable or dynamic if possible
        total_pages = 7  # Number of pages to scrape
        processed_links_global = set() # Track unique links across all pages

        # Loop through the desired number of pages
        for page_num in range(1, total_pages + 1):
            # Call the function to scrape a single page
            page_entries = scrape_ani_news_page(driver, page_num) # Gets list for the page
            new_count = 0
            if page_entries: # Check if the page scrape returned a list (might be empty)
                 # Iterate through entries from the current page
                 for entry in page_entries:
                     link = entry.get("url")
                     # Add entry only if the link is valid and not already processed
                     if link and link not in processed_links_global:
                          all_entries.append(entry)
                          processed_links_global.add(link)
                          new_count += 1
            print(f"ANI Page {page_num} finished processing. Added {new_count} new unique items. Total unique items so far: {len(all_entries)}")
            # Be polite to the server
            time.sleep(1) # Small delay between page requests

        # After looping through all pages
        print(f"\n--- ANI Scraper Finished ---")
        print(f"Total unique raw entries collected across all pages: {len(all_entries)}")
        # --- Return in the required {"data": [...]} format ---
        return {"data": all_entries}

    except Exception as e:
        # Catch errors in the main setup or looping logic
        print(f"CRITICAL ERROR in main scrape_ani_news function: {e}")
        import traceback
        traceback.print_exc()
        # Ensure driver is quit even if error happens mid-process
        if driver:
            try: driver.quit()
            except: pass
        return {"data": []} # Return correct format on error
    finally:
        # Ensure WebDriver is always closed if it was initialized
        if driver:
            print("Closing ANI WebDriver in finally block...")
            try:
                driver.quit()
                print("ANI WebDriver closed.")
            except Exception as e:
                print(f"Error closing ANI WebDriver in finally block: {e}")
