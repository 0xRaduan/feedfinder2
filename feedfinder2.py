#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

__version__ = "0.0.4"

try:
    __FEEDFINDER2_SETUP__
except NameError:
    __FEEDFINDER2_SETUP__ = False

if not __FEEDFINDER2_SETUP__:
    __all__ = ["find_feeds"]

    import logging
    import requests
    from bs4 import BeautifulSoup
    from six.moves.urllib import parse as urlparse


def coerce_url(url):
    url = url.strip()
    if url.startswith("feed://"):
        return "http://{0}".format(url[7:])
    for proto in ["http://", "https://"]:
        if url.startswith(proto):
            return url
    return "http://{0}".format(url)


class FeedFinder(object):

    def __init__(self, user_agent=None, timeout=None):
        if user_agent is None:
            user_agent = "feedfinder2/{0}".format(__version__)
        self.user_agent = user_agent
        self.timeout = timeout

    def get_feed(self, url):
        try:
            r = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=self.timeout)
        except Exception as e:
            logging.warning("Error while getting '{0}'".format(url))
            logging.warning("{0}".format(e))
            return None
        return r.text

    def is_feed_data(self, text):
        data = text.lower()
        if data.count("<html"):
            return False
        return data.count("<rss")+data.count("<rdf")+data.count("<feed")

    def is_feed(self, url):
        text = self.get_feed(url)
        if text is None:
            return False
        return self.is_feed_data(text)

    def is_feed_url(self, url):
        return any(map(url.lower().endswith,
                       [".rss", ".rdf", ".xml", ".atom"]))

    def is_feedlike_url(self, url):
        return any(map(url.lower().count,
                       ["rss", "rdf", "xml", "atom", "feed"]))


def find_feeds(url, check_all=False, user_agent=None, timeout=None):
    finder = FeedFinder(user_agent=user_agent, timeout=timeout)

    # Format the URL properly.
    url = coerce_url(url)

    # Download the requested URL.
    text = finder.get_feed(url)
    if text is None:
        return []

    # Check if it is already a feed.
    if finder.is_feed_data(text):
        return [url]

    # Look for <link> tags.
    logging.info("Looking for <link> tags.")
    tree = BeautifulSoup(text, "lxml")
    links = []
    for link in tree.find_all("link"):
        if link.get("type") in ["application/rss+xml",
                                "text/xml",
                                "application/atom+xml",
                                "application/x.atom+xml",
                                "application/x-atom+xml"]:
            links.append(urlparse.urljoin(url, link.get("href", "")))

    # Check the detected links.
    urls = list(filter(finder.is_feed, links))
    logging.info("Found {0} feed <link> tags.".format(len(urls)))
    if len(urls) and not check_all:
        return sort_urls(urls)

    # Look for <a> tags.
    logging.info("Looking for <a> tags.")
    local, remote = [], []
    for a in tree.find_all("a"):
        href = a.get("href", None)
        if href is None:
            continue
        if "://" not in href and finder.is_feed_url(href):
            local.append(href)
        if finder.is_feedlike_url(href):
            remote.append(href)

    # Check the local URLs.
    local = [urlparse.urljoin(url, l) for l in local]
    urls += list(filter(finder.is_feed, local))
    logging.info("Found {0} local <a> links to feeds.".format(len(urls)))
    if len(urls) and not check_all:
        return sort_urls(urls)

    # Check the remote URLs.
    remote = [urlparse.urljoin(url, l) for l in remote]
    urls += list(filter(finder.is_feed, remote))
    logging.info("Found {0} remote <a> links to feeds.".format(len(urls)))
    if len(urls) and not check_all:
        return sort_urls(urls)

    # Guessing potential URLs.
    logging.info("Guessing potential feed URLs.")
    parsed_url = urlparse.urlsplit(url)
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc
    root_url = "{0}://{1}/".format(scheme, netloc)
    
    # urlparse.urljoin(url, ".") correctly gives the "directory" of the current URL
    # e.g., http://example.com/foo/bar.html -> http://example.com/foo/
    # e.g., http://example.com/foo/ -> http://example.com/foo/
    # e.g., http://example.com -> http://example.com/ (if it was coerced to http://example.com/)
    # However, if url is http://example.com (no trailing slash), urljoin(url, ".") is http://example.com/
    # and urljoin(url, "atom.xml") is http://example.com/atom.xml.
    # If url is http://example.com/blog, urljoin(url, "atom.xml") is http://example.com/atom.xml (wrong!)
    # We need to ensure the base for relative leaf resolution is the actual directory.
    # A common way to get the directory is to join with "./" or ensure url ends with "/" if it's path-like
    
    current_dir_url = urlparse.urljoin(url, "./") # Ensures it's a directory

    leaf_filenames = [
        "feed.xml", "atom.xml", "rss.xml", "feed", "rss", "atom",
        "index.xml", "index.atom", "index.rss", "index.rdf",
        "feed.json", "rss.json", "wp-rss2.xml", "feeds/posts/default",
        "blog.xml"
    ]
    common_root_subdirectories = [
        "feed/", "feeds/", "rss/", "atom/", "blog/", "news/", "updates/", "comments/"
    ]

    guessed_urls = []

    # b. Leaf patterns relative to the input URL's directory
    for leaf in leaf_filenames:
        guessed_urls.append(urlparse.urljoin(current_dir_url, leaf))

    # c. Leaf patterns relative to the root
    for leaf in leaf_filenames:
        guessed_urls.append(urlparse.urljoin(root_url, leaf))

    # d. Common root subdirectories (as feeds themselves)
    for subdir in common_root_subdirectories:
        guessed_urls.append(urlparse.urljoin(root_url, subdir))

    # e. Leaf patterns within common root subdirectories
    for subdir in common_root_subdirectories:
        base_subdir_url = urlparse.urljoin(root_url, subdir)
        for leaf in leaf_filenames:
            guessed_urls.append(urlparse.urljoin(base_subdir_url, leaf))
            
    # Remove duplicates
    unique_guessed_urls = sorted(list(set(guessed_urls)))
    
    # Filter and add to the main list
    if unique_guessed_urls:
        logging.info("Trying {0} guessed URLs.".format(len(unique_guessed_urls)))
        urls += list(filter(finder.is_feed, unique_guessed_urls))
        logging.info("Found {0} feeds through guessing.".format(len(urls))) # This count is cumulative, might be better to log count from this step

    return sort_urls(urls)


def url_feed_prob(url):
    if "comments" in url:
        return -2
    if "georss" in url:
        return -1
    kw = ["atom", "rss", "rdf", ".xml", "feed"]
    for p, t in zip(range(len(kw), 0, -1), kw):
        if t in url:
            return p
    return 0


def sort_urls(feeds):
    return sorted(list(set(feeds)), key=url_feed_prob, reverse=True)


if __name__ == "__main__":
    print(find_feeds("www.preposterousuniverse.com/blog/", timeout = 1))
    print(find_feeds("www.preposterousuniverse.com/blog/"))
    print(find_feeds("http://xkcd.com"))
    print(find_feeds("dan.iel.fm/atom.xml"))
    print(find_feeds("dan.iel.fm", check_all=True))
    print(find_feeds("kapadia.github.io"))
    print(find_feeds("blog.jonathansick.ca"))
    print(find_feeds("asdasd"))
    
