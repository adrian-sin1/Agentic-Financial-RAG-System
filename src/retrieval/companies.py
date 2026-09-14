COMPANY_ALIASES = {
    "google": "Alphabet",
    "alphabet": "Alphabet",
    "googl": "Alphabet",
    "goog": "Alphabet",
    "facebook": "Meta",
    "fb": "Meta",
    "meta": "Meta",
    "meta platforms": "Meta",
    "apple": "Apple",
    "aapl": "Apple",
    "microsoft": "Microsoft",
    "msft": "Microsoft",
    "amazon": "Amazon",
    "amazon.com": "Amazon",
    "amzn": "Amazon",
}


def normalize_company_name(name: str | None) -> str | None:
    """Map a common colloquial name (Google, Facebook, ticker symbols) to the
    exact string stored in Snowflake/Pinecone (Alphabet, Meta). People say
    "Google" and "Facebook" in everyday speech, not the legal entity names
    our data is keyed on -- without this, a perfectly reasonable question
    silently finds nothing, since company is matched exactly.

    Falls back to the original (title-cased) input unchanged if it isn't a
    known alias, so this degrades gracefully for companies outside the
    current 5 rather than erroring.
    """
    if name is None:
        return None
    return COMPANY_ALIASES.get(name.strip().lower(), name)
