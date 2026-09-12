# Continuous swarm verification — 2026-09-12

Runtime commit: `ab24447bd54294cbaeb6e64771193564381947f0`.

- All 23 automated tests pass; GitHub Actions run 34711953903 passed.
- The packaged Python sources match the committed source hashes.
- Full-model experiments use 166,700 neurons and 25,582,938 signed connections.
  All 24 flies moved, six landings occurred, and the first unrated suggestion
  appeared after 240 simulated seconds. See [neural evidence](neural-evidence.json).
- Wiring/smell interventions remove measured job responses. Vision/motor
  interventions remove decoded movement. Six held-out visual angles produced
  the correct turn direction.
- The packaged candidate browser test rendered all 1,462 real, unique job URLs,
  with 24 flies, 23 habitat draw calls, 200 detailed nearby job models, and no
  browser page errors. Desktop and mobile flows passed. Liking a job changed
  52,871 existing learning-circuit edges; the swarm continued without changing
  the selected job.
- Negative feedback was independently exercised: 58,576 changed edges and a
  negative learned prediction, with exploration continuing.

## Public deployment

The browser flow passed against https://fly.jsonresume.org:

- 1,462 real jobs rendered, 24 flies moved, and 70 jobs explored before feedback.
- First autonomous suggestion: 213 simulated seconds, 78 jobs observed, nine
  landings, and **zero ratings**.
- Optional feedback changed 52,871 existing edges. Exploration continued and
  the selected job stayed selected.
- 23 habitat draw calls, 91,744 triangles, and 200 detailed nearby jobs in the
  tested view. All 1,462 job positions were rendered.
- A production service restart preserved the session URL, Thomas Davis resume,
  liked job, one rating, the learned activity sample, all 1,462 jobs, and 24 flies.
  Invalid session links returned 404.
- Mobile layout, neural intervention controls, opening the session in another
  browser, and resume restoration passed. No browser page errors occurred.


These establish working integration and causal circuit participation, not
recommendation accuracy or biological fidelity. The swarm time-shares one full
network per session. CPU software rendering was checked, not hardware-GPU frame
rate. Real job counts and source availability vary.

---

# Historical resume-first verification — 2026-09-12

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
`verify-persistence.mjs` reproduce the earlier flows. The historical results below
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
