from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from simulator import FitnessSimulator

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///antidoping.db'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

# Initialize simulator
simulator = FitnessSimulator(socketio)

# Database Models
class Athlete(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    device_id = db.Column(db.String(100))
    
class FitnessMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athlete.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    heart_rate = db.Column(db.Integer)
    steps = db.Column(db.Integer)
    sleep_hours = db.Column(db.Float)
    hrv = db.Column(db.Float)
    
class Supplement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athlete.id'))
    name = db.Column(db.String(100))
    dosage = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    risk_level = db.Column(db.String(20))

# Routes
@app.route('/api/athlete', methods=['GET', 'POST'])
def register_athlete():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            if not data.get('name') or not data.get('email'):
                return jsonify({'error': 'Name and email are required'}), 400
            
            # Check if email already exists
            existing_athlete = Athlete.query.filter_by(email=data['email']).first()
            if existing_athlete:
                return jsonify({'error': 'Email already registered'}), 409
            
            athlete = Athlete(
                name=data['name'],
                email=data['email'],
                device_id=data.get('device_id')
            )
            db.session.add(athlete)
            db.session.commit()
            
            # Start simulation for the new athlete
            simulator.start_simulation(athlete.id)
            
            return jsonify({
                'message': 'Athlete registered successfully',
                'athlete_id': athlete.id
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    else:  # GET request
        try:
            athletes = Athlete.query.all()
            return jsonify([{
                'id': athlete.id,
                'name': athlete.name,
                'email': athlete.email,
                'device_id': athlete.device_id
            } for athlete in athletes])
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/athlete/<athlete_id>', methods=['PUT'])
def update_athlete(athlete_id):
    athlete = Athlete.query.get_or_404(athlete_id)
    data = request.json
    
    athlete.name = data.get('name', athlete.name)
    athlete.email = data.get('email', athlete.email)
    athlete.device_id = data.get('device_id', athlete.device_id)
    
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'})

@app.route('/api/metrics/<athlete_id>', methods=['GET'])
def get_metrics(athlete_id):
    metrics = simulator.get_current_metrics(int(athlete_id))
    if metrics:
        return jsonify(metrics)
    return jsonify({'error': 'Athlete not found'}), 404

@app.route('/api/metrics/<athlete_id>', methods=['POST'])
def add_metrics(athlete_id):
    data = request.json
    metric = FitnessMetric(
        athlete_id=athlete_id,
        heart_rate=data.get('heart_rate'),
        steps=data.get('steps'),
        sleep_hours=data.get('sleep_hours'),
        hrv=data.get('hrv')
    )
    db.session.add(metric)
    db.session.commit()
    
    # Emit real-time update
    socketio.emit('metrics_update', {
        'athlete_id': athlete_id,
        'metrics': data
    })
    return jsonify({'message': 'Metrics added successfully'})

@app.route('/api/supplement/<athlete_id>', methods=['POST'])
def add_supplement(athlete_id):
    data = request.json
    # Basic risk assessment logic
    risk_level = assess_supplement_risk(data['name'])
    
    supplement = Supplement(
        athlete_id=athlete_id,
        name=data['name'],
        dosage=data['dosage'],
        risk_level=risk_level
    )
    db.session.add(supplement)
    db.session.commit()
    
    if risk_level == 'high':
        socketio.emit('risk_alert', {
            'athlete_id': athlete_id,
            'supplement': data['name'],
            'message': 'High risk supplement detected!'
        })
    
    return jsonify({'message': 'Supplement added successfully', 'risk_level': risk_level})

@app.route('/api/supplement/<athlete_id>', methods=['GET'])
def get_supplements(athlete_id):
    supplements = Supplement.query.filter_by(athlete_id=athlete_id).order_by(Supplement.timestamp.desc()).all()
    return jsonify([{
        'name': s.name,
        'dosage': s.dosage,
        'risk_level': s.risk_level,
        'timestamp': s.timestamp.isoformat()
    } for s in supplements])

def assess_supplement_risk(supplement_name):
    # This would connect to a comprehensive database of banned substances
    # For now, using a simple example
    high_risk = ['ephedrine', 'DMAA', 'androstenedione']
    medium_risk = ['caffeine', 'creatine', 'beta-alanine']
    
    supplement_name = supplement_name.lower()
    if supplement_name in high_risk:
        return 'high'
    elif supplement_name in medium_risk:
        return 'medium'
    return 'low'

# Frontend Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard/<athlete_id>')
def dashboard(athlete_id):
    athlete = Athlete.query.get_or_404(athlete_id)
    # Start simulation if not already running
    simulator.start_simulation(int(athlete_id))
    return render_template('dashboard.html', athlete=athlete)

@app.route('/supplements')
def supplements():
    return render_template('supplements.html')

@app.route('/profile')
def profile():
    # For demo purposes, using athlete_id 1
    # In a real app, you'd get this from the session
    athlete = Athlete.query.get_or_404(1)
    return render_template('profile.html', athlete=athlete)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Start simulation for existing athletes
        for athlete in Athlete.query.all():
            simulator.start_simulation(athlete.id)
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
