# IPL Playoff Probability Engine 🏏

A full-stack, production-ready system to predict Indian Premier League (IPL) playoff qualification probabilities and final standings using Monte Carlo simulations. The engine features a FastAPI backend calculating millions of outcomes in seconds, and a sleek, dynamic React/Tailwind frontend for live insights and "what-if" scenario testing.

![Dashboard Preview](frontend/public/vite.svg) *(Replace with actual screenshot)*

## ✨ Features

- **Real-Time Probabilities**: Accurately tracks Top-4 qualification and Top-2 finish chances using advanced stochastic modeling.
- **Monte Carlo Simulation Engine**: Highly optimized Python backend performing 10,000+ full-season iterations per second, realistically simulating batting-first vs. chasing net run rate (NRR) outcomes.
- **Dynamic What-If Scenarios**: Users can flip upcoming match winners to instantly recalculate global probabilities.
- **Live Data Updates**: Seamless background workers scraping and merging live points tables directly into the simulation state.
- **Obsidian Design System**: A premium, high-contrast UI tailored for data density, speed, and aesthetics.

---

## 🛠️ Technology Stack

**Backend**
- Python 3.10+
- FastAPI (REST API & Asynchronous scraping)
- Uvicorn (ASGI Web Server)
- Pydantic (Data validation)
- Requests / BeautifulSoup4 (Web scraping)

**Frontend**
- TypeScript
- React 18
- Vite (Fast bundler)
- Tailwind CSS (v3 / Obsidion theme)
- PostCSS / Autoprefixer

---

## 🚀 Getting Started

Follow these steps to run the complete stack locally.

### 1. Backend Setup (FastAPI)

Navigate to the backend directory and set up your Python environment:

```bash
cd ipl-engine

# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Environment Setup
cp .env.example .env
# Optional: Set IPL_LOG_LEVEL=DEBUG for granular simulation logs
```

Run the backend server:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. You can view the automatic Swagger documentation at `http://localhost:8000/docs`.

### 2. Frontend Setup (React/Vite)

Open a new terminal window, navigate to the frontend directory:

```bash
cd frontend

# Install Node.js dependencies
npm install

# Environment Setup
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000
```

Start the development server:

```bash
npm run dev
```

The dashboard will be live at `http://localhost:5173`.

---

## 📁 Repository Structure

```
.
├── ipl-engine/                  # Python/FastAPI Backend
│   ├── backend/
│   │   ├── main.py              # FastAPI app & routing
│   │   ├── models/              # Pydantic schemas (Team, Match, Simulation)
│   │   ├── services/            # Core business logic
│   │   │   ├── nrr.py           # ICC-compliant Net Run Rate logic
│   │   │   ├── probability.py   # Match outcome stochastic models
│   │   │   └── simulator.py     # Monte Carlo hot loop
│   │   └── scraper/             # Live points table ingestion
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    # React/TypeScript Frontend
│   ├── src/
│   │   ├── App.tsx              # Main Dashboard component
│   │   ├── main.tsx             # React entry point
│   │   └── index.css            # Tailwind & theme base
│   ├── tailwind.config.js       # Obsidian theme configuration
│   ├── vite.config.ts
│   └── .env.example
├── .gitignore                   # Universal ignores
└── README.md                    # You are here
```

---

## ⚙️ Core API Endpoints

- `GET /health` : Returns system status and simulation engine readiness.
- `GET /standings` : Fetches the current real-world IPL points table.
- `GET /simulate?simulations=10000` : Runs a fresh Monte Carlo simulation over remaining fixtures and returns probability aggregates and elapsed time.

---

## 📝 Future Roadmap

- [ ] Production integration with live APIs replacing HTML scraping.
- [ ] Connect Scenario Simulator UI inputs back to the `/simulate` endpoint via POST requests.
- [ ] Implement historical performance tuning for simulation weights (home advantage vs current form).
- [ ] Add Dockerfile and `docker-compose.yml` for unified deployment.

## 📄 License

This project is open-source under the MIT License.
