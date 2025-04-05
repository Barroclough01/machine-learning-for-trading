# coding: utf-8


import re
from time import sleep
import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import random


def parse_html(html):
    """Parse content from various tags from OpenTable restaurants listing"""
    data, item = pd.DataFrame(), {}
    soup = BeautifulSoup(html, 'lxml')
    
    # Debug: Print overall HTML structure
    print("\n=== FULL PAGE HTML PREVIEW ===")
    print(html[:1000])
    print("...(truncated)...")
    
    # Find all restaurant cards
    restaurants = soup.find_all('div', attrs={'data-test': 'restaurant-card'})
    print(f"\nFound {len(restaurants)} restaurant cards")
    
    # Less strict filtering - only check if the card has any content
    restaurants = [r for r in restaurants if len(r.get_text().strip()) > 0]
    print(f"Found {len(restaurants)} populated restaurant cards")
    
    for i, resto in enumerate(restaurants):
        try:
            # Print full HTML for debugging
            print(f"\n{'='*50}")
            print(f"Restaurant {i + 1} Raw HTML:")
            print(resto.prettify())
            
            # Name - look for any h6 tag within the card
            name_elem = resto.find('h6')
            if not name_elem:
                continue  # Skip only if no name found
                
            item['name'] = name_elem.text.strip()
            
            # Rating - find div with role="img"
            rating_elem = resto.find('div', attrs={'role': 'img'})
            print("\nRating element found:", rating_elem)
            if rating_elem:
                print("Rating aria-label:", rating_elem.get('aria-label', 'No aria-label found'))
                rating_text = rating_elem.get('aria-label', '').split()[0]
                item['rating'] = float(rating_text) if rating_text.replace('.', '').isdigit() else 'NA'
            else:
                item['rating'] = 'NA'
            
            # Reviews - find any text containing reviews
            all_text = resto.get_text()
            print("\nAll text in card:", all_text)
            reviews_match = re.search(r'\((\d+)[^\d]*(?:review|rating)s?\)', all_text, re.IGNORECASE)
            item['reviews'] = int(reviews_match.group(1)) if reviews_match else 'NA'
            
            # Price - find $ symbols
            price_spans = resto.find_all('span')
            print("\nAll spans found:", price_spans)
            price_text = ''
            for span in price_spans:
                if span.text.strip() and all(c == '$' for c in span.text.strip()):
                    price_text = span.text.strip()
                    break
            item['price'] = len(price_text) if price_text else 'NA'
            
            # Cuisine and Location - find text with bullets
            print("\nSearching for cuisine/location in text:", all_text)
            bullet_parts = [part.strip() for part in all_text.split('•') if part.strip()]
            print("Bullet-separated parts:", bullet_parts)
            if len(bullet_parts) >= 2:
                # Take the second-to-last part as cuisine (to avoid getting the name)
                item['cuisine'] = bullet_parts[-2].split('Price:')[0].strip()
                # Take the last part before any booking information
                location_text = bullet_parts[-1].split('Booked')[0].strip()
                item['location'] = location_text
            else:
                item['cuisine'] = 'NA'
                item['location'] = 'NA'
            
            # Bookings
            bookings_match = re.search(r'Booked (\d+)', all_text)
            item['bookings'] = int(bookings_match.group(1)) if bookings_match else 'NA'
            
            data[i] = pd.Series(item)
            
            # Print parsed results
            print(f"\nParsed data for restaurant {i + 1}:")
            for key, value in item.items():
                print(f"{key}: {value}")
            
        except Exception as e:
            print(f"\nError processing restaurant {i}: {str(e)}")
            import traceback
            print("Traceback:")
            print(traceback.format_exc())
    
    return data.T


# Initialize undetected-chromedriver
options = uc.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--disable-extensions')
options.add_argument('--no-sandbox')
options.add_argument('--disable-infobars')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-browser-side-navigation')
options.add_argument('--disable-gpu')

# Create the driver
driver = uc.Chrome(options=options)
driver.maximize_window()

# Add some randomization to seem more human-like
def random_delay():
    sleep(random.uniform(3, 7))

def random_scroll():
    driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)})")
    random_delay()

def wait_for_restaurants_to_load(driver):
    """Wait for restaurant cards to be populated with content"""
    try:
        # Wait for restaurant cards to be present
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-test='restaurant-card']"))
        )
        
        # Wait for at least one restaurant name to be visible
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "h6"))
        )
        
        # Additional wait for content to load
        sleep(5)
        
        return True
    except TimeoutException:
        return False

