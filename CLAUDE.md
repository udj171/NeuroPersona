# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

NeuroPersona is a personality assessment built on the premise that self-report is systematically distorted by self-flattery, and that the distortion itself is the interesting signal. A 35-item questionnaire feeds a Flask API that scores six domains, estimates a deception-susceptibility parameter (**lambda**, λ), subtracts a per-domain bias derived from it, runs the corrected profile through a latent-variable model, and asks Gemini to write an interpretation.

The conceptual source is **_The Elephant in the Brain: Hidden Motives in Everyday Life_** (Kevin Simler and Robin Hanson, Oxford University Press, 2018). The book argues that much human behaviour serves competitive motives — status, mating, coalition-building — and that we hide those motives from ourselves so that we can advertise better ones more convincingly. Its central image comes from Amotz Zahavi's Arabian babblers, birds that fight each other for the right to feed a rival or stand exposed as sentinel: altruism as costly signalling, where the waste is what makes the signal credible. Humans play the same game with an extra layer, an internal "press secretary" that issues flattering accounts of conduct it did not actually author.

The repository turns that into machinery. Core items probe behaviour under conditions where the flattering answer and the accurate answer diverge. Validity items `V31`–`V35` interrogate the press secretary directly. λ scores the gap. Per-domain `honesty_barrier` weights price honesty by stakes, following the handicap principle. The **Elephant Module** reweights each domain's credibility by inferred implicit bias. The authenticity index is `(1 − λ) × coherence`.

The internal name for that layer is **EFOPA** (Enhanced Framework for Personality Observation and Assessment). It is used freely in backend module names and in the design documents. **Keep it out of user-facing UI text** — a deliberate past change replaced it with "advanced analysis", and reintroducing it would undo that.

## Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
python app.py                                # dev server, port 5000
gunicorn app:app                             # production entry point

# Tests — --noconftest is currently required, see Sharp edges
cd backend && pytest test_scoring.py --noconftest

