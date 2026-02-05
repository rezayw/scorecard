# ⛳ Advanced Golf Scorecard Web

A professional golf scorecard web application designed for **Indonesia golf courses**, following **USGA (United States Golf Association)** official rules.

![Mobile Responsive](https://img.shields.io/badge/Mobile-Responsive-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![Python](https://img.shields.io/badge/Python-3.11+-yellow)

---

## ✨ Features

- 📝 **Stroke Play Scoring** - Score entry per hole with real-time calculation
- 📊 **Score Analysis** - Automatic detection of Eagle, Birdie, Par, Bogey, etc.
- 🎯 **USGA Handicap System** - Course handicap calculation per World Handicap System
- 👥 **Multi-Player Support** - Up to 10 players per game
- 📱 **Mobile-First Design** - Responsive UI optimized for mobile devices
- 📄 **PDF Export** - Professional scorecard report generation
- 📧 **Email Support** - Send scorecard via email (SMTP configuration required)
- 🇮🇩 **Indonesia Golf Courses** - Pre-configured database of Indonesian courses

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

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd scorecard

# Build and run with Docker Compose
docker-compose up -d

# Access the app
open http://localhost:5000
```

### Option 2: Docker Build Only

```bash
# Build the image
docker build -t golf-scorecard .

# Run the container
docker run -d -p 5000:5000 --name golf-scorecard golf-scorecard
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

Database Configuration
DATABASE_URL="file:./prisma/dev.db"

Resend API Configuration
RESEND_API_KEY = 'XXXXXXXXXXXXXXXX'
RESEND_FROM_EMAIL = 'XXXXXXXXXXXXXXXX'

---

## 🏗️ Project Structure

```
scorecard/
├── app.py                 # Flask application with API endpoints
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose config
├── .dockerignore         # Docker ignore file
├── templates/
│   └── index.html        # Mobile-responsive single-page app
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

## 🛠️ Tech Stack

- **Backend:** Python 3.11, Flask 3.0
- **Frontend:** HTML5, Tailwind CSS (CDN), Vanilla JavaScript
- **PDF Generation:** ReportLab
- **Production Server:** Gunicorn
- **Container:** Docker & Docker Compose

---

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

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

Made with ⛳ for golfers in Indonesia
