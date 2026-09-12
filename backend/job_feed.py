"""A current, attributed feed when JSON Resume matching is unavailable.

This fallback uses lexical similarity, not semantic matching or suitability scores.
"""
import json
import threading
import time
from html.parser import HTMLParser

import httpx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

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
        if not _cache or time.monotonic() - _fetched > 900:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                response = client.get("https://www.arbeitnow.com/api/job-board-api")
                response.raise_for_status()
                records = response.json()["data"]
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
            _cache, _fetched = jobs, time.monotonic()
        rows = list(_cache)
    documents = [json.dumps(resume)] + [f'{j["title"]} {j["description"]} {j["skills"]}' for j in rows]
    matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=20000).fit_transform(documents)
    scores = (matrix[1:] @ matrix[0].T).toarray().ravel()
    return [dict(rows[i], similarity=float(scores[i])) for i in np.argsort(-scores)[:20]]
