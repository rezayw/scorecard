from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import json
import io
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import sqlite3

app = Flask(__name__, static_folder='static')

# Database initialization
DB_PATH = os.path.join(os.path.dirname(__file__), 'prisma', 'dev.db')

def init_db():
    """Initialize SQLite database with required tables"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Player table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Player (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Course table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Course (
            id TEXT PRIMARY KEY,
            courseId TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            region TEXT,
            holes INTEGER DEFAULT 18,
            par9 INTEGER DEFAULT 36,
            par18 INTEGER DEFAULT 72,
            holePars TEXT,
            tees TEXT,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Game table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Game (
            id TEXT PRIMARY KEY,
            courseId TEXT NOT NULL,
            holeCount INTEGER NOT NULL,
            playedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'in_progress',
            totalPar INTEGER,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (courseId) REFERENCES Course(id)
        )
    ''')
    
    # Create GameResult table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS GameResult (
            id TEXT PRIMARY KEY,
            gameId TEXT NOT NULL,
            playerId TEXT NOT NULL,
            tee TEXT DEFAULT 'white',
            handicapIndex REAL DEFAULT 0,
            courseHandicap INTEGER DEFAULT 0,
            grossScore INTEGER NOT NULL,
            netScore INTEGER NOT NULL,
            vsPar INTEGER NOT NULL,
            rank INTEGER,
            scores TEXT,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (gameId) REFERENCES Game(id) ON DELETE CASCADE,
            FOREIGN KEY (playerId) REFERENCES Player(id)
        )
    ''')
    
    # Create ScoreHistory table for quick access
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ScoreHistory (
            id TEXT PRIMARY KEY,
            playerName TEXT NOT NULL,
            playerEmail TEXT,
            courseName TEXT NOT NULL,
            location TEXT NOT NULL,
            holeCount INTEGER NOT NULL,
            grossScore INTEGER NOT NULL,
            netScore INTEGER NOT NULL,
            vsPar INTEGER NOT NULL,
            playedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            scores TEXT,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Indonesia Golf Courses Database
GOLF_COURSES = {
    "jakarta": [
        {
            "id": "pig",
            "name": "Pondok Indah Golf Course",
            "location": "Jakarta Selatan",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.5, "slope": 135},
                "blue": {"rating": 71.2, "slope": 130},
                "white": {"rating": 69.0, "slope": 125},
                "red": {"rating": 67.5, "slope": 120}
            }
        },
        {
            "id": "halim",
            "name": "Padang Golf Halim",
            "location": "Jakarta Timur",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.8, "slope": 132},
                "blue": {"rating": 70.5, "slope": 128},
                "white": {"rating": 68.2, "slope": 122},
                "red": {"rating": 66.8, "slope": 118}
            }
        },
        {
            "id": "jgc",
            "name": "Jakarta Golf Club",
            "location": "Jakarta Selatan",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 74.0, "slope": 138},
                "blue": {"rating": 71.8, "slope": 133},
                "white": {"rating": 69.5, "slope": 127},
                "red": {"rating": 68.0, "slope": 122}
            }
        }
    ],
    "tangerang": [
        {
            "id": "damai_bsd",
            "name": "Damai Indah Golf - BSD Course",
            "location": "Tangerang Selatan",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 74.2, "slope": 140},
                "blue": {"rating": 72.0, "slope": 135},
                "white": {"rating": 69.8, "slope": 128},
                "red": {"rating": 68.2, "slope": 123}
            }
        },
        {
            "id": "damai_pik",
            "name": "Damai Indah Golf - PIK Course",
            "location": "Tangerang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.8, "slope": 137},
                "blue": {"rating": 71.5, "slope": 132},
                "white": {"rating": 69.2, "slope": 126},
                "red": {"rating": 67.8, "slope": 121}
            }
        },
        {
            "id": "gading_raya",
            "name": "Gading Raya Golf",
            "location": "Tangerang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.5, "slope": 130},
                "blue": {"rating": 70.2, "slope": 125},
                "white": {"rating": 68.0, "slope": 120},
                "red": {"rating": 66.5, "slope": 115}
            }
        }
    ],
    "bogor": [
        {
            "id": "rancamaya",
            "name": "Rancamaya Golf Estate",
            "location": "Bogor",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 73.0, "slope": 133},
                "blue": {"rating": 70.8, "slope": 128},
                "white": {"rating": 68.5, "slope": 122},
                "red": {"rating": 67.0, "slope": 117}
            }
        },
        {
            "id": "gunung_geulis",
            "name": "Gunung Geulis Country Club",
            "location": "Bogor",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 74.5, "slope": 142},
                "blue": {"rating": 72.2, "slope": 137},
                "white": {"rating": 70.0, "slope": 130},
                "red": {"rating": 68.5, "slope": 125}
            }
        },
        {
            "id": "riverside",
            "name": "Riverside Golf Club",
            "location": "Bogor",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.0, "slope": 128},
                "blue": {"rating": 69.8, "slope": 123},
                "white": {"rating": 67.5, "slope": 118},
                "red": {"rating": 66.0, "slope": 113}
            }
        }
    ],
    "bandung": [
        {
            "id": "dago",
            "name": "Dago Endah Golf",
            "location": "Bandung",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 71.5, "slope": 126},
                "blue": {"rating": 69.2, "slope": 121},
                "white": {"rating": 67.0, "slope": 116},
                "red": {"rating": 65.5, "slope": 111}
            }
        },
        {
            "id": "mountain",
            "name": "Mountain View Golf",
            "location": "Bandung",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.8, "slope": 130},
                "blue": {"rating": 70.5, "slope": 125},
                "white": {"rating": 68.2, "slope": 120},
                "red": {"rating": 66.8, "slope": 115}
            }
        }
    ],
    "surabaya": [
        {
            "id": "graha_famili",
            "name": "Graha Famili Golf & Country Club",
            "location": "Surabaya",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.2, "slope": 134},
                "blue": {"rating": 71.0, "slope": 129},
                "white": {"rating": 68.8, "slope": 123},
                "red": {"rating": 67.2, "slope": 118}
            }
        },
        {
            "id": "ciputra",
            "name": "Ciputra Golf Club",
            "location": "Surabaya",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 72.5, "slope": 131},
                "blue": {"rating": 70.2, "slope": 126},
                "white": {"rating": 68.0, "slope": 121},
                "red": {"rating": 66.5, "slope": 116}
            }
        }
    ],
    "bali": [
        {
            "id": "bali_national",
            "name": "Bali National Golf Club",
            "location": "Nusa Dua, Bali",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 75.0, "slope": 145},
                "blue": {"rating": 72.8, "slope": 140},
                "white": {"rating": 70.5, "slope": 133},
                "red": {"rating": 69.0, "slope": 128}
            }
        },
        {
            "id": "nirwana",
            "name": "Nirwana Bali Golf Club",
            "location": "Tabanan, Bali",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 74.5, "slope": 143},
                "blue": {"rating": 72.2, "slope": 138},
                "white": {"rating": 70.0, "slope": 131},
                "red": {"rating": 68.5, "slope": 126}
            }
        },
        {
            "id": "handara",
            "name": "Handara Golf & Resort",
            "location": "Bedugul, Bali",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.8, "slope": 140},
                "blue": {"rating": 71.5, "slope": 135},
                "white": {"rating": 69.2, "slope": 128},
                "red": {"rating": 67.8, "slope": 123}
            }
        }
    ]
}

def get_score_name(score, par):
    """Get the name of the score based on strokes relative to par"""
    diff = score - par
    if score == 1:
        return "Hole in One"
    elif diff == -3:
        return "Albatross"
    elif diff == -2:
        return "Eagle"
    elif diff == -1:
        return "Birdie"
    elif diff == 0:
        return "Par"
    elif diff == 1:
        return "Bogey"
    elif diff == 2:
        return "Double Bogey"
    elif diff == 3:
        return "Triple Bogey"
    elif score >= par * 2:
        return "Double Par+"
    else:
        return f"+{diff}"

def calculate_handicap_strokes(handicap_index, slope, rating, par):
    """Calculate course handicap using USGA formula"""
    if handicap_index is None or handicap_index == 0:
        return 0
    course_handicap = handicap_index * (slope / 113) + (rating - par)
    return round(course_handicap)

def generate_recommendations(players_data, course_par):
    """Generate personalized recommendations based on performance"""
    recommendations = []
    
    for player in players_data:
        total_score = sum(player['scores'])
        par_total = sum(course_par[:len(player['scores'])])
        diff = total_score - par_total
        
        eagles = sum(1 for i, s in enumerate(player['scores']) if s <= course_par[i] - 2)
        birdies = sum(1 for i, s in enumerate(player['scores']) if s == course_par[i] - 1)
        pars = sum(1 for i, s in enumerate(player['scores']) if s == course_par[i])
        bogeys = sum(1 for i, s in enumerate(player['scores']) if s == course_par[i] + 1)
        double_plus = sum(1 for i, s in enumerate(player['scores']) if s >= course_par[i] + 2)
        
        rec = f"📊 {player['name']}: "
        if diff <= -5:
            rec += "Outstanding round! Keep up the excellent play."
        elif diff <= 0:
            rec += "Great round at or under par!"
        elif diff <= 5:
            rec += "Solid round. Focus on reducing bogeys."
        elif diff <= 10:
            rec += "Work on approach shots and putting."
        else:
            rec += "Consider taking lessons to improve fundamentals."
        
        if double_plus > 3:
            rec += " Avoid big numbers by playing safe on difficult holes."
        if birdies > 2:
            rec += f" Great birdie opportunities ({birdies} birdies)!"
            
        recommendations.append(rec)
    
    return recommendations


def generate_id():
    """Generate a unique ID"""
    import uuid
    return str(uuid.uuid4())[:25]


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_game_to_db(course_id, course_name, location, hole_count, players):
    """Save a new game to the database"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Find or create course
        cursor.execute('SELECT id FROM Course WHERE courseId = ?', (course_id,))
        course_row = cursor.fetchone()
        
        if not course_row:
            # Get course data
            course_data = None
            region_name = ''
            for region, courses in GOLF_COURSES.items():
                for c in courses:
                    if c['id'] == course_id:
                        course_data = c
                        region_name = region
                        break
            
            if course_data:
                db_course_id = generate_id()
                cursor.execute('''
                    INSERT INTO Course (id, courseId, name, location, region, holes, par9, par18, holePars, tees)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    db_course_id,
                    course_id,
                    course_name,
                    location,
                    region_name,
                    course_data.get('holes', 18),
                    course_data.get('par', {}).get('9', 36),
                    course_data.get('par', {}).get('18', 72),
                    json.dumps(course_data.get('hole_pars', [])),
                    json.dumps(course_data.get('tees', {}))
                ))
                course_row = {'id': db_course_id}
        
        db_course_id = course_row['id'] if isinstance(course_row, dict) else course_row[0]
        
        # Calculate total par
        course_data = None
        for region_courses in GOLF_COURSES.values():
            for c in region_courses:
                if c['id'] == course_id:
                    course_data = c
                    break
        
        total_par = sum(course_data.get('hole_pars', [4]*18)[:hole_count]) if course_data else 72
        
        # Create game
        game_id = generate_id()
        cursor.execute('''
            INSERT INTO Game (id, courseId, holeCount, status, totalPar)
            VALUES (?, ?, ?, 'in_progress', ?)
        ''', (game_id, db_course_id, hole_count, total_par))
        
        conn.commit()
        return {"id": game_id, "courseId": db_course_id}
    
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def save_game_results(game_id, results, course_name, location, hole_count):
    """Save game results to database"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        for result in results:
            # Find or create player
            cursor.execute('SELECT id FROM Player WHERE name = ?', (result['name'],))
            player_row = cursor.fetchone()
            
            if not player_row:
                player_id = generate_id()
                cursor.execute('''
                    INSERT INTO Player (id, name, email)
                    VALUES (?, ?, ?)
                ''', (player_id, result['name'], result.get('email')))
            else:
                player_id = player_row[0]
            
            # Create game result
            result_id = generate_id()
            cursor.execute('''
                INSERT INTO GameResult (id, gameId, playerId, tee, handicapIndex, courseHandicap, grossScore, netScore, vsPar, rank, scores)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_id,
                game_id,
                player_id,
                result.get('tee', 'white'),
                float(result.get('handicap_index', 0)),
                result.get('course_handicap', 0),
                result['gross_score'],
                result['net_score'],
                result['vs_par'],
                result.get('rank'),
                json.dumps(result.get('scores', []))
            ))
            
            # Save to history
            history_id = generate_id()
            cursor.execute('''
                INSERT INTO ScoreHistory (id, playerName, playerEmail, courseName, location, holeCount, grossScore, netScore, vsPar, scores)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                history_id,
                result['name'],
                result.get('email'),
                course_name,
                location,
                hole_count,
                result['gross_score'],
                result['net_score'],
                result['vs_par'],
                json.dumps(result.get('scores', []))
            ))
        
        # Update game status
        cursor.execute("UPDATE Game SET status = 'completed' WHERE id = ?", (game_id,))
        
        conn.commit()
    
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_game_history(limit=20):
    """Get recent game history"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT playerName, playerEmail, courseName, location, holeCount, grossScore, netScore, vsPar, playedAt, scores
            FROM ScoreHistory
            ORDER BY playedAt DESC
            LIMIT ?
        ''', (limit * 10,))  # Get more rows to group by game
        
        rows = cursor.fetchall()
        
        # Group by game (same course and timestamp)
        games = {}
        for row in rows:
            date_str = row['playedAt'][:16] if row['playedAt'] else ''
            key = f"{row['courseName']}_{date_str}"
            
            if key not in games:
                games[key] = {
                    "course_name": row['courseName'],
                    "location": row['location'],
                    "hole_count": row['holeCount'],
                    "date": row['playedAt'][:10] if row['playedAt'] else '',
                    "players": []
                }
            
            games[key]["players"].append({
                "name": row['playerName'],
                "gross_score": row['grossScore'],
                "net_score": row['netScore']
            })
        
        return list(games.values())[:limit]
    
    finally:
        conn.close()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/courses')
