import time
import uuid
import json
from bs4 import BeautifulSoup
from driver import setup_driver
from groq import Groq
import os
from selenium import webdriver

client = Groq(api_key="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")

def extract_location_and_crime_type(headline):
    try:
        response = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": f"""
                Extract the most precise LOCATION inside DELHI NCR and STRICTLY IDENTIFY THE CRIME TYPE from the following headline: '{headline}'.
                Return the output as a valid JSON object with keys 'location' and 'crime_type'.
                Example:
                {{
                    "location": "Connaught Place",
                    "crime_type": "Robbery"
                }}
                Ensure the response is a valid JSON object and does not contain any additional text.
                """
            }],
            model="llama3-8b-8192"
        )
        result = response.choices[0].message.content.strip()
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start != -1 and json_end != -1:
            json_str = result[json_start:json_end]
            return json.loads(json_str)
        else:
            print("No JSON object found in the response.")
            return {"location": "Delhi", "crime_type": "N/A"}
    except Exception as e:
        print(f"Error extracting location and crime type: {e}")
        return {"location": "Delhi", "crime_type": "N/A"}


def scrape_ani_news_page(driver, page_num):
    url = f"https://www.aninews.in/topic/delhi/page/{page_num}/"
    try:
        print(f"Loading page {page_num}: {url}")
        driver.get(url)
        time.sleep(3)  # Wait for page to load
        
        # Scroll to load all content
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("div", class_="col-sm-4 col-xs-12") 
        
        formatted_entries = []
        for card in cards:
            try:
                # Extract image URL
                img_container = card.find("div", class_="img-container")
                image_url = img_container.get("src", "N/A") if img_container else "N/A"
                
                # Extract headline and link from figcaption
                figcaption = card.find("figcaption")
                if figcaption:
                    title_element = figcaption.find("h6", class_="title")
                    headline = title_element.get_text(strip=True) if title_element else "N/A"
                    
                    link_element = figcaption.find("a")
                    link = link_element["href"] if link_element and "href" in link_element.attrs else "N/A"
                    
                    # Extract date/time
                    time_element = figcaption.find("p", class_="time")
                    if time_element:
                        time_red = time_element.find("span", class_="time-red")
                        if time_red:
                            date_time = time_red.get_text(strip=True).replace("IST", "").strip()
                        else:
                            date_time = "N/A"
                    else:
                        date_time = "N/A"
                else:
                    headline = "N/A"
                    link = "N/A"
                    date_time = "N/A"
                
                # Process date/time (adjust based on actual format)
                date_parts = date_time.split()
                formatted_date = " ".join(date_parts[:3]) if len(date_parts) >= 3 else "N/A"
                formatted_time = " ".join(date_parts[3:]) if len(date_parts) > 3 else "N/A"
                
                # Extract crime type and location
                extracted_data = extract_location_and_crime_type(headline)
                
                formatted_entry = {
                    "content": headline,
                    "date": formatted_date,
                    "id": str(uuid.uuid4()),
                    "imageUrl": image_url,
                    "readMoreUrl": link if link.startswith("http") else f"https://www.aninews.in{link}",
                    "time": formatted_time,
                    "url": link if link.startswith("http") else f"https://www.aninews.in{link}",
                    "type": extracted_data.get("crime_type", "N/A"),
                    "location": extracted_data.get("location", "Delhi")
                }
                formatted_entries.append(formatted_entry)
            except Exception as e:
                print(f"Error processing article: {e}")
                continue
        
        return formatted_entries
        
    except Exception as e:
        print(f"Error scraping page {page_num}: {e}")
        return []

def scrape_ani_news():
    try:
        print("Initializing WebDriver...")
        # driver = setup_driver()
        # Set up Chrome options if needed
        options = webdriver.ChromeOptions()
        # Initialize the WebDriver (Selenium will manage the ChromeDriver automatically)
        driver = webdriver.Chrome(options=options)
        print("WebDriver initialized successfully.")
        
        all_entries = []
        total_pages = 7  # Number of pages to scrape
        
        for page_num in range(1, total_pages + 1):
            page_entries = scrape_ani_news_page(driver, page_num)
            all_entries.extend(page_entries)
            print(f"Page {page_num} scraped. Total entries collected: {len(all_entries)}")
            time.sleep(2)  # Be polite between page requests
        
        driver.quit()
        print(f"Scraping completed. Total entries: {len(all_entries)}")
        return {"data": all_entries}
        
    except Exception as e:
        print(f"Error in scrape_ani_news: {e}")
        if 'driver' in locals():
            driver.quit()
        return {"data": []}
    
scrape_ani_news()