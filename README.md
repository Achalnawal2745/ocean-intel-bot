# 🌊 Float Chat -ARGO OCEAN INTELLIGENCE SYSTEM

**AI-Powered Conversational Interface for ARGO Oceanographic Data**

Float Chat is an intelligent chatbot that lets you explore ocean data from ARGO floats using natural language. Ask questions in plain English and get instant visualizations, charts, and insights about ocean temperature, salinity, and float trajectories.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28-FF4B4B.svg)](https://streamlit.io/)

## ✨ Features

- 🤖 **Natural Language Queries** - Ask questions like "Show floats in Indian Ocean" or "Compare temperature of floats 1902669 and 1902670"
- 🗺️ **Interactive Maps** - Visualize float trajectories and locations with Folium
- 📊 **Dynamic Charts** - Compare temperature, salinity, pressure, and depth profiles with Plotly
- 💾 **Automated Data Pipeline** - Download and ingest ARGO NetCDF files automatically
- 🧠 **3-Layer AI System** - Intelligent query routing with Google Gemini 2.5 Flash
- 🎯 **Smart Query Understanding** - Handles complex multi-step queries with AI orchestration
- 📈 **Real-time Analytics** - SQL-based aggregations for statistical queries

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Google Gemini API key
- Supabase account (optional, for vector search)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/floatchat.git
   cd floatchat
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   
   Create a `.env` file in the project root:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/argo_db
   GEMINI_API_KEY=your_gemini_api_key_here
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```

4. **Start the application**
   
   **Windows:**
   ```bash
   start.bat
   ```
   
   **Linux/Mac:**
   ```bash
   # Terminal 1 - Backend
   python backend16.py
   
   # Terminal 2 - Frontend
   streamlit run app.py
   ```

5. **Open your browser**
   
   Navigate to `http://localhost:8501`

## 💬 Example Queries

Try these natural language queries:

- "Show all floats in the Indian Ocean"
- "What's the temperature profile for float 2900565?"
- "Compare salinity between floats 1902669 and 1902670"
- "Show me the path of float 2900565"
- "How many floats are in the Arabian Sea?"
- "Average temperature at 100m depth for float 2900565"

## 📖 Usage Guide

### Adding New Floats

**Via Web Interface:**
1. Open the sidebar in the Streamlit app
2. Navigate to "Admin Panel"
3. Enter the float ID (e.g., `2900565`)
4. Click "Download & Ingest"

**Via API:**
```bash
# Download float data
curl -X POST http://127.0.0.1:8000/admin/download-float \
  -H "Content-Type: application/json" \
  -d '{"float_id": "2900565"}'

# Ingest into database
curl -X POST http://127.0.0.1:8000/admin/ingest-float \
  -H "Content-Type: application/json" \
  -d '{"float_id": "2900565"}'
```

## 🏗️ Architecture

Float Chat uses a sophisticated 3-layer AI system:

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                         │
│            (Chat Interface + Visualizations)            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                        │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐       │
│  │ Layer 1  │→ │ Layer 2  │→ │    Layer 3       │       │
│  │Direct    │  │Complex   │  │SQL Generation    │       │
│  │Tool Call │  │Orchestr. │  │& Fallback        │       │
│  └──────────┘  └──────────┘  └──────────────────┘       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
┌──────────────┐          ┌──────────────┐
│  PostgreSQL  │          │ Gemini AI    │
│  Database    │          │ (2.5 Flash)  │
└──────────────┘          └──────────────┘
```

### Layer System

- **Layer 1**: Direct tool execution for simple queries (e.g., "show float 2900565")
- **Layer 2**: AI orchestration for complex multi-step queries (e.g., "temperature of all floats in Indian Ocean")
- **Layer 3**: SQL generation for analytical queries (e.g., "average temperature at 100m depth")

## 📁 Project Structure

```
float-chat/
├── app.py                 # Streamlit frontend
├── backend16.py           # FastAPI backend with 3-layer AI system
├── argo_ingestion.py      # Data ingestion module
├── download_floats.py     # Float download utility
├── ingest_floats.py       # Batch ingestion script
├── requirements.txt       # Python dependencies
├── start.bat             # Windows startup script
├── .env                  # Environment configuration
├── README.md             # This file
└── QUICKSTART.md         # Quick start guide
```

## 🔌 API Endpoints

### Query Endpoint
```http
POST /query
Content-Type: application/json

{
  "query": "show floats in indian ocean",
  "session_id": "optional-session-id"
}
```

### Admin Endpoints
```http
POST /admin/download-float
POST /admin/ingest-float
GET /health
GET /floats
```

See [API Documentation](docs/API.md) for full details.

## 🛠️ Technologies

| Category | Technologies |
|----------|-------------|
| **Backend** | FastAPI, Python 3.11+, asyncpg |
| **Frontend** | Streamlit, Folium, Plotly |
| **Database** | PostgreSQL, ChromaDB |
| **AI** | Google Gemini 2.5 Flash |
| **Data Format** | NetCDF4, ARGO float data |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- ARGO float data provided by the [ARGO Program](https://argo.ucsd.edu/)
- AI powered by [Google Gemini](https://deepmind.google/technologies/gemini/)
- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Streamlit](https://streamlit.io/)

## 📧 Contact

For questions, issues, or feature requests, please [open an issue](https://github.com/yourusername/float-chat/issues) on GitHub.

---

**Made with ❤️ for ocean data exploration**
