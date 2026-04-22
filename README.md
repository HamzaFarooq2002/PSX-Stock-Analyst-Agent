---
title: PSX Stock Analyst Agent
emoji: 📈
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: "1.56.0"
python_version: "3.11"
app_file: app.py
pinned: false
---


# PSX Stock Analyst Agent

An AI assistant specialized in the **Pakistan Stock Exchange (PSX)**. Built using the Google Agent Development Kit (ADK), Gemini, and Streamlit. This tool can fetch live stock prices, analyze fundamentals, collect recent news, and perform side-by-side comparisons of multiple companies.

URL: https://hamzafin-psx-stock-analyst-agent.hf.space

## Features
- **Live Stock Quotes:** Current prices, day changes, and 52-week highs/lows.
- **Fundamentals Analysis:** PE ratios, EPS, ROE, margins, and dividend yields.
- **News Sentiment:** Aggregates recent headlines for context.
- **Stock Comparison:** Side-by-side data tables for sector competitors.
- **Built-in Safety:** Rate limits and session management included.

## Tech Stack
- Google ADK (Agent Development Kit) v0.x
- Google Gemini 2.0 Flash (`google-genai`)
- Streamlit v1.40+
- Yahoo Finance (via `yfinance` open source Library)

## Local Setup

Requires Python 3.9+

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/stock-analyst-agent.git
cd stock-analyst-agent
```

2. **Create a virtual environment and install dependencies:**
```bash
python -m venv .venv
.venv\Scripts\activate   # On Windows
source .venv/bin/activate # On Mac/Linux
pip install -r requirements.txt
```

3. **Configure Environment Variables:**
Copy the `.env.example` file to create an active `.env` config.
Your `.env.example` should contain:
```toml
GOOGLE_API_KEY = ""
GOOGLE_GENAI_USE_VERTEXAI = "FALSE"
```
```bash
cp .env.example .env
```
Inside `.env`, insert your `GOOGLE_API_KEY`.

4. **Run the Application:**
```bash
streamlit run app.py
```

## Streamlit Cloud Deployment

Currently, this application is optimized for Streamlit Community Cloud.

1. Push your repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io) and click "New app".
3. Select your repository and `app.py` as the main file path.
4. **Important:** Add your API keys via the Streamlit Secrets UI. Go to _Settings -> Secrets_ and paste:
   ```toml
   GOOGLE_API_KEY = "your-api-key-here"
   GOOGLE_GENAI_USE_VERTEXAI = "FALSE"
   ```
5. Click Deploy.

## Rate Limiting Note
The live application contains session-based rate limiting to prevent API abuse:
- Maximum of 20 queries per session per day.
- A 5-second cooldown between successive queries.

## Known Limitations
- 52-week high/low values may vary slightly from PSX official figures 
  due to corporate action adjustments in Yahoo Finance historical data.
