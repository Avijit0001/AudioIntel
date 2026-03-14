import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By


class PickabooProductScraper:
    def __init__(self, url):
        self.driver = None
        self._url = url
        self._initialize_driver(url)

    def _initialize_driver(self, url):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        self.driver.get(url)
        time.sleep(8)

    def _scroll_to_load_all(self):
        """Scroll until all lazy-loaded products appear."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def get_product_urls(self):
        """Scroll to load all products, then extract product URLs."""
        self._scroll_to_load_all()

        elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/product-detail/']")
        seen = set()
        urls = []
        for elem in elements:
            try:
                link = elem.get_attribute("href")
                if link and "/product-detail/" in link:
                    clean_link = link.split('?')[0].rstrip('/')
                    if clean_link not in seen:
                        seen.add(clean_link)
                        urls.append({"url": clean_link})
            except Exception as e:
                print(f"Skipping a product link due to error: {e}")
        return urls

    def quit(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()


def scrape_pickaboo(search_query):
    """
    Scrape all product URLs from Pickaboo search results for the given query.
    Returns a JSON string of [{"url": "..."}, ...].
    """
    base_url = f"https://www.pickaboo.com/search-result/{search_query}"
    all_product_urls = []

    # Pickaboo uses infinite scroll (no pagination), so one page load + scroll is enough
    scraper = PickabooProductScraper(base_url)
    urls = scraper.get_product_urls()
    all_product_urls.extend(urls)
    print(f"Completed scraping. Found {len(all_product_urls)} product URLs.")
    scraper.quit()

    return json.dumps(all_product_urls, indent=2)


if __name__ == "__main__":
    search_term = "headphones"
    result_json = scrape_pickaboo(search_term)
    print(result_json)

    # Also save to file
    with open("pickaboo_product_urls.json", "w") as f:
        f.write(result_json)
    print(f"\nSaved {result_json.count('url')} product URLs to pickaboo_product_urls.json")