"""LastFM API client for fetching user's recently played tracks."""

import json
import base64
import requests
from typing import Dict, Optional, Any

from gitscrobble_config import config
from utils.logging_config import logger


class LastFmClient:
    """Client for interacting with LastFM API."""

    def __init__(self, username: str = config.default_user) -> None:
        """
        Initialize LastFM client for a specific user.

        Args:
            username: LastFM username to fetch data for
        """
        self.username = username
        self.api_key = config.lastfm.api_key
        self.base_url = config.lastfm.base_url

    def _build_url(self, method: str, extended: bool = False) -> str:
        """
        Build a LastFM API URL.

        Args:
            method: LastFM API method name
            extended: Whether to request extended track info

        Returns:
            Fully qualified URL for the API request
        """
        params = {
            "method": method,
            "user": self.username,
            "api_key": self.api_key,
            "format": "json",
            "limit": 1,
        }

        if extended:
            params["extended"] = 1

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.base_url}?{query_string}"

    @staticmethod
    def get_base64_image(url: str) -> Optional[str]:
        """
        Convert an image URL to base64 encoding.

        Args:
            url: URL of the image to convert

        Returns:
            Base64-encoded image string or None if failed
        """
        try:
            if not url:
                with open("./static/temp.gif", "rb") as image_file:
                    image_data = image_file.read()
                    return base64.b64encode(image_data).decode("utf-8")

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            return base64.b64encode(response.content).decode("utf-8")
        except Exception as e:
            logger.error(f"Error fetching image: {e}")
            return None

    def get_current_track(self) -> Optional[Dict[str, Any]]:
        """Fetch user's current or last played track from LastFM."""
        try:
            url = self._build_url("user.getRecentTracks", extended=True)
            logger.info(f"Fetching from URL: {url}")

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Debug: print the full API response so we see its structure
            print("=== DEBUG: LastFM API Response ===")
            print(json.dumps(data, indent=2))

            tracks = data.get("recenttracks", {}).get("track", [])
            if not tracks:
                logger.error("No tracks found in API response")
                return None

            track = tracks[0]

            # Artist extraction for extended and non-extended modes
            artist_info = track.get("artist")
            if isinstance(artist_info, dict):
                artist = artist_info.get("name") or artist_info.get("#text", "")
            else:
                artist = str(artist_info) if artist_info else ""

            name = track.get("name", "")
            is_playing = "@attr" in track and track["@attr"].get("nowplaying") == "true"
            track_url = track.get("url", "")

            image_url = ""
            if track.get("image") and isinstance(track["image"], list):
                # Find the largest image with "#text"
                for img in reversed(track["image"]):
                    if img.get("#text"):
                        image_url = img["#text"]
                        break

            thumbnail = self.get_base64_image(image_url)

            return {
                "song": name,
                "artist": artist,
                "thumbnail": thumbnail,
                "url": track_url,
                "is_playing": is_playing,
            }

        except Exception as e:
            logger.error(f"Error fetching song details: {e}")
            return None
