from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import secrets
import os
import re
import bleach
from email_validator import validate_email, EmailNotValidError

app = Flask(__name__)

# Configure CORS with specific origins in production
allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
CORS(app, origins=allowed_origins, supports_credentials=True)

# API Key for internal service communication
API_KEY = os.environ.get('EVENTS_SERVICE_API_KEY', 'golf-events-internal-key-2024')

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def require_api_key(f):
    """Decorator to require API key for internal requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({'error': 'Unauthorized - Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_user_from_headers():
    """Extract user info from headers set by main app"""
    return {
        'user_id': request.headers.get('X-User-Id'),
        'email': request.headers.get('X-User-Email'),
        'name': request.headers.get('X-User-Name')
    }

# =====================================
# Input Validation & Sanitization
# =====================================

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
        value = bleach.clean(value, tags=['b', 'i', 'u', 'em', 'strong', 'p', 'br'], strip=True)
    else:
        value = bleach.clean(value, tags=[], strip=True)
    return value

def sanitize_email_input(email):
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
    """Sanitize phone number"""
    if not phone:
        return None
    phone = sanitize_string(phone, max_length=20)
    phone = re.sub(r'[^\d+\-\s()]', '', phone)
    return phone if phone else None

def sanitize_name(name, max_length=100):
    """Sanitize name"""
    if not name:
        return None
    name = sanitize_string(name, max_length=max_length)
    name = re.sub(r"[^\w\s\-']", '', name, flags=re.UNICODE)
    return name.strip() if name else None

def sanitize_id(id_value, max_length=64):
    """Sanitize ID values"""
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

def sanitize_date(date_str):
    """Validate and sanitize date string"""
    if not date_str:
        return None
    try:
        # Parse and validate date format
        dt = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None

# Database initialization
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'events.db')

def init_db():
    """Initialize SQLite database with required tables"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Event table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Event (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            eventType TEXT NOT NULL DEFAULT 'tournament',
            courseId TEXT,
            courseName TEXT,
            location TEXT,
            eventDate DATE NOT NULL,
            startTime TIME,
            endTime TIME,
            registrationDeadline DATETIME,
            maxParticipants INTEGER DEFAULT 100,
            currentParticipants INTEGER DEFAULT 0,
            entryFee REAL DEFAULT 0,
            currency TEXT DEFAULT 'IDR',
            prizes TEXT,
            rules TEXT,
            contactPerson TEXT,
            contactPhone TEXT,
            contactEmail TEXT,
            imageUrl TEXT,
            status TEXT DEFAULT 'upcoming',
            isPublished INTEGER DEFAULT 1,
            createdBy TEXT,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create EventRegistration table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS EventRegistration (
            id TEXT PRIMARY KEY,
            eventId TEXT NOT NULL,
            userId TEXT,
            playerName TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            handicap REAL,
            teePreference TEXT DEFAULT 'white',
            registrationDate DATETIME DEFAULT CURRENT_TIMESTAMP,
            paymentStatus TEXT DEFAULT 'pending',
            notes TEXT,
            FOREIGN KEY (eventId) REFERENCES Event(id) ON DELETE CASCADE
        )
    ''')
    
    # Create EventTemplate table for standard templates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS EventTemplate (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            eventType TEXT NOT NULL,
            description TEXT,
            defaultRules TEXT,
            defaultPrizes TEXT,
            isDefault INTEGER DEFAULT 0,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # Insert default templates if not exist
    cursor.execute('SELECT COUNT(*) FROM EventTemplate')
    if cursor.fetchone()[0] == 0:
        default_templates = [
            {
                'id': secrets.token_hex(8),
                'name': 'Standard Tournament',
                'eventType': 'tournament',
                'description': 'A standard golf tournament with stroke play format.',
                'defaultRules': '''Tournament Rules:
1. USGA Rules of Golf apply
2. Stroke play format (18 holes)
3. Maximum handicap: 36 for men, 40 for women
4. Tee time start - players must report 30 minutes before
5. Pace of play: Maximum 4 hours 30 minutes
6. All players must have valid handicap index
7. Local rules as posted on course
8. Decision of tournament committee is final''',
                'defaultPrizes': '''Prizes:
