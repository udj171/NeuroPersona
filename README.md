# NeuroPersona

A Big Five personality assessment that assumes you are not a reliable narrator of
your own motives, and tries to measure the gap.

Fifty public-domain IPIP items score the five traits the ordinary way. Five more
ask how you are answering, and what they reveal is used to estimate how far your
answers were shaded in your favour. Both sets of scores are shown. A small
autoencoder, trained on just over a million public responses to the same fifty
items, places your profile among six patterns found in that data. The written
reading is generated on the same server, with no external model API involved.

The trait half is conventional and the correction is not. Keeping them separable,
and showing both numbers, is the point.

---

## The elephant in the brain

The project takes its conceptual foundation from **_The Elephant in the Brain: Hidden Motives in Everyday Life_** by Kevin Simler and Robin Hanson (Oxford University Press, 2018).

The title is a compound of two idioms. The "elephant in the room" is the important thing nobody will name. The "elephant in the brain" is the important thing nobody will name **to themselves**: that a great deal of ordinary human behaviour is driven by motives that are competitive, status-seeking, and self-interested, and that we systematically hide those motives from our own conscious awareness.

The book's argument runs in two moves.

The first move is that social life is a signalling game. Simler and Hanson lean on Amotz Zahavi's **handicap principle**, and on Zahavi's decades of fieldwork with the **Arabian babbler** in the Negev Desert. Babblers are small birds that appear to be model altruists. They feed one another, they groom one another, and they take turns as sentinel, standing exposed on a high branch where a hawk can see them, watching for the hawk. What Zahavi observed is that they do not merely do these things: they **compete** to do them. Dominant babblers force food on subordinates and shove rivals off the sentinel post. The altruism is a contest, because a costly, wasteful act is a credible advertisement. Only a genuinely strong bird can afford to burn energy and court death on someone else's behalf. The generosity is the signal, and the cost is what makes the signal honest.

The second move is what separates us from the babbler. Humans play the same game, in vastly more elaborate ways, but with an extra layer: we conceal our strategic motives from ourselves. The brain, in the book's metaphor, runs a **press secretary** — a module whose job is not to know why we did something but to produce a flattering, defensible account of why we did it. Self-deception is not a bug here. It is the mechanism that makes the deception of others work, because a motive you have never consciously registered is a motive you cannot accidentally leak through a hesitation or a glance.

The book's second half applies this to everyday institutions: body language, laughter, conversation, consumption, art, charity, education, medicine, religion, and politics. In each case the stated purpose and the functional purpose come apart, and the gap between them is where the interesting behaviour lives.

### How the book becomes code

NeuroPersona treats that gap as something to instrument.

| Idea from the book | How it appears in this repo |
| --- | --- |
| The press secretary produces a polished self-account | Five cross-check items (`V1`–`V5`) ask about admitting mistakes, real humility, cross-context consistency, opacity of one's own motives, and remembered selfishness |
| Self-deception leaks under cross-examination | The gap between the three claims and the two concessions is the largest single term in λ |
| The gap is measurable | **Lambda (λ)**, 0–1, from that claim gap, four named contradictions between traits and cross-checks, and response-style flags |
| Costly signals are honest signals | Per-trait desirability weights: agreeableness and conscientiousness are corrected hardest, because they are the ones worth inflating |
| The elephant runs in the direction that flatters | Neuroticism is corrected **upward**, since it is the trait people play down rather than talk up |

The landing page essay in `frontend/index.html` retells the babbler story as the project's thesis statement. Nothing in the code cites the book directly; the mapping above is the reading the implementation encodes.

Note what the book does **not** touch: the fifty trait items. Those are the standard
IPIP markers, chosen because they are what the training dataset used, and they carry
no costly-signal reasoning at all. The argument lives entirely in the five
cross-checks and the correction built on them.

The internal name **EFOPA** is retired. It survives only in the filename of
`EFOPA_ARCHITECTURE.md`, kept so existing links resolve.

---

## What the system actually does

```
demographics  ──▶  55 items  ──▶  scoring  ──▶  trained model  ──▶  interpretation
  age, sex         1-5 scale     λ + per-trait    6 learned         local, no API
                                 correction       patterns
```

1. **Start.** The browser posts age and sex to `POST /api/start-assessment` and receives an integer `assessment_id`.
2. **Answer.** `GET /api/questionnaire` serves the item bank; the respondent rates 55 statements from 1 to 5.
3. **Score.** `POST /api/submit-assessment` runs `ScoringEngine.process_assessment`:
   - reverse-key the 22 backward items, average each trait's ten, rescale to 0–100;
   - compute λ from the claim/concession gap in the cross-checks, four named contradictions, and response-style flags;
   - shift each trait by λ × its standout z-score × a per-trait desirability weight, capped at 18 points. Neuroticism moves up rather than down.
