# NeuroPersona

A personality assessment that assumes you are not a reliable narrator of your own motives, and tries to measure the gap.

NeuroPersona is a 35-item questionnaire with a Flask API behind it. It scores six personality domains, estimates how much the respondent's self-report is distorted by self-flattery, subtracts that distortion, and runs the corrected profile through a latent-variable model to assign one of six personality types. A Gemini call turns the numbers into prose.

The whole design rests on one idea borrowed from a book.

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
| The press secretary produces a polished self-account | The 30 core items ask about behaviour under conditions where nobody is watching, where credit is anonymous, where the flattering answer and the true answer diverge |
| Self-deception leaks under cross-examination | Five validity items (`V31`–`V35`) ask directly about admitting mistakes, real humility, cross-context consistency, opacity of one's own motives, and remembered selfishness |
| The gap between the account and the behaviour is measurable | **Lambda (λ)**, a 0–1 deception-susceptibility score derived from contradictions between domain scores and validity items |
| Costly signals are honest signals | **Domain cost functions**: each domain carries an `honesty_barrier` weight, so honesty about mating and status is priced higher than honesty about openness |
| The elephant is the part of cognition you cannot introspect | The **Elephant Module**, which weights each domain's credibility by inferred implicit bias rather than by the stated score |
| A self-account can be coherent and still be a performance | **Authenticity index** = `(1 − λ) × coherence` |

The landing page essay in `frontend/index.html` retells the babbler story as the project's thesis statement. Nothing in the code cites the book directly; the mapping above is the reading the implementation encodes.

The internal name for this layer is **EFOPA** — Enhanced Framework for Personality Observation and Assessment. It appears throughout the older design documents and in backend module names. The user-facing UI deliberately avoids the term and says "advanced analysis" instead.

---

## What the system actually does

```
demographics  ──▶  35 questions  ──▶  scoring  ──▶  latent model  ──▶  interpretation
  age, sex          0–10 scale       λ + bias        6 types          Gemini prose
                                     correction
```

1. **Start.** The browser posts age and sex to `POST /api/start-assessment` and receives an integer `assessment_id`.
2. **Answer.** The respondent rates 35 statements on a 0–10 scale: 30 core items across six domains, plus five validity items.
3. **Score.** `POST /api/submit-assessment` runs `ScoringEngine.process_assessment`:
   - mean each domain's five items into a raw score (`R`, `S`, `C`, `A`, `O`, `E`);
   - compute λ from the divergence between validity-item responses and domain responses;
   - compute a per-domain bias from λ, the domain's z-score, and validity-item variability;
   - subtract bias from raw to get corrected scores, clamped to 0–10;
   - assemble a 9-dimensional vector (six corrected scores, λ, response standard deviation, an age term).
4. **Classify.** `VAEInferenceEngine` encodes that vector into a 16-dimensional latent space, measures reconstruction error, distance from the latent mean, and local density, derives a novelty score, and assigns the nearest of six reference types (`A`–`F`).
5. **Interpret.** `GeminiClient` receives type, confidence, λ, corrected scores, and novelty, and returns a written interpretation. It falls back to templated text when no API key is present.
6. **Display.** `results.html` fetches `GET /api/results/<id>` and renders the type, confidence, interpretation, and domain bars. `advanced-analysis.js` then derives the bias, implicit-cognition, quality, and authenticity panels client-side from the same payload.

### The six domains

| Key | Domain | Items | What the items probe |
| --- | --- | --- | --- |
| `R` | Relationships | R1–R5 | Mating effort, honesty in courtship, attention to alternatives |
| `S` | Status | S6–S10 | Self-assessment accuracy, audience-dependent self-promotion |
| `C` | Reliability / Conscientiousness | C11–C15 | Effort when unobserved, credit-blind productivity |
| `A` | Agreeableness | A16–A20 | Public versus private helping, free-riding, private guilt |
| `O` | Openness | O21–O25 | Admitting ignorance, motivated reasoning, credit attribution |
| `E` | Emotional stability | E26–E30 | Composure as performance, accuracy of self-prediction |

