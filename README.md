# Thai Tax Assistant

A Thai salary tax calculator and eligibility assistant for tax year 2568.

## Run on Windows

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m tax_app.server
```

Open http://127.0.0.1:8001. For chat, copy `.env.example` to `.env` if needed and fill in the course proxy settings.

See [setup, evaluation, and demo](tax_app/README.md).