# Frontend (static, no build)
cd frontend && npm run dev                   # python -m http.server 3000
```

Browser helpers exposed by `config.js`: `window.setAPIURL(url)`, `window.resetAPIURL()`, `window.checkAPIHealth()`.

Python is pinned to 3.11.7 in `runtime.txt`. There is no linter, formatter, or CI configuration in this repository.

## Architecture you need to hold in your head

**Backend** is a Flask app with a module-level `app` object, not a factory. Blueprint `api_bp` is registered at `/api`. Three engines are constructed once at import time and injected into the blueprint via `set_engines`: `ScoringEngine`, `VAEInferenceEngine`, `GeminiClient`. Each is wrapped in its own try/except, so a failure leaves the corresponding global as `None` and the app still boots.

**The live scoring path** is `api_routes.submit_assessment` → `scoring_engine.process_assessment` → `vae_inference.process_assessment` → `gemini_client.process_assessment_with_interpretation`, persisting to `Result`, `VAEOutput`, `PersonalityClassification`, and `GeminiInterpretation` along the way. Nothing else is in that path.

**The EFOPA modules are not in that path.** `efopa_enhancement_module.py`, `scoring_integration.py`, `models_efopa_extension.py`, `api_routes_efopa.py`, `efopa_data_persistence.py`, and `efopa_config.py` are complete, self-consistent, and entirely unreferenced by `app.py`. Read them as a designed-but-unwired subsystem, not as live code.

**Frontend** is five static pages with no bundler and no framework. `architecture.html` and `features.html` are content-only explainers: each loads `config.js` and `app.js` for the shared nav behaviour and nothing else, and their diagrams are hand-written inline SVG with no chart library. Script order on `results.html` matters and is load-bearing: `config.js` sets `window.API_CONFIG`, `app.js` defines the global `apiRequest` and `showToast`, `advanced-analysis.js` defines the panel generators, `results.js` orchestrates on `DOMContentLoaded`. Everything communicates through globals on `window`.

**Domain keys** are `R`, `S`, `C`, `A`, `O`, `E` throughout — Relationships, Status, Reliability/Conscientiousness, Agreeableness, Openness, Emotional Stability. Personality types are the letters `A` through `F`, which is an unfortunate collision with the domain keys. Read carefully at every call site.

## Sharp edges

Verified against the code. Do not assume any of these have been fixed.

- **`conftest.py` is broken.** It does `from app import create_app`, and `app.py` defines no such factory. Any bare `pytest` run in `backend/` fails at collection. Use `--noconftest`, or fix the factory if the task calls for it.
- **Startup can drop the database.** `check_and_migrate_schema` in `app.py` calls `db.drop_all()` when `users.id` is not a string type, and its exception handler drops and recreates as a recovery step. Never point a fresh checkout at a database with data you care about.
- **The VAE is a mock unless a model file is supplied.** With `VAE_MODEL_PATH` unset, `_create_mock_model` returns `np.random.randn` for both encoder and decoder, and reference latent vectors are random too. Personality type, confidence, and novelty are noise in that mode. Do not write tests that assert on specific type assignments.
- **Response-range mismatch.** `ScoringEngine._validate_responses` accepts 0–10. `submit_assessment` rejects any value below 1. A respondent answering 0 gets `RESPONSE_OUT_OF_RANGE`. Fixing one side without the other will move the bug, not remove it.
- **`personality_classifier.py` uses different domain names** for the same letters: Resilience, Social Awareness, Adaptability, Extroversion. It is not in the live path. Do not use it as a naming reference.
- **Two type vocabularies.** Backend: Analytical Leader, Dynamic Innovator, Balanced Pragmatist, Empathetic Connector, Visionary Dreamer, Grounded Realist. Frontend `results.js`: The Analytical, The Builder, The Connector, The Driver, The Explorer, The Facilitator. Only the letter travels over the wire.
- **`frontend/efopa-integration.js` is dead code.** `results.html` no longer loads it; `advanced-analysis.js` replaced it. Do not edit it expecting a visible effect.
- **The advanced panels are computed in the browser.** `advanced-analysis.js` derives bias, implicit cognition, quality, and authenticity from `raw_domain_scores` and `corrected_domain_scores` returned by `/api/results/<id>`. They are approximations, not the server's EFOPA metrics, and they silently fall back to defaults (0.5, 0.6, 0.7) when fields are missing.
- **`backend/.env` is committed** despite being listed in `backend/.gitignore`. It contains a Gemini key, a Flask secret, a database URL, and SMTP credentials. Never print its values, never copy them into code, docs, logs, or commit messages. If a task touches it, say the credentials need rotating and `git rm --cached`.
- **`NEXT_PUBLIC_API_URL` does nothing.** `vercel.json` sets it, but a static page has no `process.env`, so `config.js` always falls through to its hardcoded URLs. Change the production API URL in `config.js`.
- **CORS is wide open** on `/api/*` with `supports_credentials=True`. Deliberate for now; flag it rather than silently tightening it.
- **`EFOPA_ARCHITECTURE.md` describes an aspirational system.** It documents `/api/efopa/*` as live, references a `backend/scoring.py` that does not exist, and cites performance figures that were never measured. Read it for intent. Trust the code for fact.

## Conventions to match

- Logging uses bracketed subsystem tags: `logger.info('[SUBMIT_ASSESSMENT] ...')`, `[ENGINES]`, `[SCHEMA]`, `[DB]`. Match the surrounding tag when adding a line. Existing lines use ✓ and ✗ marks; follow the file you are in.
- API errors return `{'status': 'error', 'message': ..., 'code': 'SCREAMING_SNAKE'}` with an appropriate HTTP status. Reuse the existing code strings rather than inventing near-duplicates.
- Scoring functions take and return plain dicts and lists, round floats to 4 places, and clamp with `np.clip`. Keep numeric output JSON-serialisable — cast NumPy scalars with `float()` before they reach a response.
- Frontend logs are prefixed the same way: `[RESULTS]`, `[API]`, `[CONFIG]`, `[Advanced Analysis]`.
- Frontend rendering is template strings assigned to `innerHTML`, with inline styles. That is the house style here. If you interpolate anything a user typed, escape it.
- Static pages use semantic classes from `styles.css`, not inline styles. The `.arch-*` block at the end of that file styles `architecture.html`, `features.html`, and the marketing sections on `index.html`.
- Diagram marks use the `--data-teal*` and `--data-accent` tokens, deliberately brighter than the `--color-primary` chrome so fills clear the contrast floor against the page surface. Chrome keeps `--color-primary`. Every diagram is inline SVG with a `<title>` and `<desc>`, wrapped in `.arch-scroll` so it scrolls inside its own box on narrow screens rather than shrinking or pushing the page sideways.
- Backend files open with a banner comment naming the script. Preserve it when editing.

## Boundaries

- **Do not restate the accuracy claim.** `frontend/index.html` advertises "95%+ accuracy" for deception detection. Nothing in this repository validates that figure. Do not repeat it in documentation, comments, or new copy, and do not add comparable claims.
- **This is not a clinical or validated instrument.** Keep new user-facing copy away from diagnostic language, and away from any suggestion that the output should inform hiring, admissions, or care.
- **Respondent data is personal data.** `Assessment` stores IP address and user agent alongside responses. Do not add logging that writes response content or identifiers to log files.
- **The λ correction is opinionated, not established.** Subtracting an estimated self-flattery bias from a self-report is the project's thesis, not a settled psychometric method. When asked to change the formulas, implement what is asked, and say plainly if a change alters the meaning of scores already stored in the database.

## Documentation map

`README.md` is the accurate current description. The rest are historical design notes from the EFOPA build, kept for intent rather than fact:

- `EFOPA_ARCHITECTURE.md` — intended system diagram and data flows
- `EFOPA_TECHNICAL_SPECIFICATIONS.md`, `EFOPA_IMPLEMENTATION_SUMMARY.md` — algorithm and module specs
- `EFOPA_INTEGRATION_GUIDE.md`, `README_EFOPA_INTEGRATION.md` — how the layer was meant to be wired in
- `FRONTEND_EFOPA_INTEGRATION.md`, `FRONTEND_CHANGES_SUMMARY.md` — the superseded `efopa-integration.js` client
- `COMPATIBILITY_CHECKLIST.md` — gap analysis, still largely open
- `DEBUGGING_GUIDE.md` — the engine-initialisation 500s, since fixed
- `EFOPA_DEPLOYMENT_CHECKLIST.md`, `INTEGRATION_COMPLETE_SUMMARY.txt` — deployment notes

When one of these contradicts the code, the code wins, and it is worth saying so in your response rather than quietly following the document.
