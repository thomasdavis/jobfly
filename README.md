# Jobfly

**Real jobs. Your resume. A fly brain that learns what you like.**

[Start a session →](https://fly.jsonresume.org)

![Jobfly's Three.js habitat and live neural HUD](docs/habitat.png)

A fruit fly wanders through a miniature world of job-poop. When it lands,
you decide whether the opportunity is worth your time. Your feedback changes
connections in its simulated brain, influencing what it explores next.

The habitat and neural HUD are built with **Three.js**. The simulation uses all
**166,700 neurons and 25,582,938 connections** in fly.ai's MaleCNS model.

## What you can do

- Upload PDF, DOCX, TXT, or JSON Resume, paste JSON, or use Thomas Davis’s published resume.
- Review and edit the resulting `resume.json`, then download it or start searching.
- Get a unique `/s/<random-token>` URL that restores your resume, jobs, and learning in another browser.
- Explore real job listings in Three.js; open the source posting and inspect the brain HUD.
- Like or pass after landing. The feedback changes existing learning-circuit connections.
- Keep notes and export liked jobs. No applications are submitted and no employers are contacted.

There are no bundled example jobs and no arbitrary job-import endpoint.

## Run locally

Requires Node.js 22+, Python 3.12, and about 2 GB free for dependencies and model
data. A multi-core CPU helps; simulation time is shown separately from wall time.

```sh
npm ci
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r backend/requirements.lock

# Set these to a suitable persistent data disk on your machine.
export FLY_DATA=/path/to/data/jobfly/brain
export JOBFLY_STATE=/path/to/data/jobfly/state
export NUMBA_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=1

npm run brain:setup  # downloads MaleCNS v1.0 and builds the sparse model
npm run build
npm run server      # http://127.0.0.1:8787
```

For frontend development, run `npm run dev` alongside the server. Vite uses
port 5187 and proxies `/api` to 8787. Opening a session loads the connectome and
compiles the simulation kernel; subsequent steps use the compiled kernel.
The UI remains available while the brain wakes up. An idle/disconnected
browser does not advance the simulation.

### Real jobs and session links

The first screen requires a resume. JSON Resume’s `/api/v1/jobs` is the primary
matching source. If it fails or returns no usable postings, Jobfly fetches current
[Arbeitnow listings](https://www.arbeitnow.com/blog/job-board-api), ranks them by
resume text similarity, and visibly identifies that fallback. The feed is mostly
European jobs; lexical ranking does not establish eligibility or suitability.
Every displayed job links back to its source. Availability can change after import.

Session links contain 192-bit random tokens. **Anyone with a link can read the
resume and update that session.** Keep links private; there is no account login.
Each session has its own append-only SQLite checkpoints under `JOBFLY_STATE`.
Responses are not cached, session pages are marked noindex, referrers are suppressed,
and application access logging is disabled. Server restarts preserve session URLs.
The home page does not allocate a brain or load Three.js.

### Document conversion

PDF text is extracted using pypdf; DOCX uses python-docx, including table text.
Scanned PDFs without text are rejected with an explanation. Files are limited to
5 MB, PDFs to 30 pages, and extracted text to 60,000 characters. Original documents
are processed in memory and not retained. JSON files bypass the model unchanged.

Set `OPENROUTER_API_KEY` or `JOBFLY_CONVERSION_KEY_FILE` for document conversion.
The OpenAI SDK submits a required Pydantic-validated tool call through OpenRouter,
using `openrouter/free` by default. Provider price limits are
pinned to zero, including when `JOBFLY_CONVERSION_MODEL` overrides the model.
Free-provider capacity varies; errors preserve the local review state and invite retry.
Two conversions can run at once; public conversion/session creation is rate limited.
The upload screen discloses the provider. Users review extracted facts before saving.

### Optional language model

Set `OPENAI_API_KEY` on the server and optionally `JOBFLY_LLM_MODEL` (default
`gpt-4.1-mini`). The Saved jobs page then offers **Compare jobs**.
This explicit action sends jobs, the imported resume and written feedback to
the configured model and can incur API charges. Nothing calls an LLM per tick.
The public deployment leaves this disabled unless deliberately configured.

Responses use the official OpenAI SDK's schema-validated Pydantic output.
No free-text JSON scraping or hardcoded keyword classification is used.
Written reasons are saved immediately but only influence sensory encoding
when the interpreter is explicitly run. Likes/dislikes train immediately.

## How the brain participates

```mermaid
flowchart LR
  J[Job text and optional LLM comparison] --> E[Stable lexical sensory encoder]
  E --> K[Kenyon-cell stimulation]
  K --> B[Full recurrent MaleCNS simulation]
  T[Directional target stimulus] --> B
  B --> D[DNa02 motor activity]
  D --> M[Fly movement and landing]
  M --> H[Your like or dislike]
  H --> P[Reward-modulated KC to MBON edges]
  P --> B
  P --> A[Learned attraction adapter]
  A --> T
```

- **Neurons:** upstream leaky integrate-and-fire dynamics, original sparse
  connectome, full population, 20 ms simulated steps. CPU execution is the
  supported learning backend; swapping to CUDA requires synchronizing plastic
  weight updates with the GPU matrix first.
- **Sensory interface:** character n-grams are hashed into a fixed lexical
  space and projected into sparse Kenyon-cell ensembles. This mapping remains
  stable across job imports. It is an artificial input channel, not a biological
  model of smell. An optional LLM can supply richer grounded comparison text.
- **Movement:** lateral LC10a stimulation flows through the model to DNa02
  steering neurons. A simple kinematic body converts the left/right activity
  difference into turning. Forward locomotion is a constant body-controller
  component, and the world wraps at its boundaries.
- **Learning:** recent firing in the presented Kenyon-cell ensemble determines
  eligibility. A reward strengthens or weakens existing KC → MBON connections,
  bounded to 0.25–2 times their original magnitude. Signs and topology remain
  intact. No new anatomical connections are invented.
- **Attraction:** an explicit adapter reads modified circuit strengths to bias
  stochastic target selection. Target selection is not solely an emergent
  biological decision. The full recurrent simulation controls steering.
- **Visualization:** Three.js renders all 140,638 neurons with measured positions.
  Activity packets sample at most 3,500 mapped spikes; the HUD reports the total
  spike count separately. Unmapped neurons still participate in simulation.

This is an engineered, connectome-based experiment. It is **not a validated
dopamine-learning model**, not an emulation of a complete living animal, and
not evidence that fly wiring improves job matching. Broader recommendation
quality and generalization need a held-out evaluation against simpler models.

## Verification

```sh
npm run build
npm test
CHROME_PATH=/path/to/chrome node scripts/verify-light.mjs
```

Unit tests cover reward specificity, bounds/sign preservation, stable sensory
identity, checkpoints, resume validation, lossless JSON upload, Word table extraction,
unique URLs, access boundaries, and an empty brain input before setup.
The browser verifier uses Thomas Davis’s public resume, real jobs, and the actual
brain, checking landing, feedback, changed weights, reopening in another browser,
and desktop/mobile layouts. Private test links stay outside the repository.

## Deployment

The repository includes a multi-stage `Dockerfile`, a Podman Quadlet, and a
Caddy site in `deploy/`. Build `localhost/jobfly:latest`, mount model data
read-only at `/brain` and persistent session storage at `/state`, then install
the Quadlet. The provided origin binds to `127.0.0.1:8788`; Caddy serves
`fly.jsonresume.org` with automatic TLS and unbuffered SSE.

Three resident brains maximum; disconnected sessions can be evicted and reload
their saved learning. The Quadlet limits the service to 3 GB RAM and two CPU
cores worth of time. This is a small experimental deployment, not a horizontally
scaled service. `/healthz` checks model-file presence; a moving simulation must
be verified through an actual session, not inferred from that health check.

## Credits

Built on [alextitonis/fly.ai](https://github.com/alextitonis/fly.ai), pinned to
`f05a7eae64e4cf4459396743052d368f0e2a3e51`, and
[JSON Resume](https://jsonresume.org). See [THIRD_PARTY.md](THIRD_PARTY.md) for
MaleCNS/FlyEM attribution, separate CC BY 4.0 data terms and upstream credits.

Code: MIT. Connectome data is downloaded separately and never committed.