def scroll_page_fully(driver):
    """Scroll the page fully to trigger all lazy loading"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        # Scroll down in smaller increments with longer pauses
        for i in range(0, last_height, 300):
            driver.execute_script(f"window.scrollTo(0, {i});")
            sleep(1)
        
        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(3)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    # Scroll back to top
    driver.execute_script("window.scrollTo(0, 0);")
    sleep(2)

def check_for_robot_detection(driver):
    """Check if we've been detected as a robot"""
    try:
        robot_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'robot') or contains(text(), 'Robot')]")
        if robot_elements:
            print("Robot detection found!")
            return True
        return False
    except:
        return False

# Add this function to track what we've seen
def get_restaurant_key(item):
    """Create a unique key for each restaurant based on name and location"""
    return f"{item['name']}_{item['location']}"

try:
    url = "https://www.opentable.com/new-york-restaurant-listings"
    driver.get(url)
    
    # Initial random delay
    random_delay()
    
    # Wait for initial load and content population
    print("Waiting for page to load...")
    if not wait_for_restaurants_to_load(driver):
        print("Failed to load restaurant content")
        driver.quit()
        exit(1)
    
    seen_restaurants = set()  # Track restaurants we've already processed
    page = collected = 0
    consecutive_duplicates = 0  # Track how many times we see the same restaurants

    while True:
        if check_for_robot_detection(driver):
            print("Robot detection triggered - stopping")
            break
        
        # Scroll through the entire page to load all content
        print("Scrolling page to load all content...")
        scroll_page_fully(driver)
        
        # Wait for all restaurants to load
        if not wait_for_restaurants_to_load(driver):
            print("Failed to load restaurant content")
            break
        
        new_data = parse_html(driver.page_source)
        if new_data.empty:
            print("No restaurants found on this page, stopping...")
            break
        
        # Process new restaurants...
        current_page_restaurants = set()
        new_restaurants = pd.DataFrame()
        
        for idx, row in new_data.iterrows():
            rest_key = get_restaurant_key(row)
            current_page_restaurants.add(rest_key)
            if rest_key not in seen_restaurants:
                new_restaurants = pd.concat([new_restaurants, row.to_frame().T])
                seen_restaurants.add(rest_key)
        
        # Save new restaurants...
        if not new_restaurants.empty:
            if page == 0:
                new_restaurants.to_csv('results.csv', index=False)
            else:
                new_restaurants.to_csv('results.csv', index=False, header=None, mode='a')
            
            page += 1
            collected += len(new_restaurants)
            print(f'Page: {page} | Downloaded: {collected} | Unique restaurants: {len(seen_restaurants)}')
        
        # Try to go to next page
        try:
            # Find the next button more reliably
            next_buttons = driver.find_elements(By.CSS_SELECTOR, "button")
            next_button = None
            for button in next_buttons:
                if "Next" in button.get_attribute('innerHTML'):
                    next_button = button
                    break
            
            if not next_button:
                print("No next button found - reached last page")
                break
            
            if 'disabled' in next_button.get_attribute('class'):
                print("Next button is disabled - reached last page")
                break
            
            # Scroll to and click the next button
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
            sleep(3)
            
            # Click using JavaScript for better reliability
            driver.execute_script("arguments[0].click();", next_button)
            
            # Wait for new content
            sleep(5)
            
            # Verify page changed by checking URL or content
            old_first_restaurant = driver.find_element(By.TAG_NAME, "h6").text
            max_attempts = 5
            attempts = 0
            
            while attempts < max_attempts:
                sleep(2)
                new_first_restaurant = driver.find_element(By.TAG_NAME, "h6").text
                if new_first_restaurant != old_first_restaurant:
                    break
                attempts += 1
                print(f"Waiting for new content... attempt {attempts}")
            
            if attempts == max_attempts:
                print("Failed to load new content after clicking next")
                break
        
        except Exception as e:
            print(f"Error navigating to next page: {str(e)}")
            break
            
except Exception as e:
    print(f"An error occurred: {str(e)}")
    
finally:
    driver.quit()

# Read and display results
try:
    restaurants = pd.read_csv('results.csv')
    print(f"\nTotal restaurants collected: {len(restaurants)}")
    print(restaurants)
except Exception as e:
    print(f"Error reading results: {str(e)}")
