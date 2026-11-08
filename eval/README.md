# Evaluation

Run this from the repository root. The offline run uses the Python standard library and the checked-in catalog.

```powershell
python -m eval.run
```

`gold.json` contains 30 hand-labelled Thai and English prompts. Each prompt has the IDs of the manufacturer documents needed to answer it. The set covers exact names, shortened and compact names, near-identical board variants, DDR and socket mismatches, minimum BIOS versions, and cases where the catalog cannot verify support. Nineteen prompts also have a gold compatibility verdict and a structured representation of the named parts. For example, case 01's minimum is BIOS 2423, so a board with BIOS 2403 receives `conditional`.

Both retrievers use the same frozen catalog and return up to three documents for the original prompt. The baseline uses BM25 over words. The hybrid adds character n-gram vectors and favors model mentions and the type of evidence requested. Recall@3 is the mean fraction of a prompt's relevant documents in the first three results. MRR@3 is the mean of `1 / first relevant rank`, or zero when there is no relevant result in the first three.

| Search | Prompts | Recall@3 | MRR@3 |
| --- | ---: | ---: | ---: |
| BM25 | 30 | 0.9111 | 0.8944 |
| Hybrid | 30 | 0.9833 | 0.9778 |

In case 13, BM25 missed the B550-PLUS WIFI II specs for `tufb550pluswifiii` and hybrid ranked them first. In case 27, BM25 found both BIOS tables for a comparison, while hybrid found only the plain board's table. The prompt identifies the second model with the short suffix `WIFI II`. The hybrid gave more weight to the fully named plain board and the named CPU, which used up the top three places.

The direct checker matched 19 of 19 verdicts when given the correct canonical part IDs. This isolates compatibility logic from the model's handling of user wording. The prompts were written for this small catalog, so these results describe performance on the checked-in scenarios.

`results.json` is the detailed offline run. Regenerate it with `python -m eval.run --output eval/results.json`. After installing the app dependencies and filling in `.env`, run the nineteen compatibility prompts through the actual class proxy with `python -m eval.run --live --output eval/live-results.json`. This scores the structured tool verdict and records the tool names, so model phrasing is outside the metric. Live results are measured when the command runs.
