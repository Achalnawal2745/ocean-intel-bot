# ARGO Ocean Intelligence System

AI-powered conversational interface for ARGO oceanographic float data.

## Features

- 🤖 **Natural Language Queries** - Ask questions in plain English
- 🗺️ **Interactive Maps** - Visualize float trajectories and locations
- 📊 **Dynamic Charts** - Compare temperature, salinity, and other parameters
- 💾 **Automated Data Pipeline** - Download and ingest NetCDF files via HTTP
- 🧠 **3-Layer AI System** - Intelligent query processing with Gemini 2.5 Flash

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:
```
DATABASE_URL=postgresql://user:password@localhost:5432/argo_db
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 3. Start the System

**Windows:**
```bash
start.bat
```

**Manual:**
```bash
# Terminal 1 - Backend
python -m uvicorn backend16:app --reload

# Terminal 2 - Frontend
streamlit run app.py
```

## Usage

### Web Interface

1. Open http://localhost:8501
2. Ask questions like:
   - "Show floats in Indian Ocean"
   - "Compare salinity for floats 1902669 and 1902670"
   - "Temperature depth profile for float 2900565"

### Add New Floats

Use the Admin panel in the sidebar:
1. Enter float ID (e.g., 2900565)
2. Click "Download & Ingest"
3. Wait for confirmation

Or use command line:
```bash
# Download
curl -X POST http://127.0.0.1:8000/admin/download-float -H "Content-Type: application/json" -d '{"float_id": "2900565"}'

# Ingest
curl -X POST http://127.0.0.1:8000/admin/ingest-float -H "Content-Type: application/json" -d '{"float_id": "2900565"}'
```

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │ ← User Interface
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  FastAPI Backend│ ← REST API
└────────┬────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐ ┌──────────┐
│Gemini  │ │PostgreSQL│
│AI      │ │Database  │
└────────┘ └──────────┘
```

## Project Structure

```
ocean-intel-bot/
├── app.py                 # Streamlit frontend
├── backend16.py           # FastAPI backend
├── argo_ingestion.py      # Data ingestion module
├── download_floats.py     # Download script
├── ingest_floats.py       # Ingestion script
├── requirements.txt       # Dependencies
├── start.bat             # Startup script
└── .env                  # Environment variables
```

## API Endpoints

### Query
```
POST /query
Body: {"query": "show floats in indian ocean"}
```

### Admin - Download Float
```
POST /admin/download-float
Body: {"float_id": "2900565"}
```

### Admin - Ingest Float
```
POST /admin/ingest-float
Body: {"float_id": "2900565"}
```

### Health Check
```
GET /health
```

## Technologies

- **Backend**: FastAPI, Python 3.11+
- **Frontend**: Streamlit, Folium, Plotly
- **Database**: PostgreSQL, ChromaDB
- **AI**: Google Gemini 2.5 Flash
- **Data**: ARGO NetCDF files (HTTP download)

## License

MIT License

## Contact

For questions or issues, please open an issue on GitHub.
