from flask import Flask, render_template, request, jsonify, send_file, session, g
from datetime import datetime, timedelta
import json
import io
import os
import re
import secrets
import bcrypt
import bleach
from functools import wraps
from email_validator import validate_email, EmailNotValidError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
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
import requests

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# =====================================
# Input Validation & Sanitization
# =====================================

ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
ALLOWED_ATTRS = {}

def sanitize_string(value, max_length=500, allow_html=False):
    """Sanitize a string input"""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if len(value) > max_length:
        value = value[:max_length]
    if allow_html:
        value = bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    else:
        value = bleach.clean(value, tags=[], strip=True)
    return value

def sanitize_email(email):
    """Validate and sanitize email address"""
    if not email:
        return None
    email = sanitize_string(email, max_length=254).lower()
    try:
        valid = validate_email(email, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError:
        return None

def sanitize_phone(phone):
    """Sanitize phone number - only allow digits, +, -, spaces"""
    if not phone:
        return None
    phone = sanitize_string(phone, max_length=20)
    phone = re.sub(r'[^\d+\-\s()]', '', phone)
    return phone if phone else None

def sanitize_name(name, max_length=100):
    """Sanitize name - allow letters, spaces, hyphens, apostrophes"""
    if not name:
        return None
    name = sanitize_string(name, max_length=max_length)
    # Remove any characters that aren't letters, spaces, hyphens, or apostrophes
    name = re.sub(r"[^\w\s\-']", '', name, flags=re.UNICODE)
    return name.strip() if name else None

def sanitize_id(id_value, max_length=64):
    """Sanitize ID values - only allow alphanumeric and hyphens"""
    if not id_value:
        return None
    id_value = str(id_value)[:max_length]
    id_value = re.sub(r'[^a-zA-Z0-9\-_]', '', id_value)
    return id_value if id_value else None

def sanitize_integer(value, min_val=None, max_val=None, default=0):
    """Sanitize integer input"""
    try:
        value = int(value)
        if min_val is not None and value < min_val:
            value = min_val
        if max_val is not None and value > max_val:
            value = max_val
        return value
    except (ValueError, TypeError):
        return default

def sanitize_float(value, min_val=None, max_val=None, default=0.0):
    """Sanitize float input"""
    try:
        value = float(value)
        if min_val is not None and value < min_val:
            value = min_val
        if max_val is not None and value > max_val:
            value = max_val
        return value
    except (ValueError, TypeError):
        return default

def sanitize_tee(tee):
    """Validate tee selection"""
    valid_tees = ['black', 'blue', 'white', 'red']
    tee = sanitize_string(tee, max_length=10).lower() if tee else 'white'
    return tee if tee in valid_tees else 'white'

def sanitize_otp(otp):
    """Sanitize OTP - only allow 6 digits"""
    if not otp:
        return None
    otp = re.sub(r'\D', '', str(otp))
    return otp[:6] if len(otp) == 6 else None

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password too long (max 128 characters)"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

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
    
    # Create User table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS User (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            isVerified INTEGER DEFAULT 0,
            handicapIndex REAL,
            homeCourse TEXT,
            bio TEXT,
            avatar TEXT,
            city TEXT,
            memberSince TEXT,
            totalRounds INTEGER DEFAULT 0,
            bestScore INTEGER,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create OTP table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS OTP (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            otp TEXT NOT NULL,
            type TEXT NOT NULL,
            expiresAt DATETIME NOT NULL,
            isUsed INTEGER DEFAULT 0,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create ForumPost table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ForumPost (
            id TEXT PRIMARY KEY,
            userId TEXT NOT NULL,
            userName TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            likes INTEGER DEFAULT 0,
            commentCount INTEGER DEFAULT 0,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (userId) REFERENCES User(id)
        )
    ''')
    
    # Create ForumComment table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ForumComment (
            id TEXT PRIMARY KEY,
            postId TEXT NOT NULL,
            userId TEXT NOT NULL,
            userName TEXT NOT NULL,
            content TEXT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (postId) REFERENCES ForumPost(id) ON DELETE CASCADE,
            FOREIGN KEY (userId) REFERENCES User(id)
        )
    ''')
    
    # Create ForumLike table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ForumLike (
            id TEXT PRIMARY KEY,
            postId TEXT NOT NULL,
            userId TEXT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(postId, userId),
            FOREIGN KEY (postId) REFERENCES ForumPost(id) ON DELETE CASCADE,
            FOREIGN KEY (userId) REFERENCES User(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Resend API configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'Golf Scorecard <noreply@golf-scorecard.com>')

# =====================================
# Email OTP Functions
# =====================================

def generate_otp():
    """Generate a secure 6-digit OTP using cryptographic random"""
    return ''.join(secrets.choice('0123456789') for _ in range(6))

def hash_password(password):
    """Hash password using bcrypt"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

def _legacy_hash_password(password):
    """Legacy SHA256 hash for migration purposes only"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against bcrypt hash, with fallback for legacy SHA256 hashes"""
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
    else:
        password_bytes = password
    if isinstance(hashed, str):
        hashed_str = hashed
        hashed_bytes = hashed.encode('utf-8')
    else:
        hashed_str = hashed.decode('utf-8')
        hashed_bytes = hashed
    
    # Try bcrypt first (new format)
    try:
        if hashed_str.startswith('$2'):  # bcrypt hash prefix
            return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        pass
    
    # Fallback to legacy SHA256 check for migration
    try:
        if len(hashed_str) == 64:  # SHA256 hex length
            return _legacy_hash_password(password) == hashed_str
    except Exception:
        pass
    
    return False

def migrate_password_if_legacy(user_id, password, hashed):
    """Migrate legacy SHA256 password to bcrypt"""
    if isinstance(hashed, str) and len(hashed) == 64 and not hashed.startswith('$2'):
        # This is a legacy SHA256 hash, migrate to bcrypt
        try:
            new_hash = hash_password(password)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('UPDATE User SET password = ? WHERE id = ?', (new_hash, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception:
            pass
    return False

def get_otp_email_template(otp, otp_type='verify'):
    """Generate HTML email template for OTP"""
    if otp_type == 'verify':
        title = 'Verify Your Email'
        message = 'Thank you for registering with Golf Scorecard Indonesia. Please use the following OTP to verify your email address.'
    elif otp_type == 'login':
        title = 'Login Verification'
        message = 'You are trying to login to Golf Scorecard Indonesia. Please use the following OTP to complete your login.'
    elif otp_type == 'reset':
        title = 'Reset Your Password'
        message = 'You have requested to reset your password for Golf Scorecard Indonesia. Please use the following OTP to proceed.'
    else:
        title = 'Your OTP Code'
        message = 'Here is your OTP code for Golf Scorecard Indonesia.'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td align="center" style="padding: 40px 0;">
                    <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #0A241C 0%, #0F3B2E 50%, #C9A84E 100%); padding: 40px 30px; text-align: center; border-radius: 16px 16px 0 0;">
                                <div style="font-size: 48px; margin-bottom: 10px;">⛳</div>
                                <h1 style="color: #F3F1EC; margin: 0; font-size: 28px; font-weight: bold;">Golf Scorecard</h1>
                                <p style="color: #E6C36A; margin: 5px 0 0 0; font-size: 14px;">Indonesia Edition</p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                <h2 style="color: #0A241C; margin: 0 0 20px 0; font-size: 24px; text-align: center;">{title}</h2>
                                <p style="color: #4b5563; font-size: 16px; line-height: 1.6; text-align: center; margin: 0 0 30px 0;">
                                    {message}
                                </p>
                                
                                <!-- OTP Box -->
                                <div style="background: linear-gradient(135deg, #F3F1EC 0%, #E8E4DA 100%); border: 2px solid #E6C36A; border-radius: 12px; padding: 30px; text-align: center; margin: 0 0 30px 0;">
                                    <p style="color: #6b7280; font-size: 14px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 1px;">Your OTP Code</p>
                                    <div style="font-size: 40px; font-weight: bold; color: #0A241C; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                                        {otp}
                                    </div>
                                </div>
                                
                                <p style="color: #9ca3af; font-size: 14px; text-align: center; margin: 0;">
                                    ⏱️ This code will expire in <strong>5 minutes</strong>
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Warning -->
                        <tr>
                            <td style="padding: 0 30px 30px 30px;">
                                <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 0 8px 8px 0;">
                                    <p style="color: #92400e; font-size: 13px; margin: 0;">
                                        ⚠️ <strong>Security Notice:</strong> Never share this OTP with anyone. Our team will never ask for your OTP.
                                    </p>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f9fafb; padding: 25px 30px; text-align: center; border-radius: 0 0 16px 16px; border-top: 1px solid #e5e7eb;">
                                <p style="color: #6b7280; font-size: 12px; margin: 0 0 10px 0;">
                                    🏌️ Track your scores across premium Indonesian golf courses
                                </p>
                                <p style="color: #9ca3af; font-size: 11px; margin: 0;">
                                    © 2026 Golf Scorecard Indonesia. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    '''

def send_otp_email(email, otp, otp_type='verify'):
    """Send OTP email using Resend API"""
    try:
        if otp_type == 'verify':
            subject = '🔐 Verify Your Email - Golf Scorecard Indonesia'
        elif otp_type == 'login':
            subject = '🔑 Login Verification - Golf Scorecard Indonesia'
        elif otp_type == 'reset':
            subject = '🔄 Password Reset - Golf Scorecard Indonesia'
        else:
            subject = '📧 Your OTP Code - Golf Scorecard Indonesia'
        
        html_content = get_otp_email_template(otp, otp_type)
        
        response = requests.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {RESEND_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'from': RESEND_FROM_EMAIL,
                'to': [email],
                'subject': subject,
                'html': html_content
            }
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json()
    except Exception as e:
        return False, str(e)

def save_otp(email, otp, otp_type):
    """Save OTP to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    otp_id = secrets.token_hex(16)
    expires_at = datetime.now() + timedelta(minutes=5)
    
    # Invalidate previous OTPs for this email and type
    cursor.execute('''
        UPDATE OTP SET isUsed = 1 WHERE email = ? AND type = ? AND isUsed = 0
    ''', (email, otp_type))
    
    cursor.execute('''
        INSERT INTO OTP (id, email, otp, type, expiresAt) VALUES (?, ?, ?, ?, ?)
    ''', (otp_id, email, otp, otp_type, expires_at))
    
    conn.commit()
    conn.close()
    return otp_id

def verify_otp(email, otp, otp_type):
    """Verify OTP from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id FROM OTP 
        WHERE email = ? AND otp = ? AND type = ? AND isUsed = 0 AND expiresAt > ?
    ''', (email, otp, otp_type, datetime.now()))
    
    result = cursor.fetchone()
    
    if result:
        # Mark OTP as used
        cursor.execute('UPDATE OTP SET isUsed = 1 WHERE id = ?', (result[0],))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

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
        },
        {
            "id": "senayan",
            "name": "Senayan National Golf Club",
            "location": "Jakarta Pusat",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.8, "slope": 136},
                "blue": {"rating": 71.5, "slope": 131},
                "white": {"rating": 69.2, "slope": 125},
                "red": {"rating": 67.8, "slope": 120}
            }
        },
        {
            "id": "royale",
            "name": "Royale Jakarta Golf Club",
            "location": "Jakarta Timur",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 73.2, "slope": 134},
                "blue": {"rating": 71.0, "slope": 129},
                "white": {"rating": 68.8, "slope": 124},
                "red": {"rating": 67.2, "slope": 119}
            }
        },
        {
            "id": "cengkareng",
            "name": "Cengkareng Golf Club",
            "location": "Jakarta Barat",
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
        },
        {
            "id": "alam_sutera",
            "name": "Alam Sutera Golf & Country Club",
            "location": "Tangerang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 73.5, "slope": 135},
                "blue": {"rating": 71.2, "slope": 130},
                "white": {"rating": 69.0, "slope": 124},
                "red": {"rating": 67.5, "slope": 119}
            }
        },
        {
            "id": "imperial_klub",
            "name": "Imperial Klub Golf",
            "location": "Tangerang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.8, "slope": 132},
                "blue": {"rating": 70.5, "slope": 127},
                "white": {"rating": 68.2, "slope": 122},
                "red": {"rating": 66.8, "slope": 117}
            }
        }
    ],
    "bekasi": [
        {
            "id": "jababeka",
            "name": "Jababeka Golf & Country Club",
            "location": "Cikarang, Bekasi",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.0, "slope": 133},
                "blue": {"rating": 70.8, "slope": 128},
                "white": {"rating": 68.5, "slope": 122},
                "red": {"rating": 67.0, "slope": 117}
            }
        },
        {
            "id": "emeralda",
            "name": "Emeralda Golf Club",
            "location": "Cikarang, Bekasi",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 74.0, "slope": 138},
                "blue": {"rating": 71.8, "slope": 133},
                "white": {"rating": 69.5, "slope": 127},
                "red": {"rating": 68.0, "slope": 122}
            }
        },
        {
            "id": "lippo_cikarang",
            "name": "Lippo Cikarang Golf",
            "location": "Cikarang, Bekasi",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.2, "slope": 129},
                "blue": {"rating": 70.0, "slope": 124},
                "white": {"rating": 67.8, "slope": 119},
                "red": {"rating": 66.2, "slope": 114}
            }
        }
    ],
    "karawang": [
        {
            "id": "karawang",
            "name": "Karawang International Golf",
            "location": "Karawang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 73.5, "slope": 136},
                "blue": {"rating": 71.2, "slope": 131},
                "white": {"rating": 69.0, "slope": 125},
                "red": {"rating": 67.5, "slope": 120}
            }
        },
        {
            "id": "singaperbangsa",
            "name": "Singaperbangsa Golf Club",
            "location": "Karawang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.0, "slope": 128},
                "blue": {"rating": 69.8, "slope": 123},
                "white": {"rating": 67.5, "slope": 118},
                "red": {"rating": 66.0, "slope": 113}
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
        },
        {
            "id": "sentul_highlands",
            "name": "Sentul Highlands Golf Club",
            "location": "Sentul, Bogor",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 74.8, "slope": 144},
                "blue": {"rating": 72.5, "slope": 139},
                "white": {"rating": 70.2, "slope": 132},
                "red": {"rating": 68.8, "slope": 127}
            }
        },
        {
            "id": "klub_bogor_raya",
            "name": "Klub Golf Bogor Raya",
            "location": "Bogor",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.2, "slope": 134},
                "blue": {"rating": 71.0, "slope": 129},
                "white": {"rating": 68.8, "slope": 123},
                "red": {"rating": 67.2, "slope": 118}
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
        },
        {
            "id": "parahyangan",
            "name": "Parahyangan Golf Bandung",
            "location": "Bandung",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.0, "slope": 132},
                "blue": {"rating": 70.8, "slope": 127},
                "white": {"rating": 68.5, "slope": 121},
                "red": {"rating": 67.0, "slope": 116}
            }
        },
        {
            "id": "bandung_giri_gahana",
            "name": "Bandung Giri Gahana Golf",
            "location": "Jatinangor, Bandung",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 72.5, "slope": 129},
                "blue": {"rating": 70.2, "slope": 124},
                "white": {"rating": 68.0, "slope": 119},
                "red": {"rating": 66.5, "slope": 114}
            }
        }
    ],
    "semarang": [
        {
            "id": "semarang_golf",
            "name": "Semarang Golf Club",
            "location": "Semarang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.5, "slope": 130},
                "blue": {"rating": 70.2, "slope": 125},
                "white": {"rating": 68.0, "slope": 120},
                "red": {"rating": 66.5, "slope": 115}
            }
        },
        {
            "id": "gombel",
            "name": "Gombel Golf Club",
            "location": "Semarang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 71.8, "slope": 127},
                "blue": {"rating": 69.5, "slope": 122},
                "white": {"rating": 67.2, "slope": 117},
                "red": {"rating": 65.8, "slope": 112}
            }
        }
    ],
    "yogyakarta": [
        {
            "id": "merapi",
            "name": "Merapi Golf Club",
            "location": "Yogyakarta",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.0, "slope": 128},
                "blue": {"rating": 69.8, "slope": 123},
                "white": {"rating": 67.5, "slope": 118},
                "red": {"rating": 66.0, "slope": 113}
            }
        },
        {
            "id": "hyatt_yogya",
            "name": "Hyatt Regency Yogyakarta Golf",
            "location": "Yogyakarta",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 71.5, "slope": 126},
                "blue": {"rating": 69.2, "slope": 121},
                "white": {"rating": 67.0, "slope": 116},
                "red": {"rating": 65.5, "slope": 111}
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
        },
        {
            "id": "bukit_darmo",
            "name": "Bukit Darmo Golf",
            "location": "Surabaya",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 71.8, "slope": 127},
                "blue": {"rating": 69.5, "slope": 122},
                "white": {"rating": 67.2, "slope": 117},
                "red": {"rating": 65.8, "slope": 112}
            }
        },
        {
            "id": "yani_golf",
            "name": "Yani Golf Club",
            "location": "Surabaya",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 72.0, "slope": 128},
                "blue": {"rating": 69.8, "slope": 123},
                "white": {"rating": 67.5, "slope": 118},
                "red": {"rating": 66.0, "slope": 113}
            }
        }
    ],
    "malang": [
        {
            "id": "taman_dayu",
            "name": "Taman Dayu Golf Club",
            "location": "Pasuruan, Malang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.5, "slope": 136},
                "blue": {"rating": 71.2, "slope": 131},
                "white": {"rating": 69.0, "slope": 125},
                "red": {"rating": 67.5, "slope": 120}
            }
        },
        {
            "id": "malang_golf",
            "name": "Malang Golf & Country Club",
            "location": "Malang",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 72.2, "slope": 129},
                "blue": {"rating": 70.0, "slope": 124},
                "white": {"rating": 67.8, "slope": 119},
                "red": {"rating": 66.2, "slope": 114}
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
        },
        {
            "id": "new_kuta",
            "name": "New Kuta Golf",
            "location": "Pecatu, Bali",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 74.2, "slope": 141},
                "blue": {"rating": 72.0, "slope": 136},
                "white": {"rating": 69.8, "slope": 129},
                "red": {"rating": 68.2, "slope": 124}
            }
        },
        {
            "id": "bukit_pandawa",
            "name": "Bukit Pandawa Golf & Country Club",
            "location": "Kutuh, Bali",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.5, "slope": 138},
                "blue": {"rating": 71.2, "slope": 133},
                "white": {"rating": 69.0, "slope": 126},
                "red": {"rating": 67.5, "slope": 121}
            }
        }
    ],
    "batam": [
        {
            "id": "palm_springs",
            "name": "Palm Springs Golf & Beach Resort",
            "location": "Batam",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 73.0, "slope": 133},
                "blue": {"rating": 70.8, "slope": 128},
                "white": {"rating": 68.5, "slope": 122},
                "red": {"rating": 67.0, "slope": 117}
            }
        },
        {
            "id": "southlinks",
            "name": "Southlinks Country Club",
            "location": "Batam",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.5, "slope": 131},
                "blue": {"rating": 70.2, "slope": 126},
                "white": {"rating": 68.0, "slope": 121},
                "red": {"rating": 66.5, "slope": 116}
            }
        },
        {
            "id": "tering_bay",
            "name": "Tering Bay Golf & Country Club",
            "location": "Batam",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.2, "slope": 134},
                "blue": {"rating": 71.0, "slope": 129},
                "white": {"rating": 68.8, "slope": 123},
                "red": {"rating": 67.2, "slope": 118}
            }
        }
    ],
    "medan": [
        {
            "id": "medan_golf",
            "name": "Medan Golf Club",
            "location": "Medan",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 72.0, "slope": 128},
                "blue": {"rating": 69.8, "slope": 123},
                "white": {"rating": 67.5, "slope": 118},
                "red": {"rating": 66.0, "slope": 113}
            }
        },
        {
            "id": "tiara_medan",
            "name": "Tiara Medan Golf & Country Club",
            "location": "Medan",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 71.5, "slope": 126},
                "blue": {"rating": 69.2, "slope": 121},
                "white": {"rating": 67.0, "slope": 116},
                "red": {"rating": 65.5, "slope": 111}
            }
        }
    ],
    "makassar": [
        {
            "id": "makassar_golf",
            "name": "Makassar Golf Club",
            "location": "Makassar",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 71.8, "slope": 127},
                "blue": {"rating": 69.5, "slope": 122},
                "white": {"rating": 67.2, "slope": 117},
                "red": {"rating": 65.8, "slope": 112}
            }
        },
        {
            "id": "barombong",
            "name": "Barombong Golf & Country Club",
            "location": "Makassar",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 4, 3, 5, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 72.2, "slope": 129},
                "blue": {"rating": 70.0, "slope": 124},
                "white": {"rating": 67.8, "slope": 119},
                "red": {"rating": 66.2, "slope": 114}
            }
        }
    ],
    "lombok": [
        {
            "id": "lombok_golf",
            "name": "Lombok Golf Kosaido Country Club",
            "location": "Lombok",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 73.0, "slope": 133},
                "blue": {"rating": 70.8, "slope": 128},
                "white": {"rating": 68.5, "slope": 122},
                "red": {"rating": 67.0, "slope": 117}
            }
        }
    ],
    "bintan": [
        {
            "id": "laguna_bintan",
            "name": "Laguna Bintan Golf Club",
            "location": "Bintan",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 5, 3, 4, 4, 3, 5, 4, 4, 4, 5, 3, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 74.0, "slope": 139},
                "blue": {"rating": 71.8, "slope": 134},
                "white": {"rating": 69.5, "slope": 127},
                "red": {"rating": 68.0, "slope": 122}
            }
        },
        {
            "id": "ria_bintan",
            "name": "Ria Bintan Golf Club",
            "location": "Bintan",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 5, 3, 4, 4, 4, 5, 3, 4, 4, 5, 3, 4, 4, 4, 5, 3, 4],
            "tees": {
                "black": {"rating": 74.5, "slope": 142},
                "blue": {"rating": 72.2, "slope": 137},
                "white": {"rating": 70.0, "slope": 130},
                "red": {"rating": 68.5, "slope": 125}
            }
        },
        {
            "id": "bintan_lagoon",
            "name": "Bintan Lagoon Resort Golf",
            "location": "Bintan",
            "holes": 18,
            "par": {"9": 36, "18": 72},
            "hole_pars": [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
            "tees": {
                "black": {"rating": 73.5, "slope": 137},
                "blue": {"rating": 71.2, "slope": 132},
                "white": {"rating": 69.0, "slope": 125},
                "red": {"rating": 67.5, "slope": 120}
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

# =====================================
# Authentication API Routes
# =====================================

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Register a new user and send OTP"""
    data = request.json or {}
    
    # Sanitize inputs
    email = sanitize_email(data.get('email', ''))
    password = data.get('password', '')
    name = sanitize_name(data.get('name', ''))
    phone = sanitize_phone(data.get('phone', ''))
    
    if not email:
        return jsonify({'success': False, 'message': 'Valid email is required'}), 400
    
    if not name:
        return jsonify({'success': False, 'message': 'Name is required'}), 400
    
    # Validate password strength
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return jsonify({'success': False, 'message': error_msg}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute('SELECT id, isVerified FROM User WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            if existing_user[1]:  # isVerified
                conn.close()
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            else:
                # User exists but not verified, update and resend OTP
                cursor.execute('''
                    UPDATE User SET password = ?, name = ?, phone = ?, updatedAt = ? WHERE email = ?
                ''', (hash_password(password), name, phone, datetime.now(), email))
                conn.commit()
        else:
            # Create new user
            user_id = secrets.token_hex(16)
            cursor.execute('''
                INSERT INTO User (id, email, password, name, phone) VALUES (?, ?, ?, ?, ?)
            ''', (user_id, email, hash_password(password), name, phone))
            conn.commit()
        
        conn.close()
        
        # Generate and send OTP
        otp = generate_otp()
        save_otp(email, otp, 'verify')
        success, result = send_otp_email(email, otp, 'verify')
        
        if success:
            return jsonify({'success': True, 'message': 'OTP sent to your email'})
        else:
            return jsonify({'success': True, 'message': 'Account created. OTP sending may be delayed.'})
    except Exception as e:
        conn.close()
        app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 500


@app.route('/api/auth/verify-register', methods=['POST'])
@limiter.limit("10 per minute")
def verify_register():
    """Verify registration OTP"""
    data = request.json or {}
    email = sanitize_email(data.get('email', ''))
    otp = sanitize_otp(data.get('otp', ''))
    
    if not email or not otp:
        return jsonify({'success': False, 'message': 'Valid email and OTP are required'}), 400
    
    if verify_otp(email, otp, 'verify'):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE User SET isVerified = 1, updatedAt = ? WHERE email = ?', (datetime.now(), email))
        
        # Get user data
        cursor.execute('SELECT id, name, email FROM User WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_email'] = user[2]
            session.permanent = True
            return jsonify({
                'success': True, 
                'message': 'Email verified successfully',
                'user': {'id': user[0], 'name': user[1], 'email': user[2]}
            })
    
    return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400


@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Login and send OTP"""
    data = request.json or {}
    email = sanitize_email(data.get('email', ''))
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, password, isVerified FROM User WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        # Use constant-time comparison to prevent timing attacks
        verify_password(password, hash_password('dummy'))
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    if not verify_password(password, user[2]):
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    # Migrate legacy password hash to bcrypt if needed
    migrate_password_if_legacy(user[0], password, user[2])
    
    if not user[3]:  # isVerified
        return jsonify({'success': False, 'message': 'Please verify your email first', 'needVerification': True}), 401
    
    # Generate and send OTP
    otp = generate_otp()
    save_otp(email, otp, 'login')
    success, result = send_otp_email(email, otp, 'login')
    
    return jsonify({'success': True, 'message': 'OTP sent to your email'})


@app.route('/api/auth/verify-login', methods=['POST'])
@limiter.limit("10 per minute")
def verify_login():
    """Verify login OTP"""
    data = request.json or {}
    email = sanitize_email(data.get('email', ''))
    otp = sanitize_otp(data.get('otp', ''))
    
    if not email or not otp:
        return jsonify({'success': False, 'message': 'Valid email and OTP are required'}), 400
    
    if verify_otp(email, otp, 'login'):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, email FROM User WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_email'] = user[2]
            session.permanent = True
            return jsonify({
                'success': True, 
                'message': 'Login successful',
                'user': {'id': user[0], 'name': user[1], 'email': user[2]}
            })
    
    return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400


@app.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit("5 per minute")
def forgot_password():
    """Request password reset OTP"""
    data = request.json or {}
    email = sanitize_email(data.get('email', ''))
    
    if not email:
        return jsonify({'success': False, 'message': 'Valid email is required'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM User WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    # Always return same response to prevent email enumeration
    if user:
        otp = generate_otp()
        save_otp(email, otp, 'reset')
        send_otp_email(email, otp, 'reset')
    
    return jsonify({'success': True, 'message': 'If the email exists, OTP will be sent'})


@app.route('/api/auth/verify-reset', methods=['POST'])
@limiter.limit("10 per minute")
def verify_reset():
    """Verify reset OTP"""
    data = request.json or {}
    email = sanitize_email(data.get('email', ''))
    otp = sanitize_otp(data.get('otp', ''))
    
    if not email or not otp:
        return jsonify({'success': False, 'message': 'Valid email and OTP are required'}), 400
    
    if verify_otp(email, otp, 'reset'):
        # Generate a temporary token for password reset
        reset_token = secrets.token_hex(32)
        session['reset_email'] = email
        session['reset_token'] = reset_token
        session['reset_expires'] = (datetime.now() + timedelta(minutes=15)).isoformat()
        return jsonify({'success': True, 'message': 'OTP verified', 'resetToken': reset_token})
    
    return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400


@app.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit("5 per minute")
def reset_password():
    """Reset password with verified token"""
    data = request.json or {}
    email = sanitize_email(data.get('email', ''))
    reset_token = sanitize_string(data.get('resetToken', ''), max_length=64)
    new_password = data.get('newPassword', '')
    
    if not email or not reset_token or not new_password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    # Validate password strength
    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        return jsonify({'success': False, 'message': error_msg}), 400
    
    # Verify reset token and check expiration
    if session.get('reset_email') != email or session.get('reset_token') != reset_token:
        return jsonify({'success': False, 'message': 'Invalid reset token'}), 400
    
    # Check token expiration
    reset_expires = session.get('reset_expires')
    if reset_expires and datetime.fromisoformat(reset_expires) < datetime.now():
        session.pop('reset_email', None)
        session.pop('reset_token', None)
        session.pop('reset_expires', None)
        return jsonify({'success': False, 'message': 'Reset token has expired'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE User SET password = ?, updatedAt = ? WHERE email = ?', 
                   (hash_password(new_password), datetime.now(), email))
    conn.commit()
    conn.close()
    
    # Clear reset session
    session.pop('reset_email', None)
    session.pop('reset_token', None)
    session.pop('reset_expires', None)
    
    return jsonify({'success': True, 'message': 'Password reset successfully'})


@app.route('/api/auth/resend-otp', methods=['POST'])
@limiter.limit("3 per minute")
def resend_otp():
    """Resend OTP"""
    data = request.json or {}
    email = sanitize_email(data.get('email', ''))
    otp_type = sanitize_string(data.get('type', 'verify'), max_length=10)
    
    if not email:
        return jsonify({'success': False, 'message': 'Valid email is required'}), 400
    
    if otp_type not in ['verify', 'login', 'reset']:
        return jsonify({'success': False, 'message': 'Invalid OTP type'}), 400
    
    # Generate and send new OTP
    otp = generate_otp()
    save_otp(email, otp, otp_type)
    success, result = send_otp_email(email, otp, otp_type)
    
    if success:
        return jsonify({'success': True, 'message': 'OTP resent successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again.'})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@app.route('/api/auth/me')
def get_current_user():
    """Get current logged in user"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session.get('user_id'),
                'name': session.get('user_name'),
                'email': session.get('user_email')
            }
        })
    return jsonify({'authenticated': False})


@app.route('/api/profile')
def get_profile():
    """Get current user's full profile"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, email, name, phone, handicapIndex, homeCourse, bio, avatar, city, 
               memberSince, totalRounds, bestScore, createdAt
        FROM User WHERE id = ?
    ''', (session['user_id'],))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(dict(user))


@app.route('/api/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update current user's profile"""
    data = request.json or {}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Sanitize and validate each field
    updates = []
    values = []
    
    if 'name' in data:
        name = sanitize_name(data['name'])
        if name:
            updates.append('name = ?')
            values.append(name)
    
    if 'phone' in data:
        phone = sanitize_phone(data['phone'])
        updates.append('phone = ?')
        values.append(phone)
    
    if 'handicapIndex' in data:
        handicap = sanitize_float(data['handicapIndex'], min_val=-10.0, max_val=54.0, default=None)
        updates.append('handicapIndex = ?')
        values.append(handicap)
    
    if 'homeCourse' in data:
        home_course = sanitize_string(data['homeCourse'], max_length=200)
        updates.append('homeCourse = ?')
        values.append(home_course)
    
    if 'bio' in data:
        bio = sanitize_string(data['bio'], max_length=1000)
        updates.append('bio = ?')
        values.append(bio)
    
    if 'avatar' in data:
        # Validate avatar URL or data
        avatar = sanitize_string(data['avatar'], max_length=500)
        if avatar and (avatar.startswith('data:image/') or avatar.startswith('https://')):
            updates.append('avatar = ?')
            values.append(avatar)
    
    if 'city' in data:
        city = sanitize_string(data['city'], max_length=100)
        updates.append('city = ?')
        values.append(city)
    
    if not updates:
        conn.close()
        return jsonify({'error': 'No valid fields to update'}), 400
    
    updates.append('updatedAt = CURRENT_TIMESTAMP')
    values.append(session['user_id'])
    
    query = f"UPDATE User SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, values)
    
    # Update session if name changed
    if 'name' in data and sanitize_name(data['name']):
        session['user_name'] = sanitize_name(data['name'])
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Profile updated successfully'})


@app.route('/api/profile/stats')
@require_auth
def get_profile_stats():
    """Get user's golf statistics"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    user_id = session['user_id']
    
    # Get total rounds played
    cursor.execute('''
        SELECT COUNT(DISTINCT g.id) as totalRounds,
               MIN(p.totalScore) as bestScore,
               AVG(p.totalScore) as avgScore
        FROM Game g
        JOIN Player p ON g.id = p.gameId
        WHERE p.name = (SELECT name FROM User WHERE id = ?)
    ''', (user_id,))
    
    stats = cursor.fetchone()
    
    # Get courses played
    cursor.execute('''
        SELECT COUNT(DISTINCT c.id) as coursesPlayed
        FROM Game g
        JOIN Course c ON g.courseId = c.id
        JOIN Player p ON g.id = p.gameId
        WHERE p.name = (SELECT name FROM User WHERE id = ?)
    ''', (user_id,))
    
    courses = cursor.fetchone()
    
    # Get recent games
    cursor.execute('''
        SELECT g.date, c.name as courseName, p.totalScore, g.holeCount
        FROM Game g
        JOIN Course c ON g.courseId = c.id
        JOIN Player p ON g.id = p.gameId
        WHERE p.name = (SELECT name FROM User WHERE id = ?)
        ORDER BY g.date DESC
        LIMIT 5
    ''', (user_id,))
    
    recent_games = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'totalRounds': stats['totalRounds'] or 0,
        'bestScore': stats['bestScore'],
        'avgScore': round(stats['avgScore'], 1) if stats['avgScore'] else None,
        'coursesPlayed': courses['coursesPlayed'] or 0,
        'recentGames': recent_games
    })


@app.route('/api/profile/change-password', methods=['POST'])
@require_auth
@limiter.limit("5 per hour")
def change_password():
    """Change user's password"""
    data = request.json or {}
    current_password = data.get('currentPassword', '')
    new_password = data.get('newPassword', '')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password required'}), 400
    
    # Validate new password strength
    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify current password
    cursor.execute('SELECT password FROM User WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    if not user or not verify_password(current_password, user[0]):
        conn.close()
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    # Update password with bcrypt
    hashed_password = hash_password(new_password)
    cursor.execute('UPDATE User SET password = ?, updatedAt = CURRENT_TIMESTAMP WHERE id = ?',
                   (hashed_password, session['user_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Password changed successfully'})


# =====================================
# Forum API Routes
# =====================================

@app.route('/api/forum/posts', methods=['GET'])
def get_forum_posts():
    """Get all forum posts"""
    category = request.args.get('category', None)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if category and category != 'all':
        cursor.execute('''
            SELECT * FROM ForumPost WHERE category = ? ORDER BY createdAt DESC
        ''', (category,))
    else:
        cursor.execute('SELECT * FROM ForumPost ORDER BY createdAt DESC')
    
    posts = [dict(row) for row in cursor.fetchall()]
    
    # Check if current user has liked each post
    user_id = session.get('user_id')
    if user_id:
        for post in posts:
            cursor.execute('SELECT id FROM ForumLike WHERE postId = ? AND userId = ?', 
                          (post['id'], user_id))
            post['isLiked'] = cursor.fetchone() is not None
    
    conn.close()
    return jsonify(posts)


@app.route('/api/forum/posts', methods=['POST'])
@require_auth
@limiter.limit("10 per hour")
def create_forum_post():
    """Create a new forum post"""
    data = request.json or {}
    
    # Sanitize inputs
    title = sanitize_string(data.get('title', ''), max_length=200)
    content = sanitize_string(data.get('content', ''), max_length=5000, allow_html=True)
    category = sanitize_string(data.get('category', 'general'), max_length=50)
    
    # Validate category
    valid_categories = ['general', 'tips', 'equipment', 'courses', 'tournaments', 'other']
    if category not in valid_categories:
        category = 'general'
    
    if not title or len(title) < 3:
        return jsonify({'success': False, 'message': 'Title must be at least 3 characters'}), 400
    
    if not content or len(content) < 10:
        return jsonify({'success': False, 'message': 'Content must be at least 10 characters'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    post_id = secrets.token_hex(16)
    cursor.execute('''
        INSERT INTO ForumPost (id, userId, userName, title, content, category)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (post_id, session['user_id'], sanitize_name(session['user_name']), title, content, category))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True, 
        'message': 'Post created successfully',
        'postId': post_id
    })


@app.route('/api/forum/posts/<post_id>', methods=['GET'])
def get_forum_post(post_id):
    """Get a single forum post with comments"""
    # Sanitize post_id
    post_id = sanitize_id(post_id)
    if not post_id:
        return jsonify({'error': 'Invalid post ID'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM ForumPost WHERE id = ?', (post_id,))
    post = cursor.fetchone()
    
    if not post:
        conn.close()
        return jsonify({'error': 'Post not found'}), 404
    
    post = dict(post)
    
    # Get comments
    cursor.execute('SELECT * FROM ForumComment WHERE postId = ? ORDER BY createdAt ASC', (post_id,))
    post['comments'] = [dict(row) for row in cursor.fetchall()]
    
    # Check if current user has liked
    user_id = session.get('user_id')
    if user_id:
        cursor.execute('SELECT id FROM ForumLike WHERE postId = ? AND userId = ?', (post_id, user_id))
        post['isLiked'] = cursor.fetchone() is not None
    
    conn.close()
    return jsonify(post)


@app.route('/api/forum/posts/<post_id>', methods=['DELETE'])
@require_auth
def delete_forum_post(post_id):
    """Delete a forum post"""
    # Sanitize post_id
    post_id = sanitize_id(post_id)
    if not post_id:
        return jsonify({'success': False, 'message': 'Invalid post ID'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if user owns the post
    cursor.execute('SELECT userId FROM ForumPost WHERE id = ?', (post_id,))
    post = cursor.fetchone()
    
    if not post:
        conn.close()
        return jsonify({'success': False, 'message': 'Post not found'}), 404
    
    if post[0] != session['user_id']:
        conn.close()
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    cursor.execute('DELETE FROM ForumPost WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Post deleted'})


@app.route('/api/forum/posts/<post_id>/comments', methods=['POST'])
@require_auth
@limiter.limit("30 per hour")
def add_forum_comment(post_id):
    """Add a comment to a post"""
    # Sanitize post_id
    post_id = sanitize_id(post_id)
    if not post_id:
        return jsonify({'success': False, 'message': 'Invalid post ID'}), 400
    
    data = request.json or {}
    content = sanitize_string(data.get('content', ''), max_length=2000)
    
    if not content or len(content) < 1:
        return jsonify({'success': False, 'message': 'Comment cannot be empty'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if post exists
    cursor.execute('SELECT id FROM ForumPost WHERE id = ?', (post_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Post not found'}), 404
    
    comment_id = secrets.token_hex(16)
    cursor.execute('''
        INSERT INTO ForumComment (id, postId, userId, userName, content)
        VALUES (?, ?, ?, ?, ?)
    ''', (comment_id, post_id, session['user_id'], sanitize_name(session['user_name']), content))
    
    # Update comment count
    cursor.execute('UPDATE ForumPost SET commentCount = commentCount + 1 WHERE id = ?', (post_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Comment added',
        'comment': {
            'id': comment_id,
            'content': content,
            'userName': sanitize_name(session['user_name']),
            'createdAt': datetime.now().isoformat()
        }
    })


@app.route('/api/forum/posts/<post_id>/like', methods=['POST'])
@require_auth
@limiter.limit("60 per hour")
def toggle_forum_like(post_id):
    """Toggle like on a post"""
    # Sanitize post_id
    post_id = sanitize_id(post_id)
    if not post_id:
        return jsonify({'success': False, 'message': 'Invalid post ID'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify post exists
    cursor.execute('SELECT id FROM ForumPost WHERE id = ?', (post_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Post not found'}), 404
    
    # Check if already liked
    cursor.execute('SELECT id FROM ForumLike WHERE postId = ? AND userId = ?', 
                  (post_id, session['user_id']))
    existing = cursor.fetchone()
    
    if existing:
        # Unlike
        cursor.execute('DELETE FROM ForumLike WHERE id = ?', (existing[0],))
        cursor.execute('UPDATE ForumPost SET likes = MAX(0, likes - 1) WHERE id = ?', (post_id,))
        liked = False
    else:
        # Like
        like_id = secrets.token_hex(16)
        cursor.execute('INSERT INTO ForumLike (id, postId, userId) VALUES (?, ?, ?)',
                      (like_id, post_id, session['user_id']))
        cursor.execute('UPDATE ForumPost SET likes = likes + 1 WHERE id = ?', (post_id,))
        liked = True
    
    # Get new like count
    cursor.execute('SELECT likes FROM ForumPost WHERE id = ?', (post_id,))
    result = cursor.fetchone()
    likes = result[0] if result else 0
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'liked': liked, 'likes': likes})


# Events Service Proxy Routes
EVENTS_SERVICE_URL = os.environ.get('EVENTS_SERVICE_URL', 'http://localhost:5001')

@app.route('/api/events', methods=['GET', 'POST'])
def proxy_events():
    try:
        if request.method == 'GET':
            resp = requests.get(f'{EVENTS_SERVICE_URL}/api/events', params=request.args, timeout=10)
        else:
            resp = requests.post(f'{EVENTS_SERVICE_URL}/api/events', json=request.json, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Events service unavailable', 'details': str(e)}), 503

@app.route('/api/events/<int:event_id>', methods=['GET', 'PUT', 'DELETE'])
def proxy_event_detail(event_id):
    try:
        if request.method == 'GET':
            resp = requests.get(f'{EVENTS_SERVICE_URL}/api/events/{event_id}', timeout=10)
        elif request.method == 'PUT':
            resp = requests.put(f'{EVENTS_SERVICE_URL}/api/events/{event_id}', json=request.json, timeout=10)
        else:
            resp = requests.delete(f'{EVENTS_SERVICE_URL}/api/events/{event_id}', timeout=10)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Events service unavailable', 'details': str(e)}), 503

@app.route('/api/events/<int:event_id>/register', methods=['POST'])
def proxy_event_register(event_id):
    try:
        resp = requests.post(f'{EVENTS_SERVICE_URL}/api/events/{event_id}/register', json=request.json, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Events service unavailable', 'details': str(e)}), 503

@app.route('/api/events/<int:event_id>/registrations', methods=['GET'])
def proxy_event_registrations(event_id):
    try:
        resp = requests.get(f'{EVENTS_SERVICE_URL}/api/events/{event_id}/registrations', timeout=10)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Events service unavailable', 'details': str(e)}), 503

@app.route('/api/events/<int:event_id>/cancel-registration', methods=['POST'])
def proxy_cancel_registration(event_id):
    try:
        resp = requests.post(f'{EVENTS_SERVICE_URL}/api/events/{event_id}/cancel-registration', json=request.json, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Events service unavailable', 'details': str(e)}), 503

@app.route('/api/event-templates', methods=['GET'])
def proxy_event_templates():
    try:
        resp = requests.get(f'{EVENTS_SERVICE_URL}/api/event-templates', timeout=10)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Events service unavailable', 'details': str(e)}), 503


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
@limiter.limit("20 per hour")
def create_player():
    """Create a new player"""
    data = request.json or {}
    
    # Sanitize inputs
    name = sanitize_name(data.get('name', ''))
    email = sanitize_email(data.get('email', ''))
    
    if not name or len(name) < 2:
        return jsonify({"error": "Valid name is required"}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        player_id = generate_id()
        cursor.execute('''
            INSERT INTO Player (id, name, email)
            VALUES (?, ?, ?)
        ''', (player_id, name, email))
        conn.commit()
        conn.close()
        return jsonify({"id": player_id, "name": name, "email": email})
    except Exception as e:
        app.logger.error(f"Error creating player: {e}")
        return jsonify({"error": "Failed to create player"}), 500


@app.route('/api/calculate', methods=['POST'])
def calculate_scores():
    data = request.json or {}
    
    # Sanitize inputs
    course_id = sanitize_id(data.get('course_id'))
    hole_count = sanitize_integer(data.get('hole_count', 18), min_val=9, max_val=18, default=18)
    game_id = sanitize_id(data.get('game_id'))
    players = data.get('players', [])
    
    if not course_id:
        return jsonify({"error": "Course ID is required"}), 400
    
    if not isinstance(players, list) or len(players) == 0:
        return jsonify({"error": "At least one player is required"}), 400
    
    if len(players) > 8:
        return jsonify({"error": "Maximum 8 players allowed"}), 400
    
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
        # Sanitize player data
        name = sanitize_name(player.get('name', ''), max_length=50)
        if not name:
            continue
            
        email = sanitize_email(player.get('email', ''))
        tee = sanitize_tee(player.get('tee', 'white'))
        handicap_index = sanitize_float(player.get('handicap', 0), min_val=-10, max_val=54, default=0)
        
        # Sanitize scores
        raw_scores = player.get('scores', [])
        if not isinstance(raw_scores, list):
            continue
        scores = [sanitize_integer(s, min_val=1, max_val=20, default=5) for s in raw_scores[:hole_count]]
        
        if len(scores) != hole_count:
            continue
        
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
            'name': name,
            'email': email,
            'tee': tee,
            'handicap_index': handicap_index,
            'course_handicap': course_handicap,
            'gross_score': gross_score,
            'net_score': net_score,
            'vs_par': gross_score - total_par,
            'holes': hole_details,
            'scores': scores
        })
    
    if not results:
        return jsonify({"error": "No valid player data provided"}), 400
    
    # Sort by net score for ranking
    results.sort(key=lambda x: x['net_score'])
    for i, r in enumerate(results):
        r['rank'] = i + 1
    
    recommendations = generate_recommendations(
        [{'name': p['name'], 'scores': p.get('scores', [])} for p in results],
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
            app.logger.error(f"Error saving results: {e}")
    
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
        textColor=colors.HexColor('#0F3B2E')
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
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F3B2E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#E6C36A')),
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
@limiter.limit("10 per hour")
def send_email():
    """Send scorecard via email (requires SMTP configuration)"""
    data = request.json or {}
    email = sanitize_email(data.get('email', ''))
    
    if not email:
        return jsonify({
            "success": False, 
            "message": "Valid email address is required."
        }), 400
    
    # In production, configure SMTP settings
    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_port = sanitize_integer(os.environ.get('SMTP_PORT', 587), min_val=1, max_val=65535, default=587)
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    
    if not smtp_host or not smtp_user:
        return jsonify({
            "success": False, 
            "message": "Email service not configured. Please download the PDF instead."
        }), 503
    
    try:
        # Send email with attachment
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = f"Your Golf Scorecard - {sanitize_string(data.get('date', ''), max_length=20)}"
        
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
        app.logger.error(f"Email sending failed: {e}")
        return jsonify({"success": False, "message": "Failed to send email. Please try again."}), 500

if __name__ == '__main__':
    # Use environment for debug mode
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=5000, debug=debug)