🥇 1st Place: Trophy + Voucher IDR 5,000,000
🥈 2nd Place: Trophy + Voucher IDR 3,000,000
🥉 3rd Place: Trophy + Voucher IDR 2,000,000
🎯 Nearest to Pin: Golf Equipment
🏌️ Longest Drive: Golf Equipment
⭐ Best Net Score: Special Prize''',
                'isDefault': 1
            },
            {
                'id': secrets.token_hex(8),
                'name': 'Monthly Medal',
                'eventType': 'medal',
                'description': 'Monthly medal competition for club members.',
                'defaultRules': '''Medal Competition Rules:
1. USGA Rules of Golf apply
2. Stroke play - Net score competition
3. Players compete in their respective flights
4. All scores must be attested
5. Maximum score per hole: Net double bogey
6. Players must complete all 18 holes
7. Scorecards must be submitted within 30 minutes''',
                'defaultPrizes': '''Prizes:
🏆 Overall Winner: Monthly Medal + Pro Shop Voucher
Flight A Winner: Certificate + Golf Balls
Flight B Winner: Certificate + Golf Balls
Flight C Winner: Certificate + Golf Balls''',
                'isDefault': 0
            },
            {
                'id': secrets.token_hex(8),
                'name': 'Corporate Outing',
                'eventType': 'corporate',
                'description': 'Corporate golf outing with team format.',
                'defaultRules': '''Corporate Event Rules:
1. Best Ball/Scramble format
2. Teams of 4 players
3. Each player must contribute minimum 3 drives
4. Maximum handicap: 24
5. Shotgun start
6. Pace of play strictly enforced
7. Dress code: Smart casual golf attire
8. Caddies provided''',
                'defaultPrizes': '''Prizes:
🏆 Best Team Score: Trophy + Company Vouchers
🎯 Nearest to Pin (All Par 3s): Individual Prizes
🏌️ Longest Drive: Individual Prize
🍀 Lucky Draw: Various Prizes
🎁 Door Prizes for All Participants''',
                'isDefault': 0
            },
            {
                'id': secrets.token_hex(8),
                'name': 'Charity Golf',
                'eventType': 'charity',
                'description': 'Charity golf event to raise funds for good causes.',
                'defaultRules': '''Charity Event Rules:
1. Four-ball better ball format
2. All skill levels welcome
3. Mulligans available for purchase (max 2)
4. String game available
5. Participation is more important than winning
6. All proceeds go to charity
7. Auction and raffle after golf
8. Dinner included in entry fee''',
                'defaultPrizes': '''Recognition:
🏆 Winning Team: Charity Champion Trophy
⭐ Top Fundraiser: Special Recognition
🎯 Skill Prizes: Various Categories
🎁 Raffle & Auction Items
📜 Certificate of Participation for All''',
                'isDefault': 0
            },
            {
                'id': secrets.token_hex(8),
                'name': 'Junior Golf Clinic',
                'eventType': 'clinic',
                'description': 'Golf clinic and training for junior players.',
                'defaultRules': '''Clinic Guidelines:
1. Age groups: 8-12, 13-17
2. All equipment provided
3. Professional instruction included
4. Focus on fundamentals and etiquette
5. Safety briefing mandatory
6. Parents welcome to observe
7. Certificate of completion provided
8. Light refreshments included''',
                'defaultPrizes': '''Awards:
⭐ Most Improved Player
🎯 Best Short Game
🏌️ Best Swing
🤝 Best Sportsmanship
📜 Completion Certificate for All
🎁 Participation Gifts''',
                'isDefault': 0
            }
        ]
        
        for template in default_templates:
            cursor.execute('''
                INSERT INTO EventTemplate (id, name, eventType, description, defaultRules, defaultPrizes, isDefault)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (template['id'], template['name'], template['eventType'], 
                  template['description'], template['defaultRules'], template['defaultPrizes'], template['isDefault']))
        
        conn.commit()
    
    conn.close()

# Initialize database on startup
init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# =====================================
# Event Templates API
# =====================================

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all event templates"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM EventTemplate ORDER BY isDefault DESC, name')
    templates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(templates)

@app.route('/api/templates/<template_id>', methods=['GET'])
def get_template(template_id):
    """Get a single template"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM EventTemplate WHERE id = ?', (template_id,))
    template = cursor.fetchone()
    conn.close()
    
    if template:
        return jsonify(dict(template))
    return jsonify({'error': 'Template not found'}), 404

# =====================================
# Events CRUD API
# =====================================

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all events with optional filters"""
    status = request.args.get('status', None)
    event_type = request.args.get('type', None)
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM Event WHERE isPublished = 1'
    params = []
    
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    if event_type:
        query += ' AND eventType = ?'
        params.append(event_type)
    
    query += ' ORDER BY eventDate ASC'
    
    cursor.execute(query, params)
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(events)

