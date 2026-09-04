from common.wrc_bodies import (
    EAT,
    EQUALITY_TRIBUNAL,
    LABOUR_COURT,
    WRC,
    body_for_identifier,
    body_from_content,
)


def test_wrc_prefixes():
    assert body_for_identifier("ADJ-00053994") == WRC
    assert body_for_identifier("IR-SC-00003624") == WRC
    assert body_for_identifier("adj-00046044") == WRC  # case-insensitive


def test_equality_tribunal_prefixes():
    assert body_for_identifier("DEC-E2010-007") == EQUALITY_TRIBUNAL
    assert body_for_identifier("DEC-S2010-007") == EQUALITY_TRIBUNAL


def test_eat_prefixes():
    for identifier in ["UD1851", "MN123", "RP45", "WT9", "PW1", "TE1", "TU1", "I1", "P3"]:
        assert body_for_identifier(identifier) == EAT


def test_unknown_prefix_defaults_to_labour_court():
    # Labour Court's codes are open-ended (LCR, AD, EDA, DIC, DWT, FTD, HSD,
    # PTD, UDD, and any future ones) so it's the default, not a whitelist.
    for identifier in ["LCR22979", "AD1355", "EDA1431", "DIC142", "DWT2024", "SOMETHING-NEW"]:
        assert body_for_identifier(identifier) == LABOUR_COURT


def test_body_from_content_signatures():
    assert body_from_content("ADJUDICATION OFFICER DECISION") == WRC
    assert body_from_content("THE EQUALITY TRIBUNAL") == EQUALITY_TRIBUNAL
    assert body_from_content("EMPLOYMENT APPEALS TRIBUNAL") == EAT
    assert body_from_content("Signed on behalf of the Labour Court") == LABOUR_COURT
    assert body_from_content("nothing recognizable here") is None