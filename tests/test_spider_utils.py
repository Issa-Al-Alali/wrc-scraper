from wrc_scraper.spiders.wrc_spider import _strip_volatile_markers


def test_strips_elapsed_time_comment():
    raw = b"<html>content</html><!-- cached or not being index.aspx page --><!-- Elapsed time: 0.0156007 -->"
    stripped = _strip_volatile_markers(raw)
    assert b"Elapsed time" not in stripped
    assert b"<html>content</html>" in stripped


def test_same_content_hashes_equal_after_stripping():
    import hashlib

    page_a = b"<html>same content</html><!-- Elapsed time: 0.011 -->"
    page_b = b"<html>same content</html><!-- Elapsed time: 0.099 -->"
    assert hashlib.sha256(_strip_volatile_markers(page_a)).digest() == hashlib.sha256(
        _strip_volatile_markers(page_b)
    ).digest()


def test_hashes_equal_when_cache_status_comment_is_entirely_absent():
    # The cache-status comment isn't just variable text -- on a cache hit the
    # server omits it completely, which a regex only matching the timing
    # comment's *contents* would miss (confirmed against two real fetches of
    # the same case a few minutes apart, one with each comment).
    import hashlib

    with_both_comments = (
        b"<html>same content</html>"
        b"<!-- cached or not being index.aspx page --><!-- Elapsed time: 0.011 -->"
    )
    without_cache_comment = b"<html>same content</html><!-- Elapsed time: 0.099 -->"
    assert hashlib.sha256(_strip_volatile_markers(with_both_comments)).digest() == hashlib.sha256(
        _strip_volatile_markers(without_cache_comment)
    ).digest()


def test_leaves_content_without_marker_untouched():
    raw = b"<html>no marker here</html>"
    assert _strip_volatile_markers(raw) == raw