@app.route('/api/events/<event_id>', methods=['GET'])
def get_event(event_id):
    """Get a single event with registrations count"""
    # Sanitize event_id
    event_id = sanitize_id(event_id)
    if not event_id:
        return jsonify({'error': 'Invalid event ID'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM Event WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    
    if not event:
        conn.close()
        return jsonify({'error': 'Event not found'}), 404
    
    event = dict(event)
    
    # Get registration count
    cursor.execute('SELECT COUNT(*) FROM EventRegistration WHERE eventId = ?', (event_id,))
    event['registrationCount'] = cursor.fetchone()[0]
    
    conn.close()
    return jsonify(event)

@app.route('/api/events', methods=['POST'])
@limiter.limit("10 per hour")
@require_api_key
def create_event():
    """Create a new event"""
    data = request.json or {}
    
    # Sanitize and validate all inputs
    title = sanitize_string(data.get('title', ''), max_length=200)
    if not title or len(title) < 3:
        return jsonify({'success': False, 'message': 'Title is required (min 3 characters)'}), 400
    
    event_date = sanitize_date(data.get('eventDate'))
    if not event_date:
        return jsonify({'success': False, 'message': 'Valid event date is required'}), 400
    
    # Sanitize other fields
    description = sanitize_string(data.get('description', ''), max_length=5000, allow_html=True)
    event_type = sanitize_string(data.get('eventType', 'tournament'), max_length=50)
    valid_types = ['tournament', 'medal', 'corporate', 'charity', 'clinic', 'other']
    if event_type not in valid_types:
        event_type = 'tournament'
    
    course_id = sanitize_id(data.get('courseId'))
    course_name = sanitize_string(data.get('courseName', ''), max_length=200)
    location = sanitize_string(data.get('location', ''), max_length=300)
    start_time = sanitize_string(data.get('startTime', ''), max_length=10)
    end_time = sanitize_string(data.get('endTime', ''), max_length=10)
    registration_deadline = sanitize_date(data.get('registrationDeadline'))
    max_participants = sanitize_integer(data.get('maxParticipants', 100), min_val=1, max_val=1000, default=100)
    entry_fee = sanitize_float(data.get('entryFee', 0), min_val=0, max_val=100000000, default=0)
    currency = sanitize_string(data.get('currency', 'IDR'), max_length=10)
    valid_currencies = ['IDR', 'USD', 'SGD']
    if currency not in valid_currencies:
        currency = 'IDR'
    prizes = sanitize_string(data.get('prizes', ''), max_length=2000, allow_html=True)
    rules = sanitize_string(data.get('rules', ''), max_length=5000, allow_html=True)
    contact_person = sanitize_name(data.get('contactPerson', ''))
    contact_phone = sanitize_phone(data.get('contactPhone', ''))
    contact_email = sanitize_email_input(data.get('contactEmail', ''))
    image_url = data.get('imageUrl', '')
    # Validate image - accept base64 data URLs (max 5MB ~= 7MB string) or https URLs
    if image_url:
        if image_url.startswith('data:image/'):
            if len(image_url) > 7 * 1024 * 1024:
                return jsonify({'error': 'Image too large (max 5MB)'}), 400
        elif not (image_url.startswith('https://') or image_url.startswith('/')):
            image_url = None
    created_by = sanitize_id(data.get('createdBy'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    event_id = secrets.token_hex(16)
    
    cursor.execute('''
        INSERT INTO Event (
            id, title, description, eventType, courseId, courseName, location,
            eventDate, startTime, endTime, registrationDeadline, maxParticipants,
            entryFee, currency, prizes, rules, contactPerson, contactPhone,
            contactEmail, imageUrl, status, createdBy
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event_id, title, description, event_type, course_id, course_name, location,
        event_date, start_time, end_time, registration_deadline, max_participants,
        entry_fee, currency, prizes, rules, contact_person, contact_phone,
        contact_email, image_url, 'upcoming', created_by
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Event created successfully',
        'eventId': event_id
    })

@app.route('/api/events/<event_id>', methods=['PUT'])
@require_api_key
def update_event(event_id):
    """Update an event"""
    data = request.json
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if event exists
    cursor.execute('SELECT id FROM Event WHERE id = ?', (event_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Event not found'}), 404
    
    # Build update query dynamically
    update_fields = []
    params = []
    
    allowed_fields = [
        'title', 'description', 'eventType', 'courseId', 'courseName', 'location',
        'eventDate', 'startTime', 'endTime', 'registrationDeadline', 'maxParticipants',
        'entryFee', 'currency', 'prizes', 'rules', 'contactPerson', 'contactPhone',
        'contactEmail', 'imageUrl', 'status', 'isPublished'
    ]
    
    for field in allowed_fields:
        if field in data:
            update_fields.append(f'{field} = ?')
            params.append(data[field])
    
    if update_fields:
        update_fields.append('updatedAt = ?')
        params.append(datetime.now().isoformat())
        params.append(event_id)
        
        query = f'UPDATE Event SET {", ".join(update_fields)} WHERE id = ?'
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()
    
    return jsonify({'success': True, 'message': 'Event updated successfully'})

@app.route('/api/events/<event_id>', methods=['DELETE'])
@limiter.limit("10 per hour")
@require_api_key
def delete_event(event_id):
    """Delete an event"""
    # Sanitize event_id
    event_id = sanitize_id(event_id)
    if not event_id:
        return jsonify({'success': False, 'message': 'Invalid event ID'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM Event WHERE id = ?', (event_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Event not found'}), 404
    
    cursor.execute('DELETE FROM Event WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Event deleted successfully'})

# =====================================
# Event Registration API
# =====================================

@app.route('/api/events/<event_id>/register', methods=['POST'])
@limiter.limit("20 per hour")
@require_api_key
def register_for_event(event_id):
    """Register for an event"""
    # Sanitize event_id
    event_id = sanitize_id(event_id)
    if not event_id:
        return jsonify({'success': False, 'message': 'Invalid event ID'}), 400
    
    data = request.json or {}
    
    # Sanitize and validate inputs
    player_name = sanitize_name(data.get('playerName', ''))
    email = sanitize_email_input(data.get('email', ''))
    
    if not player_name or len(player_name) < 2:
        return jsonify({'success': False, 'message': 'Valid player name is required'}), 400
    
    if not email:
        return jsonify({'success': False, 'message': 'Valid email is required'}), 400
    
    # Sanitize other fields
    user_id = sanitize_id(data.get('userId'))
    phone = sanitize_phone(data.get('phone', ''))
    handicap = sanitize_float(data.get('handicap'), min_val=-10, max_val=54, default=None)
    tee_preference = sanitize_string(data.get('teePreference', 'white'), max_length=10)
    valid_tees = ['black', 'blue', 'white', 'red']
    if tee_preference not in valid_tees:
        tee_preference = 'white'
    notes = sanitize_string(data.get('notes', ''), max_length=500)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if event exists and has capacity
    cursor.execute('SELECT maxParticipants, currentParticipants, registrationDeadline, status FROM Event WHERE id = ?', (event_id,))
    event = cursor.fetchone()
    
    if not event:
        conn.close()
        return jsonify({'success': False, 'message': 'Event not found'}), 404
    
    if event['status'] != 'upcoming':
        conn.close()
        return jsonify({'success': False, 'message': 'Registration is closed'}), 400
    
    if event['currentParticipants'] >= event['maxParticipants']:
        conn.close()
        return jsonify({'success': False, 'message': 'Event is full'}), 400
    
    # Check for duplicate registration
    cursor.execute('SELECT id FROM EventRegistration WHERE eventId = ? AND email = ?', (event_id, email))
    if cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Already registered with this email'}), 400
    
    # Create registration
    reg_id = secrets.token_hex(16)
    cursor.execute('''
        INSERT INTO EventRegistration (id, eventId, userId, playerName, email, phone, handicap, teePreference, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        reg_id, event_id, user_id, player_name, email,
        phone, handicap, tee_preference, notes
    ))
    
    # Update participant count
    cursor.execute('UPDATE Event SET currentParticipants = currentParticipants + 1 WHERE id = ?', (event_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'registrationId': reg_id
    })

@app.route('/api/events/<event_id>/registrations', methods=['GET'])
def get_event_registrations(event_id):
    """Get all registrations for an event"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM EventRegistration WHERE eventId = ? ORDER BY registrationDate DESC', (event_id,))
    registrations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(registrations)

@app.route('/api/registrations/<reg_id>', methods=['DELETE'])
def cancel_registration(reg_id):
    """Cancel a registration"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT eventId FROM EventRegistration WHERE id = ?', (reg_id,))
    reg = cursor.fetchone()
    
    if not reg:
        conn.close()
        return jsonify({'success': False, 'message': 'Registration not found'}), 404
    
    event_id = reg['eventId']
    
    cursor.execute('DELETE FROM EventRegistration WHERE id = ?', (reg_id,))
    cursor.execute('UPDATE Event SET currentParticipants = currentParticipants - 1 WHERE id = ?', (event_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Registration cancelled'})

@app.route('/api/events/<event_id>/cancel-registration', methods=['POST'])
@require_api_key
def cancel_event_registration(event_id):
    """Cancel registration for an event by user ID or email"""
    event_id = sanitize_id(event_id)
    if not event_id:
        return jsonify({'success': False, 'message': 'Invalid event ID'}), 400
    
    data = request.json or {}
    user_id = sanitize_id(data.get('userId'))
    email = sanitize_email_input(data.get('email', ''))
    
    if not user_id and not email:
        return jsonify({'success': False, 'message': 'User ID or email required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Find the registration
    if user_id:
        cursor.execute('SELECT id FROM EventRegistration WHERE eventId = ? AND userId = ?', (event_id, user_id))
    else:
        cursor.execute('SELECT id FROM EventRegistration WHERE eventId = ? AND email = ?', (event_id, email))
    
    reg = cursor.fetchone()
    
    if not reg:
        conn.close()
        return jsonify({'success': False, 'message': 'Registration not found'}), 404
    
    reg_id = reg['id']
    
    cursor.execute('DELETE FROM EventRegistration WHERE id = ?', (reg_id,))
    cursor.execute('UPDATE Event SET currentParticipants = currentParticipants - 1 WHERE id = ?', (event_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Registration cancelled'})


@app.route('/api/user-data', methods=['DELETE'])
@require_api_key
def delete_user_data():
    """Delete all data associated with a user (for account deletion)"""
    data = request.json or {}
    user_id = sanitize_id(data.get('userId'))
    email = sanitize_email_input(data.get('email', ''))
    
    if not user_id and not email:
        return jsonify({'success': False, 'message': 'User ID or email required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    deleted_count = 0
    
    # Delete registrations by user ID
    if user_id:
        cursor.execute('SELECT eventId FROM EventRegistration WHERE userId = ?', (user_id,))
        event_ids = [row['eventId'] for row in cursor.fetchall()]
        cursor.execute('DELETE FROM EventRegistration WHERE userId = ?', (user_id,))
        deleted_count += cursor.rowcount
        # Update participant counts
        for event_id in event_ids:
            cursor.execute('UPDATE Event SET currentParticipants = currentParticipants - 1 WHERE id = ? AND currentParticipants > 0', (event_id,))
    
    # Delete registrations by email
    if email:
        cursor.execute('SELECT eventId FROM EventRegistration WHERE email = ? AND (userId IS NULL OR userId != ?)', (email, user_id or ''))
        event_ids = [row['eventId'] for row in cursor.fetchall()]
        cursor.execute('DELETE FROM EventRegistration WHERE email = ? AND (userId IS NULL OR userId != ?)', (email, user_id or ''))
        deleted_count += cursor.rowcount
        # Update participant counts
        for event_id in event_ids:
            cursor.execute('UPDATE Event SET currentParticipants = currentParticipants - 1 WHERE id = ? AND currentParticipants > 0', (event_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Deleted {deleted_count} registration(s)'})


# =====================================
# Health Check
# =====================================

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'service': 'events-service'})

@app.route('/')
def index():
    return jsonify({
        'service': 'Golf Events Service',
        'version': '1.0.0',
        'endpoints': [
            'GET /api/templates',
            'GET /api/events',
            'POST /api/events',
            'GET /api/events/<id>',
            'PUT /api/events/<id>',
            'DELETE /api/events/<id>',
            'POST /api/events/<id>/register',
            'GET /api/events/<id>/registrations'
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
