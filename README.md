# BigQuery Release Radar & Tweet Composer 🚀

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-BigQuery-4285F4.svg)](https://cloud.google.com/bigquery)
[![X / Twitter](https://img.shields.io/badge/X%20(Twitter)-Intent%20API-000000.svg)](https://x.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An elegant, dark-themed, glassmorphic web application that parses Google Cloud's official BigQuery Release Notes Atom feed, structures daily release dumps into individual actionable updates, provides instant client-side filtering and search, and includes a smart character-counted tweet composer to broadcast updates to X (Twitter).

> **Origin & Workshop Context**: Developed as part of the **Google x Kaggle AI Course / Agents Workshop**, demonstrating real-time data ingestion, resilient caching, and automated developer tooling.

---

<p align="center">
  <img src="static/images/screenshot.jpg" alt="BigQuery Release Radar Dashboard" width="850"/>
</p>

---

## Key Features

* **🔄 Live Feed Ingestion & Multi-Tier Caching**:
  * Directly parses Google Cloud's official BigQuery Atom/XML feed (`https://docs.cloud.google.com/feeds/bigquery-release-notes.xml`).
  * Features dual-tier caching (in-memory TTL + persistent disk fallback) to guarantee 100% uptime even during network downtime.
  * Automatic retry strategies using HTTP connection pooling.
* **📊 Granular Release Decomposition**:
  * Instead of monolithic daily release dumps, splits multi-feature updates by header categories (`Feature`, `Announcement`, `Changed`, `Deprecation`, `Issue / Fix`).
  * Enforces safe link rewriting (`target="_blank"` and `rel="noopener noreferrer"`).
* **⚡ Instant Client-Side Search & Tag Filtering**:
  * Type-ahead search matching across dates, feature descriptions, and categories.
  * Dynamic pill filters for quick category exploration.
* **🐦 Integrated X (Twitter) Composer**:
  * One-click "Tweet This Update" modal pre-formats concise, formatted tweets with hashtags (`#BigQuery #GCP #DataWarehouse`).
  * Exact Twitter character calculation (treating all URLs as 23 characters per Twitter `t.co` specifications).
  * 280-character limit enforcement with visual warnings and safety button locks.
  * Direct "Post to X" redirection via Web Intent API and instant "Copy to Clipboard" support.
* **📈 Real-Time Dashboard Analytics**:
  * Live counters displaying total updates, feature releases, announcements, and deprecations with smooth numerical count-up animations.
* **📥 CSV Export Utility**:
  * One-click export of filtered release notes to timestamped CSV files.
* **🌓 Modern Glassmorphic Aesthetics**:
  * Dark mode by default with radial glow orbs, glassmorphism cards, and fluid light/dark mode toggling persisted in `localStorage`.

---

## System Architecture

```
Google Cloud BigQuery Atom Feed (XML)
                │
                ▼
      [ Requests Session ]  (Retries & Connection Pooling)
                │
                ▼
     [ BeautifulSoup Parser ] ──► Extracts entries, splits <h3> headers, sanitizes links
                │
        ┌───────┴────────┐
        ▼                ▼
 [ In-Memory Cache ]  [ Persistent Disk Cache ] (data/feed_cache.json)
        │
        ▼
   [ Flask API ] ───────► GET /api/releases
                          GET /health
                          GET /
        │
        ▼
 [ Glassmorphic UI ] ───► Real-Time Search, Filters, CSV Export, X (Twitter) Composer
```

---

## Technical Stack

* **Backend**: Python 3.9+, Flask, Requests, BeautifulSoup4, Gunicorn
* **Frontend**: Vanilla HTML5, CSS3 (Custom Glassmorphism, CSS Grid, Variables), Modern ES6+ JavaScript
* **Typography**: Plus Jakarta Sans (UI), Space Grotesk (Metrics), JetBrains Mono (Code)
* **Containerization**: Docker, Docker Compose

---

## Directory Structure

```bash
bigquery-release-radar/
├── data/                            # Persistent feed cache fallback
│   └── feed_cache.json
├── static/
│   ├── css/
│   │   └── style.css                # Glassmorphic themes, animations & responsive layout
│   ├── images/
│   │   └── screenshot.jpg           # Application preview screenshot
│   └── js/
│       └── main.js                  # Frontend state, filters, search, Twitter intent logic
├── templates/
│   └── index.html                   # Dashboard shell and composer modal
├── .dockerignore                    # Docker build ignore rules
├── .env.example                     # Environment configuration template
├── .gitignore                       # Python and macOS git ignore rules
├── app.py                           # Optimized Flask backend server & feed parser
├── Dockerfile                       # Multi-stage production container
├── docker-compose.yml               # Single-command container deployment
├── requirements.txt                 # Clean project dependencies
└── README.md                        # Documentation
```

---

## Installation & Quickstart

### Option 1: Local Python Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/RJ1899157/bigquery-release-radar.git
   cd bigquery-release-radar
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # On macOS / Linux:
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows:
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the server:**
   ```bash
   python app.py
   ```
   *Dashboard will be available at:* **[http://localhost:5001](http://localhost:5001)**

---

### Option 2: Docker & Docker Compose

Run the entire application in an isolated container:

```bash
docker compose up --build
```
*Access the app at:* **[http://localhost:5001](http://localhost:5001)**

To run in the background:
```bash
docker compose up -d
```

---

## API Reference

### `GET /api/releases`
Fetches structured release note items.

**Query Parameters:**
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `refresh` | `boolean` | `false` | If `true`, bypasses cache and forces live re-sync |
| `category` | `string` | `""` | Filter by category (e.g. `feature`, `announcement`, `deprecation`) |
| `q` | `string` | `""` | Search query across update text, date, and type |

**Sample Response:**
```json
{
  "success": true,
  "total_count": 63,
  "filtered_count": 50,
  "last_updated": "2026-09-19 12:06:44 AM",
  "updates": [
    {
      "id": "tag:google.com,2026:bigquery:release-notes:2026-09-17#0",
      "date": "September 17, 2026",
      "type": "Feature",
      "html": "<p>BigQuery now supports enhanced...</p>",
      "text": "BigQuery now supports enhanced..."
    }
  ]
}
```

### `GET /health`
Returns application health and cache status for container probes.
```json
{
  "status": "healthy",
  "timestamp": "2026-09-18T18:36:43Z",
  "cache_entries": 63
}
```

---

## Author & License

* **Author**: [Rishabh Jain](https://github.com/RJ1899157)
* **Course Context**: Built during the **Google x Kaggle AI Course**.
* **License**: MIT License.
