from typing import List, Dict, Any


def get_translation(
    translations: List[Dict[str, Any]] | None, lang: str, fallback: str
) -> str:
    """Find text for 'lang' in translations list, else return fallback."""
    if not translations:
        return fallback
    for entry in translations:
        if entry.get("language") == lang:
            return entry.get("name", fallback)
    return fallback
