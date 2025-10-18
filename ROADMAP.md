# Feedfinder2 Roadmap

This document outlines planned features and improvements for feedfinder2.

## Version 0.2.0 - Deep Crawl & Enhanced Discovery

### Priority 1: Deep Crawl API

**Goal**: Add comprehensive website crawling to discover RSS feeds in uncommon or deeply nested locations.

**Use Case**: Some websites have multiple RSS feeds (per category, per author, per tag) that aren't linked from the homepage. A deep crawl can discover these by exploring the site structure.

**Proposed API**:

```python
from feedfinder2 import deep_crawl_feeds, DeepCrawlConfig

# Synchronous
config = DeepCrawlConfig(
    max_depth=3,                    # How many levels deep to crawl
    max_pages=100,                  # Max pages to visit
    timeout_per_page=5.0,           # Timeout per page
    follow_external_links=False,    # Stay on same domain
    respect_robots_txt=True,        # Honor robots.txt
    crawl_delay=0.5,               # Delay between requests (seconds)
)

feeds = deep_crawl_feeds("https://example.com", config)
# Returns: {
#   "feeds": ["https://example.com/blog/feed", "https://example.com/author/john/rss", ...],
#   "pages_crawled": 45,
#   "feeds_found": 5,
#   "crawl_stats": {...}
# }

# Async version
feeds_data = await deep_crawl_feeds_async("https://example.com", config)
```

**Features**:
- **Breadth-first or depth-first crawling** strategies
- **Intelligent link extraction** from HTML (follow blog links, archive links, etc.)
- **Deduplication** of discovered feeds
- **Crawl statistics** (pages visited, feeds found, errors encountered)
- **Respect robots.txt** and crawl-delay directives
- **Rate limiting** to avoid overwhelming servers
- **Pattern-based link prioritization** (prioritize /blog/, /posts/, /category/ links)
- **Feed validation** during crawl (verify feeds are valid before adding to results)
- **Resume capability** for interrupted crawls (optional)

**Implementation Notes**:
- Build on existing async infrastructure
- Use BeautifulSoup for link extraction
- Implement URL normalization and deduplication
- Add configurable filters for link patterns
- Consider using a proper web crawler library (e.g., Scrapy) vs custom implementation

**Timeline**: Target for v0.2.0 (Q2 2025)

---

## Version 0.2.x - Performance & Reliability

### Priority 2: Rate Limiting

Add per-domain rate limiting to prevent overwhelming servers or triggering anti-bot measures.

**Features**:
- Configurable requests/second per domain
- Automatic backoff on HTTP 429 (Too Many Requests)
- Token bucket or leaky bucket algorithm
- Domain-aware semaphores

**API**:
```python
config = FeedFinderConfig(
    max_concurrent_requests=15,
    rate_limit_per_domain=5,  # Max 5 requests/second per domain
)
```

### Priority 3: Response Size Limits

Prevent memory issues with extremely large responses.

**Features**:
- Max response size (default: 10MB)
- Stream large responses
- Early termination for oversized content

**API**:
```python
config = FeedFinderConfig(
    max_response_size=10 * 1024 * 1024,  # 10MB
)
```

### Priority 4: HEAD Request Optimization

Implement the `use_head_requests` flag to reduce bandwidth.

**Features**:
- Check content-type with HEAD before GET
- Skip non-HTML/XML/JSON content-types
- Fallback to GET if HEAD not supported

---

## Version 0.3.0 - Intelligence & Accuracy

### Priority 5: Platform-Specific Discoverers

Add optimized discovery for popular platforms that follow predictable patterns.

**Platforms**:
- WordPress (wp-json API, standard feed paths)
- Ghost (standard paths, API)
- Substack (predictable structure)
- Medium (user feeds, publication feeds)
- Blogger (Atom feeds)
- Tumblr (RSS paths)

**API**:
```python
config = FeedFinderConfig(
    platform_hints=["wordpress", "ghost"],  # Try these first
)
```

### Priority 6: Feed Quality Scoring

Return feeds with quality/confidence scores to help users choose the best feed.

**Scoring Factors**:
- Feed freshness (last updated date)
- Number of items
- Proper metadata (title, description, author)
- Valid XML/JSON structure
- Complete vs partial feeds

**API**:
```python
feeds = find_feeds_with_scores("https://example.com")
# Returns: [
#   {"url": "https://example.com/feed", "score": 0.95, "reason": "Recent updates, full content"},
#   {"url": "https://example.com/rss", "score": 0.70, "reason": "Valid but outdated"},
# ]
```

### Priority 7: Content Validation

Deep validation using feedparser to ensure feeds are actually parseable.

**Features**:
- Optional feedparser integration
- Return feed metadata (title, items count, last updated)
- Filter out broken/empty feeds

---

## Version History

- **v0.1.0**: Initial release with async support, JSON Feed, enhanced patterns
- **v0.2.0**: Deep crawl API
- **v0.3.0**: Intelligence & accuracy improvements

---

## Feedback

Have ideas for feedfinder2? Open an issue at https://github.com/0xRaduan/feedfinder2/issues

Maintained by [The Summary Company](https://thesummary.company) and [Summate](https://summate.io).
