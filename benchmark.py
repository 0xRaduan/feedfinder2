#!/usr/bin/env python
"""
Performance benchmark comparing synchronous and async feed finding.

This script benchmarks the performance improvement of the async API over
the synchronous API for feed discovery.
"""

import asyncio
import time
from typing import List

from feedfinder2 import FeedFinderConfig, find_feeds, find_feeds_async


# Test URLs representing common blog platforms and websites
TEST_URLS = [
    "https://xkcd.com",
    "https://www.joelonsoftware.com",
    "https://daringfireball.net",
    "https://blog.codinghorror.com",
    "https://www.scottaaronson.com/blog/",
    "https://marginalrevolution.com",
    "https://slatestarcodex.com",
    "https://www.gwern.net",
]


def benchmark_sync(urls: List[str], timeout: float = 10.0) -> tuple[float, int]:
    """
    Benchmark synchronous feed finding.

    Args:
        urls: List of URLs to test
        timeout: Timeout per request

    Returns:
        Tuple of (total_time, total_feeds_found)
    """
    start = time.time()
    total_feeds = 0

    for url in urls:
        try:
            feeds = find_feeds(url, check_all=False, timeout=timeout)
            total_feeds += len(feeds)
            print(f"  [Sync] {url}: {len(feeds)} feeds")
        except Exception as e:
            print(f"  [Sync] {url}: Error - {e}")

    elapsed = time.time() - start
    return elapsed, total_feeds


async def benchmark_async(urls: List[str], config: FeedFinderConfig) -> tuple[float, int]:
    """
    Benchmark async feed finding.

    Args:
        urls: List of URLs to test
        config: Configuration for async finder

    Returns:
        Tuple of (total_time, total_feeds_found)
    """
    start = time.time()
    total_feeds = 0

    # Run all URL discoveries concurrently
    tasks = [find_feeds_async(url, config) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            print(f"  [Async] {url}: Error - {result}")
        else:
            total_feeds += len(result)
            print(f"  [Async] {url}: {len(result)} feeds")

    elapsed = time.time() - start
    return elapsed, total_feeds


def benchmark_async_sequential(
    urls: List[str], config: FeedFinderConfig
) -> tuple[float, int]:
    """
    Benchmark async feed finding sequentially (one at a time).

    Args:
        urls: List of URLs to test
        config: Configuration for async finder

    Returns:
        Tuple of (total_time, total_feeds_found)
    """

    async def run_sequential():
        start = time.time()
        total_feeds = 0

        for url in urls:
            try:
                feeds = await find_feeds_async(url, config)
                total_feeds += len(feeds)
                print(f"  [Async-Seq] {url}: {len(feeds)} feeds")
            except Exception as e:
                print(f"  [Async-Seq] {url}: Error - {e}")

        elapsed = time.time() - start
        return elapsed, total_feeds

    return asyncio.run(run_sequential())


def main():
    """Run performance benchmarks."""
    print("=" * 80)
    print("Feedfinder2 Performance Benchmark")
    print("=" * 80)
    print(f"\nTesting with {len(TEST_URLS)} URLs")
    print(f"URLs: {', '.join(TEST_URLS[:3])}...")
    print()

    timeout = 10.0

    # Benchmark 1: Synchronous API
    print("\n" + "=" * 80)
    print("Benchmark 1: Synchronous API (Sequential)")
    print("=" * 80)
    sync_time, sync_feeds = benchmark_sync(TEST_URLS, timeout=timeout)
    print(f"\nTotal time: {sync_time:.2f}s")
    print(f"Total feeds found: {sync_feeds}")
    print(f"Average time per URL: {sync_time / len(TEST_URLS):.2f}s")

    # Benchmark 2: Async API (Sequential - one at a time)
    print("\n" + "=" * 80)
    print("Benchmark 2: Async API (Sequential - one at a time)")
    print("=" * 80)
    config = FeedFinderConfig(
        timeout=timeout,
        check_all=False,
        max_concurrent_requests=15,
    )
    async_seq_time, async_seq_feeds = benchmark_async_sequential(TEST_URLS, config)
    print(f"\nTotal time: {async_seq_time:.2f}s")
    print(f"Total feeds found: {async_seq_feeds}")
    print(f"Average time per URL: {async_seq_time / len(TEST_URLS):.2f}s")

    # Benchmark 3: Async API (Concurrent - all at once)
    print("\n" + "=" * 80)
    print("Benchmark 3: Async API (Concurrent - all URLs at once)")
    print("=" * 80)
    async_time, async_feeds = asyncio.run(benchmark_async(TEST_URLS, config))
    print(f"\nTotal time: {async_time:.2f}s")
    print(f"Total feeds found: {async_feeds}")
    print(f"Average time per URL: {async_time / len(TEST_URLS):.2f}s")

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Synchronous API:           {sync_time:.2f}s ({sync_feeds} feeds)")
    print(f"Async API (Sequential):    {async_seq_time:.2f}s ({async_seq_feeds} feeds)")
    print(f"Async API (Concurrent):    {async_time:.2f}s ({async_feeds} feeds)")
    print()
    print(f"Speedup (Async Sequential vs Sync): {sync_time / async_seq_time:.2f}x")
    print(f"Speedup (Async Concurrent vs Sync): {sync_time / async_time:.2f}x")
    print(f"Speedup (Async Concurrent vs Async Sequential): {async_seq_time / async_time:.2f}x")
    print()
    print("Note: The async concurrent version processes all URLs in parallel,")
    print("      while sync and async sequential process them one at a time.")
    print("      Within each URL discovery, async uses concurrent HTTP requests.")
    print()

    # Detailed concurrency benchmark
    print("\n" + "=" * 80)
    print("Detailed Concurrency Benchmark (Single URL)")
    print("=" * 80)
    print("Testing single URL with check_all=True to compare concurrent guessing")
    test_url = TEST_URLS[0]

    # Sync with check_all
    print(f"\nSynchronous (check_all=True): {test_url}")
    start = time.time()
    sync_all_feeds = find_feeds(test_url, check_all=True, timeout=timeout)
    sync_all_time = time.time() - start
    print(f"  Time: {sync_all_time:.2f}s, Feeds: {len(sync_all_feeds)}")

    # Async with check_all
    print(f"\nAsync (check_all=True): {test_url}")
    config_all = FeedFinderConfig(
        timeout=timeout,
        check_all=True,
        max_concurrent_requests=20,
    )

    async def test_async_all():
        start = time.time()
        feeds = await find_feeds_async(test_url, config_all)
        elapsed = time.time() - start
        return elapsed, feeds

    async_all_time, async_all_feeds = asyncio.run(test_async_all())
    print(f"  Time: {async_all_time:.2f}s, Feeds: {len(async_all_feeds)}")
    print(f"\nSpeedup: {sync_all_time / async_all_time:.2f}x")


if __name__ == "__main__":
    main()
