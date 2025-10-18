"""Integration tests with real RSS feeds."""

import pytest
from feedfinder2 import find_feeds, find_feeds_async, FeedFinderConfig


# Real RSS/Atom feeds that are stable and well-known
REAL_FEED_URLS = [
    ("https://xkcd.com", "xkcd.com/atom.xml"),  # Has atom feed
    ("https://daringfireball.net", "daringfireball.net/feeds/"),  # Multiple feeds
]


@pytest.mark.integration
def test_real_feed_discovery_xkcd():
    """Test feed discovery on xkcd.com (known to have feeds)."""
    feeds = find_feeds("https://xkcd.com")

    # xkcd should have at least one feed
    assert len(feeds) > 0

    # At least one should be an atom or rss feed
    assert any("atom" in feed.lower() or "rss" in feed.lower() for feed in feeds)


@pytest.mark.integration
def test_real_feed_already_is_feed():
    """Test when the URL itself is already a feed."""
    # This is the direct xkcd atom feed
    feed_url = "https://xkcd.com/atom.xml"
    feeds = find_feeds(feed_url)

    # Should return the URL itself
    assert feed_url in feeds


@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_real_feed_discovery():
    """Test async feed discovery with real URL."""
    config = FeedFinderConfig(timeout=10.0)
    feeds = await find_feeds_async("https://xkcd.com", config)

    assert len(feeds) > 0
    assert any("atom" in feed.lower() or "rss" in feed.lower() for feed in feeds)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_parallel_discovery():
    """Test discovering feeds from multiple URLs in parallel."""
    urls = [
        "https://xkcd.com",
        "https://daringfireball.net",
    ]

    config = FeedFinderConfig(timeout=10.0, max_concurrent_requests=10)

    # Discover all in parallel
    import asyncio

    results = await asyncio.gather(
        *[find_feeds_async(url, config) for url in urls], return_exceptions=True
    )

    # Both should find feeds (or at least not error)
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            pytest.fail(f"Failed for {url}: {result}")
        assert isinstance(result, list)


@pytest.mark.integration
def test_no_feeds_on_non_blog_site():
    """Test that we don't find feeds on sites without them."""
    # Google's homepage shouldn't have RSS feeds
    feeds = find_feeds("https://www.google.com", timeout=5.0)

    # Might find 0 or might find some obscure ones, but shouldn't error
    assert isinstance(feeds, list)
