import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By


class TechlandProductScraper:
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
        time.sleep(6)

    def get_page_count(self):
        return self.total_pages

    def _get_search_result_page_count(self):
        """Parse Techland BD's pagination to find total number of pages."""
        try:
            elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                'button[aria-label]'
            )
            pages = []
            for el in elements:
                label = el.get_attribute('aria-label') or ''
                for prefix in ['Go to page ', 'Current page, ']:
                    if label.startswith(prefix):
                        num_str = label.replace(prefix, '').strip()
                        if num_str.isdigit():
                            pages.append(int(num_str))
                        break
            if not pages:
                return 0
            return max(pages)
        except Exception:
            return 0

    def get_product_urls(self):
        """Extract product URLs from the current page's product grid."""
        urls = []
        try:
            product_anchors = self.driver.find_elements(
                By.CSS_SELECTOR,
                '.grid a.text-gray-800'
            )
            if not product_anchors:
                product_anchors = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    '.grid div.h-full a'
                )

            seen = set()
            for anchor in product_anchors:
                try:
                    product_url = anchor.get_attribute('href')
                    if not product_url:
                        continue

                    clean_url = product_url.split('?')[0].rstrip('/')

                    if 'techlandbd.com' not in clean_url:
                        continue

                    if clean_url.count('/') != 3:
                        continue

                    skip_list = [
                        '/search', '/login', '/register', '/cart', '/wishlist',
                        '/account', '/about', '/contact', '/page', '/offers',
                        '/tools', '/pc-builder', '/track-order', '/brands', '/all-category'
                    ]
                    if any(clean_url.endswith(kw) or f"{kw}/" in clean_url for kw in skip_list):
                        continue

                    if clean_url in seen:
                        continue

                    seen.add(clean_url)
                    urls.append({"url": clean_url})
                except Exception as e:
                    print(f"Skipping a product link due to error: {e}")
        except Exception as e:
            print(f"Error finding product links: {e}")
        return urls

    def quit(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()


def scrape_techland(search_query):
    """
    Scrape all product URLs from Techland BD search results for the given query.
    Returns a JSON string of [{"url": "..."}, ...].
    """
    base_url = f"https://www.techlandbd.com/search/advance/product/result/{search_query}"
    all_product_urls = []

    # First page — also determines total page count
    scraper = TechlandProductScraper(base_url)
    total_pages = scraper.get_page_count()

    urls = scraper.get_product_urls()
    all_product_urls.extend(urls)
    print(f"Completed page: 1 of {total_pages}")
    scraper.quit()

    # Remaining pages
    for page_num in range(2, total_pages + 1):
        separator = "&" if "?" in base_url else "?"
        page_url = f"{base_url}{separator}page={page_num}"
        scraper = TechlandProductScraper(page_url)
        urls = scraper.get_product_urls()
        all_product_urls.extend(urls)
        print(f"Completed page: {page_num} of {total_pages}")
        scraper.quit()

    return json.dumps(all_product_urls, indent=2)


if __name__ == "__main__":
    search_term = "headphones"
    result_json = scrape_techland(search_term)
    print(result_json)

    # Also save to file
    with open("techland_product_urls.json", "w") as f:
        f.write(result_json)
    print(f"\nSaved {result_json.count('url')} product URLs to techland_product_urls.json")