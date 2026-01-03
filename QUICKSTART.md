# 🚀 Float Chat - Quick Start Guide

## Start the System

### Option 1: Automatic (Recommended)
```bash
start.bat
```

### Option 2: Manual
```bash
# Terminal 1 - Backend
python -m uvicorn backend16:app --reload

# Terminal 2 - Frontend  
streamlit run app.py
```

## Access the Application

- **Frontend**: http://localhost:8501
- **Backend API**: http://127.0.0.1:8000
- **API Docs**: http://127.0.0.1:8000/docs

## Example Queries

Try these in the chat:

1. **Regional Queries**
   - "Show floats in Indian Ocean"
   - "Floats in Arabian Sea"
   - "List all floats near equator"

2. **Visualization Queries**
   - "Show floats in Indian Ocean and their salinity on graph"
   - "Compare temperature for floats 1902669 and 1902670"
   - "Show trajectory of float 2900565"

3. **Data Queries**
   - "Temperature depth profile for float 1902669"
   - "Salinity trend for float 2900565"
   - "Show all floats on map"

## Add New Floats

### Via Web Interface
1. Click sidebar → "Admin: Add Float"
2. Enter float ID (e.g., 2900565)
3. Click "Download & Ingest"

### Via Command Line
```powershell
# Download + Ingest
Invoke-WebRequest -Uri "http://127.0.0.1:8000/admin/download-float" -Method POST -ContentType "application/json" -Body '{"float_id": "2900565"}' -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:8000/admin/ingest-float" -Method POST -ContentType "application/json" -Body '{"float_id": "2900565"}' -UseBasicParsing
```

## Features

✅ **Chat Interface** - Natural language queries
✅ **Interactive Maps** - Float trajectories and locations
✅ **Dynamic Charts** - Temperature, salinity comparisons
✅ **Real-time Data** - Live backend connection
✅ **Admin Panel** - Easy float management

## Troubleshooting

### Backend not connecting?
- Check if backend is running on port 8000
- Verify `.env` file has correct credentials

### Frontend not loading?
- Make sure Streamlit is installed: `pip install streamlit`
- Check port 8501 is not in use

### No data showing?
- Add floats using the Admin panel
- Verify database connection in backend

## Support

For issues, check:
1. Backend logs in terminal
2. Frontend error messages
3. Health status in sidebar
