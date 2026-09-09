# Training

The model that assigns a personality type is trained here, once, and served by
`backend/model_inference.py` as plain numpy matrices. Production never imports
PyTorch.

## The dataset

**Open-Source Psychometrics Project, "Big Five Personality Test"**

| | |
| --- | --- |
| Responses | 1,015,342 |
| Items | 50, the IPIP Big-Five Factor Markers (Goldberg, 1992) |
| Scale | 1 to 5, where 0 marks an unanswered item |
| Collected | 2016 to 2018, online, worldwide |
| Licence | Public domain. The Open-Source Psychometrics Project releases its raw data without restriction, and the IPIP items themselves are public domain |
| Kaggle | <https://www.kaggle.com/datasets/tunguz/big-five-personality-test> |
| Original | <https://openpsychometrics.org/_rawdata/> |

No account tier, no payment, no request form, no data-use agreement. The Kaggle
mirror is the convenient copy; the openpsychometrics archive is the primary source.

It was chosen because it is the largest freely accessible dataset that pairs the
Big Five items with individual responses. The alternatives are smaller: Johnson's
IPIP-NEO-120 archive holds about 619,000 responses and the IPIP-NEO-300 about
307,000, both also public domain and both usable here with a different column map.

## Files

| File | What it is |
| --- | --- |
| `train_vae_ocean.py` | The trainer. Runs on Kaggle or locally |
| `kaggle_train_ocean.ipynb` | The notebook to upload to Kaggle |

## Running it on Kaggle

1. New Notebook, then **+ Add Input → Datasets**, search `big-five-personality-test`, add the one by `tunguz`.
2. Settings: Accelerator **GPU T4 x2** or **P100**, Internet **On**.
3. Upload `kaggle_train_ocean.ipynb` and run the cells in order.
4. Download `ocean_vae.npz` from the output and commit it to `backend/model_weights/`.

A full 30-epoch run over roughly 850,000 cleaned rows takes about 15 to 25 minutes
on a T4. The weekly free quota is around 30 GPU hours, so this costs a fraction of
one week's allowance.

### Training for longer than one session

A Kaggle session is capped at 12 hours, which is the reason the trainer checkpoints
every epoch rather than only at the end. To continue across sessions:

1. Save the notebook version, so `/kaggle/working` is kept as notebook output.
2. In the next session, **+ Add Input → Notebook Output** and attach that output.
3. Set `RESUME_DIR` to its path under `/kaggle/input/...` and run again.

The trainer reloads the model and optimiser state and resumes at the next epoch.
Repeating that daily lets a run span a week within the free tier.

## Running it locally

```bash
pip install torch pandas numpy
python train_vae_ocean.py --data path/to/data-final.csv --epochs 30 --out ./out
python train_vae_ocean.py --data path/to/data-final.csv --epochs 2 --max-rows 50000  # smoke run
```

## What the trainer produces

A single compressed `.npz`, a few hundred kilobytes, small enough to commit:

- encoder and decoder matrices, already transposed for `x @ W` in numpy
- per-item mean and standard deviation of the training responses
- six k-means centroids in latent space, with each cluster's mean OCEAN profile
- type names derived from the clusters themselves, not written in advance
- per-trait percentile tables, so a result can be placed against the reference sample
- reconstruction-error statistics, used for the novelty score
- a metadata blob recording the dataset, row count, epochs and date

## The contract with the backend

`backend/test_model_contract.py` pins the boundary between the two. It checks that
the trainer's embedded item bank still matches `backend/ocean_items.py`, that the
trainer's trait scoring agrees with the backend's to three decimal places, and that
the exported matrices reproduce a PyTorch `nn.Linear` forward pass exactly. It needs
no PyTorch to do it.

Run it after any change to either side:

```bash
cd backend && pytest
```

If the item order in the weight file ever stops matching `ocean_items.ITEM_ORDER`,
the backend refuses to load the file rather than scoring people against silently
transposed columns.
