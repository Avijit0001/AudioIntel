import json
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def scrape_pickaboo_products(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"Input file not found: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        urls_data = json.load(f)
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    products_data = []
    
    for item in urls_data:
        url = item.get("url")
        if not url:
            continue
            
        print(f"Scraping: {url}")
        driver.get(url)
        time.sleep(5)  # Wait for page to load
        
        try:
            # 1. Product Name
            try:
                name_el = driver.find_element(By.CSS_SELECTOR, "h1")
                product_name = name_el.text.strip()
            except:
                product_name = ""
                
            # 2. Price
            try:
                price_el = driver.find_element(By.CSS_SELECTOR, ".price, [class*='price']")
                price_text = price_el.text.strip()
                # Often price is formatted, so split by newline (if there's a discounted price)
                price = price_text.split('\n')[0].replace('৳', '').strip()
            except:
                price = ""
                
            # 3. Description
            try:
                # We check multiple common class names that could contain the product description
                desc_elements = driver.find_elements(By.CSS_SELECTOR, "div.description div.read-more.full")
                description = ""
                for el in desc_elements:
                    text = el.text.strip()
                    if text:
                        description = text
                        break
            except:
                description = ""
                
            product_info = {
                "product_name": product_name,
                "price": price,
                "description": description,
                "url": url
            }
            
            products_data.append(product_info)
            print(f"  -> Name: {product_name}")
            print(f"  -> Price: {price}")
            
        except Exception as e:
            print(f"Error extracting data from {url}: {e}")
            
    driver.quit()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nSaved {len(products_data)} products to {output_file}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file_path = os.path.join(base_dir, "pickaboo_product_urls.json")
    output_file_path = os.path.join(base_dir, "pickaboo_products.json")
    
    print(f"Starting scraping from: {input_file_path}")
    scrape_pickaboo_products(input_file_path, output_file_path)