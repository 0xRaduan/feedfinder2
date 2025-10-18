"""Unit tests for feedfinder2 core functions."""

import pytest
from feedfinder2 import (
    coerce_url,
    url_feed_prob,
    sort_urls,
    FeedFinderConfig,
    FeedFinder,
    AsyncFeedFinder,
    _is_feed_data_impl,
)


def test_coerce_url_with_feed_protocol():
    """Test URL coercion from feed:// to http://."""
    assert coerce_url("feed://example.com/rss") == "http://example.com/rss"


def test_coerce_url_with_http():
    """Test URL coercion with http://."""
    assert coerce_url("http://example.com") == "http://example.com"


def test_coerce_url_with_https():
    """Test URL coercion with https://."""
    assert coerce_url("https://example.com") == "https://example.com"


def test_coerce_url_without_protocol():
    """Test URL coercion without protocol."""
    assert coerce_url("example.com") == "http://example.com"


def test_coerce_url_strips_whitespace():
    """Test URL coercion strips whitespace."""
    assert coerce_url("  example.com  ") == "http://example.com"


def test_url_feed_prob_comments():
    """Test URL probability scoring for comments feeds."""
    assert url_feed_prob("http://example.com/comments/feed") == -2


def test_url_feed_prob_georss():
    """Test URL probability scoring for georss feeds."""
    assert url_feed_prob("http://example.com/georss") == -1


def test_url_feed_prob_atom():
    """Test URL probability scoring for atom feeds."""
    score = url_feed_prob("http://example.com/atom.xml")
    assert score > 0  # Atom should have positive score


def test_url_feed_prob_rss():
    """Test URL probability scoring for RSS feeds."""
    score = url_feed_prob("http://example.com/rss.xml")
    assert score > 0  # RSS should have positive score


def test_url_feed_prob_feed_keyword():
    """Test URL probability scoring for feed keyword."""
    score = url_feed_prob("http://example.com/feed")
    assert score > 0  # Feed keyword should have positive score


def test_url_feed_prob_no_keywords():
    """Test URL probability scoring for URLs without keywords."""
    assert url_feed_prob("http://example.com/page.html") == 0


def test_sort_urls_removes_duplicates():
    """Test that sort_urls removes duplicate URLs."""
    urls = [
        "http://example.com/feed",
        "http://example.com/feed",  # duplicate
        "http://example.com/atom.xml",
    ]
    result = sort_urls(urls)
    assert len(result) == 2
    assert "http://example.com/feed" in result
    assert "http://example.com/atom.xml" in result


def test_sort_urls_prioritizes_by_score():
    """Test that sort_urls prioritizes higher-scored URLs."""
    urls = [
        "http://example.com/comments/feed",  # score: -2
        "http://example.com/atom.xml",       # score: positive (atom)
        "http://example.com/feed",            # score: positive (feed)
    ]
    result = sort_urls(urls)

    # Atom and feed should come before comments
    assert result[-1] == "http://example.com/comments/feed"


def test_feedfinder_config_defaults():
    """Test FeedFinderConfig default values."""
    config = FeedFinderConfig()

    assert config.timeout == 10.0
    assert config.max_retries == 3
    assert config.max_concurrent_requests == 15
    assert config.check_all is False
    assert config.enable_json_feed is True
    assert config.enable_retry_logic is True


def test_feedfinder_config_custom_values():
    """Test FeedFinderConfig with custom values."""
    config = FeedFinderConfig(
        timeout=5.0,
        max_retries=1,
        check_all=True,
        enable_json_feed=False,
    )

    assert config.timeout == 5.0
    assert config.max_retries == 1
    assert config.check_all is True
    assert config.enable_json_feed is False


def test_feedfinder_config_user_agent():
    """Test FeedFinderConfig user agent generation."""
    config = FeedFinderConfig()
    assert "feedfinder2" in config.get_user_agent()

    config_custom = FeedFinderConfig(user_agent="MyBot/1.0")
    assert config_custom.get_user_agent() == "MyBot/1.0"


def test_feedfinder_is_feed_url():
    """Test FeedFinder.is_feed_url() method."""
    finder = FeedFinder()

    assert finder.is_feed_url("http://example.com/feed.xml") is True
    assert finder.is_feed_url("http://example.com/feed.rss") is True
    assert finder.is_feed_url("http://example.com/feed.atom") is True
    assert finder.is_feed_url("http://example.com/feed.json") is True
    assert finder.is_feed_url("http://example.com/page.html") is False


def test_feedfinder_is_feedlike_url():
    """Test FeedFinder.is_feedlike_url() method."""
    finder = FeedFinder()

    assert finder.is_feedlike_url("http://example.com/rss") is True
    assert finder.is_feedlike_url("http://example.com/atom") is True
    assert finder.is_feedlike_url("http://example.com/feed") is True
    assert finder.is_feedlike_url("http://example.com/feeds/posts") is True
    assert finder.is_feedlike_url("http://example.com/page") is False


def test_feedfinder_is_feed_data_rss():
    """Test FeedFinder.is_feed_data() with RSS content."""
    finder = FeedFinder()
    rss_content = "<rss><channel><title>Test</title></channel></rss>"

    assert finder.is_feed_data(rss_content) is True


def test_feedfinder_is_feed_data_atom():
    """Test FeedFinder.is_feed_data() with Atom content."""
    finder = FeedFinder()
    atom_content = '<feed xmlns="http://www.w3.org/2005/Atom"><title>Test</title></feed>'

    assert finder.is_feed_data(atom_content) is True


