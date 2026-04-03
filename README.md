# T&C Analyzer

AI-powered Terms & Conditions analyzer for PDFs, links, and document photos.

It extracts the text, chunks it for retrieval, scores risky clauses, answers follow-up questions with citations, exports a PDF report, and supports Google-based account history.

## Features

- Multi-input analysis:
  - PDF upload
  - webpage or PDF link
  - photos of printed documents
- RAG-based Q&A with cited source chunks
- Clause classification and risk scoring
- Risk overview dashboard + deep-dive review
- Downloadable PDF analysis report
- Google sign-in + saved analysis history

## Stack

- Backend: FastAPI
- Frontend: Streamlit
- Retrieval: FAISS
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- LLM:
  - Primary: Gemini 2.5 Flash
  - Fallback: FLAN-T5 small
- Storage: SQLite

## Project Structure

```text
app/
  db/                  sqlite + faiss helpers
  models/              request/response schemas
  services/            rag, parsing, auth, persistence, reports
  main.py              FastAPI app
frontend/
  app.py               Streamlit UI
data/
  uploads/             uploaded files
  tnc_analyzer.db      SQLite database
```

## Local Setup

1. Create a virtual environment and install dependencies.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy the env template.

```powershell
Copy-Item .env.example .env
```

3. Fill in at least:

- `GEMINI_API_KEY`
- `BACKEND_BASE_URL`
- `FRONTEND_BASE_URL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

## Run Locally

Backend:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
streamlit run frontend/app.py
```

Default local URLs:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://localhost:8501`

## Google Sign-In Setup

Create OAuth credentials in Google Cloud Console and configure:

- Authorized redirect URI:
  - `http://127.0.0.1:8000/auth/google/callback`
- For deployment, add your deployed backend callback too:
  - `https://your-backend-domain/auth/google/callback`

Then set in `.env`:

```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
```

The current app uses Google-only sign-in in the UI. There is no email/password form in the product flow.

## Important Environment Variables

```env
GEMINI_API_KEY=...
BACKEND_BASE_URL=http://127.0.0.1:8000
FRONTEND_BASE_URL=http://localhost:8501
API_BASE_URL=http://127.0.0.1:8000
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
```

## Deployment Notes

Recommended free-first split:

- Backend: Render or Railway
- Frontend: Streamlit Community Cloud

This repo includes `render.yaml` for the backend service.

### Backend

Use:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set backend env vars:

- `GEMINI_API_KEY`
- `BACKEND_BASE_URL`
- `FRONTEND_BASE_URL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

### Frontend

Set frontend env vars:

- `BACKEND_BASE_URL`
- `FRONTEND_BASE_URL`

Example:

- `BACKEND_BASE_URL=https://your-backend-domain`
- `FRONTEND_BASE_URL=https://your-streamlit-domain`

## Current Limitations

- SQLite is good for prototyping, but Postgres is better for larger-scale production.
- The local fallback model is small and may be less accurate than Gemini.
- Image text extraction currently depends on Gemini.

## Resume-Friendly Summary

Built an AI-powered Terms & Conditions Analyzer using FastAPI, Streamlit, FAISS, and transformer embeddings. Implemented clause-level risk scoring, citation-grounded RAG Q&A, PDF report export, Google sign-in, and saved document history across PDFs, links, and document photos.
