import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By


class StarTechProductScraper:
    def __init__(self, url):
        self.driver = None
        self._url = url
        self.current_page = 1
        self.total_pages = 1
        self._initialize_driver(url)
        page_count = self._get_search_result_page_count()
        if page_count > 0:
            self.total_pages = page_count

    def _initialize_driver(self, url):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.driver.get(url)
        time.sleep(5)

    def get_page_count(self):
        return self.total_pages

    def _get_search_result_page_count(self):
        """Parse StarTech's pagination to find total number of pages."""
        elements = self.driver.find_elements(
            By.CSS_SELECTOR,
            "ul.pagination li a"
        )
        pages = [
            int(el.text)
            for el in elements
            if el.text.strip().isdigit()
        ]
        if not pages:
            return 0
        return max(pages)

    def get_product_urls(self):
        """Extract product URLs from the current page's product cards."""
        product_item_divs = self.driver.find_elements(By.CSS_SELECTOR, 'div.p-item')
        urls = []
        for div in product_item_divs:
            try:
                anchor_element = div.find_element(By.CSS_SELECTOR, '.p-item-img a')
                product_url = anchor_element.get_attribute('href')
                if product_url:
                    urls.append({"url": product_url})
            except Exception as e:
                print(f"Skipping a product div due to error: {e}")
        return urls

    def quit(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()


def scrape_startech(search_query):
    """
    Scrape all product URLs from StarTech search results for the given query.
    Returns a JSON string of [{"url": "..."}, ...].
    """
    base_url = f"https://www.startech.com.bd/product/search?search={search_query}"
    all_product_urls = []

    # First page — also determines total page count
    scraper = StarTechProductScraper(base_url)
    total_pages = scraper.get_page_count()

    urls = scraper.get_product_urls()
    all_product_urls.extend(urls)
    print(f"Completed page: 1 of {total_pages}")
    scraper.quit()

    # Remaining pages
    for page_num in range(2, total_pages + 1):
        page_url = f"{base_url}&page={page_num}"
        scraper = StarTechProductScraper(page_url)
        urls = scraper.get_product_urls()
        all_product_urls.extend(urls)
        print(f"Completed page: {page_num} of {total_pages}")
        scraper.quit()

    return json.dumps(all_product_urls, indent=2)


if __name__ == "__main__":
    search_term = "headphones"
    result_json = scrape_startech(search_term)
    print(result_json)

    # Also save to file
    with open("startech_product_urls.json", "w") as f:
        f.write(result_json)
    print(f"\nSaved {result_json.count('url')} product URLs to startech_product_urls.json")