# Classroom Analytics System - README

A comprehensive AI-powered single-camera classroom analytics application with real-time student monitoring, attention tracking, and behavioral analysis.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                     │
│                    Port 3000 (Development)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Backend (Node.js + Express)                    │
│                         Port 3001                               │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│    │  REST API    │  │  WebSocket   │  │  AI Service  │        │
│    │   Routes     │  │   Server     │  │    Client    │        │
│    └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
          │                    │                   │
          ▼                    ▼                   ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│    MongoDB       │  │   Real-time      │  │  Python AI       │
│   Database       │  │   Updates        │  │   Service        │
│                  │  │                  │  │   Port 8000      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## 📁 Project Structure

```
classroom-analytics/
├── backend/                    # Node.js Express Backend
│   ├── src/
│   │   ├── config/            # Configuration files
│   │   ├── middleware/        # Express middleware
│   │   ├── models/            # MongoDB schemas
│   │   ├── routes/            # API routes
│   │   ├── services/          # Business logic
│   │   └── server.js          # Entry point
│   ├── package.json
│   └── .env.example
│
├── ai_service/                 # Python AI Microservice
│   ├── models/                # AI model wrappers
│   │   ├── detection.py       # YOLOv8, InsightFace
│   │   └── pose_gaze.py       # MediaPipe pose/gaze
│   ├── trackers/              # Object tracking
│   │   └── bytetrack.py       # ByteTrack implementation
│   ├── main.py                # FastAPI server
│   ├── pipeline.py            # Processing pipeline
│   ├── config.py              # Configuration
│   └── requirements.txt
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # Reusable components
│   │   ├── contexts/          # React contexts
│   │   ├── pages/             # Page components
│   │   ├── services/          # API services
│   │   ├── App.jsx            # Main app
│   │   └── main.jsx           # Entry point
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+
- MongoDB 6.0+ (local or Atlas)
- CUDA-compatible GPU (recommended for AI processing)

### 1. Backend Setup

```bash
cd backend
npm install

# Copy environment file and configure
cp .env.example .env
# Edit .env with your MongoDB connection string and JWT secret

# Start the server
npm run dev
```

### 2. AI Service Setup

```bash
cd ai_service

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start the service
python main.py
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## 📚 API Documentation

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new faculty account |
| `/api/auth/login` | POST | Login and get JWT token |
| `/api/auth/me` | GET | Get current user profile |

### Students

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/students` | GET | List all students |
| `/api/students` | POST | Create new student |
| `/api/students/:id` | GET | Get student details |
| `/api/students/:id/enrollment/start` | POST | Start face enrollment |
| `/api/students/:id/enrollment/capture` | POST | Capture face image |
| `/api/students/:id/enrollment/complete` | POST | Finalize enrollment |

### Sessions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | GET | List all sessions |
| `/api/sessions` | POST | Create new session |
| `/api/sessions/:id` | GET | Get session details |
| `/api/sessions/:id/start` | POST | Start session |
| `/api/sessions/:id/pause` | POST | Pause session |
| `/api/sessions/:id/complete` | POST | Complete session |
| `/api/sessions/:id/analytics` | GET | Get session analytics |

## 🤖 AI Components

### Detection Models

- **YOLOv8**: Person and object detection (phone, laptop, etc.)
- **InsightFace (ArcFace)**: Face detection and recognition
- **MediaPipe**: Pose estimation and gaze direction

### Tracking

- **ByteTrack**: Multi-object tracking without Re-ID (single-camera optimized)

### Event Types

| Event | Description |
|-------|-------------|
| `attention_drop` | Student attention decreased below threshold |
| `phone_detected` | Phone/mobile device detected |
| `poor_posture` | Poor sitting posture detected |
| `looking_away` | Student not looking at screen/board |
| `student_identified` | Student face matched to enrolled profile |

## 🔒 Privacy Features

- No raw face images stored (embeddings only)
- Video snippets only captured for specific events
- Configurable snippet retention period
- Data accessible only to authenticated faculty

## 📊 Analytics

### Session Metrics

- Overall attention average
- Student count and identification rate
- Event frequency and distribution
- Timeline-based attention tracking

### Per-Student Analytics

- Individual attention scores
- Phone usage incidents
- Posture quality metrics
- Gaze direction analysis
- Time in frame statistics

## 🔧 Configuration

### Backend Environment Variables

```env
PORT=3001
NODE_ENV=development
MONGODB_URI=mongodb://localhost:27017/classroom-analytics
JWT_SECRET=your-secure-secret
JWT_EXPIRES_IN=7d
AI_SERVICE_URL=http://localhost:8000
```

### AI Service Environment Variables

```env
DEBUG=true
HOST=0.0.0.0
PORT=8000
MONGODB_URI=mongodb://localhost:27017/classroom-analytics
YOLO_MODEL=yolov8n.pt
FACE_MODEL=buffalo_l
TARGET_FPS=5
DEVICE=cuda
```

## 🔄 WebSocket Events

### Client → Server

| Event | Description |
|-------|-------------|
| `subscribe` | Subscribe to session updates |
| `unsubscribe` | Unsubscribe from session |

### Server → Client

| Event | Description |
|-------|-------------|
| `session_metrics` | Real-time session metrics |
| `new_event` | New event detected |
| `student_detected` | Student identified |
| `student_update` | Student metrics updated |

## 📝 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues and questions, please open a GitHub issue.
