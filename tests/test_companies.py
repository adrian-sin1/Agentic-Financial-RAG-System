from src.retrieval.companies import normalize_company_name


def test_maps_colloquial_names_to_the_stored_canonical_name():
    assert normalize_company_name("Google") == "Alphabet"
    assert normalize_company_name("google") == "Alphabet"
    assert normalize_company_name("Facebook") == "Meta"
    assert normalize_company_name("FB") == "Meta"


def test_ticker_symbols_map_to_the_canonical_name():
    assert normalize_company_name("AAPL") == "Apple"
    assert normalize_company_name("MSFT") == "Microsoft"
    assert normalize_company_name("AMZN") == "Amazon"


def test_already_canonical_names_pass_through_unchanged():
    for name in ["Apple", "Microsoft", "Alphabet", "Amazon", "Meta"]:
        assert normalize_company_name(name) == name


def test_unknown_company_falls_back_to_the_original_input():
    assert normalize_company_name("Netflix") == "Netflix"


def test_none_passes_through_as_none():
    assert normalize_company_name(None) is None
