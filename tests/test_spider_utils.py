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


def test_leaves_content_without_marker_untouched():
    raw = b"<html>no marker here</html>"
    assert _strip_volatile_markers(raw) == raw