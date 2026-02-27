"""
Gemini API Client
==================
Shared client for calling Gemini LLM with structured JSON output.
Handles API calls, retries, and response parsing.
"""

import json
import re
import time
import urllib.request
import urllib.error
from typing import Optional


GEMINI_API_KEY = "###Gemini-key"
GEMINI_MODEL = "gemini-3.1-pro-preview"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

MAX_RETRIES = 4
RETRY_DELAY = 2  # seconds base delay (exponential backoff)
DEFAULT_RATE_LIMIT_DELAY = 1.5  # seconds between calls


class GeminiClient:
    """Client for Gemini API with structured JSON output and rate limiting."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        self.api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        self.rate_limit_delay = rate_limit_delay
        self._last_call_time = 0.0

    def call(self, prompt: str, temperature: float = 0.2) -> Optional[dict]:
        """Send a prompt to Gemini and parse the JSON response.

        Args:
            prompt: The full prompt string (including instructions for JSON output).
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            Parsed JSON dict from the LLM response, or None on failure.
        """
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }

        # Rate limiting: wait between calls
        elapsed = time.time() - self._last_call_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

        for attempt in range(MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    self.api_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    response_data = json.loads(resp.read().decode("utf-8"))

                # Extract text from Gemini response structure
                text = (
                    response_data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )

                self._last_call_time = time.time()
                return self._parse_json(text)

            except urllib.error.HTTPError as e:
                error_body = ""
                try:
                    error_body = e.read().decode()[:300]
                except Exception:
                    pass

                if e.code == 429:
                    # Rate limited — wait and retry
                    if attempt == 0:
                        print(f"[GeminiClient] Rate limited (429). Retrying...")
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                elif e.code >= 500:
                    # Server error — retry
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    print(f"[GeminiClient] HTTP error {e.code}: {e.reason}")
                    if error_body:
                        print(f"[GeminiClient] Details: {error_body}")
                    return None

            except (urllib.error.URLError, TimeoutError) as e:
                print(f"[GeminiClient] Network error (attempt {attempt + 1}): {e}")
                time.sleep(RETRY_DELAY)
                continue

            except Exception as e:
                print(f"[GeminiClient] Unexpected error: {e}")
                return None

        print("[GeminiClient] All retries exhausted.")
        return None

    def _parse_json(self, text: str) -> Optional[dict]:
        """Parse JSON from LLM response, handling markdown code fences."""
        text = text.strip()

        # Remove markdown code fences if present
        if text.startswith("```"):
            # Remove opening fence (```json or ```)
            text = re.sub(r'^```(?:json)?\s*\n?', '', text)
            # Remove closing fence
            text = re.sub(r'\n?```\s*$', '', text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from the text
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            print(f"[GeminiClient] Failed to parse JSON from response: {text[:200]}...")
            return None
