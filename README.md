<div align="center">

# ⚡ AIDE
### Adaptive Intelligence Data Engine

**A zero-cost, fully automated AI signal intelligence pipeline.**  
Crawls → Scores → Classifies → Delivers the most relevant AI/ML/tech signals, 24/7, for free.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![Vercel](https://img.shields.io/badge/Deployed-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://aide-dashboard.vercel.app)
[![GitHub Actions](https://img.shields.io/badge/Automated-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Cost](https://img.shields.io/badge/Monthly_Cost-$0.00-brightgreen?style=flat-square)](https://github.com/Peepeepoopookk/AIDE)

**[🌐 Live Dashboard](https://aide-dashboard.vercel.app)** · **[📖 Documentation](#setup--installation)** · **[🗺️ Roadmap](#roadmap)**

---

*Built by a college student in Kerala, India — with zero budget and full automation.*

</div>

---

## Table of Contents

- [What is AIDE?](#what-is-aide)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Signal Sources](#signal-sources)
- [LLM Pipeline](#llm-pipeline)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [Supabase Schema](#supabase-schema)
- [Environment Variables](#environment-variables)
- [GitHub Actions Automation](#github-actions-automation)
- [Project Structure](#project-structure)
- [Dashboard](#dashboard)
- [Telegram Bot](#telegram-bot)
- [Cold Storage](#cold-storage)
- [Roadmap](#roadmap)
- [License](#license)

---

## What is AIDE?

AIDE is a **personal signal intelligence system** — a private feed that automatically monitors the AI and tech landscape and surfaces only what matters.

Every 4 hours, AIDE:
1. **Crawls** 6 major sources across 20+ endpoints
2. **Deduplicates** using URL hashing and fuzzy string matching
3. **Classifies** each signal by category, language, and tags
4. **Scores** it across 5 dimensions: relevance, novelty, hype, impact, and confidence
5. **Summarizes** high-value signals and performs deep analysis on top-tier ones
6. **Delivers** results via a live dashboard and a Telegram bot

The entire system runs **24/7 at zero cost** using free tiers of GitHub Actions, Supabase, Vercel, Groq, Cerebras, Mistral, and OpenRouter.

---

## Key Features

| Feature | Description |
|---|---|
| 🕷️ **6-Source Crawler** | HN, arXiv, GitHub Trending, Reddit, Dev.to, Medium |
| 🧠 **Multi-LLM Router** | 5-provider fallback chain with automatic failover |
| 📊 **5-Dimension Scoring** | Relevance · Novelty · Hype · Impact · Confidence |
| 🔍 **Smart Deduplication** | URL hash + RapidFuzz fuzzy matching (85% threshold) |
| 🗃️ **Automated Retention** | 45-day rolling window with weekly cleanup |
| 🗄️ **Cold Storage Archive** | Monthly Google Drive gzip backup of expired signals |
| 📱 **Telegram Bot** | `/top`, `/summary`, `/search` command interface |
| 🖥️ **Live Dashboard** | Server-side pagination, filters, search, and sort |
| ⚙️ **Zero Maintenance** | Fully automated via GitHub Actions cron schedules |
| 💸 **Zero Cost** | 100% free-tier stack — no credit card ever required |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SIGNAL SOURCES                           │
│   Hacker News · arXiv · GitHub Trending · Reddit · Dev.to · Medium │
└──────────────────────────────┬──────────────────────────────────┘
                               │  Every 4 hours (GitHub Actions)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CRAWL LAYER                                │
│                  pipeline/run_pipeline.py                       │
│                                                                 │
│  • Fetches raw content from all 6 sources in sequence           │
│  • Generates URL hash for deduplication                         │
│  • RapidFuzz fuzzy match against title cache (85% threshold)    │
│  • Saves unique signals to Supabase                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │  New unscored signals
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SCORING LAYER                              │
│                   aide_router/pipeline.py                       │
│                    (Runs 30min after crawl)                     │
│                                                                 │
│  For each signal (batch of 200):                                │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────────┐  │
│  │  CLASSIFY   │ → │    SCORE     │ → │     SUMMARIZE       │  │
│  │  category   │   │  relevance   │   │  (all signals)      │  │
│  │  tags       │   │  novelty     │   └─────────────────────┘  │
│  │  language   │   │  hype        │   ┌─────────────────────┐  │
│  │  is_relevant│   │  impact      │ → │      ANALYZE        │  │
│  └─────────────┘   │  confidence  │   │  (score >= 7 only)  │  │
│                    └──────────────┘   └─────────────────────┘  │
│                                                                 │
│  LLM Fallback Chain:                                            │
│  groq_fast → cerebras → groq_strong → mistral → openrouter     │
└──────────────────────────────┬──────────────────────────────────┘
                               │  Scored + classified signals
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                              │
│                    Supabase (PostgreSQL)                        │
│                                                                 │
│  • RLS-enabled signals table                                    │
│  • 45-day retention (weekly cleanup workflow)                   │
│  • Monthly cold archive → Google Drive (.json.gz)              │
└──────────────┬──────────────────────────┬───────────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────┐    ┌─────────────────────────────────────┐
│    TELEGRAM BOT      │    │           DASHBOARD                 │
│  bot/telegram_bot.py │    │    aide-dashboard.vercel.app        │
│                      │    │                                     │
│  /top   — top picks  │    │  • Server-side pagination (100/pg)  │
│  /summary — digest   │    │  • Source + category filters        │
│  /search — search    │    │  • Full-text search                 │
└──────────────────────┘    │  • Sort by score or recency        │
                            │  • Live stats bar                   │
                            └─────────────────────────────────────┘
```

---

## Signal Sources

AIDE monitors **6 sources** across **20+ endpoints**, covering the full breadth of the AI/ML/tech landscape:

| Source | Coverage | Endpoints |
|---|---|---|
| **Hacker News** | Top stories, Ask HN, Show HN | HN Algolia API |
| **arXiv** | AI, ML, CV, NLP, CS research papers | arXiv RSS feeds |
| **GitHub Trending** | Trending repos by language and date range | 12 URL variations |
| **Reddit** | Community discussions and announcements | r/MachineLearning, r/LocalLLaMA, r/programming, r/artificial |
| **Dev.to** | Developer articles and tutorials | Tags: ai, machinelearning, python, webdev |
| **Medium** | Long-form tech articles | Tags: artificial-intelligence, machine-learning, python, programming |

---

## LLM Pipeline

AIDE uses a **5-provider fallback chain** to guarantee uptime and zero cost. Each provider is tried in order; if one fails or hits a rate limit, the next takes over automatically.

```
Task: CLASSIFY
  └─→ groq_fast (llama-3.1-8b-instant)
        └─→ cerebras (fallback)
              └─→ mistral (fallback)
                    └─→ openrouter (final fallback)

Task: SCORE / SUMMARIZE / ANALYZE
  └─→ groq_strong (llama-3.3-70b-versatile)
        └─→ cerebras (fallback)
              └─→ mistral (fallback)
                    └─→ openrouter (final fallback)
```

**Scoring dimensions** (each 0–10):

| Dimension | What it measures |
|---|---|
| `relevance` | How relevant to AI/ML/tech landscape |
| `novelty` | Is this genuinely new information? |
| `hype` | Community excitement and traction |
| `impact` | Potential real-world significance |
| `confidence` | LLM's confidence in its own scoring |

**Final score:** `score_weighted = relevance × confidence / 10`

Signals scoring **≥ 7** receive an additional deep analysis pass covering implications, key entities, and recommended follow-up.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Language** | Python 3.11 | Crawlers, pipeline, bot |
| **Frontend** | Next.js 15 + React | Dashboard UI |
| **Database** | Supabase (PostgreSQL) | Free-tier, RLS, real-time |
| **Automation** | GitHub Actions | Free cron scheduling |
| **Hosting** | Vercel | Free-tier Next.js deployment |
| **LLM: Fast** | Groq (llama-3.1-8b-instant) | Classify tasks — ultra-fast |
| **LLM: Strong** | Groq (llama-3.3-70b-versatile) | Score, summarize, analyze |
| **LLM: Fallback 1** | Cerebras | Fast secondary fallback |
| **LLM: Fallback 2** | Mistral | Tertiary fallback |
| **LLM: Fallback 3** | OpenRouter | Final fallback |
| **Deduplication** | RapidFuzz | Fuzzy title matching |
| **HTML Parsing** | BeautifulSoup4 | Content extraction |
| **Cold Storage** | Google Drive API | Monthly archive |
| **Delivery** | Telegram Bot API | Push notifications |

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- A free [Supabase](https://supabase.com) account
- Free API keys from [Groq](https://groq.com), [Cerebras](https://cerebras.ai), [Mistral](https://mistral.ai), [OpenRouter](https://openrouter.ai)
- A [Telegram bot token](https://core.telegram.org/bots#how-do-i-create-a-bot)

### Step 1 — Clone the repository

```bash
git clone https://github.com/Peepeepoopookk/AIDE.git
cd AIDE
```

### Step 2 — Create virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

See the [Environment Variables](#environment-variables) section for a full reference.

### Step 5 — Set up Supabase

Create a new Supabase project and run the schema SQL from the [Supabase Schema](#supabase-schema) section. Then add the three RLS policies.

### Step 6 — Run locally

```bash
# Run all 6 crawlers
python pipeline/run_pipeline.py

# Run the scoring pipeline (processes 50 signals)
python -m aide_router.pipeline 50

# Run the Telegram bot
python bot/telegram_bot.py
```

### Step 7 — Set up GitHub Actions

Add all environment variables as **repository secrets** under:  
`Settings → Secrets and variables → Actions → New repository secret`

The three workflow files in `.github/workflows/` will handle everything automatically from here.

---

## Supabase Schema

Run this SQL in your Supabase SQL editor to create the signals table:

```sql
CREATE TABLE public.signals (
    id            uuid                     NOT NULL,
    title         text                     NULL,
    url           text                     NULL,
    source        text                     NULL,
    raw_content   text                     NULL,
    crawled_at    timestamp with time zone NULL,
    url_hash      text                     NULL,
    scored        boolean                  NULL DEFAULT false,
    classification jsonb                   NULL,
    score_data    jsonb                    NULL,
    summary_data  jsonb                    NULL,
    analysis_data jsonb                    NULL,
    score_weighted double precision        NULL,
    score_total   double precision         NULL,
    relevance     double precision         NULL,
    score_novelty double precision         NULL,
    score_hype    double precision         NULL,
    score_impact  double precision         NULL,
    score_confidence double precision      NULL,
    category      text                     NULL,
    tags          text[]                   NULL,
    CONSTRAINT signals_pkey PRIMARY KEY (id)
);
```

Then add the required **Row Level Security (RLS)** policies:

```sql
-- Enable RLS
ALTER TABLE public.signals ENABLE ROW LEVEL SECURITY;

-- Allow anonymous reads
CREATE POLICY "Public read access"
ON public.signals FOR SELECT TO anon USING (true);

-- Allow anonymous inserts
CREATE POLICY "Allow anon inserts"
ON public.signals FOR INSERT TO anon WITH CHECK (true);

-- Allow anonymous updates (required for scoring pipeline)
CREATE POLICY "Allow anon updates"
ON public.signals FOR UPDATE TO anon USING (true) WITH CHECK (true);
```

> ⚠️ The UPDATE policy is **critical**. Without it, the scoring pipeline will classify and score signals silently but fail to save results back to the database.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | ✅ | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon key (public, safe for free-tier use with RLS) |
| `GROQ_API_KEY` | ✅ | Groq API key (primary LLM provider) |
| `CEREBRAS_API_KEY` | ✅ | Cerebras API key (fast fallback) |
| `MISTRAL_API_KEY` | ✅ | Mistral API key (tertiary fallback) |
| `OPENROUTER_API_KEY` | ✅ | OpenRouter API key (final fallback) |
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | Your Telegram chat or channel ID |
| `GDRIVE_FOLDER_ID` | Optional | Google Drive folder ID for cold storage |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | Optional | Full JSON of Google Drive service account |

---

## GitHub Actions Automation

AIDE is fully automated. Once secrets are configured, no manual intervention is needed.

### `crawl_signals.yml` — Runs every 4 hours
```yaml
cron: "0 */4 * * *"
command: python pipeline/run_pipeline.py
```
Executes all 6 crawlers sequentially. New signals are deduplicated and saved to Supabase.

### `score_signals.yml` — Runs 30 minutes after crawl
```yaml
cron: "30 */4 * * *"
command: python -m aide_router.pipeline 200
timeout: 25 minutes
```
Picks up the latest unscored signals in batches of 200. Classifies, scores, summarizes, and analyzes each one using the LLM fallback chain.

### `cleanup_signals.yml` — Runs weekly
```yaml
cron: "0 3 * * 0"
```
Deletes signals older than 45 days that have already been archived to cold storage.

### `cold_storage.yml` — Runs on the 1st of every month
```yaml
cron: "0 2 1 * *"
command: python -m pipeline.cold_storage
```
Archives signals older than 45 days as a compressed gzip JSON file (`aide_archive_YYYY_MM.json.gz`) to Google Drive.

---

## Project Structure

```
AIDE/
│
├── .github/
│   └── workflows/
│       ├── crawl_signals.yml      # Crawler cron (every 4h)
│       ├── score_signals.yml      # Scoring cron (30min after crawl)
│       ├── cleanup_signals.yml    # 45-day retention cleanup
│       └── cold_storage.yml       # Monthly Google Drive archive
│
├── aide_router/
│   ├── llm/
│   │   ├── config.py              # Provider config & fallback order
│   │   ├── router.py              # LLM routing logic
│   │   ├── scorer.py              # Score signals (5 dimensions)
│   │   ├── classifier.py          # Classify signals
│   │   └── summarizer.py          # Summarize & analyze signals
│   └── pipeline.py                # Main scoring pipeline entry point
│
├── crawlers/
│   ├── hn_crawler.py              # Hacker News
│   ├── arxiv_crawler.py           # arXiv research papers
│   ├── github_crawler.py          # GitHub Trending (12 endpoints)
│   ├── reddit_crawler.py          # Reddit (4 subreddits)
│   ├── devto_crawler.py           # Dev.to (4 tags)
│   └── medium_crawler.py          # Medium RSS (4 tags)
│
├── db/
│   └── supabase_client.py         # Supabase client, save_signal(), deduplication
│
├── pipeline/
│   ├── run_pipeline.py            # Orchestrates all 6 crawlers
│   └── cold_storage.py            # Google Drive archive logic
│
├── bot/
│   └── telegram_bot.py            # Telegram bot (/top, /summary, /search)
│
├── utils/
│   ├── logger.py                  # Rotating file logger
│   ├── retry.py                   # Retry with exponential backoff + jitter
│   ├── config_validator.py        # Startup environment validation
│   └── task_manager.py            # TaskManager singleton
│
├── .env                           # Local secrets (never commit)
├── .env.example                   # Environment variable template
├── gdrive_service_account.json    # GDrive service account (never commit)
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## Dashboard

**Live at: [aide-dashboard.vercel.app](https://aide-dashboard.vercel.app)**

The dashboard is a Next.js 15 application with a pure black glassmorphism design.

**Features:**
- **Stats bar** — Total signals ever ingested, total relevant/scored signals, per-source counts
- **Collapsible sidebar** — Dynamic source and category filters
- **Server-side pagination** — 100 signals per page, all filtering pushed to Supabase
- **Search** — Full-text search across title, URL, and content
- **Sort** — By weighted score (descending) or crawl time (newest first)
- **Signal cards** — Show title, source, score, category, tags, summary, and analysis

All filtering, searching, and sorting happens in the Supabase query layer — no client-side filtering.

---

## Telegram Bot

The bot delivers signals directly to your Telegram chat.

| Command | Description |
|---|---|
| `/top` | Shows the top 10 highest-scored signals from the last 24 hours |
| `/summary` | Sends a digest of today's classified signals by category |
| `/search <query>` | Searches the database for signals matching the query |

---

## Cold Storage

Signals older than 45 days are archived monthly to Google Drive as compressed gzip JSON files.

**Archive format:** `aide_archive_YYYY_MM.json.gz`  
**Storage:** Google Drive folder (2TB personal drive)  
**Method:** Google Drive API via service account

Each archive file contains the full signal record including all scoring, classification, summary, and analysis data.

---

## Roadmap

### Near-term
- [ ] Dashboard auto-refresh (poll for new signals every 5 minutes)
- [ ] Telegram bot source filters (filter by reddit / devto / medium)
- [ ] Budget data push to Supabase (track LLM token usage in DB)

### Additional Crawlers
- [ ] YouTube RSS crawler (channel feeds for AI/ML channels)
- [ ] Papers With Code crawler (state-of-the-art benchmarks)
- [ ] Lobste.rs crawler (niche tech community)

### Intelligence Features
- [ ] **Trend Detection** — Alert when a topic spikes 5× in 24 hours
- [ ] **Semantic Search** — ChromaDB vector embeddings for meaning-based search
- [ ] **Entity Extraction** — Index companies, models, and people mentioned in signals
- [ ] **Topic Clustering** — Auto-group signals by theme on the dashboard
- [ ] **Signal Timeline** — Visualize topic velocity over time

### Stock Prediction Integration
AIDE is being integrated with a local FinBERT + XGBoost stock prediction platform targeting NSE/BSE markets.

- [ ] Indian financial news crawlers (Economic Times, Moneycontrol, Business Standard, Livemint, NSE/BSE RSS)
- [ ] Ticker-to-keyword mapper (signal mentions → NSE ticker symbols)
- [ ] Per-ticker sentiment aggregation (bullish/bearish/neutral signal counts)
- [ ] AIDE-derived XGBoost features: `signal_count`, `avg_aide_score`, `signal_velocity`
- [ ] `signal_velocity` — rate of change in ticker mentions — key leading indicator of price volatility

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with 0 dollars and a lot of stubbornness.**

*Kerala, India · 2026*

</div>