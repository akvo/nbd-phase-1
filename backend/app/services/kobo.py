import os
from typing import List, Dict, Any
import httpx


class KoboService:
    def __init__(self):
        self.api_url = os.getenv(
            "KOBOTOOLBOX_API_URL", "https://eu.kobotoolbox.org"
        ).rstrip("/")
        self.api_token = os.getenv("KOBOTOOLBOX_API_TOKEN")
        self.headers = {}
        if self.api_token:
            self.headers["Authorization"] = f"Token {self.api_token}"

    def get_forms(self) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/api/v2/assets.json"
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])

    def get_submissions(self, form_id: str) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/api/v2/assets/{form_id}/data.json"
        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
