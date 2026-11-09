# Thai Tax Assistant

Thai-language eligibility Q&A and an estimate for tax year 2568 (2025). The calculator covers individual filing, taxable employment income only, with no special income exemptions. It applies the salary expense deduction, personal allowance, eligible own life and health insurance, and Easy E-Receipt 2.0. Optional withholding produces an estimated balance. Enter eligible payments from the covered categories once. The form uses the amounts supplied and treats blank optional deductions as zero.

## Run

From the repository root in PowerShell, use the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m tax_app.server
```

Open http://127.0.0.1:8001. The calculator works offline. For chat, populate `OPENAI_API_KEY` and `OPENAI_BASE_URL` in the root `.env` using the values issued by the course. Use fictional profiles in chat. The course proxy receives questions submitted to it. Direct calculation runs locally. If starting from a clean clone, create the venv and install `requirements.txt` as described in the root README.

## Design

- `rules.json` contains Thai paraphrases with official manual page numbers. `retrieval.py` indexes them and returns links to the exact PDF pages. The search combines lexical overlap and sparse character TF-IDF vectors with curated synonyms.
- `calculator.py` validates baht amounts and the tax year with Pydantic and computes with `Decimal`. Receipt group inputs are disjoint eligible totals. The general allowance can consume eligible special-group spend, then the extra tier uses the remaining eligible special spend once. Premiums are allocated to life first, then health within the shared cap.
- `agent.py` calls `gemma-4-E4B-it` through the course proxy. It has two allow-listed tools, `search_rules` and `calculate_tax`, validated arguments, and a five-round limit. The UI displays the computed figure and inputs separately from model prose.
- `server.py` serves the browser and REST endpoints `POST /api/calculate` and `POST /api/ask`. The calculation output is an estimate rounded to satang. The app's coverage excludes other deductions and special exemptions. The receipt and premium inputs require the user to confirm eligibility before entering totals.

## Evaluation

```powershell
.\.venv\Scripts\python.exe -m tax_app.evaluate
.\.venv\Scripts\python.exe -m tax_app.evaluate --live --output tax_app/results.json
```

The 30 cases include 15 labelled retrieval questions and 15 independently calculated profiles. Keyword overlap ranks the same rule IDs by title and text. The hybrid also uses curated synonyms and character vectors. Recall@3 is the mean fraction of gold rule IDs in the first three. Live evaluation uses the same prompt for the model-only and agent runs and scores exact tax before withholding. See `results.json` for the observed rankings and outputs.

## Proposal

Thai Tax Assistant helps salaried individuals understand the eligibility and impact of covered deductions for Thai tax year 2568. It combines retrieval over a page-cited Revenue Department corpus with an agent that validates a structured profile and calls a deterministic Python calculator. The web interface shows the estimated tax before and after eligible expenses. A 30-case benchmark compares retrieval against lexical search and tests numerical accuracy against independent gold figures and a model-only baseline.

## Demo plan (about four minutes)

1. Show the tax-year and employment-only scope. Enter annual income of 600,000 baht, eligible life premiums of 85,000 baht and eligible health premiums of 30,000 baht. Show that the health allowance is limited to 15,000 baht by the shared ceiling and the estimated tax changes from 21,500 to 11,500 baht.
2. In chat, ask whether a home electricity bill can qualify for Easy E-Receipt 2.0 and open the cited rule. Ask a supported calculation question with synthetic inputs and show the separately rendered tool result.
3. Show `python -m tax_app.evaluate` and compare both retrieval variants. Open a missed query from `results.json` and show how the correct document can fall outside the top three. Explain why calculator correctness is measured separately from model extraction.
4. For the live defence, try a new single-filer scenario and verify the rule, inputs and arithmetic from the result.

[Official 2568 filing materials](https://www.rd.go.th/67335.html) · [P.N.D.91 instructions](https://www.rd.go.th/fileadmin/tax_pdf/pit/2568/Ins91_241268.pdf)

The Thai Capstone report is submitted separately as a PDF.
