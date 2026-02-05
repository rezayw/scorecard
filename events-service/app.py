from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import secrets
import os

app = Flask(__name__)
CORS(app)

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
def create_event():
    """Create a new event"""
    data = request.json
    
    required_fields = ['title', 'eventDate']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} is required'}), 400
    
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
        event_id,
        data.get('title'),
        data.get('description'),
        data.get('eventType', 'tournament'),
        data.get('courseId'),
        data.get('courseName'),
        data.get('location'),
        data.get('eventDate'),
        data.get('startTime'),
        data.get('endTime'),
        data.get('registrationDeadline'),
        data.get('maxParticipants', 100),
        data.get('entryFee', 0),
        data.get('currency', 'IDR'),
        data.get('prizes'),
        data.get('rules'),
        data.get('contactPerson'),
        data.get('contactPhone'),
        data.get('contactEmail'),
        data.get('imageUrl'),
        'upcoming',
        data.get('createdBy')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Event created successfully',
        'eventId': event_id
    })

@app.route('/api/events/<event_id>', methods=['PUT'])
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
def delete_event(event_id):
    """Delete an event"""
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
def register_for_event(event_id):
    """Register for an event"""
    data = request.json
    
    if not data.get('playerName') or not data.get('email'):
        return jsonify({'success': False, 'message': 'Name and email are required'}), 400
    
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
    cursor.execute('SELECT id FROM EventRegistration WHERE eventId = ? AND email = ?', (event_id, data['email']))
    if cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Already registered with this email'}), 400
    
    # Create registration
    reg_id = secrets.token_hex(16)
    cursor.execute('''
        INSERT INTO EventRegistration (id, eventId, userId, playerName, email, phone, handicap, teePreference, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        reg_id, event_id, data.get('userId'), data['playerName'], data['email'],
        data.get('phone'), data.get('handicap'), data.get('teePreference', 'white'), data.get('notes')
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
