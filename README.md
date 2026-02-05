# ⛳ Unit Ganesha Golf - Scorecard App

A professional golf scorecard web application for **Unit Ganesha Golf ITB**, following **USGA (United States Golf Association)** official rules.

![Mobile Responsive](https://img.shields.io/badge/Mobile-Responsive-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Python](https://img.shields.io/badge/Python-3.11+-yellow)
![Flask](https://img.shields.io/badge/Flask-3.0-red)

---

## ✨ Features

### Core Features
- 📝 **Stroke Play Scoring** - Score entry per hole with real-time calculation
- 📊 **Score Analysis** - Automatic detection of Eagle, Birdie, Par, Bogey, etc.
- 🎯 **USGA Handicap System** - Course handicap calculation per World Handicap System
- 👥 **Multi-Player Support** - Up to 10 players per game
- 📱 **Mobile-First PWA** - Progressive Web App optimized for mobile devices
- 🇮🇩 **Indonesia Golf Courses** - Pre-configured database of Indonesian courses

### User Management
- 🔐 **User Registration** - Email verification with OTP (ITB & Gmail domains only)
- 👤 **User Profiles** - Username, Student ID, phone number, avatar, bio
- 🚻 **Gender Selection** - Male/Female option during registration
- 🔑 **Secure Login** - Password with complexity requirements + OTP verification
- 🔄 **Password Reset** - Forgot password with email OTP verification
- ❌ **Account Deletion** - Full data removal with confirmation

### Game Features
- 💾 **Autosave** - Game progress saved every 10 seconds
- 🔄 **Session Resume** - Continue unfinished games after closing the app
- 📸 **Photo Capture** - Required photo before downloading scorecard
- 📄 **PDF Export** - Professional scorecard report generation
- 📧 **Email Support** - Send scorecard via email (Resend API)

### Social Features
- 💬 **Forum** - Community posts with categories, comments, and likes
- 🏆 **Leaderboard** - Best scores ranking across all players
- 📜 **Game History** - View past games and scores
- 📅 **Events** - Golf events management (separate microservice)

---

## 🏌️ Supported Golf Courses

| Region | Courses |
|--------|---------|
| **Jakarta** | Pondok Indah Golf, Padang Golf Halim, Jakarta Golf Club |
| **Tangerang** | Damai Indah BSD, Damai Indah PIK, Gading Raya Golf |
| **Bogor** | Rancamaya Golf Estate, Gunung Geulis CC, Riverside Golf |
| **Bandung** | Dago Endah Golf, Mountain View Golf |
| **Surabaya** | Graha Famili Golf & CC, Ciputra Golf Club |
| **Bali** | Bali National Golf, Nirwana Bali Golf, Handara Golf |

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd scorecard

# Create .env file with required variables
cp .env.example .env
# Edit .env with your RESEND_API_KEY

# Build and run with Docker Compose
docker-compose up -d --build

# Access the app
open http://localhost:5000
```

### Option 2: Docker Build Only

```bash
# Build the image
docker build -t golf-scorecard .

# Run the container
docker run -d -p 5000:5000 \
  -e SECRET_KEY=your-secret-key \
  -e RESEND_API_KEY=your-resend-key \
  --name golf-scorecard golf-scorecard
```

### Option 3: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Access the app
open http://localhost:5000
```

---

## 📱 How to Use

### Game Flow

1. **Setup** - Select region and golf course from the dropdown
2. **Configure** - Choose 9 or 18 holes, add 1-10 players with names
3. **Tee Selection** - Select tee color (Black/Blue/White/Red) per player
4. **Handicap** - Enter handicap index for each player (optional)
5. **Play** - Enter scores per hole using +/- buttons
6. **Finish** - View leaderboard with gross/net scores
7. **Export** - Download PDF or send via email

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SECRET_KEY` | Flask session secret key | **Yes** | Random (not persistent!) |
| `RESEND_API_KEY` | Resend API key for OTP emails | **Yes** | - |
| `DATABASE_URL` | SQLite database path | No | `file:./prisma/dev.db` |
| `EVENTS_SERVICE_URL` | Events microservice URL | No | `http://golf-events:5001` |
| `RESEND_FROM_EMAIL` | Sender email address | No | `UGG-ITB Scorecard <OTP@ugg.my.id>` |

### Docker Compose Environment

Create a `.env` file in the root directory:

```env
# Required
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx

# Optional (override defaults)
SECRET_KEY=your-secure-secret-key-here
RESEND_FROM_EMAIL=Your App <noreply@yourdomain.com>
```

> ⚠️ **Important:** Always set `SECRET_KEY` in production to ensure session persistence across container restarts.

---

## 🏗️ Project Structure

```
scorecard/
├── app.py                 # Flask application with API endpoints
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose config
├── .env                  # Environment variables (create from .env.example)
├── .dockerignore         # Docker ignore file
├── templates/
│   └── index.html        # Mobile-responsive single-page app
├── static/
│   ├── css/
│   │   └── styles.css    # Custom styles
│   ├── js/
│   │   ├── app.js        # Main application JavaScript
│   │   └── sw.js         # Service worker for PWA
│   ├── icons/            # App icons
│   └── manifest.json     # PWA manifest
├── prisma/
│   └── schema.prisma     # Database schema
├── events-service/       # Separate events microservice
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── info/
│   ├── calculation.md    # Scoring calculations reference
│   ├── logic-flow.md     # Application flow documentation
│   ├── report-illustration.md
│   ├── study-case.md
│   ├── usga-rule.md
│   └── prompt-ai.md
└── README.md
```

---

## 📚 USGA Rules Implemented

- **World Handicap System (WHS)** - Course handicap calculation
- **Course Rating & Slope** - Per tee box (Black, Blue, White, Red)

### Handicap Formula

```
Course Handicap = Handicap Index × (Slope Rating / 113) + (Course Rating - Par)
```

### Scoring Terms

| Score | Description |
|-------|-------------|
| Hole in One | 1 stroke |
| Albatross | 3 under par |
| Eagle | 2 under par |
| Birdie | 1 under par |
| Par | Expected strokes |
| Bogey | 1 over par |
| Double Bogey | 2 over par |
| Triple Bogey | 3 over par |

---

## �️ Database Schema

### Main Tables

| Table | Description |
|-------|-------------|
| `User` | User accounts with email, password, profile info, gender |
| `Player` | Game players (linked to games) |
| `Course` | Golf courses with tee configurations |
| `Game` | Game sessions |
| `GameResult` | Player scores per game |
| `ScoreHistory` | Historical scores for leaderboard |
| `UserScoreHistory` | User-specific score history |
| `OTP` | One-time passwords for auth |
| `ForumPost` | Forum posts with categories |
| `ForumComment` | Comments on posts |
| `ForumLike` | Post likes |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, Flask 3.0, Gunicorn |
| **Frontend** | HTML5, Tailwind CSS (CDN), Vanilla JavaScript |
| **Database** | SQLite3 |
| **PDF Generation** | ReportLab |
| **Email** | Resend API |
| **Container** | Docker & Docker Compose |
| **PWA** | Service Worker, Web Manifest |

---

## 🐳 Docker Commands

```bash
# Build and start (with logs)
docker-compose up -d --build

# View logs
docker-compose logs -f golf-scorecard

# View events service logs
docker-compose logs -f golf-events

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Rebuild without cache
docker-compose build --no-cache

# Check container status
docker-compose ps
```

---

## 🔐 Security Features

- **Password Requirements**: 8+ characters with uppercase, lowercase, and numbers
- **OTP Verification**: Email-based one-time passwords for login and registration
- **Session Security**: Secure session cookies with configurable secret key
- **Rate Limiting**: API endpoints protected against abuse
- **Input Sanitization**: XSS protection on all user inputs

---

## 📄 License

MIT License - Feel free to use and modify for your own projects.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

Made with ⛳ for **Unit Ganesha Golf ITB**
