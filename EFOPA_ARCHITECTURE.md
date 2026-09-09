# NeuroPersona System Architecture

**Version 2.0 — September 2026**

This replaces the version 1.0 document entirely. That one described a six-domain
bespoke questionnaire, a Gemini API call, a mock latent model, and a set of
`/api/efopa/*` endpoints that were never registered. None of that is in the
system any more. The filename is kept so existing links resolve; the EFOPA name
itself is retired.

---

## 1. What the system is

A Big Five personality assessment with one addition: it estimates how far the
respondent's answers were shaded in their own favour, and corrects the trait
scores by that estimate.

The two halves are deliberately separable.

| Half | What it is | How opinionated |
| --- | --- | --- |
| Trait measurement | The IPIP Big-Five Factor Markers, 50 public-domain items, scored the standard way | Not at all. Decades-old instrument, conventional keying |
| The correction | Five cross-check items, a lambda estimate, and a per-trait shift | Entirely this project's argument. Not established psychometrics |

Both sets of scores are computed, stored, returned by the API, and shown to the
respondent. Hiding the uncorrected numbers would make the correction unfalsifiable.

The idea behind the correction comes from *The Elephant in the Brain* (Simler and
Hanson, Oxford University Press, 2018) and, behind that, Zahavi's handicap
principle: a signal is credible in proportion to what it costs to send, and humans
hide competitive motives from themselves in order to advertise better ones more
convincingly. The trait items do not encode that idea. The five cross-checks and
the correction do.

---

## 2. The questionnaire

**55 items, answered 1 to 5**, where 1 is *strongly disagree* and 5 is
*strongly agree*. This scale is not a design preference: it is the scale the
training dataset uses, and matching it is what makes the trained model usable.

### 2.1 The 50 scored items

The IPIP "Big-Five Factor Markers" (Goldberg, 1992), distributed by the
International Personality Item Pool and explicitly public domain. Ten items per
trait.

| Key | Trait | Item codes | Reverse-keyed |
| --- | --- | --- | --- |
| `O` | Openness | `OPN1`–`OPN10` | 2, 4, 6 |
| `C` | Conscientiousness | `CSN1`–`CSN10` | 2, 4, 6, 8 |
| `E` | Extraversion | `EXT1`–`EXT10` | 2, 4, 6, 8, 10 |
| `A` | Agreeableness | `AGR1`–`AGR10` | 1, 3, 5, 7 |
| `N` | Neuroticism | `EST1`–`EST10` | 2, 4 |

Twenty-two of the fifty run backwards, scattered rather than grouped, so agreeing
with everything lands mid-scale on every trait instead of high on all of them.

**The item codes are the dataset's column names.** `EXT1` here is `EXT1` in
`data-final.csv`. Renaming them would silently transpose the model's inputs, so
`model_inference.py` refuses to load a weight file whose stored item order does
not match `ocean_items.ITEM_ORDER`.