def get_courses():
    return jsonify(GOLF_COURSES)

@app.route('/api/course/<course_id>')
def get_course(course_id):
    for region in GOLF_COURSES.values():
        for course in region:
            if course['id'] == course_id:
                return jsonify(course)
    return jsonify({"error": "Course not found"}), 404


@app.route('/api/games', methods=['POST'])
def create_game():
    """Create a new game"""
    data = request.json
    
    try:
        result = save_game_to_db(
            data.get('course_id'),
            data.get('course_name'),
            data.get('location'),
            data.get('hole_count', 18),
            data.get('players', [])
        )
        return jsonify(result)
    except Exception as e:
        print(f"Error creating game: {e}")
        return jsonify({"id": None, "error": str(e)})


@app.route('/api/games/history')
def get_history():
    """Get game history"""
    try:
        history = get_game_history()
        return jsonify(history)
    except Exception as e:
        print(f"Error getting history: {e}")
        return jsonify([])


@app.route('/api/players', methods=['GET'])
def get_players():
    """Get all players"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, email FROM Player ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{"id": r['id'], "name": r['name'], "email": r['email']} for r in rows])
    except Exception as e:
        print(f"Error fetching players: {e}")
        return jsonify([])


@app.route('/api/players', methods=['POST'])
def create_player():
    """Create a new player"""
    data = request.json
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        player_id = generate_id()
        cursor.execute('''
            INSERT INTO Player (id, name, email)
            VALUES (?, ?, ?)
        ''', (player_id, data.get('name'), data.get('email')))
        conn.commit()
        conn.close()
        return jsonify({"id": player_id, "name": data.get('name'), "email": data.get('email')})
    except Exception as e:
        print(f"Error creating player: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/calculate', methods=['POST'])
def calculate_scores():
    data = request.json
    players = data.get('players', [])
    course_id = data.get('course_id')
    hole_count = data.get('hole_count', 18)
    game_id = data.get('game_id')
    
    # Get course info
    course = None
    for region in GOLF_COURSES.values():
        for c in region:
            if c['id'] == course_id:
                course = c
                break
    
    if not course:
        return jsonify({"error": "Course not found"}), 404
    
    hole_pars = course['hole_pars'][:hole_count]
    total_par = sum(hole_pars)
    
    results = []
    for player in players:
        scores = player.get('scores', [])
        tee = player.get('tee', 'white')
        handicap_index = player.get('handicap', 0)
        
        tee_data = course['tees'].get(tee, course['tees']['white'])
        course_handicap = calculate_handicap_strokes(
            handicap_index, 
            tee_data['slope'], 
            tee_data['rating'],
            total_par
        )
        
        gross_score = sum(scores)
        net_score = gross_score - course_handicap
        
        hole_details = []
        for i, score in enumerate(scores):
            par = hole_pars[i]
            hole_details.append({
                'hole': i + 1,
                'par': par,
                'score': score,
                'score_name': get_score_name(score, par),
                'diff': score - par
            })
        
        results.append({
            'name': player['name'],
            'email': player.get('email'),
            'tee': tee,
            'handicap_index': handicap_index,
            'course_handicap': course_handicap,
            'gross_score': gross_score,
            'net_score': net_score,
            'vs_par': gross_score - total_par,
            'holes': hole_details,
            'scores': scores
        })
    
    # Sort by net score for ranking
    results.sort(key=lambda x: x['net_score'])
    for i, r in enumerate(results):
        r['rank'] = i + 1
    
    recommendations = generate_recommendations(
        [{'name': p['name'], 'scores': p.get('scores', [])} for p in players],
        hole_pars
    )
    
    # Save results to database
    if game_id:
        try:
            save_game_results(
                game_id, 
                results, 
                course['name'],
                course['location'],
                hole_count
            )
        except Exception as e:
            print(f"Error saving results: {e}")
    
    return jsonify({
        'course': course,
        'hole_count': hole_count,
        'total_par': total_par,
        'results': results,
        'recommendations': recommendations,
        'date': datetime.now().strftime('%d-%m-%Y')
    })

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    data = request.json
    
    buffer = io.BytesIO()
    
    if data.get('hole_count', 18) > 9:
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                               leftMargin=0.5*inch, rightMargin=0.5*inch,
                               topMargin=0.5*inch, bottomMargin=0.5*inch)
    else:
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=0.5*inch, rightMargin=0.5*inch,
                               topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1a5f2a')
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    elements = []
    
    # Title
    hole_count = data.get('hole_count', 18)
    elements.append(Paragraph(f"🎉 Congratulations! You Finished {hole_count} Holes! 🎉", title_style))
    elements.append(Spacer(1, 10))
    
    # Course info
    course = data.get('course', {})
    elements.append(Paragraph(f"<b>{course.get('name', 'Golf Course')}</b>", subtitle_style))
    elements.append(Paragraph(f"{course.get('location', '')}", subtitle_style))
    elements.append(Paragraph(f"Date: {data.get('date', datetime.now().strftime('%d-%m-%Y'))}", subtitle_style))
    elements.append(Spacer(1, 20))
    
    # Build scorecard table
    results = data.get('results', [])
    hole_pars = course.get('hole_pars', [4]*18)[:hole_count]
    
    # Header row
    header = ['Rank', 'Player', 'Tee', 'HCP', 'Gross', 'Net', 'vs Par']
    for i in range(1, hole_count + 1):
        header.append(str(i))
    
    # Par row
    par_row = ['', 'PAR', '', '', str(sum(hole_pars)), '', '']
    for par in hole_pars:
        par_row.append(str(par))
    
    table_data = [header, par_row]
    
    # Player rows
    for result in results:
        row = [
            str(result.get('rank', '')),
            result.get('name', '')[:12],
            result.get('tee', '').upper()[:1],
            str(result.get('course_handicap', 0)),
            str(result.get('gross_score', 0)),
            str(result.get('net_score', 0)),
            f"+{result.get('vs_par')}" if result.get('vs_par', 0) > 0 else str(result.get('vs_par', 0))
        ]
        for score in result.get('scores', []):
            row.append(str(score))
        table_data.append(row)
    
    # Create table
    col_widths = [0.4*inch, 1.0*inch, 0.3*inch, 0.4*inch, 0.5*inch, 0.5*inch, 0.5*inch]
    col_widths.extend([0.35*inch] * hole_count)
    
    table = Table(table_data, colWidths=col_widths)
    
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5f2a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#90EE90')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    
    # Alternate row colors
    for i in range(2, len(table_data)):
        if i % 2 == 0:
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f0f0f0'))
    
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Recommendations
    recommendations = data.get('recommendations', [])
    if recommendations:
        elements.append(Paragraph("<b>📋 Recommendations:</b>", styles['Heading2']))
        for rec in recommendations:
            elements.append(Paragraph(f"• {rec}", styles['Normal']))
            elements.append(Spacer(1, 5))
    
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"scorecard_{data.get('date', 'golf')}.pdf"
    )

@app.route('/api/send-email', methods=['POST'])
def send_email():
    """Send scorecard via email (requires SMTP configuration)"""
    data = request.json
    email = data.get('email')
    
    # For demo purposes, return success
    # In production, configure SMTP settings
    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    
    if not smtp_host or not smtp_user:
        return jsonify({
            "success": False, 
            "message": "Email service not configured. Please download the PDF instead."
        }), 503
    
    try:
        # Generate PDF
        # ... (same PDF generation logic)
        
        # Send email with attachment
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = f"Your Golf Scorecard - {data.get('date', '')}"
        
        body = "Please find your golf scorecard attached."
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        return jsonify({"success": True, "message": "Email sent successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
