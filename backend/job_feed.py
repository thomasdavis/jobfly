"""Hourly cached, paginated real listings. No pre-ranking or synthetic fill."""
import threading
import time
from html.parser import HTMLParser

import httpx

_cache = []
_fetched = 0
_lock = threading.Lock()


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def match_public_jobs(resume):
    global _cache, _fetched
    with _lock:
        if not _cache or time.monotonic() - _fetched > 3600:
            records = []
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                for page in range(1, 13):
                    try:
                        response = client.get("https://www.arbeitnow.com/api/job-board-api", params={"page": page})
                        response.raise_for_status()
                        payload = response.json()
                        records.extend(payload["data"])
                        if not payload.get("links", {}).get("next"):
                            break
                    except (httpx.HTTPError, ValueError, KeyError):
                        if not records:
                            raise
                        break
            jobs = []
            for row in records:
                if not row.get("title") or not row.get("company_name") or not str(row.get("url", "")).startswith("https://"):
                    continue
                parser = PlainText()
                parser.feed(row.get("description", ""))
                jobs.append(dict(id="arbeitnow-" + row["slug"], title=row["title"],
                                 company=row["company_name"], description=" ".join(parser.parts)[:12000],
                                 location=row.get("location"), url=row["url"], source="arbeitnow",
                                 postedAt=row.get("created_at"), remote=row.get("remote"),
                                 skills=row.get("tags", [])))
            if not jobs:
                raise ValueError("No jobs are available right now. Please try again later.")
            _cache, _fetched = list({j["url"]: j for j in jobs}.values()), time.monotonic()
        rows = list(_cache)
    return rows
