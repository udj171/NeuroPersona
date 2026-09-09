# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

NeuroPersona is a Big Five personality assessment with one addition: it estimates how far the respondent's answers were shaded in their own favour, and corrects the trait scores by that estimate. Both sets of scores are always computed, stored, returned and displayed.

Two halves, deliberately separable:

- **Trait measurement.** The IPIP Big-Five Factor Markers, 50 public-domain items, standard reverse-keying, 1-5 scale. Not opinionated. Decades-old instrument.
- **The correction.** Five cross-check items, a lambda estimate, a per-trait shift. Entirely this project's argument, not established psychometrics.

The correction's idea comes from **_The Elephant in the Brain_** (Kevin Simler and Robin Hanson, Oxford University Press, 2018) and behind it Zahavi's handicap principle: a signal is credible in proportion to what it costs, and humans hide competitive motives from themselves so they can advertise better ones more convincingly. Zahavi's Arabian babblers, which fight each other for the right to feed a rival or stand exposed as sentinel, are the book's central image and the landing page's essay.

**The 50 trait items carry none of that reasoning.** They are the standard IPIP markers, chosen because they are the items behind the training dataset. Do not describe them as costly-signal items; an earlier version of the copy did, and it was wrong.

**EFOPA is retired.** The name survives only in the filename `EFOPA_ARCHITECTURE.md`, kept so links resolve. Do not reintroduce it in code or UI text.

## Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
python app.py                                # dev server, port 5000
gunicorn app:app                             # production entry point
pytest                                       # 35 tests, no flags needed

# Frontend (static, no build)
cd frontend && npm run dev                   # python -m http.server 3000

