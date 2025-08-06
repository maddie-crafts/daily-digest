# Daily Digest

A Python-based article aggregator that fetches, processes, and displays news articles from multiple sources. The system includes web scraping, data processing, ML-powered sentiment analysis, and a FastAPI-based web interface.

## Features

- **Multi-Source Daily Digest**: Scrapes from 6 major news sources (BBC, Guardian, NPR, AP News, TechCrunch, Ars Technica)
- **Automated Scheduling**: Configurable scraping intervals with APScheduler
- **ML-Powered Analysis**: Sentiment analysis using VADER and TextBlob
- **Text Summarization**: Automatic content summarization
- **Trend Detection**: Identify trending topics and keywords
- **Web Interface**: FastAPI-based dashboard with search and filtering
- **Email Notifications**: Daily digest and trending topic alerts
- **Data Export**: CSV export functionality
- **Duplicate Detection**: Content similarity matching to avoid duplicates

## Architecture

```
daily-digest/
├── src/
│   ├── scraper/          # Web scraping components
│   │   ├── base_scraper.py
│   │   ├── news_sources.py
│   │   └── content_extractor.py
│   ├── processor/        # Text processing & ML
│   │   ├── sentiment_analyzer.py
│   │   ├── summarizer.py
│   │   ├── text_processor.py
│   │   └── trending_analyzer.py
│   ├── storage/          # Database layer
│   │   ├── database.py
│   │   └── models.py
│   ├── web/              # FastAPI web interface
│   │   ├── app.py
│   │   └── templates/
│   └── utils/            # Configuration & services
│       ├── config.py
│       ├── email_service.py
│       └── export_service.py
├── data/                 # SQLite database
├── tests/               # Test suite
├── config.yaml         # Configuration file
└── main.py            # Application entry point
```

## Quick Start

### Prerequisites

- Python 3.11+
- uv (recommended) or pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd daily-digest
```

2. Install dependencies:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

3. Configure the application:
   - Review `config.yaml` and adjust settings as needed
   - For email notifications, configure SMTP settings in the email section

### Running the Application

```bash
# Run the complete application (web server + scheduler)
python main.py

# Or using uv
uv run python main.py
```

The web interface will be available at `http://127.0.0.1:8000`

## Configuration

The application is configured via `config.yaml`:

### News Sources
Currently configured sources:
- **General News**: BBC News, Guardian, NPR, AP News
- **Technology**: TechCrunch, Ars Technica

Each source includes:
- CSS selectors for content extraction
- Rate limiting settings
- Maximum articles per scrape

### Key Settings
- **Scraping**: Rate limits, user agent, timeout settings
- **Processing**: Content length thresholds, sentiment analysis parameters
- **Database**: SQLite path and retention policies
- **Web**: Server host, port, pagination settings
- **Email**: SMTP configuration for notifications

## API Endpoints

The FastAPI application provides:

- `GET /` - Main dashboard
- `GET /api/articles` - List articles with pagination and filtering
- `GET /api/articles/{id}` - Get specific article
- `GET /api/sources` - List news sources and status
- `GET /api/analytics/trends` - Trending topics analysis
- `POST /api/scrape` - Manually trigger scraping
- `GET /api/export/csv` - Export articles to CSV

## Development

### Testing

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest --cov=src tests/

# Run specific test file
uv run pytest tests/test_scraper.py
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Check linting
uv run ruff check src/ tests/
```

### Development Server

For development with auto-reload:
```bash
uvicorn src.web.app:app --reload --host 127.0.0.1 --port 8000
```

## Database Schema

### Articles Table
- `id`, `title`, `content`, `summary`, `url`
- `source`, `published_date`, `scraped_date`
- `sentiment_score`, `sentiment_label`, `category`
- `keywords`, `author`

### Sources Table
- `id`, `name`, `base_url`, `scraping_config`
- `last_scraped`, `is_active`, `success_count`, `error_count`

## Technologies Used

- **Python 3.11+**: Core language
- **FastAPI**: Web framework and API
- **BeautifulSoup4**: HTML parsing and scraping
- **SQLite**: Database storage
- **APScheduler**: Task scheduling
- **NLTK/TextBlob/VADER**: Natural language processing
- **Pandas/NumPy**: Data processing
- **Jinja2**: Template rendering

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite and ensure all tests pass
6. Submit a pull request