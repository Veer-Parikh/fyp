# backend/app/crawler.py
import time
import re
import json
from urllib.parse import urljoin, urlparse
from collections import deque
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import Dict, Any, List
import logging

logger = logging.getLogger("crawler")
logger.setLevel(logging.INFO)

DEFAULT_WAIT = 1.0

class SeleniumCrawler:
    def __init__(self, max_pages: int = 200, headless: bool = True, page_timeout: int = 20):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--window-size=1366,768")
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(page_timeout)

        self.max_pages = max_pages
        self.visited = set()
        self.to_visit = deque()
        self.xhr = set()

    def _normalize(self, base: str, link: str) -> str:
        if not link:
            return None
        if link.startswith("javascript") or link.startswith("#"):
            return None
        return urljoin(base, link)

    def _same_domain(self, url1: str, url2: str) -> bool:
        try:
            return urlparse(url1).netloc == urlparse(url2).netloc
        except Exception:
            return False

    def _collect_xhr(self):
        try:
            # performance logs may require enabling performance logging in options; best-effort
            for entry in self.driver.get_log("performance"):
                msg = entry.get("message", "")
                m = re.search(r'"url":"([^"]+)"', msg)
                if m:
                    u = m.group(1)
                    if u.startswith("http"):
                        self.xhr.add(u)
        except Exception:
            pass
    def crawl(self, start_url: str, max_depth: int = 2):
        visited = set()
        queue = [(start_url, 0)]

        results = {
            "pages": [],
            "links": set(),
            "js_files": set(),
            "api_calls": set()
        }

        while queue:
            url, depth = queue.pop(0)
            if url in visited or depth > max_depth:
                continue

            visited.add(url)

            try:
                self.driver.get(url)
                time.sleep(1)

                title = self.driver.title
                html = self.driver.page_source

                results["pages"].append({"url": url, "title": title})

                # extract links
                anchors = self.driver.find_elements(By.TAG_NAME, "a")
                for a in anchors:
                    href = a.get_attribute("href")
                    if href and href.startswith(start_url):
                        results["links"].add(href)
                        if href not in visited:
                            queue.append((href, depth + 1))

                # JS files
                scripts = self.driver.find_elements(By.TAG_NAME, "script")
                for s in scripts:
                    src = s.get_attribute("src")
                    if src and src.startswith(start_url):
                        results["js_files"].add(src)

                # XHR / fetch network logs
                logs = self.driver.get_log("performance")
                for entry in logs:
                    msg = json.loads(entry["message"])
                    if "Network.requestWillBeSent" in msg["message"]["method"]:
                        req = msg["message"]["params"]["request"]
                        url_req = req.get("url")
                        if url_req and url_req.startswith(start_url):
                            if any(method in req.get("method", "") for method in ["POST", "PUT", "DELETE", "PATCH"]):
                                results["api_calls"].add(url_req)

            except Exception as e:
                logger.warning(f"Error crawling {url}: {e}")

        # Convert sets to lists
        results["links"] = list(results["links"])
        results["js_files"] = list(results["js_files"])
        results["api_calls"] = list(results["api_calls"])

        return results


    # def crawl(self, start_url: str, max_depth: int = 2) -> Dict[str, Any]:
    #     results = {"pages": [], "xhr": []}
    #     self.to_visit.append((start_url, 0))
    #     while self.to_visit and len(self.visited) < self.max_pages:
    #         url, depth = self.to_visit.popleft()
    #         if depth > max_depth or url in self.visited:
    #             continue
    #         if not self._same_domain(start_url, url):
    #             continue
    #         try:
    #             self.driver.get(url)
    #             time.sleep(DEFAULT_WAIT)
    #             self._collect_xhr()
    #             anchors = self.driver.find_elements(By.XPATH, "//a[@href]")
    #             links = [a.get_attribute("href") for a in anchors if a.get_attribute("href")]
    #             results["pages"].append({"url": url, "title": self.driver.title, "found_links": links, "depth": depth})
    #             self.visited.add(url)
    #             for l in links:
    #                 new = self._normalize(url, l)
    #                 if new and new not in self.visited:
    #                     self.to_visit.append((new, depth + 1))
    #         except Exception as e:
    #             logger.warning("Error crawling %s: %s", url, e)
    #             results["pages"].append({"url": url, "error": str(e)})
    #     results["xhr"] = list(self.xhr)
    #     return results

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass

# # backend/app/crawler.py
# import time
# import re
# from urllib.parse import urljoin, urlparse
# from collections import deque
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager

# DEFAULT_WAIT = 1.0

# class SeleniumCrawler:
#     def __init__(self, max_pages=200, headless=True):
#         options = Options()
#         if headless:
#             options.add_argument("--headless=new")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-dev-shm-usage")
#         options.add_argument("--ignore-certificate-errors")
#         options.add_argument("--window-size=1366,768")
#         prefs = {"profile.managed_default_content_settings.images": 2}
#         options.add_experimental_option("prefs", prefs)

#         service = Service(ChromeDriverManager().install())
#         self.driver = webdriver.Chrome(service=service, options=options)
#         self.driver.set_page_load_timeout(20)

#         self.max_pages = max_pages
#         self.visited = set()
#         self.to_visit = deque()
#         self.xhr = set()

#     def _normalize(self, base, link):
#         if not link:
#             return None
#         if link.startswith("javascript") or link.startswith("#"):
#             return None
#         return urljoin(base, link)

#     def _same_domain(self, url1, url2):
#         try:
#             return urlparse(url1).netloc == urlparse(url2).netloc
#         except:
#             return False

#     def _collect_xhr(self):
#         try:
#             for entry in self.driver.get_log("performance"):
#                 msg = entry.get("message", "")
#                 m = re.search(r'"url":"([^"]+)"', msg)
#                 if m:
#                     u = m.group(1)
#                     if u.startswith("http"):
#                         self.xhr.add(u)
#         except Exception:
#             pass

#     def crawl(self, start_url, max_depth=2):
#         results = {"pages": [], "xhr": []}
#         self.to_visit.append((start_url, 0))
#         while self.to_visit and len(self.visited) < self.max_pages:
#             url, depth = self.to_visit.popleft()
#             if depth > max_depth or url in self.visited:
#                 continue
#             if not self._same_domain(start_url, url):
#                 continue
#             try:
#                 self.driver.get(url)
#                 time.sleep(DEFAULT_WAIT)
#                 self._collect_xhr()
#                 anchors = self.driver.find_elements(By.XPATH, "//a[@href]")
#                 links = [a.get_attribute("href") for a in anchors if a.get_attribute("href")]
#                 results["pages"].append({"url": url, "title": self.driver.title, "found_links": links, "depth": depth})
#                 self.visited.add(url)
#                 for l in links:
#                     new = self._normalize(url, l)
#                     if new and new not in self.visited:
#                         self.to_visit.append((new, depth + 1))
#             except Exception as e:
#                 results["pages"].append({"url": url, "error": str(e)})
#         results["xhr"] = list(self.xhr)
#         return results

#     def close(self):
#         try:
#             self.driver.quit()
#         except Exception:
#             pass
