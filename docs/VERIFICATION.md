# Resume-first verification — 2026-09-12

The light interface was checked against the actual CPU brain and real job feed.

- Thomas Davis’s published resume loads into an editable JSON review screen.
- A new search creates a unique 192-bit session URL and 20 real, source-linked jobs.
- Local full-flow test: a like changed **7,322 existing KC → MBON edges**.
- A fresh browser opening the same URL restores the resume, feedback, and learned preference.
- After restarting the deployed service, the same URL restored one rating, its liked
  job, the learned weights, and Thomas’s resume. The check waits for HTTP readiness.
- PDF upload was exercised through the public site: extraction, schema-validated
  AI conversion, editable review, download as `resume.json`, and a lossless JSON re-upload.
- Word extraction, including tables, is covered by an automated test.
- Desktop 1440 px and mobile 390 px have no horizontal overflow or browser page errors.
- The home page starts no simulation and loads no Three.js bundle.
- Fifteen tests pass, including access controls, URL uniqueness, input validation,
  zero-price conversion failover, and the existing neural learning/persistence tests.
- Production uses the original mounted connectome, isolated SQLite sessions, and
  a read-only application container. Neither model assets nor personal session data
  are included in the repository.

JSON Resume’s matching endpoint returned HTTP 500 (`fetch failed`) during this
run. The application used current Arbeitnow postings, visibly attributed as a
lexical fallback. Its existing document converter also rejected its generated
schema; Jobfly uses its own Pydantic tool schema through OpenRouter instead.
Free provider calls are limited to zero-priced endpoints, bounded to 45 seconds
per attempt, and retried once. Failed conversion returns a recoverable error.

Artifacts and private session tokens are stored on the mounted research drive,
not in this repository. `verify-light.mjs`, `verify-upload.mjs`, and
`verify-persistence.mjs` reproduce the current flows. The historical results below
refer to the previous example-based version, which is no longer served.

---

# Initial verification — 2026-09-12

The initial public browser test ran against `https://fly.jsonresume.org` with
the real MaleCNS CPU simulation and a separate test-only browser identity.

- Autonomous landing: `example-11`, after 3.9 simulated seconds.
- Browser-submitted rejection changed **7,411 existing KC → MBON edges**.
- The rejected job's learned attraction value moved from 0 to **-0.22**.
- Pause stopped simulated time advancing.
- Imported a synthetic saved-job JSON file through the actual file picker.
- Rejected malformed import without replacing the existing habitat.
- Feedback survived a browser reload.
- After replacing and restarting the production container, the original signed
  browser session restored its one lesson, passed mark and **-0.22** preference.
- A second browser identity saw zero lessons and no marks. Cross-site mutation
  was rejected with HTTP 403. Production cookies had HttpOnly, Secure and
  SameSite=Strict flags.
- Desktop 1440 px and mobile 390 px rendered without horizontal page overflow.
- Browser page-error list was empty.

Nine unit tests verify selective plasticity, weight bounds and signs, no reward
for zero activity, stable sensory encoding across corpora, persistence, input
identity validation, signed sessions, isolation and capacity limits.

These results verify the implementation path. They do not establish improved
job recommendation quality, biological validity, or held-out generalization.
The optional paid LLM path and live personal-resume matching were not invoked;
no personal resume was used in testing.

The exact screenshot/test artifacts and the private browser verification cookie
are retained outside the repository on the operator's data drive. Cookie files
and per-visitor data must never be committed.
