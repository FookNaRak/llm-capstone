# PC Parts Check

A capstone for first-time PC builders and people upgrading an existing PC. Ask in Thai or English whether the CPU, motherboard and RAM you named can be used together. The app checks a small catalog of AMD AM4 and AM5 parts and cites manufacturer evidence. A direct checker works without model credentials.

## Run on Windows

Use Python 3.12 or newer. From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Use the **API key and base URL issued by the course**. Put the values on the right of the equals signs in the repository's `.env` file. If the file already exists, edit it directly.

```dotenv
OPENAI_API_KEY=your_class_proxy_key
OPENAI_BASE_URL=your_class_proxy_base_url
```

The file is ignored by Git. Keep your values local. The backend calls `OpenAI()` with `model="gemma-4-E4B-it"`. On macOS or Linux, use `python3` to create the environment, `.venv/bin/python` as its interpreter, and `cp` to copy the example.

```powershell
.\.venv\Scripts\python.exe -m app.server
```

Open **http://127.0.0.1:8000**. Use the right-hand form to check parts without a key. Use the left-hand form to send a question through the course proxy. You can pass `--port 8001` to change the port.

Try these inputs:

- `TUF GAMING B550-PLUS + Ryzen 7 5700X3D + KF432C16BBK2/16 ตอนนี้ BIOS 2803 ใช้ได้ไหม`
- `TUF GAMING B550-PLUS + Ryzen 7 5700X3D + KF432C16BBK2/16 ตอนนี้ BIOS 2423 ใช้ได้ไหม`
- `TUF GAMING B650-PLUS WIFI + Ryzen 5 7600 + KF432C16BBK2/16 ใช้ด้วยกันได้ไหม`

The expected statuses are compatible within the checks covered, conditional on a BIOS update, and incompatible because of the DDR generation. The UI shows the structured result, manufacturer links, and the tools called.

## Design

- `data/catalog.json` holds 13 parts, 12 CPU-support rows and manufacturer links. This curated snapshot can be used offline. The support tables in the app cover the rows in the snapshot.
- `app/catalog.py` creates an in-memory index over specification and CPU-support documents. Hybrid retrieval combines BM25, sparse character TF-IDF vectors and model/evidence-type matches. Search hits carry source URLs.
- `app/agent.py` runs up to five model calls. It exposes two allow-listed functions, validates their arguments, requires explicit searched part IDs for checks and validates the submitted BIOS value against the user's input.
- `app/checker.py` applies socket, CPU support, minimum BIOS and DDR generation rules. Missing evidence yields `unknown` and an absent or older BIOS yields `conditional` if a minimum is listed.
- `app/server.py` serves the web UI and REST endpoints. `GET /api/parts` lists parts, `POST /api/check` accepts `motherboard`, `cpu`, `memory` and optional `bios` as JSON strings, and `POST /api/ask` accepts `{"query":"…"}`. The direct checker accepts a board with at least one of CPU or RAM.

The RAM rule checks DDR generation. Kit validation, memory speeds and other build components fall outside this catalog. Treat the structured checker result as the verdict. The model's explanation and handling of ambiguous wording are evaluated separately.

## Reproduce the evaluation

```powershell
.\.venv\Scripts\python.exe -m eval.run --output eval/results.json
.\.venv\Scripts\python.exe -m eval.run --live --output eval/live-results.json
```

The first command runs without credentials. On 30 hand-labelled prompts, hybrid search scored **0.9833 Recall@3** and **0.9778 MRR@3**, compared with **0.9111** and **0.8944** for BM25. The direct rule checker matched **19/19** gold statuses with the correct part IDs. The second command measures the full class-proxy tool path on the 19 compatibility prompts and requires a configured `.env`. See [evaluation details](eval/README.md) for the observed retrieval failure and scoring definitions.

See [the project report](output/pdf/pc-parts-check-report.pdf) and [demo notes](DEMO.md).
