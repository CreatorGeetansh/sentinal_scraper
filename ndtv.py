from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import uuid
from groq import Groq
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Initialize Groq client
client = Groq(api_key="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")

def extract_location_and_crime_type(headline):
    try:
        response = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": f"""
                Extract the most precise LOCATION inside DELHI NCR and STRICLTY IDENTIFY THE CRIME TYPE from the following headline: '{headline}'.
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

def download_selenium():
     chrome_options = Options()
     chrome_options.add_argument("--headless=new")
     chrome_options.add_argument("--no-sandbox")
     chrome_options.add_argument("--disable-dev-shm-usage")
     chrome_options.add_argument("--remote-debugging-port=9222")
     chrome_options.add_argument("--disable-extensions")
    
     driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
     )
     return driver

def scrape_ndtv_news():
    try:
        print("Initializing WebDriver...")
        driver = download_selenium()
        print("WebDriver initialized successfully.")
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        return []

    url = "https://www.ndtv.com/delhi-news#pfrom=home-ndtv_mainnavigation"
    try:
        print(f"Loading webpage: {url}")
        driver.get(url)
        print("Webpage loaded successfully.")
    except Exception as e:
        print(f"Error loading webpage: {e}")
        driver.quit()
        return []

    print("Waiting for the page to load...")
    time.sleep(5)

    try:
        print("Simulating scrolling to load more content...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        print("Scrolling completed.")
    except Exception as e:
        print(f"Error during scrolling: {e}")

    try:
        print("Extracting page source...")
        page_source = driver.page_source
        print("Page source extracted successfully.")
    except Exception as e:
        print(f"Error extracting page source: {e}")
        driver.quit()
        return []

    print("Closing WebDriver...")
    driver.quit()
    print("WebDriver closed.")

    try:
        print("Parsing HTML with BeautifulSoup...")
        soup = BeautifulSoup(page_source, "html.parser")
        print("HTML parsed successfully.")
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return []

    try:
        print("Searching for news items...")
        news_items = soup.find_all("a", class_="NwsLstPg_img")
        print(f"Found {len(news_items)} news items.")
    except Exception as e:
        print(f"Error finding news items: {e}")
        return []

    formatted_entries = []
    for item in news_items:
        try:
            date_time_element = item.find("span", class_="NwsLstPg_ovl-dt-nm")
            date_time = date_time_element.get_text(strip=True) if date_time_element else "N/A"
            img_element = item.find("img", class_="NwsLstPg_img-full")
            headline = img_element.get("title", "N/A") if img_element else "N/A"
            link = item["href"]
            image_url = img_element.get("src", "N/A") if img_element else "N/A"
            news_id = str(uuid.uuid4())
            extracted_data = extract_location_and_crime_type(headline)
            location = extracted_data.get("location", "N/A")
            crime_type = extracted_data.get("crime_type", "N/A")
            formatted_entry = {
                "content": headline,
                "date": date_time.split()[0] + date_time.split()[1] + date_time.split()[2],
                "id": news_id,
                "imageUrl": image_url,
                "readMoreUrl": link,
                "time": date_time.split()[3] + date_time.split()[4],
                "url": link,
                "type": crime_type,
                "location": location
            }
            formatted_entries.append(formatted_entry)
        except Exception as e:
            print(f"Error processing news item: {e}")

    return {"data": formatted_entries}
