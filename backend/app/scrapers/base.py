"""
Base scraper with retry logic, rotating user agents, proxy support,
and rate limiting. All scrapers inherit from BaseScraper.
"""
import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

BASE_HEADERS = {
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


class ScraperError(Exception):
    """Raised when a scraper fails after all retries."""


class BaseScraper:
    def __init__(self, base_url: str, name: str):
        self.base_url = base_url
        self.name = name
        self._proxy_index = 0
        self._request_times: List[float] = []
        self._rate_limit = 10   # max requests per 10 seconds

    def _get_headers(self, extra: Optional[Dict] = None) -> Dict[str, str]:
        headers = {**BASE_HEADERS, "User-Agent": random.choice(USER_AGENTS)}
        if extra:
            headers.update(extra)
        return headers

    def _get_proxy(self) -> Optional[str]:
        proxies = settings.proxy_list
        if not proxies:
            return None
        proxy = proxies[self._proxy_index % len(proxies)]
        self._proxy_index += 1
        return proxy

    def _check_rate_limit(self):
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 10]
        if len(self._request_times) >= self._rate_limit:
            sleep_for = 10 - (now - self._request_times[0]) + 0.1
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._request_times.append(time.time())

    def _build_client(self) -> httpx.AsyncClient:
        proxy = self._get_proxy()
        kwargs: Dict[str, Any] = {
            "timeout": settings.REQUEST_TIMEOUT,
            "follow_redirects": True,
            "headers": self._get_headers(),
        }
        if proxy:
            kwargs["proxy"] = proxy
        return httpx.AsyncClient(**kwargs)

    async def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        retries: int = settings.MAX_RETRIES,
    ) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        for attempt in range(retries):
            try:
                async with self._build_client() as client:
                    if headers:
                        client.headers.update(headers)
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    return resp.json()
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "[%s] HTTP %s on attempt %d/%d: %s",
                    self.name, exc.response.status_code, attempt + 1, retries, url,
                )
                last_exc = exc
                if exc.response.status_code in (403, 429):
                    # Back off longer on rate-limit / block
                    await asyncio.sleep(settings.RETRY_DELAY * (attempt + 2) * 2)
                else:
                    await asyncio.sleep(settings.RETRY_DELAY * (attempt + 1))
            except (httpx.RequestError, Exception) as exc:
                logger.warning("[%s] Request error attempt %d/%d: %s — %s", self.name, attempt + 1, retries, url, exc)
                last_exc = exc
                await asyncio.sleep(settings.RETRY_DELAY * (attempt + 1))

        raise ScraperError(f"[{self.name}] Failed after {retries} attempts: {url}") from last_exc

    async def get_text(self, url: str, params: Optional[Dict] = None) -> str:
        """Fetch raw text (for HTML scraping)."""
        last_exc: Optional[Exception] = None
        for attempt in range(settings.MAX_RETRIES):
            try:
                async with self._build_client() as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    return resp.text
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(settings.RETRY_DELAY * (attempt + 1))
        raise ScraperError(f"[{self.name}] Text fetch failed: {url}") from last_exc