Every core item is written so that the socially attractive answer and the accurate answer can come apart. That is the point.

### The six types

`A` Analytical Leader, `B` Dynamic Innovator, `C` Balanced Pragmatist, `D` Empathetic Connector, `E` Visionary Dreamer, `F` Grounded Realist.

Note that the frontend labels these differently: The Analytical, The Builder, The Connector, The Driver, The Explorer, The Facilitator. See "Known gaps" below.

---

## Repository layout

```
backend/                        Flask API (deployed to Render)
  app.py                        App object, CORS, schema check, engine wiring
  api_routes.py                 The blueprint that is actually served, at /api
  scoring_engine.py             Raw scores, lambda, biases, corrected scores, VAE input
  vae_inference.py              Latent encoding, novelty, type assignment
  personality_classifier.py     Standalone rule-based classifier (not in the live path)
  gemini_client.py              Interpretation generation with fallback
  models.py                     User, Assessment, Result, VAEOutput, Classification, Interpretation
  config.py                     Config classes by environment
  test_scoring.py               Unit tests for ScoringEngine

  efopa_enhancement_module.py   The full EFOPA engine: lambda, costs, elephant, validity, authenticity
  scoring_integration.py        Layer combining ScoringEngine with the EFOPA engine
  models_efopa_extension.py     Six EFOPA tables
  api_routes_efopa.py           Eight /api/efopa/* endpoints
  efopa_data_persistence.py     Save and load helpers for EFOPA tables
  efopa_config.py               Thresholds, weights, feature flags

frontend/                       Static site (deployed to Vercel)
  index.html                    Landing page, carries the babbler essay
  questionnaire.html/.js        Demographics form and the 35 items
  results.html/.js              Results rendering
  advanced-analysis.js          Derives the advanced panels client-side
  efopa-integration.js          Earlier client for /api/efopa/*, no longer loaded
  config.js                     API base URL resolution
  app.js                        apiRequest with retry, toasts, validators
```

The five `EFOPA_*.md` files plus `COMPATIBILITY_CHECKLIST.md`, `DEBUGGING_GUIDE.md`, `FRONTEND_*.md`, and `README_EFOPA_INTEGRATION.md` are design and integration notes written during the EFOPA build. They describe the intended system. Where they disagree with the code, the code is authoritative — see "Known gaps".

---

## Running it locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env .env.local   # then edit; see Configuration below
python app.py        # serves on http://localhost:5000
```

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

Without an override, `config.js` uses `http://localhost:5000` on localhost and `https://neuropersona.onrender.com` everywhere else.

### Tests

```bash
cd backend
pytest test_scoring.py --noconftest
```

`--noconftest` is currently required. `conftest.py` imports a `create_app` factory that `app.py` does not define, so collection fails without it. The tests in `test_scoring.py` do not use those fixtures.

---

## Configuration

Backend environment variables, read via `python-dotenv`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///assessment.db` |
| `SECRET_KEY` | Flask secret | a development placeholder |
| `GEMINI_API_KEY` | Enables real interpretations | unset, falls back to templates |
| `VAE_MODEL_PATH` | Pickled VAE model | unset, falls back to a mock model |
| `VAE_SCALER_PATH` | Pickled scaler | unset, fits a default scaler |
| `PORT` | Listen port | `5000` |
| `FLASK_ENV` | `development` turns on debug | unset |
| `CORS_ORIGINS` | Present in `.env`, not currently read by `app.py` | — |

Frontend: `vercel.json` sets `NEXT_PUBLIC_API_URL`. Since this is a plain static site with no bundler, `process.env` is undefined in the browser and `config.js` falls through to its hardcoded defaults. Changing the production API URL means editing `config.js`.

---

## API

Served today, under `/api`:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness, no database access |
| `POST` | `/start-assessment` | Create user and assessment, return `assessment_id` |
| `POST` | `/submit-assessment` | Score, classify, interpret, persist |
| `GET` | `/results/<int:id>` | Full result payload |
| `GET` | `/assessments` | Paginated list |
| `GET` | `/users/<user_id>/assessments` | Per-user history |
| `GET` | `/stats` | Aggregate counts |

