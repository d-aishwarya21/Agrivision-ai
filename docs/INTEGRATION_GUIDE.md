# CausalAg-Net: Integration Guide

This document explains how to bring the entire system (Frontend, Backend, and ML models) together. 

## 1. System Architecture Overview
The system relies on three separate layers communicating over REST and JSON:
1. **Frontend (Next.js)**: Runs on `http://localhost:3000`. Handles user interactions, auth, and UI state.
2. **Backend (FastAPI)**: Runs on `http://localhost:8000`. Handles the database (`DiagnosticHistory`), user validation (JWT), and hosts the PyTorch weights.
3. **ML Layer (PyTorch)**: Embedded directly inside the FastAPI backend. Loads the `.pth` weights exactly once into RAM.

## 2. Booting the Full Stack Locally
To run the full stack on your local machine for end-to-end testing, open two separate terminal windows.

### Terminal 1: Boot the Backend
```bash
cd backend
# 1. Activate your virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
# 2. Install dependencies if needed
pip install -r requirements.txt
# 3. Start the FastAPI server
uvicorn api.diagnose:app --reload --port 8000
```
*Wait until you see "Application startup complete". The PyTorch model is now loaded into RAM.*

### Terminal 2: Boot the Frontend
```bash
cd frontend
# 1. Install packages
npm install
# 2. Start Next.js
npm run dev
```
*Navigate to `http://localhost:3000` in your browser.*

## 3. The API Contract Checklist
Before deploying to production, ensure these items match perfectly between frontend and backend:
- [ ] **JWT Bearer Token**: Frontend sends it in the `Authorization` header. Backend MUST reject requests without it.
- [ ] **Form Data Keys**: Frontend sends the image as `image`, and floats as `manual_humidity` and `manual_leaf_wetness`. Backend must parse these exactly.
- [ ] **Response JSON Structure**: The backend MUST return the exact structure (including `logic_proof_trace` and `explainable_ai`) defined in `FRONTEND_DOCS.md`, or the React components will crash.
- [ ] **CORS Configuration**: The FastAPI backend MUST have `CORSMiddleware` configured to allow `http://localhost:3000` (and your eventual production URL).
