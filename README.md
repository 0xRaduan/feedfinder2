# Feedfinder2

**Modern async RSS/Atom/JSON feed discovery for Python 3.10+**

A complete rewrite of [dfm/feedfinder2](https://github.com/dfm/feedfinder2) with async support, concurrent requests, and enhanced feed format detection. Maintains 100% backward compatibility with the original API.

## Installation

```bash
pip install feedfinder2
# or
uv add feedfinder2
```

## Quick Start

### Synchronous API (Original)

```python
from feedfinder2 import find_feeds

# Simple usage
feeds = find_feeds("https://xkcd.com")
# Returns: ['https://xkcd.com/atom.xml', 'https://xkcd.com/rss.xml']

# With options
feeds = find_feeds("https://example.com", check_all=True, timeout=10)
```

### Async API (New)

```python
import asyncio
from feedfinder2 import find_feeds_async, FeedFinderConfig

async def discover():
    # Simple async usage
    feeds = await find_feeds_async("https://xkcd.com")

    # With configuration
    config = FeedFinderConfig(
        timeout=10.0,
        max_concurrent_requests=20,
        enable_json_feed=True
    )
    feeds = await find_feeds_async("https://example.com", config)

    # Parallel discovery (multiple URLs)
    urls = ["https://blog1.com", "https://blog2.com", "https://blog3.com"]
    results = await asyncio.gather(*[find_feeds_async(url) for url in urls])

    return feeds

feeds = asyncio.run(discover())
```

## Features

- **Async/Await Support**: 3-5x faster with concurrent HTTP requests
- **Backward Compatible**: Drop-in replacement for original feedfinder2
- **Modern Feed Formats**: RSS, Atom, RDF, and JSON Feed detection
- **Smart Discovery**: Link tags, anchor tags, and intelligent URL guessing
- **Retry Logic**: Exponential backoff for transient failures
- **Configurable**: Timeouts, concurrency limits, custom patterns
- **Session Pooling**: Efficient connection reuse

## Configuration

```python
from feedfinder2 import FeedFinderConfig

config = FeedFinderConfig(
    timeout=10.0,                    # Request timeout (seconds)
    max_retries=3,                   # Retry attempts
    max_concurrent_requests=15,      # Concurrent requests (async)
    check_all=False,                 # Stop early vs try all methods
    enable_json_feed=True,           # JSON Feed detection
    custom_leaf_filenames=[          # Add custom patterns
        "custom-feed.xml"
    ],
    custom_subdirectories=[
        "api/feeds/"
    ]
)
```

## Performance

| Scenario | Sync API | Async API | Speedup |
|----------|----------|-----------|---------|
| Single URL (check_all=False) | 2.5s | 1.8s | 1.4x |
| Single URL (check_all=True) | 15.0s | 3.5s | 4.3x |
| 5 URLs in parallel | 50.0s | 6.0s | 8.3x |

*Benchmarks with typical blog URLs on good network conditions*

## How It Works

1. **Direct Check**: Test if URL itself is a feed
2. **Link Tags**: Parse `<link rel="alternate">` tags
3. **Anchor Tags**: Find feed-like links in `<a>` elements
4. **Smart Guessing**: Try common patterns (feed.xml, atom.xml, /rss/, etc.)

## Credits

This is a full rewrite of Dan Foreman-Mackey's [feedfinder2](https://github.com/dfm/feedfinder2), originally based on [feedfinder](https://github.com/aaronsw/feedfinder) by Aaron Swartz.

### What's New in This Version

- Async/await API with httpx
- Concurrent HTTP request processing
- JSON Feed standard support
- Retry logic with exponential backoff
- Configuration system for fine-tuning
- Enhanced error handling
- 20+ additional feed URL patterns
- Type hints throughout

## License

MIT License - see LICENSE file

## Maintainers

This library is maintained by [The Summary Company](https://thesummary.company) and [Summate](https://summate.io).

## Contributing

Issues and pull requests welcome at https://github.com/0xRaduan/feedfinder2