The `EST` items are worded toward neuroticism rather than emotional stability,
which is why only `EST2` ("I am relaxed most of the time") and `EST4` ("I seldom
feel blue") are reversed.

### 2.2 The 5 cross-checks

Never scored as traits, never part of the model input.

| Id | Asks about | Candid answer |
| --- | --- | --- |
| `V1` | Ease of admitting a mistake | Middling |
| `V2` | Genuine versus performed humility | Middling |
| `V3` | Consistency across social contexts | Middling |
| `V4` | Opacity of one's own motives | Higher |
| `V5` | Recalling a specific selfish act | Higher |

`V1`–`V3` are claims about oneself; `V4`–`V5` are concessions. A respondent who
maxes the claims and floors the concessions has described someone who has never
been at odds with themselves.

### 2.3 Single source of truth

`backend/ocean_items.py` holds the bank. The questionnaire page fetches it from
`GET /api/questionnaire` rather than hardcoding it, so the wording, the ids and
the scale cannot drift between the page and the scorer. `training/train_vae_ocean.py`
embeds a copy so it runs standalone on Kaggle, and `backend/test_model_contract.py`
fails if the copy diverges.

---

## 3. The dataset

### 3.1 Recommendation

**Open-Source Psychometrics Project — "Big Five Personality Test" (IPIP-FFM)**

| | |
| --- | --- |
| **Responses** | **1,015,342** |
| Items | The same 50 IPIP Big-Five Factor Markers the questionnaire uses |
| Scale | 1–5, with 0 marking an unanswered item |
| Collected | 2016–2018, online, worldwide |
| Extras | Response times per item, country, screen size, repeat-visit count |
| Licence | Public domain, no restrictions |
| Kaggle | <https://www.kaggle.com/datasets/tunguz/big-five-personality-test> |
| Primary source | <https://openpsychometrics.org/_rawdata/> |
| Size | ~400 MB uncompressed, tab-separated |

No account tier, no payment, no data-use agreement, no request form. The Kaggle
mirror is the convenient copy; the openpsychometrics archive is the original and
can be downloaded directly.

### 3.2 Why this one

It is the largest freely accessible dataset that pairs Big Five items with
individual-level responses, and its items are the exact items in this
questionnaire, so no crosswalk or imputation is needed between what the model
learns and what the app collects.

Alternatives considered, all also public domain and all smaller:

| Dataset | Responses | Why not chosen |
| --- | --- | --- |
| Johnson IPIP-NEO-120 | ~619,150 | Fewer responses; 120 different items would mean a 120-item questionnaire |
| Johnson IPIP-NEO-300 | ~307,313 | Fewer still; 300 items is not a usable questionnaire |
| Open Psychometrics IPIP-FFM (this one) | 1,015,342 | Chosen |

myPersonality, once the largest of its kind, was withdrawn in 2018 and is no
longer distributed.

### 3.3 Cleaning

`load_responses()` keeps a row only if all 50 items are within 1–5, which drops
unanswered and malformed rows, then drops straight-lined sheets whose across-item
standard deviation is at or below 0.05. Roughly 850,000 rows survive.

---

## 4. Training on a free Kaggle notebook

### 4.1 The model

```
        50 raw responses (1-5)
                 |
        standardise per item          feature_mean, feature_std
                 |
   Linear 50 -> 128 -> tanh
   Linear 128 -> 64  -> tanh          encoder
   Linear 64  -> 16                   latent mean (mu)
                 |
   Linear 16  -> 64  -> tanh          decoder
   Linear 64  -> 50
```

A variational autoencoder. Loss is mean-squared reconstruction error on the
standardised inputs plus `0.5 x` KL divergence. At inference the sampling step is
dropped and the latent mean is used, so the same answers always give the same
result.

Six k-means centroids are fitted over 200,000 sampled latents. Those centroids are
the personality types. They are **found in the data, not written in advance**, and
each is named after whichever trait most separates it from the other five.

### 4.2 Fitting inside the free tier

| Limit | Value | How this design handles it |
| --- | --- | --- |
| Session length | 12 hours | A full 30-epoch run takes 15–25 minutes on a T4 |
| Weekly GPU quota | ~30 hours | One full run costs well under an hour |
| Disk | 20 GB working | Dataset is ~400 MB; the export is a few hundred KB |
| Internet | Off by default | Turn it on so the notebook can fetch the trainer |

The task brief allows up to a week of training. The model does not need it: this
is a small network over a million rows of 50 numbers. The week's budget instead
buys headroom for a larger latent space, more clusters, longer schedules, or
repeated runs for stability, and the checkpoint protocol below is what makes that
possible across the 12-hour session cap.

### 4.3 Resuming across sessions

Every epoch writes `checkpoint.pt` containing model state, optimiser state and
epoch number. To continue a run in a later session:

1. Save the notebook version, so `/kaggle/working` is retained as notebook output.
2. In the next session, **+ Add Input → Notebook Output**, attaching that output.
3. Set `RESUME_DIR` to its `/kaggle/input/...` path and run again.

The trainer reloads both states and resumes at the next epoch. Repeat daily and a
run spans a week without losing work or exceeding any single-session limit.

### 4.4 The exported weight file

One compressed `.npz`, a few hundred kilobytes, small enough to commit:

| Key | Shape | Purpose |
| --- | --- | --- |
| `item_order` | (50,) | Guards against transposed inputs |
| `feature_mean`, `feature_std` | (50,) | Per-item standardisation |
| `enc_w1/b1`, `enc_w2/b2`, `enc_mu_w/b` | | Encoder, pre-transposed for `x @ W` |
| `dec_w1/b1`, `dec_w2/b2` | | Decoder |
| `centroids` | (6, 16) | Type centroids in latent space |
| `centroid_traits` | (6, 5) | Each cluster's mean OCEAN profile, 0–100 |
| `type_names` | (6,) | Names derived from the clusters |
| `latent_mean`, `latent_std` | (16,) | Novelty scaling |
| `recon_mean`, `recon_std` | scalar | Novelty scaling |
| `trait_quantiles` | (5, 101) | Percentile lookup against the reference sample |
| `meta_json` | scalar | Dataset, row count, epochs, date |

PyTorch stores `nn.Linear.weight` as `(out, in)` and computes `x @ W.T + b`. The
export transposes every matrix so the server can compute `x @ W + b` directly.
`backend/test_model_contract.py` verifies this equivalence without needing torch.

### 4.5 Installing the weights

Download `ocean_vae.npz` and commit it to `backend/model_weights/`, or set
`MODEL_WEIGHTS_PATH`. The backend loads it at startup and logs the outcome.

**The app runs without it.** Every profile is still scored, corrected and written
up. What changes is that no type is claimed: `weights_loaded` is `false`,
confidence is `null` rather than invented, percentiles and novelty are omitted,
and the results page says so. The previous architecture filled this gap with
`np.random.randn`, which produced confident-looking nonsense.

---

## 5. Serving

### 5.1 Request flow

```
  Browser (static, no framework, no build)
      |
      |  GET  /api/questionnaire        the item bank
      |  POST /api/start-assessment     age, sex  ->  assessment_id
      |  POST /api/submit-assessment    55 answers
      |  GET  /api/results/<id>         everything computed
      v
  Flask API
      |
      +-- ScoringEngine        trait scores, lambda, correction     (numpy)
      +-- ModelInferenceEngine latent, type, novelty, percentiles   (numpy)
      +-- NarrativeGenerator   the written reading                  (local)
      |
      v
  Database: Result, ModelOutput, PersonalityClassification, Interpretation
```

`submit-assessment` runs the whole pipeline in one pass and stores every
intermediate result, so `results/<id>` is a pure read and the link reopens the
same numbers rather than recomputing them.

### 5.2 Scoring

1. **Trait scores.** Reverse-key the 22 backward items, average each trait's ten,
   rescale from 1–5 to 0–100.
2. **Lambda.** `0.50 x claim_gap + 0.30 x contradiction_load + 0.20 x style_penalty`,
   clipped to 0–1.
   - `claim_gap` is the mean of `V1`–`V3` minus the mean of `V4`–`V5`, normalised.
   - `contradiction_load` counts four specific pairs, such as agreeableness at or
     above 70 alongside `V5` at or below 2.
   - `style_penalty` flags straight-lining, all-or-nothing answering, and parking
     on the midpoint.
   Bands: below 0.35 light, below 0.65 moderate, otherwise substantial.
3. **Correction.** Per trait,
   `shift = direction x lambda x min(z, 2) x weight x 9`, where `z` is how far the
   trait stands out from the profile's own mean.

   | Trait | Weight | Direction |
   | --- | --- | --- |
   | Agreeableness | 0.90 | lowered |
   | Conscientiousness | 0.85 | lowered |
   | Neuroticism | 0.70 | **raised** |
   | Openness | 0.55 | lowered |
   | Extraversion | 0.45 | lowered |

   Neuroticism runs the other way because it is the trait people play down rather
   than talk up. Maximum shift is 18 points on the 0–100 scale.

### 5.3 Model input parity

The model receives the **50 raw responses**, not the corrected scores and not the
reverse-keyed values. The weights only ever saw raw responses, so feeding anything
else would break train/serve parity. The correction is a separate layer applied to
the reported trait scores, and the results page presents it as such.

---

## 6. Written interpretations, without Gemini

The Gemini client, its dependency, its key and its config are gone. Two local
backends replace it, selected with `NARRATIVE_BACKEND`.

### 6.1 `template` (default)

A deterministic generator in `backend/narrative.py`. Pure Python: no model, no
network, no key, no rate limit, no per-request cost, no cold start. It bands each
trait score, picks the two traits furthest from the profile's own mean, and
composes an opening, a two-trait reading, a settled-traits note, a percentile note
where available, a correction note, and the caveat. Phrasing varies by a hash of
the profile, so the same answers always produce the same page while different
answers do not read identically.

This is the shipped default and it is genuinely free at any scale. For input that
is five numbers and a band, a template also cannot hallucinate a trait you do not
have.

### 6.2 `llm` (opt-in, open weights, local)

For a model-written reading, `llama-cpp-python` loads a GGUF instruct model from
`LLM_MODEL_PATH`. Nothing leaves the host and there is no API involved.

| Model | Licence | Q4 size | RAM |
| --- | --- | --- | --- |
| Qwen2.5-0.5B-Instruct | Apache-2.0 | ~400 MB | ~700 MB |
| SmolLM2-360M-Instruct | Apache-2.0 | ~270 MB | ~500 MB |
| Qwen2.5-1.5B-Instruct | Apache-2.0 | ~1.1 GB | ~1.6 GB |

Any failure — missing library, missing file, bad output — logs a warning and falls
back to `template` rather than failing the request. `llama-cpp-python` is left
commented out in `requirements.txt` so the default install stays small.

---

## 7. Hosting, without Render

Render's free web services sleep and cold-start, which is what the brief asks to
move away from. Two things changed here that make free hosting easy: torch is not
a runtime dependency, and there is no external model API to pay for.

**Runtime footprint:** Flask, Flask-SQLAlchemy, Flask-CORS, SQLAlchemy,
psycopg2-binary, python-dotenv, numpy, gunicorn. Roughly 120 MB installed. The
weight file adds a few hundred kilobytes.

### 7.1 Recommended: Oracle Cloud Always Free

| | |
| --- | --- |
| Compute | Ampere A1 ARM, up to 4 cores and 24 GB RAM across your instances |
| Duration | Always free, not a trial |
| Database | Two autonomous databases included, or run Postgres on the VM |
| Catch | A card is required at signup for identity verification; the Always Free resources are not billed. Capacity in popular regions can be scarce |

It is the only genuinely free tier with enough memory to run the API *and* a local
GGUF model comfortably, which makes the `llm` backend a real option rather than a
theoretical one. Deploy with gunicorn behind nginx or Caddy, or as a Docker
container.

### 7.2 Alternatives

| Platform | Fits | Watch out for |
| --- | --- | --- |
| **Koyeb** free tier | One web service, Git or Docker deploy, no card | Small instance; cold starts; `template` backend only |
| **PythonAnywhere** free | Flask supported, browser-based editing, no card | CPU-second quota, restricted outbound network, no custom domain |
| **Fly.io** | Docker, good ergonomics | The old free allowance is gone; now trial credit |
| **Google Cloud Run** | Scales to zero, generous request quota | Requires a billing account |

**Hugging Face Spaces is no longer viable.** As of 2026, creating a Space that runs
on compute — Docker or Gradio — requires a paid plan, even on CPU Basic hardware.
Only static Spaces remain free. It would otherwise have been the obvious choice.

The frontend stays on Vercel as a static site, which remains free and is unaffected
by any of this.

### 7.3 Environment

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///assessment.db` |
| `SECRET_KEY` | Flask secret | a development placeholder |
| `MODEL_WEIGHTS_PATH` | Trained weights | `backend/model_weights/ocean_vae.npz` |
| `NARRATIVE_BACKEND` | `template` or `llm` | `template` |
| `LLM_MODEL_PATH` | GGUF file, when `llm` | unset |
| `LLM_THREADS` | Threads for the local model | `2` |
| `PORT` | Listen port | `5000` |

`GEMINI_API_KEY`, `GEMINI_API_TIMEOUT`, `GEMINI_MAX_RETRIES`, `GEMINI_RETRY_DELAY`,
`VAE_MODEL_PATH` and `VAE_SCALER_PATH` are all gone.

---

## 8. API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness, no database access |
| `GET` | `/api/questionnaire` | The item bank, scale and trait metadata |
| `POST` | `/api/start-assessment` | Create the record, return `assessment_id` |
| `POST` | `/api/submit-assessment` | Validate, score, infer, write up, persist |
| `GET` | `/api/results/<int:id>` | The full result payload |
| `GET` | `/api/assessments` | Paginated list |
| `GET` | `/api/users/<user_id>/assessments` | Per-user history |
| `GET` | `/api/stats` | Counts, type distribution, mean lambda |

Submission requires all 55 ids exactly once, each an integer from 1 to 5. Missing
ids return `INCOMPLETE_RESPONSES` with the first ten named; unknown ids return
`UNKNOWN_ITEM_IDS`; out-of-range values return `RESPONSE_OUT_OF_RANGE`. The
version 1.0 mismatch, where the scorer accepted 0 and the route rejected it, is
gone: one validator now owns the rule.

---

## 9. Data model

| Table | Holds |
| --- | --- |
| `users` | Age, sex, uuid. No name, email or password is collected |
| `assessments` | Raw responses, timestamps, IP address, user agent |
| `results` | Both score sets, per-trait biases, lambda, band, full lambda analysis, model input |
| `model_outputs` | `weights_loaded`, model version, latent, reconstruction error, novelty, percentiles |
| `personality_classifications` | Type index and name, confidence, runner-up, centroid profile, probabilities |
| `interpretations` | The written text, which backend produced it, and how long it took |

`vae_outputs` and `gemini_interpretations` are replaced by `model_outputs` and
`interpretations`. `personality_classifications.personality_type`, a single letter
constrained to A–F, is replaced by `type_index` plus `type_name`, because the types
are now learned clusters rather than fixed letters.

---

## 10. Repository layout

```
backend/
  ocean_items.py          The 55-item bank. Single source of truth
  scoring_engine.py       Trait scores, lambda, the correction
  model_inference.py      numpy forward pass over the exported weights
  narrative.py            Template and local-LLM interpretation backends
  api_routes.py           The blueprint served at /api
  app.py                  App object, CORS, schema check, engine wiring
  models.py               SQLAlchemy models
  config.py               Config classes by environment
  model_weights/          ocean_vae.npz goes here
  test_scoring.py         21 tests over the scoring layer
  test_model_contract.py  14 tests over the trainer/server boundary

training/
  train_vae_ocean.py      The trainer. Kaggle or local
  kaggle_train_ocean.ipynb  The notebook to upload
  README.md               Dataset details and the run protocol

frontend/
  index.html              Landing page
  architecture.html       Plain-language walkthrough with diagrams
  features.html           What the assessment gives you
  questionnaire.html/.js  Fetches the bank, renders 55 items
  results.html/.js        Renders the result
  advanced-analysis.js    The deeper panels, all from server data
```

**Removed in this revision:** `gemini_client.py`, `vae_inference.py`,
`preprocessing.py`, `personality_classifier.py`, `data_handler.py`,
`validators.py`, `efopa_enhancement_module.py`, `scoring_integration.py`,
`models_efopa_extension.py`, `api_routes_efopa.py`, `efopa_data_persistence.py`,
`efopa_config.py`, and `frontend/efopa-integration.js`. All were either unreachable
or keyed to the retired six-domain questionnaire, and several encoded item indices
that no longer refer to anything.

Dependencies dropped: `google-generativeai`, `scikit-learn`, `scipy`, `pandas`,
`redis`, `Flask-Caching`, `Flask-Limiter`, `Flask-Migrate`, `requests`.

---

## 11. Deployment runbook

```bash
# 1. Train, once, on Kaggle
#    Upload training/kaggle_train_ocean.ipynb, attach the dataset, run it.
#    Download ocean_vae.npz.

# 2. Install the weights
cp ~/Downloads/ocean_vae.npz backend/model_weights/ocean_vae.npz

# 3. Verify locally
cd backend
pip install -r requirements.txt
pytest                       # 35 tests, no flags needed
python app.py                # look for "Loaded weights ... (6 types ...)"

# 4. Deploy the API
gunicorn app:app --bind 0.0.0.0:$PORT

# 5. Point the frontend at it
#    Edit BACKEND URL in frontend/config.js, then deploy the static site.
```

Note that `NEXT_PUBLIC_API_URL` in `vercel.json` has no effect: the frontend is a
plain static site with no bundler, so `process.env` does not exist in the browser
and `config.js` falls through to its hardcoded URLs. Change the URL there.

---

## 12. Known issues

1. **Results are enumerable.** `/api/results/<int:id>` takes a sequential integer,
   so anyone can walk the range and read other people's results. The `assessments`
   table already carries a UUID `external_id`; routing on that instead would fix
   it. This is the most serious open issue in the system.
2. **Startup can drop the database.** `check_and_migrate_schema` in `app.py` calls
   `db.drop_all()` when it finds an unexpected `users.id` type, including in its
   exception-recovery path.
3. **CORS is open to all origins** on `/api/*` with `supports_credentials=True`.
4. **`backend/.env` is committed** despite being listed in `.gitignore`. The Gemini
   key has been removed from the file, but it remains in git history and should be
   treated as exposed and rotated, along with the Flask secret and the SMTP
   credentials still in it.
5. **The correction is unvalidated.** Its weights and thresholds are reasoned, not
   fitted, and have not been checked against any external criterion. The dataset
   contains no ground truth about self-flattery, so it cannot validate this half.
6. **No CI.** The test suite has to be run by hand.

---

## 13. What this is not

A research prototype. The trait half rests on a long-established public instrument
and a model trained on over a million public responses. The correction on top of it
is an argument this project is making, not a finding.

It is not a validated psychological test and not a clinical instrument, and its
output should not inform decisions about hiring, admissions, care, or anyone's
standing.

---

## References

- Simler, K. and Hanson, R. (2018). *The Elephant in the Brain: Hidden Motives in Everyday Life*. Oxford University Press.
- Zahavi, A. and Zahavi, A. (1997). *The Handicap Principle: A Missing Piece of Darwin's Puzzle*. Oxford University Press.
- Goldberg, L. R. (1992). The development of markers for the Big-Five factor structure. *Psychological Assessment*, 4(1), 26–42.
- International Personality Item Pool. <https://ipip.ori.org>
- Open-Source Psychometrics Project raw data archive. <https://openpsychometrics.org/_rawdata/>
