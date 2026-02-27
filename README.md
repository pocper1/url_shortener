# NanoLink - URL Shortener API

A modern, comprehensive URL Shortener application built with FastAPI and SQLite. Features a beautiful glassmorphic frontend UI made with Tailwind CSS, advanced click statistics tracking, and a robust test suite.

## 🌟 Features
- **FastAPI Backend**: High performance and easy-to-read asynchronous routing.
- **Auto-generated API Docs**: Built-in Swagger UI for easy endpoint testing.
- **Click Tracking**: Detailed analytics capturing click timestamps, user agent (browser/OS), and HTTP referer.
- **Ultra-Fast Redirects**: Analytics tracking is delegated to background tasks (`fastapi.BackgroundTasks`) to ensure instantaneous 302 redirects.
- **Rate Limiting**: Protects the URL generation API against abuse using `slowapi` (100 reqs/min).
- **Link Expiration**: Set an optional expiration constraint (in days) on generated links.
- **Beautiful UI**: Glassmorphic frontend included right out of the box using vanilla HTML + TailwindCSS.

---

## 🏗️ Architecture

```mermaid
graph TD
    User([User / Browser])
    
    sublayer[Frontend]
        UI[UI Dashboard (index.html, stats.html)]
    end
    
    sublayer2[Backend API (FastAPI)]
        APIShorten[POST /api/shorten]
        APIRedirect[GET /{short_code}]
        APIStats[GET /api/stats/{short_code}]
    end

    sublayer3[Data Layer (SQLite + SQLAlchemy)]
        DB[(Database)]
        TableURL[urls Table]
        TableClick[click_analytics Table]
    end

    User -->|Generates URL| UI
    User -->|Clicks Short Link| APIRedirect
    UI -->|JSON payload| APIShorten
    UI -->|Fetches Stats| APIStats
    
    APIShorten -->|Write| TableURL
    APIRedirect -->|Read| TableURL
    APIRedirect -->|Write Analytics| TableClick
    APIStats -->|Read/Join| TableURL
    APIStats -->|Read| TableClick
    
    TableURL -.-> DB
    TableClick -.-> DB
```

---

## 🛠️ Design Choices & Advanced Topics

### 1. Hash Collisions Handling (Short Code Generation)
To generate the short codes, we use `nanoid`, which is URL-friendly and highly collision-resistant. For this project, a `size=7` is used.
- **Probability of Collision**: An alphabet of 64 characters over 7 positions gives `64^7 = ~4.39 trillion` possible combinations.
- **Resolution Strategy**: Even with a low probability, a collision *can* happen. In `main.py`, the system implements a `while` loop that checks the database (`DB.query(URL).filter(URL.short_code == short_code)`). If the generated hash already exists, it simply generates a new one. In a massive scale environment, an auto-incrementing integer counter encoded into Base62 is often used instead to guarantee 0% collisions mathematically.

### 2. Database Indexing Strategy
To ensure query performance remains $O(1)$ or $O(\log n)$ as the database grows, specific indexes were applied in `models.py`:
- **`urls.id` (Primary Key)**: Clustered index by default. Used for fast foreign-key joins from the analytics table.
- **`urls.short_code` (Unique Index)**: 
  - **Why?** The most frequent operation is `GET /{short_code}`. By indexing this column (`index=True, unique=True`), the database can find the destination URL using a B-Tree search almost instantly, instead of doing a full table scan ($O(n)$).
- **`click_analytics.url_id` (Foreign Key)**: 
  - **Why?** When fetching statistics (`GET /api/stats/{short_code}`), the ORM issues a relation query to fetch all clicks where `click.url_id == url.id`. Without an index (or implicitly created by the FK constraint depending on the DB), this join would degrade substantially as clicks reach the millions.

### 3. Background Tasks for Performance
The heaviest operation during a user's redirect (`GET /{short_code}`) is extracting headers and inserting a new analytical record into the DB. Instead of blocking the HTTP response, FastAPI's `BackgroundTasks` is utilized. The API instantly triggers the 302 Redirect while the database insertion of the `ClickAnalytics` model is offloaded to a background thread, dropping response times from milliseconds to microseconds.

### 4. Application Security (Rate Limiting)
To prevent malicious scripts or botnets from flooding the database with billions of unused short URLs, the `POST /api/shorten` API is protected with `slowapi` (a limiter matching by client IP addresses). It restricts endpoint usage (currently set to 100 requests per minute), automatically rejecting abusers with an `HTTP 429 Too Many Requests` error.

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.9+

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd nano-link

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup Environment Variables
cp .env.example .env
# Edit .env and supply your database URL if needed (defaults to SQLite)
```

### 3. Running the Server
```bash
uvicorn main:app --reload --port 8000
```
> **Note**: On the very first run, SQLAlchemy will automatically create the `url_shortener.db` SQLite database file and all required tables. No manual database migration or initialization is needed!
- **UI Dashboard**: Open [http://localhost:8000](http://localhost:8000)
- **API Docs (Swagger UI)**: Open [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Running Tests
The project includes a `pytest` suite testing all API endpoints and edge cases (like 404s).
```bash
pytest test_main.py --cov=. --cov-report=term-missing
```
*Current Coverage: ~94%*

---

## 📄 API Documentation Overview

The API documentation is automatically generated by FastAPI using OpenAPI/Swagger. You can view the interactive documentation by navigating to `/docs` on the running server.

### Key Endpoints:
- **`POST /api/shorten`**
  - **Body**: `{"original_url": "https://example.com", "expires_in_days": 7}`
  - **Response**: Returns the URL object including the generated `short_code`.
- **`GET /{short_code}`**
  - **Action**: Issues a `302 Redirect` to the original URL.
  - **Side-effect**: Records a click in the `click_analytics` table.
- **`GET /api/stats/{short_code}`**
  - **Response**: Returns the URL metadata along with an array of related `ClickAnalytics` objects.
