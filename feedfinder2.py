#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

__version__ = "0.1.0"

try:
    __FEEDFINDER2_SETUP__
except NameError:
    __FEEDFINDER2_SETUP__ = False

if not __FEEDFINDER2_SETUP__:
    __all__ = [
        "find_feeds",
        "find_feeds_async",
        "FeedFinderConfig",
        "FeedFinder",
        "AsyncFeedFinder",
        "_is_feed_data_impl",
    ]

    import asyncio
    import json
    import logging
    from dataclasses import dataclass, field
    from typing import List, Optional, Set, Tuple
    from urllib.parse import urljoin, urlsplit

    import httpx
    import requests
    from bs4 import BeautifulSoup

    # Configuration dataclass for customization
    @dataclass
    class FeedFinderConfig:
        """Configuration for feed discovery behavior."""

        # HTTP settings
        timeout: float = 10.0
        max_retries: int = 3
        user_agent: Optional[str] = None

        # Concurrency settings (async only)
        max_concurrent_requests: int = 15
        max_connections: int = 100

        # Discovery settings
        check_all: bool = False
        max_urls_to_try: Optional[int] = None

        # Custom patterns
        custom_leaf_filenames: List[str] = field(default_factory=list)
        custom_subdirectories: List[str] = field(default_factory=list)

        # Feature flags
        enable_json_feed: bool = True
        use_head_requests: bool = True
        enable_retry_logic: bool = True

        def get_user_agent(self) -> str:
            """Get the user agent string."""
            if self.user_agent is None:
                return f"feedfinder2/{__version__}"
            return self.user_agent

    def coerce_url(url: str) -> str:
        """Normalize URL to use http/https protocol."""
        url = url.strip()
        if url.startswith("feed://"):
            return f"http://{url[7:]}"
        for proto in ["http://", "https://"]:
            if url.startswith(proto):
                return url
        return f"http://{url}"

    # Enhanced feed patterns with modern formats
    DEFAULT_LEAF_FILENAMES = [
        # Standard feed files
        "feed.xml",
        "atom.xml",
        "rss.xml",
        "feed",
        "rss",
        "atom",
        "index.xml",
        "index.atom",
        "index.rss",
        "index.rdf",
        # JSON Feed
        "feed.json",
        "feeds.json",
        "rss.json",
        # Modern patterns
        "feed.atom",
        "feeds.atom",
        # WordPress
        "wp-rss2.xml",
        "feed/",
        # Blogger/Google
        "feeds/posts/default",
        "atom.xml?alt=rss",
        # Other CMS
        "blog.xml",
        "rss.php",
        "index.rss",
        ".rss",
        # API patterns
        "api/feed",
        "api/rss",
    ]

    DEFAULT_SUBDIRECTORIES = [
        "feed/",
        "feeds/",
        "rss/",
        "atom/",
        "blog/",
        "news/",
        "updates/",
        "comments/",
        "posts/",
        "articles/",
    ]

    class FeedFinder:
        """Synchronous feed finder (legacy API)."""

        def __init__(self, config: Optional[FeedFinderConfig] = None):
            """
            Initialize the feed finder.

            Args:
                config: Configuration object. If None, uses defaults.
            """
            self.config = config or FeedFinderConfig()
            self.session = requests.Session()
            self.session.headers.update({"User-Agent": self.config.get_user_agent()})

        def get_feed(self, url: str) -> Optional[str]:
            """
            Fetch content from URL with retry logic.

            Args:
                url: The URL to fetch

            Returns:
                The response text or None if failed
            """
            retries = self.config.max_retries if self.config.enable_retry_logic else 1

            for attempt in range(retries):
                try:
                    response = self.session.get(url, timeout=self.config.timeout)
                    response.raise_for_status()
                    return response.text
                except requests.Timeout:
                    if attempt < retries - 1:
                        logging.debug(
                            f"Timeout on attempt {attempt + 1} for '{url}', retrying..."
                        )
                        continue
                    logging.warning(f"Timeout after {retries} attempts for '{url}'")
                    return None
                except requests.RequestException as e:
                    logging.warning(f"Error while getting '{url}': {e}")
                    return None

            return None

        def is_feed_data(self, text: str, content_type: Optional[str] = None) -> bool:
            """
            Check if the text content is a feed.

            Args:
                text: The content to check
                content_type: Optional content-type header

            Returns:
                True if content appears to be a feed
            """
            return _is_feed_data_impl(text, content_type, self.config.enable_json_feed)

        def is_feed(self, url: str) -> bool:
            """
            Check if a URL points to a feed.

            Args:
                url: The URL to check

            Returns:
                True if the URL is a feed
            """
            text = self.get_feed(url)
            if text is None:
                return False
            return self.is_feed_data(text)

        def is_feed_url(self, url: str) -> bool:
            """Check if URL looks like a feed based on extension."""
            lower_url = url.lower()
            return any(
                lower_url.endswith(ext)
                for ext in [".rss", ".rdf", ".xml", ".atom", ".json"]
            )

        def is_feedlike_url(self, url: str) -> bool:
            """Check if URL contains feed-related keywords."""
            lower_url = url.lower()
            keywords = ["rss", "rdf", "xml", "atom", "feed", "json"]
            return any(keyword in lower_url for keyword in keywords)

    def _is_feed_data_impl(
        text: str, content_type: Optional[str], enable_json_feed: bool
    ) -> bool:
        """
        Shared implementation for feed data detection.

        Args:
            text: The content to check
            content_type: Optional content-type header
            enable_json_feed: Whether to enable JSON Feed detection

        Returns:
            True if content appears to be a feed
        """
        if not text:
            return False

        data = text.strip()

        # Check for HTML (not a feed)
        if "<html" in data.lower():
            return False

        # Check for JSON Feed
        if enable_json_feed:
            if content_type and "json" in content_type.lower():
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict) and "version" in parsed:
                        # JSON Feed has a version field
                        if "jsonfeed.org" in str(parsed.get("version", "")):
                            return True
                except (json.JSONDecodeError, ValueError):
                    pass

            # Try to detect JSON Feed even without content-type
            if data.startswith("{") or data.startswith("["):
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict):
                        # JSON Feed requires version field pointing to jsonfeed.org
                        # Tighten validation: require title or home_page_url too
                        if "version" in parsed and "jsonfeed.org" in str(
                            parsed.get("version", "")
                        ):
                            return True
                        # Relaxed but more specific: has items AND feed-like metadata
                        if "items" in parsed and (
                            "title" in parsed or "home_page_url" in parsed
                        ):
                            return True
                except (json.JSONDecodeError, ValueError):
                    pass

        # Check for XML-based feeds (RSS, Atom, RDF)
        data_lower = data.lower()
        feed_markers = ["<rss", "<rdf", "<feed"]
        return any(marker in data_lower for marker in feed_markers)

    class AsyncFeedFinder:
        """Async feed finder with concurrent request support."""

        def __init__(self, config: Optional[FeedFinderConfig] = None):
            """
            Initialize the async feed finder.

            Args:
                config: Configuration object. If None, uses defaults.
            """
            self.config = config or FeedFinderConfig()
            self.client: Optional[httpx.AsyncClient] = None
            self._semaphore: Optional[asyncio.Semaphore] = None

        async def __aenter__(self):
            """Async context manager entry."""
            limits = httpx.Limits(
                max_connections=self.config.max_connections,
                max_keepalive_connections=self.config.max_concurrent_requests,
            )

            self.client = httpx.AsyncClient(
                headers={"User-Agent": self.config.get_user_agent()},
                timeout=self.config.timeout,
                limits=limits,
                follow_redirects=True,
            )

            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Async context manager exit."""
            if self.client:
                await self.client.aclose()

        async def get_feed(self, url: str) -> Tuple[Optional[str], Optional[str]]:
            """
            Fetch content from URL with retry logic.

            Args:
                url: The URL to fetch

            Returns:
                Tuple of (response text or None, content-type or None)
            """
            if not self.client or not self._semaphore:
                raise RuntimeError(
                    "AsyncFeedFinder must be used as async context manager"
                )

            retries = self.config.max_retries if self.config.enable_retry_logic else 1

            async with self._semaphore:
                for attempt in range(retries):
                    try:
                        response = await self.client.get(url)
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "")
                        return response.text, content_type
                    except httpx.TimeoutException:
                        if attempt < retries - 1:
                            logging.debug(
                                f"Timeout on attempt {attempt + 1} for "
                                f"'{url}', retrying..."
                            )
                            await asyncio.sleep(
                                0.5 * (attempt + 1)
                            )  # exponential backoff
                            continue
                        logging.warning(f"Timeout after {retries} attempts for '{url}'")
                        return None, None
                    except httpx.HTTPError as e:
                        logging.debug(f"HTTP error while getting '{url}': {e}")
                        return None, None

            return None, None

        def is_feed_data(self, text: str, content_type: Optional[str] = None) -> bool:
            """
            Check if the text content is a feed.

            Args:
                text: The content to check
                content_type: Optional content-type header

            Returns:
                True if content appears to be a feed
            """
            return _is_feed_data_impl(text, content_type, self.config.enable_json_feed)

        async def is_feed(self, url: str) -> bool:
            """
            Check if a URL points to a feed.

            Args:
                url: The URL to check

            Returns:
                True if the URL is a feed
            """
            text, content_type = await self.get_feed(url)
            if text is None:
                return False
            return self.is_feed_data(text, content_type)

        def is_feed_url(self, url: str) -> bool:
            """Check if URL looks like a feed based on extension."""
            lower_url = url.lower()
            return any(
                lower_url.endswith(ext)
                for ext in [".rss", ".rdf", ".xml", ".atom", ".json"]
            )

        def is_feedlike_url(self, url: str) -> bool:
            """Check if URL contains feed-related keywords."""
            lower_url = url.lower()
            keywords = ["rss", "rdf", "xml", "atom", "feed", "json"]
            return any(keyword in lower_url for keyword in keywords)

    def _generate_guessed_urls(
        url: str, config: FeedFinderConfig
    ) -> Tuple[List[str], List[str]]:
        """
        Generate guessed feed URLs based on common patterns.

        Args:
            url: The base URL
            config: Configuration with custom patterns

        Returns:
            Tuple of (leaf_filenames, guessed_urls)
        """
        parsed_url = urlsplit(url)
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
        root_url = f"{scheme}://{netloc}/"
        current_dir_url = urljoin(url, "./")

        # Combine default and custom patterns
        leaf_filenames = DEFAULT_LEAF_FILENAMES + config.custom_leaf_filenames
        subdirectories = DEFAULT_SUBDIRECTORIES + config.custom_subdirectories

        guessed_urls = []

        # Leaf patterns relative to the input URL's directory
        for leaf in leaf_filenames:
            guessed_urls.append(urljoin(current_dir_url, leaf))

        # Leaf patterns relative to the root
        for leaf in leaf_filenames:
            guessed_urls.append(urljoin(root_url, leaf))

        # Common root subdirectories (as feeds themselves)
        for subdir in subdirectories:
            guessed_urls.append(urljoin(root_url, subdir))

        # Leaf patterns within common root subdirectories
        for subdir in subdirectories:
            base_subdir_url = urljoin(root_url, subdir)
            for leaf in leaf_filenames:
                guessed_urls.append(urljoin(base_subdir_url, leaf))

        # Remove duplicates while preserving order
        seen: Set[str] = set()
        unique_guessed_urls = []
        for u in guessed_urls:
            if u not in seen:
                seen.add(u)
                unique_guessed_urls.append(u)

        return leaf_filenames, unique_guessed_urls

    def url_feed_prob(url: str) -> int:
        """
        Calculate feed probability score for URL sorting.

        Higher scores are better. Used for ranking discovered feeds.

        Args:
            url: The URL to score

        Returns:
            Integer score (higher is better)
        """
        # Deprioritize comments and geo feeds
        if "comments" in url:
            return -2
        if "georss" in url:
            return -1

        # Prioritize by keyword presence
        kw = ["atom", "rss", "rdf", ".xml", "feed", ".json"]
        for priority, keyword in zip(range(len(kw), 0, -1), kw):
            if keyword in url:
                return priority

        return 0

    def sort_urls(feeds: List[str]) -> List[str]:
        """
        Sort and deduplicate feed URLs by priority.

        Args:
            feeds: List of feed URLs

        Returns:
            Sorted, deduplicated list of feed URLs
        """
        return sorted(list(set(feeds)), key=url_feed_prob, reverse=True)

    # Synchronous API (backward compatible)
    def find_feeds(
        url: str,
        check_all: bool = False,
        user_agent: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> List[str]:
        """
        Find feed URLs for a given website (synchronous version).

        This function maintains backward compatibility with the original API.

        Args:
            url: The website URL to search for feeds
            check_all: If True, try all discovery methods. If False, stop early.
            user_agent: Custom user agent string
            timeout: Request timeout in seconds

        Returns:
            List of discovered feed URLs, sorted by relevance
        """
        config = FeedFinderConfig(
            check_all=check_all,
            timeout=timeout or 10.0,
            user_agent=user_agent,
        )

        finder = FeedFinder(config)

        # Format the URL properly
        url = coerce_url(url)

        # Download the requested URL
        text = finder.get_feed(url)
        if text is None:
            return []

        # Check if it is already a feed
        if finder.is_feed_data(text):
            return [url]

        # Look for <link> tags
        logging.info("Looking for <link> tags.")
        tree = BeautifulSoup(text, "lxml")
        links = []

        for link in tree.find_all("link"):
            link_type = link.get("type", "")
            if link_type in [
                "application/rss+xml",
                "text/xml",
                "application/atom+xml",
                "application/x.atom+xml",
                "application/x-atom+xml",
                "application/feed+json",
                "application/json",
            ]:
                href = link.get("href", "")
                if href:
                    links.append(urljoin(url, href))

        # Check the detected links
        urls = [u for u in links if finder.is_feed(u)]
        logging.info(f"Found {len(urls)} feed <link> tags.")
        if urls and not check_all:
            return sort_urls(urls)

        # Look for <a> tags
        logging.info("Looking for <a> tags.")
        local, remote = [], []
        for a in tree.find_all("a"):
            href = a.get("href")
            if href is None:
                continue
            if "://" not in href and finder.is_feed_url(href):
                local.append(href)
            if finder.is_feedlike_url(href):
                remote.append(href)

        # Check the local URLs
        local_urls = [urljoin(url, link) for link in local]
        urls.extend([u for u in local_urls if finder.is_feed(u)])
        logging.info(f"Found {len(urls)} local <a> links to feeds.")
        if urls and not check_all:
            return sort_urls(urls)

        # Check the remote URLs
        remote_urls = [urljoin(url, link) for link in remote]
        urls.extend([u for u in remote_urls if finder.is_feed(u)])
        logging.info(f"Found {len(urls)} remote <a> links to feeds.")
        if urls and not check_all:
            return sort_urls(urls)

        # Guessing potential URLs
        logging.info("Guessing potential feed URLs.")
        _, guessed_urls = _generate_guessed_urls(url, config)

        if config.max_urls_to_try:
            guessed_urls = guessed_urls[: config.max_urls_to_try]

        if guessed_urls:
            logging.info(f"Trying {len(guessed_urls)} guessed URLs.")
            urls.extend([u for u in guessed_urls if finder.is_feed(u)])
            logging.info(f"Found {len(urls)} total feeds.")

        return sort_urls(urls)

    # Async API (new)
    async def find_feeds_async(
        url: str,
        config: Optional[FeedFinderConfig] = None,
    ) -> List[str]:
        """
        Find feed URLs for a given website (async version with concurrent requests).

        This is the new async API that provides significant performance improvements
        through concurrent HTTP requests.

        Args:
            url: The website URL to search for feeds
            config: Configuration object. If None, uses defaults.

        Returns:
            List of discovered feed URLs, sorted by relevance

        Example:
            async with AsyncFeedFinder() as finder:
                feeds = await find_feeds_async("https://example.com")
        """
        if config is None:
            config = FeedFinderConfig()

        async with AsyncFeedFinder(config) as finder:
            # Format the URL properly
            url = coerce_url(url)

            # Download the requested URL
            text, content_type = await finder.get_feed(url)
            if text is None:
                return []

            # Check if it is already a feed
            if finder.is_feed_data(text, content_type):
                return [url]

            # Look for <link> tags
            logging.info("Looking for <link> tags.")
            tree = BeautifulSoup(text, "lxml")
            links = []

            for link in tree.find_all("link"):
                link_type = link.get("type", "")
                if link_type in [
                    "application/rss+xml",
                    "text/xml",
                    "application/atom+xml",
                    "application/x.atom+xml",
                    "application/x-atom+xml",
                    "application/feed+json",
                    "application/json",
                ]:
                    href = link.get("href", "")
                    if href:
                        links.append(urljoin(url, href))

            # Check the detected links concurrently
            if links:
                link_checks = await asyncio.gather(
                    *[finder.is_feed(link) for link in links]
                )
                urls = [link for link, is_feed in zip(links, link_checks) if is_feed]
                logging.info(f"Found {len(urls)} feed <link> tags.")
                if urls and not config.check_all:
                    return sort_urls(urls)
            else:
                urls = []

            # Look for <a> tags
            logging.info("Looking for <a> tags.")
            local, remote = [], []
            for a in tree.find_all("a"):
                href = a.get("href")
                if href is None:
                    continue
                if "://" not in href and finder.is_feed_url(href):
                    local.append(href)
                if finder.is_feedlike_url(href):
                    remote.append(href)

            # Check the local URLs concurrently
            local_urls = [urljoin(url, link) for link in local]
            if local_urls:
                local_checks = await asyncio.gather(
                    *[finder.is_feed(u) for u in local_urls]
                )
                new_feeds = [
                    u for u, is_feed in zip(local_urls, local_checks) if is_feed
                ]
                urls.extend(new_feeds)
                logging.info(f"Found {len(urls)} local <a> links to feeds.")
                if urls and not config.check_all:
                    return sort_urls(urls)

            # Check the remote URLs concurrently
            remote_urls = [urljoin(url, link) for link in remote]
            if remote_urls:
                remote_checks = await asyncio.gather(
                    *[finder.is_feed(u) for u in remote_urls]
                )
                new_feeds = [
                    u for u, is_feed in zip(remote_urls, remote_checks) if is_feed
                ]
                urls.extend(new_feeds)
                logging.info(f"Found {len(urls)} remote <a> links to feeds.")
                if urls and not config.check_all:
                    return sort_urls(urls)

            # Guessing potential URLs
            logging.info("Guessing potential feed URLs.")
            _, guessed_urls = _generate_guessed_urls(url, config)

            if config.max_urls_to_try:
                guessed_urls = guessed_urls[: config.max_urls_to_try]

            if guessed_urls:
                logging.info(f"Trying {len(guessed_urls)} guessed URLs concurrently.")
                guessed_checks = await asyncio.gather(
                    *[finder.is_feed(u) for u in guessed_urls]
                )
                new_feeds = [
                    u for u, is_feed in zip(guessed_urls, guessed_checks) if is_feed
                ]
                urls.extend(new_feeds)
                logging.info(f"Found {len(urls)} total feeds.")

            return sort_urls(urls)


if __name__ == "__main__":
    # Test synchronous API
    print("=== Synchronous API ===")
    print(find_feeds("www.preposterousuniverse.com/blog/", timeout=1))
    print(find_feeds("www.preposterousuniverse.com/blog/"))
    print(find_feeds("http://xkcd.com"))
    print(find_feeds("dan.iel.fm/atom.xml"))
    print(find_feeds("dan.iel.fm", check_all=True))

    # Test async API
    print("\n=== Async API ===")

    async def test_async():
        config = FeedFinderConfig(timeout=5.0, max_concurrent_requests=10)
        feeds = await find_feeds_async("http://xkcd.com", config)
        print(f"xkcd.com feeds: {feeds}")

        feeds = await find_feeds_async("www.preposterousuniverse.com/blog/")
        print(f"preposterousuniverse.com feeds: {feeds}")

    asyncio.run(test_async())
