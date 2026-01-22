# 🎓 AI Classroom Monitoring System

Real-time student engagement and attention tracking using Computer Vision and AI.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

## ✨ Features

- **👥 Multi-face Detection & Recognition** - Detect and identify enrolled students in real-time
- **👀 Attention Tracking** - Head pose and gaze estimation to measure student attention
- **📱 Phone Detection** - Detect students using phones during class
- **🪑 Posture Analysis** - Monitor student posture for engagement
- **📊 Real-time Dashboard** - Live statistics, metrics, and alerts
- **📈 Session Analytics** - Detailed post-session reports and charts
- **👤 Student Enrollment** - Face enrollment system for student recognition
- **💾 Local Storage** - No database required - runs entirely on your machine

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│    Backend      │────▶│   AI Service    │
│   (React)       │     │   (Node.js)     │     │   (FastAPI)     │
│   Port: 3000    │     │   Port: 5000    │     │   Port: 8000    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Local Storage  │
                        │  (JSON files)   │
                        └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** 
- **Node.js 18+**
- **Webcam**

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/VikaashSK/Ai-Classroom.git
   cd Ai-Classroom
   ```

2. **Install Backend Dependencies**
   ```bash
   cd backend
   npm install
   ```

3. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

4. **Install AI Service Dependencies**
   ```bash
   cd ai_service
   pip install -r requirements.txt
   ```

### Running the Application

**Option 1: Run all services manually**

Terminal 1 - Backend:
```bash
cd backend
npm start
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

Terminal 3 - AI Service:
```bash
cd ai_service
python main.py
```

**Option 2: Access the app**

Open http://localhost:3000 in your browser

### Default Login
- **Email:** 123@gmail.com
- **Password:** abcd

## 📁 Project Structure

```
Ai-Classroom/
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── pages/        # Page components
│   │   ├── components/   # Reusable components
│   │   ├── contexts/     # React contexts
│   │   └── services/     # API services
│   └── package.json
│
├── backend/               # Node.js backend server
│   ├── src/
│   │   ├── routes/       # API routes
│   │   ├── store/        # Local data storage
│   │   ├── services/     # Business logic
│   │   └── middleware/   # Express middleware
│   ├── data/             # JSON data files
│   └── package.json
│
├── ai_service/            # Python AI processing service
│   ├── models/           # AI model wrappers
│   ├── trackers/         # Object tracking (ByteTrack)
│   ├── main.py           # FastAPI server
│   └── pipeline.py       # Processing pipeline
│
└── models/               # Pre-trained model files
```

## 🔧 Key Features Explained

### 📷 Student Enrollment
1. Add student details (name, ID, course)
2. Capture 15 face images from different angles
3. Face embeddings are generated and stored locally
4. Students can now be recognized during sessions

### 🎬 Session Monitoring
1. Create a new monitoring session
2. Start the session to begin real-time tracking
3. View live metrics: student count, attention %, events
4. Events are logged: phone usage, poor posture, looking away
5. End session to save analytics

### 📊 Analytics Dashboard
- Session summary with key metrics
- Event distribution charts
- Per-student performance table
- Export data to CSV

## 🧠 AI Models Used

| Model | Purpose | Source |
|-------|---------|--------|
| OpenCV Haar Cascades | Face Detection | OpenCV |
| Custom Embeddings | Face Recognition | Local processing |
| Pose Analysis | Attention Tracking | OpenCV-based |
| YOLO (optional) | Person Detection | Ultralytics |

## 💾 Data Storage

All data is stored locally in JSON files:

| File | Contents |
|------|----------|
| `backend/data/users.json` | User accounts |
| `backend/data/students.json` | Student records |
| `backend/data/sessions.json` | Session data |
| `backend/data/events.json` | Detected events |

## ⚙️ Configuration

### Backend Config (`backend/src/config/index.js`)
- Port settings
- CORS configuration
- Storage paths

### AI Service Config (`ai_service/config.py`)
- Model paths
- Processing FPS
- Detection thresholds

## 🐛 Troubleshooting

**Camera not working:**
- Close other apps using the camera
- Check browser permissions (allow camera access)
- Try Chrome or Edge browser

**AI Service errors:**
- Ensure Python 3.10+ is installed
- Install OpenCV: `pip install opencv-python`
- Check if port 8000 is available

**Backend connection issues:**
- Check if port 5000 is available
- Verify Node.js is installed correctly

**Slow performance:**
- Reduce processing FPS in AI service config
- Close unnecessary applications
- Use a device with better CPU/GPU

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenCV for computer vision capabilities
- React and Vite for the frontend framework
- Express.js for the backend server
- FastAPI for the AI service

---

**Made  for better classroom engagement**
