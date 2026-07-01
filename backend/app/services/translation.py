from typing import List, Dict, Any


SWAHILI_TRANSLATIONS = {
    # Question Labels
    "Report an incident": "Ripoti tukio",
    "Select Sub-County": "Chagua Kaunti Ndogo",
    "Upload photo evidence": "Pakia ushahidi wa picha",
    "Select Site": "Chagua Kituo",
    "Sampling ID": "Kitambulisho cha Sampuli",
    "Site Photo": "Picha ya Eneo",
    "GPS Reading": "Kipimo cha GPS",
    "pH Level": "Kiwango cha pH",
    "Water Temperature (°C)": "Joto la Maji (°C)",
    "Dissolved Oxygen (mg/L)": "Oksijeni Iliyoyeyuka (mg/L)",
    "Crops grown in catchment": "Mazao yanayopandwa kwenye bonde la maji",
    "Plant species in catchment": "Aina za mimea kwenye bonde la maji",
    "Select Wetland": "Chagua Eneo la Wetland",
    "Dependant Population": "Idadi ya Watu Wanaotegemea",
    "Different uses of the wetland": "Matumizi tofauti ya ardhi ya wetland",
    "Major anthropogenic/natural threats": (
        "Vitisho vikuu vya kibinadamu/vya asili"
    ),
    "Primary land use in the area": "Matumizi kuu ya ardhi katika eneo",
    "Approximate area of the wetland": "Eneo la karibu la wetland",
    "Fish Abundance Trend": "Mwelekeo wa Wingi wa Samaki",
    "Water Clarity Trend": "Mwelekeo wa Usafi wa Maji",
    "Vegetation Cover Trend": "Mwelekeo wa Kufunika kwa Mimea",
    "pH": "pH",
    "Water Temperature": "Joto la Maji",
    "Dissolved Oxygen": "Oksijeni Iliyoyeyuka",
    "Biochemical Oxygen Demand (BOD)": (
        "Mahitaji ya Oksijeni ya Kibaolojia (BOD)"
    ),
    "Orthophosphate": "Orthophosphate",
    "Nitrate": "Nitrate",
    "Mercury": "Mercury",
    "Heavy Metals (Description/PPM)": "Metali Nzito (Maelezo/PPM)",
    "Total Nitrogen (N)": "Nitrojeni Jumla (N)",
    "Total Phosphorus (P)": "Fosforasi Jumla (P)",
    # Options
    "Water colour (darker/murkier)": "Rangi ya maji (nyeusi/chafu)",
    "Smell (bad odour)": "Harufu (harufu mbaya)",
    "Fish or animal kills": "Vifo vya samaki au wanyama",
    "Storm event": "Tukio la dhoruba",
    "High water level": "Kiwango cha juu cha maji",
    "Low water level": "Kiwango cha chini cha maji",
    "Same or increased": "Sawa au kuongezeka",
    "Slightly declined": "Kupungua kidogo",
    "Moderately declined": "Kupungua kwa kiasi",
    "Severely declined": "Kupungua sana",
    "Same or clearer": "Sawa au wazi zaidi",
    "Somewhat worse": "Mbaya kiasi",
    "Much worse": "Mbaya zaidi",
    "Same or more": "Sawa au zaidi",
    "Partially lost": "Imepotea kwa kiasi",
    "Severely lost": "Imepotea sana",
}


def get_translation(
    translations: List[Dict[str, Any]] | None, lang: str, fallback: str
) -> str:
    """Find text for 'lang' in translations list, else return fallback."""
    if translations:
        for entry in translations:
            if entry.get("language") == lang:
                val = entry.get("name")
                if val:
                    return val
    # Fallback to local dict for Swahili if missing in DB list
    if lang == "sw" and fallback in SWAHILI_TRANSLATIONS:
        return SWAHILI_TRANSLATIONS[fallback]
    return fallback
