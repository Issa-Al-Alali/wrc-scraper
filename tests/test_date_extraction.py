from common.date_extraction import extract_published_date


def test_wrc_dated_label():
    text = "Some findings.\nDated:   26/08/2025\nWorkplace Relations Commission Adjudication Officer"
    assert extract_published_date(text) == "2025-08-26"


def test_equality_tribunal_date_of_issue_label():
    text = "Date of issue:    26th January 2010      \nDecision text follows mentioning 1st May 2009 too."
    assert extract_published_date(text) == "2010-01-26"


def test_labour_court_signoff_date():
    text = "Findings and determination.\nSigned on behalf of the Labour Court\n\n24th May 2024"
    assert extract_published_date(text) == "2024-05-24"


def test_fallback_takes_last_date_in_text():
    text = "Complaint received 13 September 2024. Hearing held 2 July 2025. 27 January 2010"
    assert extract_published_date(text) == "2010-01-27"


def test_no_date_returns_none():
    assert extract_published_date("no dates in here at all") is None