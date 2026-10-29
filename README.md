# Ratio Backend Engine 🏋️‍♂️⚡

> A high-precision, asynchronous FastAPI service driving automated workout double-progression logic, TDEE macro coaching, and multi-source nutrition logging via Telegram Webhooks.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Groq AI](https://img.shields.io/badge/Groq_LLM-F05032?style=for-the-badge&logo=git&logoColor=white)](https://groq.com/)
[![Telegram Webhook](https://img.shields.io/badge/Telegram_Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)

---

## 🌐 Live API & Integration
* **API Documentation (Swagger):** [https://your-render-app.onrender.com/docs](https://your-render-app.onrender.com/docs)
* **Frontend Web Dashboard:** [https://your-dashboard-domain.com](https://your-dashboard-domain.com)

---

## 🎯 Problem & Solution

### The Problem
Traditional fitness and nutrition tracking applications suffer from excessive tracking friction, lack intelligent double-progression set recommendation logic for hypertrophy, and offer rigid, manual macro target calculations that ignore physiological body composition updates.

### The Solution
Ratio Backend serves as an automated, event-driven orchestration system. It processes conversational workout logs and meal entries directly inside Telegram using structured LLM schema parsing (Groq/Llama-3), calculates individualized TDEE targets based on InBody composition data, enforces automated set-by-set double progression recommendations, and syncs asynchronously to Supabase for real-time frontend visualization.

---

## 🏗️ System Architecture & Data Flow

```
                                 ┌────────────────┐
                                 │  Telegram API  │
                                 └───────┬────────┘
                                         │ (HTTPS Webhook)
                                         ▼
┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
│   USDA FDC API  │ ◄────────── │   FastAPI Core  │ ──────────► │  Groq LLM Engine│
└─────────────────┘ (Search)    └────────┬────────┘ (Schema)   └─────────────────┘
                                         │
                                         │ (Async DB Operations)
                                         ▼
                                ┌─────────────────┐
                                │  Supabase DB    │
                                └─────────────────┘
```

* **Webhook Handling & Asynchronous Processing:** FastAPI processes incoming Telegram updates concurrently. Long-running tasks, such as rest-timer reminders, are managed via FastAPI `BackgroundTasks`.
* **Structured Data Extraction:** Raw natural-language meal strings and workout sets are constrained into Pydantic models (`FoodStructure` and `WorkoutStructure`) via JSON-schema enforcement on Groq LLM completions.
* **Double Progression Engine:** Evaluates past historical exercise volume from Supabase (`exercise_logs`) against target rep-caps to determine load adjustments, Reverse Pyramid Training (RPT) drops, or deload phase triggers.
* **TDEE & Macro Calculations:** Dynamically derives Basal Metabolic Rate (BMR) from InBody body composition metrics and applies activity multipliers (1.55 baseline) for personalized surplus/deficit calculations.
* **Time Zone Isolation:** All timestamps are standardized using IANA time zones (`America/Chicago`) to guarantee seamless day-boundary management between backend logging and client interfaces.

---

## 🛠️ Local Setup Instructions

### Prerequisites
* Python 3.10+
* Virtual Environment Tool (`venv`)
* Active API keys for **Supabase**, **Telegram Bot Father**, **Groq**, and **USDA FDC**.

### Step 1: Clone Repository
```bash
git clone https://github.com/your-username/fitness-bot-backend.git
cd fitness-bot-backend
```

### Step 2: Create & Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create a `.env` file in the root directory matching the provided template:
```env
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
TELEGRAM_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
USDA_API_KEY=your_usda_api_key
```

### Step 5: Start the Local Development Server
```bash
uvicorn chatbot:app --reload --port 8000
```
Access the interactive Swagger API documentation at `http://localhost:8000/docs`.