# Training (Kaggle, or locally with torch + pandas installed)
python training/train_vae_ocean.py --data data-final.csv --epochs 30
python training/train_vae_ocean.py --data data-final.csv --epochs 2 --max-rows 50000
```

Browser helpers from `config.js`: `window.setAPIURL(url)`, `window.resetAPIURL()`, `window.checkAPIHealth()`.

Python is pinned to 3.11.7 in `runtime.txt`. There is no linter, formatter, or CI configuration in this repository.

## Architecture you need to hold in your head

**Backend** is a Flask app with a module-level `app` object, not a factory. Blueprint `api_bp` is registered at `/api`. Three engines are built at import time and injected via `set_engines`: `ScoringEngine`, `ModelInferenceEngine`, `NarrativeGenerator`. Each is wrapped in its own try/except, so a failure leaves that global as `None` and the app still boots.

**The live path** is `api_routes.submit_assessment` → `scoring_engine.process_assessment` → `model_engine.process` → `narrative_generator.generate`, persisting to `Result`, `ModelOutput`, `PersonalityClassification` and `Interpretation`. There is no other path; every module in `backend/` is now reachable.

**Training and serving are split on purpose.** The model is trained in PyTorch on Kaggle and exported as plain numpy matrices to a single `.npz`. Production runs the forward pass by hand in numpy. **Never add torch to `backend/requirements.txt`** — keeping it out is what lets the whole backend fit on a free host.

**Trait keys** are `O`, `C`, `E`, `A`, `N`. **Item ids** are `EXT1`-`EXT10`, `EST1`-`EST10`, `AGR1`-`AGR10`, `CSN1`-`CSN10`, `OPN1`-`OPN10`, plus `V1`-`V5`. Note the mismatch: neuroticism items are coded `EST` because the dataset codes them that way, and `EST2`/`EST4` are the reversed ones since the items are worded toward neuroticism rather than stability.

**`backend/ocean_items.py` is the single source of truth** for items, wording, keying and scale. The questionnaire page fetches it from `GET /api/questionnaire` rather than hardcoding it. `training/train_vae_ocean.py` embeds a copy so it runs standalone on Kaggle, and `test_model_contract.py` fails if the copy diverges. Change the bank in one place and let the tests catch the rest.

**Frontend** is five static pages, no bundler, no framework. Script order on `results.html` is load-bearing: `config.js` sets `window.API_CONFIG`, `app.js` defines the global `apiRequest` and `showToast`, `advanced-analysis.js` defines `loadAdvancedAnalysis`, `results.js` orchestrates on `DOMContentLoaded`. Everything communicates through globals on `window`.

## Sharp edges

Verified against the code. Do not assume any of these have been fixed.

- **Results are enumerable.** `/api/results/<int:id>` takes a sequential integer, so the range can be walked to read other people's results. `assessments.external_id` already holds a UUID that would fix it. The most serious open issue here.
- **Startup can drop the database.** `check_and_migrate_schema` in `app.py` calls `db.drop_all()` when `users.id` is not a string type, and its exception handler drops and recreates as a recovery step. Never point a fresh checkout at a database with data you care about.
- **Without weights, no type is claimed.** With no `.npz` installed, `ModelInferenceEngine` returns `weights_loaded: false`, `confidence: null`, and a `notice`. It is deterministic and never random. Do not "fix" this by inventing a confidence number; the previous version used `np.random.randn` here and produced confident-looking nonsense.
- **Model input is raw, not keyed and not corrected.** The weights only ever saw raw 1-5 responses. Feeding reverse-keyed or corrected values would break train/serve parity. `test_scoring.py` pins this.
- **Weight-file item order is checked on load.** A `.npz` whose `item_order` does not match `ocean_items.ITEM_ORDER` is refused, because the alternative is silently scoring people against transposed columns.
- **`backend/.env` is committed** despite being in `.gitignore`. The Gemini key has been removed from the file but remains in git history. Treat it, the Flask secret and the SMTP credentials as exposed and say they need rotating and `git rm --cached`. Never print its values.
- **The SMTP variables in `.env` are dead.** There is no email code anywhere in the repository.
- **`NEXT_PUBLIC_API_URL` does nothing.** `vercel.json` sets it, but a static page has no `process.env`, so `config.js` always falls through to its hardcoded URLs, which still point at the old Render deployment. Change the URL in `config.js`.
- **CORS is wide open** on `/api/*` with `supports_credentials=True`. Deliberate for now; flag it rather than silently tightening it.
- **The correction is unvalidated.** Its weights and thresholds are reasoned, not fitted. The training dataset contains no ground truth about self-flattery, so it cannot validate this half.
- **Hugging Face Spaces is not a free hosting option any more.** As of 2026, Docker and Gradio Spaces require a paid plan even on CPU Basic. Only static Spaces are free. See `EFOPA_ARCHITECTURE.md` section 7 for what is.

## Conventions to match

- Logging uses bracketed subsystem tags: `[SUBMIT_ASSESSMENT]`, `[ENGINES]`, `[SCHEMA]`, `[DB]`, `[SCORING]`, `[MODEL]`, `[NARRATIVE]`. Match the surrounding tag when adding a line. Existing lines use ✓ and ✗ marks; follow the file you are in.
- API errors return `{'status': 'error', 'message': ..., 'code': 'SCREAMING_SNAKE'}` with an appropriate HTTP status. Reuse the existing code strings rather than inventing near-duplicates.
- Scoring functions take and return plain dicts and lists, round floats sensibly, and clamp with `np.clip`. Cast NumPy scalars with `float()` before they reach a response.
- Frontend logs are prefixed the same way: `[RESULTS]`, `[API]`, `[CONFIG]`, `[QUESTIONNAIRE]`, `[Advanced Analysis]`.
- Frontend rendering is template strings assigned to `innerHTML`, with inline styles. That is the house style. Escape anything a user typed; `escapeHtml` already exists in `results.js`, `questionnaire.js` and `advanced-analysis.js`.
- Static pages use semantic classes from `styles.css`, not inline styles. The `.arch-*` block at the end of that file styles `architecture.html`, `features.html`, and the marketing sections on `index.html`.
- Diagram marks use the `--data-teal*` and `--data-accent` tokens, deliberately brighter than the `--color-primary` chrome so fills clear the contrast floor against the page surface. Every diagram is inline SVG with a `<title>` and `<desc>`, wrapped in `.arch-scroll` so it scrolls inside its own box on narrow screens rather than shrinking or pushing the page sideways.
- Backend files open with a banner comment naming the script. Preserve it when editing.

## Boundaries

- **No accuracy claims.** Nothing in this repository validates any figure about how well the correction works. Do not add one, and do not restate the "95%+ accuracy" line that used to be on the landing page.
- **This is not a clinical or validated instrument.** Keep user-facing copy away from diagnostic language and away from any suggestion the output should inform hiring, admissions, or care.
- **Respondent data is personal data.** `Assessment` stores IP address and user agent alongside responses. Do not add logging that writes response content or identifiers to log files.
- **Show both score sets.** The uncorrected numbers are always returned and always displayed. Hiding them would make the correction unfalsifiable, which is the opposite of the point.
- **The correction is opinionated, not established.** When asked to change its formulas, implement what is asked, and say plainly if the change alters the meaning of scores already stored in the database.

## Documentation map

- `EFOPA_ARCHITECTURE.md` — **current**, version 2.0. The questionnaire, the dataset, the Kaggle training protocol, the weight contract, the Gemini replacement, and free hosting options.
- `README.md` — current. Orientation and the honest issues list.
- `training/README.md` — current. Dataset citation, licence, run protocol.

The rest describe the retired six-domain system and are kept only as history. When one contradicts the code, the code wins, and say so rather than quietly following the document: `EFOPA_TECHNICAL_SPECIFICATIONS.md`, `EFOPA_IMPLEMENTATION_SUMMARY.md`, `EFOPA_INTEGRATION_GUIDE.md`, `README_EFOPA_INTEGRATION.md`, `FRONTEND_EFOPA_INTEGRATION.md`, `FRONTEND_CHANGES_SUMMARY.md`, `COMPATIBILITY_CHECKLIST.md`, `DEBUGGING_GUIDE.md`, `EFOPA_DEPLOYMENT_CHECKLIST.md`, `INTEGRATION_COMPLETE_SUMMARY.txt`.