Defined in `api_routes_efopa.py` but **not currently reachable**, because `app.py` never registers the `efopa` blueprint: `/api/efopa/lambda-analysis/<id>`, `/domain-costs/<id>`, `/elephant-module/<id>`, `/validity-metrics/<id>`, `/authenticity-metrics/<id>`, `/assessment-metadata/<id>`, `/complete-analysis/<id>`, `/health`.

`EFOPA_ARCHITECTURE.md` documents those endpoints as live. They are not. The frontend was changed to compute the equivalent panels in the browser instead.

---

## Deployment

- **Backend** on Render, Python 3.11.7 (`runtime.txt`), started with gunicorn against `app:app`. Non-API routes return a 404 JSON body pointing at the frontend.
- **Frontend** on Vercel as a static site with `cleanUrls`, no build step.
- CORS is open to all origins on `/api/*`.

---

## Known gaps

These are real divergences between the documentation, the design, and the running code. They are listed here so nobody rediscovers them the hard way.

1. **The EFOPA blueprint is not registered.** `efopa_bp` exists with eight endpoints; `app.py` only registers `api_bp`. Every `/api/efopa/*` route 404s.
2. **The EFOPA tables are never created.** `models_efopa_extension.py` defines six tables, but nothing imports it into the app, so `db.create_all()` never sees them.
3. **`EFOPAEnhancementEngine` is not in the request path.** The live scoring uses the simpler λ in `scoring_engine.py`, not the contradiction-detection λ in `efopa_enhancement_module.py`. Contradiction rules, cost functions, and the elephant module are implemented and unused.
4. **The advanced panels are client-derived.** `advanced-analysis.js` reconstructs bias, implicit cognition, quality, and authenticity from raw and corrected scores in the browser. They are not the server's EFOPA metrics.
5. **The VAE is a mock.** Without `VAE_MODEL_PATH`, `_create_mock_model` returns random latent vectors, and reference type vectors are random as well. Type assignment and confidence are not meaningful in that mode.
6. **Response range mismatch.** `ScoringEngine` accepts 0–10; `submit_assessment` rejects anything below 1. A legitimate 0 answer is refused with `RESPONSE_OUT_OF_RANGE`.
7. **Three different domain vocabularies.** `personality_classifier.py` reads `R`/`S`/`A`/`E` as Resilience, Social Awareness, Adaptability, Extroversion. The questionnaire and the EFOPA engine read them as Relationships, Status, Agreeableness, Emotional Stability. That classifier is not in the live path, but the naming will mislead.
8. **Two sets of type names.** Backend says Analytical Leader; frontend says The Analytical.
9. **`conftest.py` is broken.** It imports a `create_app` factory that does not exist.
10. **`efopa-integration.js` is dead code.** `results.html` no longer loads it.
11. **`backend/.env` is committed** even though `.gitignore` lists it. Treat every credential in it as exposed and rotate it.
12. **Startup can drop the database.** The schema check in `app.py` drops all tables when it sees an unexpected `users.id` type, including in its exception-recovery path.
13. **The landing page claims "95%+ accuracy"** for deception detection. No validation study in this repository supports that number.

---

## Status

Working prototype. The assessment runs end to end and produces stable, reproducible scores from the deterministic parts of the pipeline. The latent classification is not meaningful without a trained model, and none of the psychometric claims have been validated against an external criterion.

This is not a clinical instrument and not a validated psychometric test. Do not use its output to make decisions about hiring, admission, care, or anyone's life.

---

## Reading

Kevin Simler and Robin Hanson, _The Elephant in the Brain: Hidden Motives in Everyday Life_, Oxford University Press, 2018.

Amotz Zahavi and Avishag Zahavi, _The Handicap Principle: A Missing Piece of Darwin's Puzzle_, Oxford University Press, 1997, for the babbler fieldwork and the costly-signalling argument the project's framing rests on.