4. **Infer.** `ModelInferenceEngine` standardises the 50 raw responses, runs a numpy forward pass through the trained encoder, and picks the nearest of six k-means centroids. It also returns reconstruction error, novelty, and per-trait percentiles against the reference sample.
5. **Write up.** `NarrativeGenerator` composes the reading locally.
6. **Display.** `results.html` renders the type, both score sets, and the panels behind them.

### The five traits

| Key | Trait | Items | Reverse-keyed |
| --- | --- | --- | --- |
| `O` | Openness | `OPN1`–`OPN10` | 2, 4, 6 |
| `C` | Conscientiousness | `CSN1`–`CSN10` | 2, 4, 6, 8 |
| `E` | Extraversion | `EXT1`–`EXT10` | 2, 4, 6, 8, 10 |
| `A` | Agreeableness | `AGR1`–`AGR10` | 1, 3, 5, 7 |
| `N` | Neuroticism | `EST1`–`EST10` | 2, 4 |

The item codes are the training dataset's column names. Renaming them would
transpose the model's inputs, so the loader refuses a weight file whose stored
item order does not match.

### The training data

**Open-Source Psychometrics Project, "Big Five Personality Test"**: 1,015,342
responses to the same 50 items, 1–5 scale, public domain.
[Kaggle](https://www.kaggle.com/datasets/tunguz/big-five-personality-test) ·
[original archive](https://openpsychometrics.org/_rawdata/). See `training/README.md`.

### The six types

Not fixed letters. Six k-means clusters found in the training latents, each named
after whichever trait most separates it from the others. A retrain on different
data renames them rather than mislabelling them.

---

## Repository layout

```
backend/                        Flask API
  ocean_items.py                The 55-item bank. Single source of truth
  scoring_engine.py             Trait scores, lambda, the correction
  model_inference.py            numpy forward pass over the exported weights
  narrative.py                  Template and local-LLM interpretation backends
  api_routes.py                 The blueprint served at /api
  app.py                        App object, CORS, schema check, engine wiring
  models.py                     User, Assessment, Result, ModelOutput,
                                PersonalityClassification, Interpretation
  config.py                     Config classes by environment
  model_weights/                ocean_vae.npz goes here
  test_scoring.py               21 tests over the scoring layer
  test_model_contract.py        14 tests over the trainer/server boundary

training/
  train_vae_ocean.py            The trainer. Kaggle or local
  kaggle_train_ocean.ipynb      The notebook to upload to Kaggle
  README.md                     Dataset details and the run protocol

frontend/                       Static site (deployed to Vercel)
  index.html                    Landing page, carries the babbler essay
  architecture.html             Plain-language walkthrough with inline SVG diagrams
  features.html                 What the assessment gives you
  questionnaire.html/.js        Fetches the item bank, renders 55 items
  results.html/.js              Results rendering
  advanced-analysis.js          The deeper panels, all from server data
  config.js                     API base URL resolution
  app.js                        apiRequest with retry, toasts, validators
```

`EFOPA_ARCHITECTURE.md` is the current architecture document. The remaining
`EFOPA_*.md` files and `COMPATIBILITY_CHECKLIST.md`, `DEBUGGING_GUIDE.md`,
`FRONTEND_*.md` and `README_EFOPA_INTEGRATION.md` describe the retired
six-domain system and are kept only as history.

## Running it locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env .env.local   # then edit; see Configuration below
python app.py        # serves on http://localhost:5000
```

Startup logs whether the trained weights loaded. Without them the app still runs
and still scores every profile; it simply does not claim a type.

`app.py` exposes a module-level `app`, so production runs as:

```bash
gunicorn app:app
```

On startup the app verifies the database connection, inspects the `users.id` column, and **drops and recreates every table** if it finds an old integer or GUID primary key. That is intentional migration behaviour for this project, and it is destructive.

### Frontend

```bash
cd frontend
npm run dev          # python -m http.server 3000
```

Then point it at your local API from the browser console:

```js
window.setAPIURL('http://localhost:5000')   // persists in localStorage
window.resetAPIURL()                        // back to the default
window.checkAPIHealth()                     // pings /api/health
```

Without an override, `config.js` uses `http://localhost:5000` on localhost and the
hardcoded production URL everywhere else. That URL still points at the old Render
deployment; see `EFOPA_ARCHITECTURE.md` section 7 for where to move it.

### Tests

```bash
cd backend
pytest                       # 35 tests, no flags needed
```

`test_scoring.py` covers the item bank, trait scoring, lambda and the correction.
`test_model_contract.py` pins the boundary between the Kaggle trainer and the numpy
server: that the trainer's embedded item bank still matches `ocean_items.py`, that
its trait scoring agrees with the backend's, and that the exported matrices
reproduce a PyTorch `nn.Linear` forward pass exactly. It needs no PyTorch to do it.

---

## Configuration

Backend environment variables, read via `python-dotenv`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///assessment.db` |
| `SECRET_KEY` | Flask secret | a development placeholder |
| `MODEL_WEIGHTS_PATH` | Trained weight file | `backend/model_weights/ocean_vae.npz` |
| `NARRATIVE_BACKEND` | `template` or `llm` | `template` |
| `LLM_MODEL_PATH` | GGUF file, when `NARRATIVE_BACKEND=llm` | unset |
| `LLM_THREADS` | Threads for the local model | `2` |
| `PORT` | Listen port | `5000` |
| `FLASK_ENV` | `development` turns on debug | unset |

Frontend: `vercel.json` sets `NEXT_PUBLIC_API_URL`, which has no effect. This is a
plain static site with no bundler, so `process.env` is undefined in the browser and
`config.js` falls through to its hardcoded defaults. Change the production API URL
in `config.js`.

## Written interpretations

No third-party API. Two local backends, selected with `NARRATIVE_BACKEND`:

- **`template`** (default) — a deterministic generator. No model, no network, no
  key, no rate limit, no per-request cost. Bands each trait, picks the two
  furthest from the profile's own mean, and composes the reading. Phrasing varies
  by a hash of the profile, so the same answers always give the same page.
- **`llm`** (opt-in) — a local open-weights GGUF instruct model through
  `llama-cpp-python`, such as Qwen2.5-0.5B-Instruct or SmolLM2-360M-Instruct, both
  Apache-2.0. Nothing leaves the host. Any failure falls back to `template`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness, no database access |
| `GET` | `/api/questionnaire` | The item bank, scale and trait metadata |
| `POST` | `/api/start-assessment` | Create user and assessment, return `assessment_id` |
| `POST` | `/api/submit-assessment` | Validate, score, infer, write up, persist |
| `GET` | `/api/results/<int:id>` | Full result payload |
| `GET` | `/api/assessments` | Paginated list |
| `GET` | `/api/users/<user_id>/assessments` | Per-user history |
| `GET` | `/api/stats` | Counts, type distribution, mean lambda |

Submission requires all 55 item ids exactly once, each an integer from 1 to 5.

## Deployment

- **Backend**: any host that runs Python. The runtime needs Flask, SQLAlchemy and
  numpy, roughly 120 MB installed; PyTorch is a training-only dependency.
  `EFOPA_ARCHITECTURE.md` section 7 compares the free options. Oracle Cloud Always
  Free is the recommendation. Hugging Face Spaces is no longer free for Docker.
- **Frontend**: Vercel, static, no build step.
- CORS is open to all origins on `/api/*`.

## Known issues

1. **Results are enumerable.** `/api/results/<int:id>` takes a sequential integer,
   so the range can be walked to read other people's results. The `assessments`
   table already has a UUID `external_id` that would fix this. Most serious open
   issue in the system.
2. **Startup can drop the database.** `check_and_migrate_schema` in `app.py` calls
   `db.drop_all()` when it finds an unexpected `users.id` type, including in its
   exception-recovery path.
3. **Without trained weights, no type is claimed.** The app still scores, corrects
   and writes up every profile, but `weights_loaded` is `false`, confidence is
   `null` rather than invented, and percentiles and novelty are omitted. See
   `training/` to produce the weights.
4. **The correction is unvalidated.** Its weights and thresholds are reasoned, not
   fitted, and have not been checked against any external criterion.
5. **`backend/.env` is committed** despite being listed in `.gitignore`. The Gemini
   key has been removed from the file but remains in git history; it and the Flask
   secret and SMTP credentials should be treated as exposed and rotated.
6. **CORS is open to all origins** with `supports_credentials=True`.
7. **`NEXT_PUBLIC_API_URL` does nothing.** See Configuration above.
8. **No CI.** The test suite has to be run by hand.

## Status

Working prototype. The trait half rests on a long-established public instrument and
a model trained on over a million public responses. The correction on top of it is
this project's argument, not a finding.

This is not a validated psychological test and not a clinical instrument. Do not
use its output to make decisions about hiring, admission, care, or anyone's life.

---

## Reading

Kevin Simler and Robin Hanson, _The Elephant in the Brain: Hidden Motives in Everyday Life_, Oxford University Press, 2018.

Amotz Zahavi and Avishag Zahavi, _The Handicap Principle: A Missing Piece of Darwin's Puzzle_, Oxford University Press, 1997.

Lewis R. Goldberg, "The development of markers for the Big-Five factor structure", _Psychological Assessment_ 4(1), 1992, and the International Personality Item Pool at <https://ipip.ori.org>.
