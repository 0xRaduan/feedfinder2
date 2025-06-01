import unittest
from unittest.mock import patch
from feedfinder2 import find_feeds
import requests  # Required for requests.exceptions


# Helper class for mock responses
class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"Mock HTTP Error {self.status_code}")


class TestFeedGuessing(unittest.TestCase):
    def setUp(self):
        # self.mock_responses will map URL -> content string
        self.mock_responses = {}
        # self.feed_content is a generic valid feed string
        self.feed_content = "<rss><channel><title>Test Feed</title></channel></rss>"
        self.html_content = (
            "<html><head><title>Test Page</title></head><body></body></html>"
        )

    def mock_requests_get_logic(self, url, headers=None, timeout=None):
        # Print for debugging during test development
        # print(f"Mock GET request for: {url}")
        # print(f"Available mock responses for: {list(self.mock_responses.keys())}")
        if url in self.mock_responses:
            # print(f"Mocking URL: {url} with content: "
            #       f"{self.mock_responses[url][:30]}...")
            return MockResponse(self.mock_responses[url])
        # Default response for any other URL is a simple HTML page
        # print(f"Mocking URL: {url} with default HTML content.")
        return MockResponse(self.html_content)

    @patch("feedfinder2.requests.get")
    def test_guess_leaf_at_root(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://example.com"
        feed_url = "http://example.com/atom.xml"

        # Mock the main page and the feed page
        self.mock_responses[test_url] = self.html_content
        self.mock_responses[feed_url] = self.feed_content

        # check_all=True forces guessing
        feeds = find_feeds(test_url, check_all=True)
        self.assertIn(feed_url, feeds)
        self.assertEqual(len(feeds), 1)

    @patch("feedfinder2.requests.get")
    def test_guess_leaf_in_subdir_relative_to_input(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://example.com/blog/"
        feed_url = "http://example.com/blog/feed.xml"

        self.mock_responses[test_url] = self.html_content
        self.mock_responses[feed_url] = self.feed_content

        feeds = find_feeds(test_url, check_all=True)
        self.assertIn(feed_url, feeds)
        self.assertEqual(len(feeds), 1)

    @patch("feedfinder2.requests.get")
    def test_guess_leaf_in_subdir_relative_to_input_no_trailing_slash(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        # Test URL without trailing slash, expecting feed relative to it as a directory
        test_url = "http://example.com/blog"
        # feedfinder2.py's current_dir_url = urlparse.urljoin(url, "./") will make this http://example.com/blog/
        feed_url = "http://example.com/blog/feed.xml"

        self.mock_responses[test_url] = self.html_content
        self.mock_responses[feed_url] = self.feed_content

        feeds = find_feeds(test_url, check_all=True)
        self.assertIn(feed_url, feeds)
        self.assertEqual(len(feeds), 1)

    @patch("feedfinder2.requests.get")
    def test_guess_leaf_in_common_root_subdir(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://example.com"
        # Example: http://example.com/news/rss.xml
        # common_root_subdirectories = [
        #    "feed/", "feeds/", "rss/", "atom/", "blog/", "news/", "updates/"
        # ]
        # leaf_filenames = ["feed.xml", "atom.xml", "rss.xml", ...]
        feed_url = "http://example.com/news/rss.xml"

        self.mock_responses[test_url] = self.html_content
        self.mock_responses[feed_url] = self.feed_content

        feeds = find_feeds(test_url, check_all=True)
        self.assertIn(feed_url, feeds)
        self.assertEqual(len(feeds), 1)

    @patch("feedfinder2.requests.get")
    def test_guess_common_root_subdir_itself_as_feed(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://example.com"
        # Example: http://example.com/feed/
        feed_url = "http://example.com/feed/"

        self.mock_responses[test_url] = self.html_content
        self.mock_responses[feed_url] = self.feed_content

        feeds = find_feeds(test_url, check_all=True)
        self.assertIn(feed_url, feeds)
        self.assertEqual(len(feeds), 1)

    @patch("feedfinder2.requests.get")
    def test_no_feeds_found_guessing_misses(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://anotherdomain.com"
        self.mock_responses[test_url] = self.html_content
        # No other self.mock_responses entries means all guesses
        # will get default html_content

        feeds = find_feeds(test_url, check_all=True)
        self.assertEqual(len(feeds), 0)

    @patch("feedfinder2.requests.get")
    def test_guessing_with_check_all_true(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://checkall.com"
        # leaf_filenames includes "wp-rss2.xml"
        feed_url = "http://checkall.com/wp-rss2.xml"  # This is a leaf at root

        # Main page has no links, so find_feeds would return [] if not for guessing
        self.mock_responses[test_url] = self.html_content
        self.mock_responses[feed_url] = self.feed_content

        feeds = find_feeds(test_url, check_all=True)
        self.assertIn(feed_url, feeds)
        self.assertEqual(len(feeds), 1)

    @patch("feedfinder2.requests.get")
    def test_sort_order_of_guessed_feeds(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://priority.com"
        # From leaf_filenames, "feed" has higher priority than "atom"
        # based on url_feed_prob
        # url_feed_prob: "atom", "rss", "rdf", ".xml", "feed"
        # "feed" in url -> p=1
        # "atom" in url -> p=5
        # So atom.xml should come before feed.xml if both are simple leaves.
        # Let's re-check url_feed_prob:
        # kw = ["atom", "rss", "rdf", ".xml", "feed"]
        # zip(range(len(kw), 0, -1), kw) gives:
        # (5, "atom"), (4, "rss"), (3, "rdf"), (2, ".xml"), (1, "feed")
        # Higher p is better. So "atom" (p=5) is better than "feed" (p=1).

        # Test case: atom.xml (higher priority) and feed.xml (lower priority)
        # feed_url_high_priority = "http://priority.com/atom.xml"  # p=5
        # feed_url_low_priority = "http://priority.com/feed.xml"  # p=2 (due to .xml)
        # If it was just /feed, it would be p=1.
        # If it was /blog/feed, also p=1.

        # Let's use one that is clearly higher due to "atom" vs one with "comments"
        feed_url_good = "http://priority.com/atom.xml"  # p=5
        feed_url_comments = (
            "http://priority.com/comments/feed.xml"  # p=-2 because of "comments"
        )
        # then p=2 for ".xml"
        # sort_urls uses key=url_feed_prob.
        # url_feed_prob returns -2 if "comments" in url.

        self.mock_responses[test_url] = self.html_content
        self.mock_responses[feed_url_good] = self.feed_content
        self.mock_responses[feed_url_comments] = self.feed_content

        feeds = find_feeds(test_url, check_all=True)

        # We expect feed_url_good to be first.
        expected_order = [feed_url_good, feed_url_comments]
        self.assertEqual(feeds, expected_order)

    @patch("feedfinder2.requests.get")
    def test_guess_leaf_jsonfeed_not_detected_by_default_is_feed_data(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://jsonfeed.org"
        # leaf_filenames includes "feed.json"
        json_feed_url = "http://jsonfeed.org/feed.json"

        self.mock_responses[test_url] = self.html_content
        # is_feed_data checks for "<rss", "<rdf", "<feed".
        # A pure JSON feed won't have these.
        self.mock_responses[json_feed_url] = (
            '{"version": "https://jsonfeed.org/version/1", "title": "My Example Feed"}'
        )

        feeds = find_feeds(test_url, check_all=True)
        # It should NOT find this feed because is_feed_data won't recognize it
        self.assertNotIn(json_feed_url, feeds)
        self.assertEqual(len(feeds), 0)

    # Test for a case where input URL itself is a feed
    @patch("feedfinder2.requests.get")
    def test_input_url_is_already_a_feed(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        feed_url = "http://example.com/directfeed.xml"
        self.mock_responses[feed_url] = self.feed_content

        feeds = find_feeds(feed_url, check_all=True)
        self.assertEqual(feeds, [feed_url])

    # Test for feeds found via <link> tags - ensure guessing is skipped
    # if check_all=False
    @patch("feedfinder2.requests.get")
    def test_feeds_from_link_tags_skips_guessing_if_not_check_all(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://example.com"
        linked_feed_url = "http://example.com/linkedfeed.rss"
        guessed_feed_url = "http://example.com/atom.xml"  # A potential guessed feed

        # Page has a link to a feed
        page_with_link_tag = f'''
        <html><head>
            <link type="application/rss+xml" href="{linked_feed_url}" />
        </head><body></body></html>
        '''
        self.mock_responses[test_url] = page_with_link_tag
        self.mock_responses[linked_feed_url] = self.feed_content
        self.mock_responses[guessed_feed_url] = (
            self.feed_content
        )  # Make this a valid feed too

        feeds = find_feeds(test_url, check_all=False)  # check_all=False
        self.assertIn(linked_feed_url, feeds)
        self.assertNotIn(
            guessed_feed_url,
            feeds,
            "Guessing should not have occurred if a feed was found via <link> "
            "and check_all=False",
        )
        self.assertEqual(len(feeds), 1)

    @patch("feedfinder2.requests.get")
    def test_feeds_from_link_tags_does_guessing_if_check_all_true(self, mock_get):
        mock_get.side_effect = self.mock_requests_get_logic

        test_url = "http://example.com"
        linked_feed_url = "http://example.com/linkedfeed.rss"
        guessed_feed_url = "http://example.com/atom.xml"

        page_with_link_tag = f'''
        <html><head>
            <link type="application/rss+xml" href="{linked_feed_url}" />
        </head><body></body></html>
        '''
        self.mock_responses[test_url] = page_with_link_tag
        self.mock_responses[linked_feed_url] = self.feed_content
        self.mock_responses[guessed_feed_url] = self.feed_content

        feeds = find_feeds(test_url, check_all=True)  # check_all=True
        self.assertIn(linked_feed_url, feeds)
        self.assertIn(
            guessed_feed_url, feeds, "Guessing should have occurred with check_all=True"
        )
        self.assertEqual(len(feeds), 2)  # Actual order depends on sort_urls


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
