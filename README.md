# Ocean Intel Bot (FloatChat AI)

An AI-powered oceanographic data analysis system designed to interact with Argo float data. This project combines a FastAPI backend with a React frontend to provide intelligent querying, visualization, and analysis of ocean data.

## Project Overview

**Ocean Intel Bot** (also referred to as FloatChat AI) allows users to query Argo float data using natural language. The system leverages Google's Gemini AI to interpret queries and generate SQL, explanations, or visualizations.

### Key Features
- **Natural Language Querying**: Ask questions about ocean data in plain English.
- **AI-Powered Analysis**: Uses Gemini Pro for query understanding and response generation.
- **Data Visualization**: Interactive graphs and maps for depth profiles, trajectories, and time series.
- **Regional Analysis**: Specialized analysis for regions like Arabian Sea, Indian Ocean, Bay of Bengal, etc.

## Technology Stack

### Backend
- **FastAPI**: High-performance web framework for building APIs.
- **Supabase (PostgreSQL)**: Database for storing float metadata, profiles, and measurements.
- **Google Gemini AI**: For natural language processing and SQL generation.
- **ChromaDB**: Vector database for semantic search (if applicable).
- **Python Libraries**: `asyncpg`, `pandas`, `numpy`, `plotly`.

### Frontend
- **Vite**: Next Generation Frontend Tooling.
- **React**: Library for building user interfaces.
- **TypeScript**: Typed superset of JavaScript.
- **shadcn-ui**: Reusable components built with Radix UI and Tailwind CSS.
- **Tailwind CSS**: Utility-first CSS framework.

## Getting Started

### Prerequisites
- Node.js & npm
- Python 3.10+
- Supabase account and database setup
- Google Gemini API Key

### Installation

1.  **Clone the repository**
    ```sh
    git clone <YOUR_GIT_URL>
    cd ocean-intel-bot
    ```

2.  **Install Frontend Dependencies**
    ```sh
    npm install
    ```

3.  **Install Backend Dependencies**
    ```sh
    pip install -r requirements.txt
    ```

### Running the Application

You can run both the backend and frontend concurrently using the provided script:

```sh
npm run dev:full
```

Or run them separately:

**Backend:**
```sh
npm run start:backend
# OR directly with python
# python -m uvicorn backend15:app --reload
```

**Frontend:**
```sh
npm run start:frontend
# OR
# npm run dev
```

## Project Structure

- `src/`: Frontend source code (React components, pages, hooks).
- `backend15.py`: Main backend application entry point.
- `backend*.py`: Previous iterations/modules of the backend.
- `requirements.txt`: Python dependencies.
- `package.json`: Frontend dependencies and scripts.

## License

[Add License Information Here]
