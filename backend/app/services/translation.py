from typing import List, Dict, Any


def get_translation(
    translations: List[Dict[str, Any]] | None, lang: str, fallback: str
) -> str:
    """Finds the text corresponding to 'lang' in a translations JSONB list, falling back to 'fallback'."""
    if not translations:
        return fallback
    for entry in translations:
        if entry.get("language") == lang:
            return entry.get("name", fallback)
    return fallback
