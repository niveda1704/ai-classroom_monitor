# AI Classroom Monitor - Local Desktop Version

## Overview

This is a **fully local desktop application** that replicates all functionality of the web-based AI Classroom Monitor, but runs entirely on your local machine without any network delays.

## Key Features

- ✅ **Zero Network Latency** - Everything runs locally, no WebSocket delays
- ✅ **CSV-Based Storage** - Human-readable data files, easy to backup
- ✅ **Modern Dark UI** - PyQt6-based interface matching the web version
- ✅ **Full Feature Parity** - All features from web app included
- ✅ **Offline Ready** - No internet connection required
- ✅ **Easy Export** - Export analytics to CSV for Excel

## Quick Start

### Option 1: Run the Batch File (Windows)
```cmd
run_local_app.bat
```

### Option 2: Manual Setup
```cmd
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r local_app/requirements.txt

# Run the app
python -m local_app.main
```

## Application Structure

```
local_app/
├── main.py              # Main application window
├── data_manager.py      # CSV-based data storage
├── requirements.txt     # Python dependencies
├── data/               # CSV data files
│   ├── students.csv
│   ├── sessions.csv
│   ├── events.csv
│   └── attention_logs.csv
├── embeddings/         # Face embedding files (.npy)
└── pages/
    ├── dashboard.py     # Dashboard overview
    ├── students.py      # Student management
    ├── sessions.py      # Session management
    ├── enrollment.py    # Face enrollment
    ├── session_monitor.py # Live monitoring
    └── analytics.py     # Session analytics
```

## Features

### 📊 Dashboard
- Overview statistics (students, sessions, active sessions)
- Recent sessions with quick access
- Quick action buttons

### 👥 Students Management
- Add/edit/delete students
- Search functionality
- Face enrollment status

### 📷 Face Enrollment
- Camera capture interface
- 15-photo enrollment process
- Face embedding storage

### 🎬 Sessions
- Create monitoring sessions
- Session status tracking
- Quick access to monitor/analytics

### 🎥 Live Monitoring
- Real-time camera feed
- AI-powered detection:
  - Person detection (YOLO)
  - Face recognition (InsightFace)
  - Pose & gaze analysis (MediaPipe)
  - Phone detection
- Live metrics display
- Event logging

### 📈 Analytics
- Session summary statistics
- Event distribution
- Student performance table
- CSV export

## Data Storage

All data is stored in CSV files in the `local_app/data/` directory:

| File | Description |
|------|-------------|
| `students.csv` | Student records |
| `sessions.csv` | Session information |
| `events.csv` | Detected events |
| `attention_logs.csv` | Attention data over time |

Face embeddings are stored as `.npy` files in `local_app/embeddings/`.

## Comparison with Web Version

| Feature | Web Version | Local Version |
|---------|-------------|---------------|
| Latency | 50-200ms+ | ~10-30ms |
| Dependencies | Node.js + React + Python | Python only |
| Deployment | 3 servers | 1 app |
| Data Storage | MongoDB | CSV files |
| Multi-user | ✅ Yes | ❌ Single machine |
| Offline | ❌ No | ✅ Yes |
| Data Export | Via API | Direct CSV |

## System Requirements

- Windows 10/11 (or Linux/Mac with minor modifications)
- Python 3.10+
- 8GB RAM minimum (16GB recommended)
- Webcam
- NVIDIA GPU recommended for faster AI processing

## Troubleshooting

### Camera not working
- Check if another application is using the camera
- Grant camera permissions to Python

### AI models not loading
- Ensure all models are downloaded (run `python download_model.py` from project root)
- Check GPU drivers if using CUDA

### Application crashes
- Check the console for error messages
- Ensure all dependencies are installed correctly

## Contributing

The local app uses the same AI models as the web version. Any improvements to the AI pipeline will benefit both versions.
