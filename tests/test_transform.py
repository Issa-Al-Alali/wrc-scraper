from transform.transform import clean_html


SAMPLE_DETAIL_PAGE = b"""
<html><body>
<header><nav>site nav</nav></header>
<div class="language-switch">Gaeilge</div>
<div class="return-to-search"><a>Return to Search</a></div>
<div class="col-sm-9">
  <h1 class="page-title">ADJ-00053994</h1>
  <div class="content"><h1>ADJUDICATION OFFICER DECISION</h1><p>Some decision text.</p></div>
</div>
<footer>site footer</footer>
</body></html>
"""


def test_clean_html_keeps_only_main_content():
    cleaned = clean_html(SAMPLE_DETAIL_PAGE, "ADJ-00053994").decode()
    assert "Some decision text." in cleaned
    assert "ADJUDICATION OFFICER DECISION" in cleaned


def test_clean_html_strips_nav_and_footer():
    cleaned = clean_html(SAMPLE_DETAIL_PAGE, "ADJ-00053994").decode()
    assert "site nav" not in cleaned
    assert "site footer" not in cleaned
    assert "Return to Search" not in cleaned
    assert "Gaeilge" not in cleaned


def test_clean_html_missing_content_div_returns_empty_body():
    cleaned = clean_html(b"<html><body><p>no content div here</p></body></html>", "X-1").decode()
    assert "no content div here" not in cleaned