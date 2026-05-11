# Financial Assistant

Personal finance tracker. Single user, local-first.

## Phase 1: Backend (this milestone)

### Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate   # PowerShell on Windows
pip install -r requirements.txt
copy .env.example .env
```

### Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Tests

```bash
pytest
```