def test_feedfinder_is_feed_data_rdf():
    """Test FeedFinder.is_feed_data() with RDF content."""
    finder = FeedFinder()
    rdf_content = '<rdf:RDF xmlns:rdf="..."><channel><title>Test</title></channel></rdf:RDF>'

    assert finder.is_feed_data(rdf_content) is True


def test_feedfinder_is_feed_data_json_feed():
    """Test FeedFinder.is_feed_data() with JSON Feed content."""
    finder = FeedFinder()
    json_content = '{"version": "https://jsonfeed.org/version/1", "title": "Test"}'

    assert finder.is_feed_data(json_content, content_type="application/json") is True


def test_feedfinder_is_feed_data_html():
    """Test FeedFinder.is_feed_data() rejects HTML content."""
    finder = FeedFinder()
    html_content = "<html><head><title>Test</title></head><body></body></html>"

    assert finder.is_feed_data(html_content) is False


def test_feedfinder_is_feed_data_empty():
    """Test FeedFinder.is_feed_data() with empty content."""
    finder = FeedFinder()

    assert finder.is_feed_data("") is False
    assert finder.is_feed_data(None) is False


def test_config_custom_patterns():
    """Test FeedFinderConfig with custom patterns."""
    config = FeedFinderConfig(
        custom_leaf_filenames=["custom.xml", "special-feed.rss"],
        custom_subdirectories=["api/v1/feed/", "content/feeds/"],
    )

    assert "custom.xml" in config.custom_leaf_filenames
    assert "special-feed.rss" in config.custom_leaf_filenames
    assert "api/v1/feed/" in config.custom_subdirectories
    assert "content/feeds/" in config.custom_subdirectories


# Async-specific tests


@pytest.mark.asyncio
async def test_async_feed_finder_context_manager():
    """Test AsyncFeedFinder requires context manager."""
    config = FeedFinderConfig()
    finder = AsyncFeedFinder(config)

    # Should raise error if used outside context manager
    with pytest.raises(RuntimeError, match="must be used as async context manager"):
        await finder.get_feed("http://example.com")


@pytest.mark.asyncio
async def test_async_feed_finder_is_feed_data():
    """Test AsyncFeedFinder.is_feed_data() method."""
    config = FeedFinderConfig()
    async with AsyncFeedFinder(config) as finder:
        rss_content = "<rss><channel><title>Test</title></channel></rss>"
        assert finder.is_feed_data(rss_content) is True

        html_content = "<html><head><title>Test</title></head></html>"
        assert finder.is_feed_data(html_content) is False


@pytest.mark.asyncio
async def test_async_feed_finder_json_feed():
    """Test AsyncFeedFinder JSON Feed detection."""
    config = FeedFinderConfig(enable_json_feed=True)
    async with AsyncFeedFinder(config) as finder:
        # Valid JSON Feed
        json_feed = '{"version": "https://jsonfeed.org/version/1", "title": "Test"}'
        assert finder.is_feed_data(json_feed, "application/json") is True

        # JSON with items and title (feed-like)
        json_like = '{"items": [], "title": "Test Feed"}'
        assert finder.is_feed_data(json_like, "application/json") is True

        # Plain JSON (not a feed)
        plain_json = '{"data": "value"}'
        assert finder.is_feed_data(plain_json, "application/json") is False


# Shared function tests


def test_is_feed_data_impl_rss():
    """Test _is_feed_data_impl with RSS content."""
    rss = "<rss><channel><title>Test</title></channel></rss>"
    assert _is_feed_data_impl(rss, None, False) is True


def test_is_feed_data_impl_atom():
    """Test _is_feed_data_impl with Atom content."""
    atom = '<feed xmlns="http://www.w3.org/2005/Atom"><title>Test</title></feed>'
    assert _is_feed_data_impl(atom, None, False) is True


def test_is_feed_data_impl_json_feed_strict():
    """Test _is_feed_data_impl with strict JSON Feed."""
    json_feed = '{"version": "https://jsonfeed.org/version/1", "title": "Test"}'
    assert _is_feed_data_impl(json_feed, "application/json", True) is True


def test_is_feed_data_impl_json_feed_relaxed():
    """Test _is_feed_data_impl with relaxed JSON Feed detection."""
    # Has items + title = feed-like
    json_like = '{"items": [], "title": "Test"}'
    assert _is_feed_data_impl(json_like, "application/json", True) is True

    # Has items + home_page_url = feed-like
    json_like2 = '{"items": [], "home_page_url": "https://example.com"}'
    assert _is_feed_data_impl(json_like2, "application/json", True) is True

    # Has items but no feed metadata = not a feed
    json_not_feed = '{"items": []}'
    assert _is_feed_data_impl(json_not_feed, "application/json", True) is False


def test_is_feed_data_impl_plain_json_not_feed():
    """Test _is_feed_data_impl rejects plain JSON."""
    plain_json = '{"data": "value", "status": "ok"}'
    assert _is_feed_data_impl(plain_json, "application/json", True) is False


def test_is_feed_data_impl_html_rejection():
    """Test _is_feed_data_impl rejects HTML."""
    html = "<html><head><title>Test</title></head></html>"
    assert _is_feed_data_impl(html, "text/html", True) is False


def test_is_feed_data_impl_empty():
    """Test _is_feed_data_impl with empty content."""
    assert _is_feed_data_impl("", None, True) is False
    assert _is_feed_data_impl(None, None, True) is False
