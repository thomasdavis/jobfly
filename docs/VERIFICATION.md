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
