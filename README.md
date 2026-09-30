# AI Ethical Hacker Lab

![Cybersecurity Lab](https://img.shields.io/badge/Platform-Web-blue.svg)
![Language](https://img.shields.io/badge/Language-Python_%7C_Node.js-green.svg)
![Framework](https://img.shields.io/badge/Framework-FastAPI_%7C_React-purple.svg)

**AI Ethical Hacker Lab** is a local cybersecurity laboratory demonstrating powerful AI-targeted attacks such as **pre-LLM backend injection** (Attack 1) and **RAG document poisoning** (Attack 2). Compare vulnerabilities across tenants and observe the differences between **Vulnerable Mode** and **Protected Mode**.

## 🚀 Lab Overview

The objective of this lab is to understand how LLMs interact with backend systems and how to protect against sophisticated injection and poisoning attacks. The lab comes with pre-configured attack scripts, a simulated API backend, and a modern web frontend.

### Attack Modes
- **Attack 1 (Pre-LLM Injection):** Exploit backend logic before the prompt even reaches the LLM (e.g., SQLi, environment leaks, cross-tenant data leaks).
- **Attack 2 (RAG Poisoning):** Hijack an LLM's response by feeding it a poisoned document payload, observing how protected modes quarantine malicious context.

## 🎮 Features
- **Dual Modes**: Toggle instantly between *Vulnerable Mode* and *Protected Mode* to see real-time defense mechanisms (prompt injection detection, permission denial).
- **Simulated Environment**: Built-in simulators for database and LLM APIs if external services aren't provided.
- **Audit Logging**: Track real-time attack events directly from the UI or API endpoint.
- **Automated Demos**: Includes a suite of PowerShell scripts to fire off automated injection payloads.

## 🛠️ Technology Stack
- **Backend**: Python 3.10+, FastAPI
- **Frontend**: Node.js 18+, React (npm)
- **Database**: MongoDB (Local or in-memory fallback), ChromaDB (Vector Store)
- **AI Integration**: Groq API (Optional)

## 📥 Setup & Run

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- *(Optional)* MongoDB on `localhost:27017`
- *(Optional)* Groq API Key

### 2. Environment Variables
Copy the template to create your `.env` file in the `backend/` directory:
```powershell
cd backend
copy .env.example .env
```
Configure your `GROQ_API_KEY` or leave it empty to use the offline simulator.

### 3. Start the Backend & Frontend
**Backend (Terminal 1):**
```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
**Frontend (Terminal 2):**
```powershell
cd frontend
npm install
npm run dev
```

### 4. Run Automated Attacks
**Attack Scripts (Terminal 3):**
```powershell
powershell -ExecutionPolicy Bypass -File .\demo-payloads\attack1-demo.ps1 -NoPause
```

## 📜 Development & Testing Notes
- **Urls**: Frontend (`http://localhost:5173`), Backend (`http://localhost:8000`), Docs (`http://localhost:8000/docs`).
- **Demo Users**: `u_tanush`, `u_anon` (tenant_acme); `u_aishwarya` (tenant_globex).
- **Tests**: Run `python -m pytest tests/ -q` inside the `backend` directory.

> **Note:** Never put real production credentials in `DEMO_*` keys. They are purely for demonstrating data leakage vs blocking in the lab.

---
*Created by Aishwarya Achari*
