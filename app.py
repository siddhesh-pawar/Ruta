from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_session import Session
from flask_mail import Mail
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
import secrets
import uuid

from config import Config
from models import Database
from auth import Auth, login_required
from email_utils import mail, send_verification_email, send_welcome_email
import os

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
Session(app)
CORS(app)
mail.init_app(app)

# Initialize services
auth = Auth()
db = Database()

# Store verification tokens temporarily (in production, use Redis or database)
verification_tokens = {}


@app.route('/')
def index():
    """Landing page or home based on auth status"""
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
    """Welcome page for non-authenticated users"""
    return render_template('welcome.html')

  
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']

        res = auth.send_magic_link(
            email,
            redirect_url=url_for('login', _external=True)
        )

        flash('Check your email for the signup link.', 'info')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        res = auth.send_magic_link(email, redirect_url=url_for('login', _external=True))
        flash('Check your email for the login link.', 'info')
        return redirect(url_for('login'))
    return render_template('login.html')


@app.route("/verify_token", methods=["POST"])
def verify_token():
    """Verify Supabase magic link tokens and log user in."""
    data = request.get_json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        return jsonify({"success": False, "error": "Missing access token"}), 400

    try:
        auth.supabase.auth.set_session(access_token, refresh_token)
        user = auth.supabase.auth.get_user()
        
        if user and getattr(user, "user", None):
            user_id = user.user.id
            user_email = user.user.email

            # ✅ Save in session
            session["user_id"] = user_id
            session["email"] = user_email

            if not db.get_user_profile(user_id):
                db.create_user_profile(user_id, user_email)

            intake_data = db.get_user_intake_data(user_id)

            if not intake_data:
                return jsonify({"success": True, "redirect": url_for('tally_form')})
            else:
                return jsonify({"success": True, "redirect": url_for('home')})
        else:
            return jsonify({"success": False, "error": "Invalid user"})
            
    except Exception as e:
        print(f"Verification error: {e}")
        return jsonify({"success": False, "error": str(e)})


        

@app.route('/logout')
def logout():
    """User logout"""
    auth.sign_out()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('welcome'))

@app.route('/home')
@login_required
def home():
    """Home page with personalized recommendations"""
    user_id = session.get('user_id')
    profile = db.get_user_profile(user_id)
    intake_data = db.get_user_intake_data(user_id)
    
    # Generate recommendations (hardcoded for now)
    recommendations = generate_recommendations(intake_data)
    
    return render_template('home.html', profile=profile, recommendations=recommendations)

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    user_id = session.get('user_id')
    profile = db.get_user_profile(user_id)

    # Fetch all intake records (history)
    intake_history = db.supabase.table('comprehensive_intake') \
        .select('*') \
        .eq('user_id', user_id) \
        .order('created_at', desc=True) \
        .execute() \
        .data

    # Use the latest one for analysis (optional)
    latest_intake = intake_history[0] if intake_history else None
    root_causes = analyze_root_causes(latest_intake)

    return render_template(
        'profile.html',
        profile=profile,
        root_causes=root_causes,
        intake_history=intake_history
    )

@app.route('/explore')
@login_required
def explore():
    """Explore page"""
    return render_template('explore.html')

@app.route('/tally-form')
@login_required
def tally_form():
    """Tally intake form page"""
    user_id = session.get('user_id')
    email = session.get('email')
    
    # Pre-fill Tally form with user data
    prefill_data = {
        'user_id': user_id,
        'email': email
    }
    
    return render_template('tally_form.html', prefill_data=prefill_data)

@app.route('/tally-webhook', methods=['POST'])
def tally_webhook():
    """Handle Tally form submission webhook"""
    try:
        data = request.json
           
        # Extract user_id from hidden fields
        fields = data.get('data', {}).get('fields', [])
        user_id = None
           
        for field in fields:
            if field.get('key') == 'question_bdVV96_173643ff-973c-4990-b125-0fe255b0ab67':  # user_id field
                user_id = field.get('value')
                break
           
        if not user_id:
            print("WARNING: No user_id found in webhook data")
            return jsonify({'error': 'Missing user_id'}), 400
           
        # Process and save the comprehensive intake data
        process_tally_data(user_id, data)
           
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 400
    


import uuid
from datetime import datetime

def process_tally_data(user_id, tally_data):
    """Process and save Tally form data to comprehensive_intake table"""
    print("=" * 60)
    print("PROCESSING TALLY WEBHOOK DATA")
    print("=" * 60)
    print(f"Raw webhook payload: {json.dumps(tally_data, indent=2)}")
    
    try:
        # Extract fields from the nested data structure
        fields_array = tally_data.get('data', {}).get('fields', [])
        
        print(f"\nProcessing {len(fields_array)} fields for user {user_id}")
        
        # Build a dictionary mapping field keys to their values
        fields_dict = {}
        
        if isinstance(fields_array, list):
            for field in fields_array:
                key = field.get('key')
                value = field.get('value')
                label = field.get('label')
                
                print(f"Field: {key} | Label: {label} | Value: {value}")
                
                if key:
                    # Handle multiple choice - extract the selected option text
                    if isinstance(value, list) and len(value) > 0:
                        # Get the options array
                        options = field.get('options', [])
                        selected_ids = value
                        
                        # Map selected IDs to their text values
                        selected_texts = []
                        for opt in options:
                            if opt.get('id') in selected_ids:
                                selected_texts.append(opt.get('text'))
                        
                        fields_dict[key] = selected_texts if len(selected_texts) > 1 else (selected_texts[0] if selected_texts else None)
                    else:
                        fields_dict[key] = value
        
        print(f"\nProcessed fields dictionary:")
        for k, v in fields_dict.items():
            print(f"  {k}: {v}")
        
        # Map Tally field keys to database columns based on actual webhook structure
        intake_data = {
            'user_id': user_id,
            'preferred_name': fields_dict.get('question_d9ONWo'),  # "First things first, what would you like us to call you?"
            'birthday': fields_dict.get('question_Y41R5B'),  # "When's your birthday?"
            'location': fields_dict.get('question_D7jK4R'),  # "Where are you living?"
            'biological_sex': fields_dict.get('question_l6xqbk'),  # "What's your biological sex?"
            'goals': fields_dict.get('question_RDAdG9'),  # "What do you hope to get out of Ruta?"
            'chronic_conditions': fields_dict.get('question_o2qDbP'),  # "Do you have any chronic conditions?"
            'medications_supplements': fields_dict.get('question_GRZKxZ'),  # "Are you taking any meds or supplements?"
            'pregnancy_status': fields_dict.get('question_O76lDR'),  # "Are you pregnant, breastfeeding, or planning to be?"
            'has_menstrual_cycle': fields_dict.get('question_VzKjLg'),  # "Do you have a menstrual cycle?"
            'menstrual_symptoms': fields_dict.get('question_Pz7DdV'),  # "Do you experience any of the following related to your menstrual cycle?"
            'bowel_movement_frequency': fields_dict.get('question_Ex25k4'),  # "How often do you have a bowel movement?"
            'bowel_movement_type': fields_dict.get('question_roeBjN'),  # "How would you describe your bowel movements?"
            'digestive_symptoms': fields_dict.get('question_4KMBaX'),  # "Do you notice any of the following related to your digestion?"
            'other_symptoms': fields_dict.get('question_jljbea'),  # "Do you experience any other symptoms?"
            'body_temperature': fields_dict.get('question_2KpBjj'),  # "How does your body temperature run?"
            'nervous_system_signals': fields_dict.get('question_xJAjVr'),  # "Do you notice any of these nervous system signals?"
            'energy_pattern': fields_dict.get('question_RDAdWd'),  # "How's your energy throughout the day?"
            'sleep_pattern': fields_dict.get('question_o2qD9e'),  # "How's your sleep?"
            'movement_level': fields_dict.get('question_GRZKep'),  # "What does your daily movement look like?"
            'appetite_pattern': fields_dict.get('question_O76lQ7'),  # "How's your appetite lately?"
            'diet_type': fields_dict.get('question_VzKjpJ'),  # "Do you eat according to a specific diet?"
            'food_allergies': fields_dict.get('question_Pz7DR5'),  # "Do you have any food allergies or intolerances?"
            'emotional_patterns': fields_dict.get('question_Ex25qX'),  # "Do you experience any of these emotional or stress patterns?"
            'birth_history': fields_dict.get('question_roeBDl'),  # "What's your birth history?"
            'past_medications': fields_dict.get('question_4KMBak'),  # "Have you ever taken any of these in the past?"
            'significant_history': fields_dict.get('question_jljbex'),  # "Do you have a history of any of the following?"
            'updated_at': datetime.utcnow().isoformat()
        }
        
        print("\n" + "=" * 60)
        print("MAPPED INTAKE DATA")
        print("=" * 60)
        for key, value in intake_data.items():
            print(f"{key}: {value}")
        
        # Check if user already has intake data
        existing = db.get_user_intake_data(user_id)
        
        if existing:
            print(f"\n✓ Updating existing intake data for user {user_id}")
            result = db.supabase.table('comprehensive_intake').update(intake_data).eq('user_id', user_id).execute()
        else:
            print(f"\n✓ Creating new intake data for user {user_id}")
            intake_data['id'] = str(uuid.uuid4())
            intake_data['created_at'] = datetime.utcnow().isoformat()
            result = db.supabase.table('comprehensive_intake').insert(intake_data).execute()
        
        print(f"\n✓ Database operation successful!")
        print(f"Result: {result}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ ERROR in process_tally_data: {e}")
        import traceback
        traceback.print_exc()
        raise



def generate_recommendations(intake_data):
    """Generate personalized recommendations based on intake data"""
    # Hardcoded recommendations for now
    # Later will be replaced with RAG chatbot
    
    recommendations = [
        {
            'title': 'Morning Hydration Ritual',
            'category': 'Hydration',
            'description': 'Start your day with warm lemon water to support digestion and detoxification.',
            'icon': '💧'
        },
        {
            'title': 'Probiotic-Rich Foods',
            'category': 'Gut Health',
            'description': 'Include fermented foods like kimchi, sauerkraut, or kefir to support gut bacteria balance.',
            'icon': '🥬'
        },
        {
            'title': '10-Minute Morning Movement',
            'category': 'Exercise',
            'description': 'Gentle stretching or yoga to activate your nervous system and improve circulation.',
            'icon': '🧘'
        },
        {
            'title': 'Mindful Eating Practice',
            'category': 'Digestion',
            'description': 'Chew each bite 20-30 times and eat without distractions to improve nutrient absorption.',
            'icon': '🍽️'
        },
        {
            'title': 'Evening Wind-Down Routine',
            'category': 'Sleep',
            'description': 'No screens 1 hour before bed. Try reading or gentle breathing exercises instead.',
            'icon': '😴'
        },
        {
            'title': 'Anti-Inflammatory Spices',
            'category': 'Nutrition',
            'description': 'Add turmeric, ginger, and cinnamon to meals to reduce inflammation.',
            'icon': '🌿'
        },
        {
            'title': 'Nature Connection',
            'category': 'Mental Health',
            'description': 'Spend 20 minutes outdoors daily for vitamin D and stress reduction.',
            'icon': '🌳'
        },
        {
            'title': 'Breathwork Session',
            'category': 'Stress',
            'description': 'Practice 4-7-8 breathing technique when feeling overwhelmed or anxious.',
            'icon': '🫁'
        },
        {
            'title': 'Magnesium Before Bed',
            'category': 'Supplements',
            'description': 'Consider magnesium glycinate to support better sleep and muscle relaxation.',
            'icon': '💊'
        },
        {
            'title': 'Gratitude Journal',
            'category': 'Mental Wellness',
            'description': 'Write 3 things you\'re grateful for each night to improve mood and perspective.',
            'icon': '📝'
        }
    ]
    
    return recommendations

def analyze_root_causes(intake_data):
    """Analyze root causes based on intake data"""
    # Sample root cause analysis
    root_causes = [
        {
            'title': 'Gut Dysbiosis',
            'description': 'Your gut bacteria may be out of balance, which can cause bloating, gas, and irregular bowel movements.',
            'symptoms': ['Bloating, gas, constipation, loose stools'],
            'drivers': ['Antibiotic history, high sugar intake, stress'],
            'connection': 'Your history of antibiotics and sugar intake weakened beneficial gut bacteria, while stress further disrupted digestion, resulting in bloating and irregular bowel habits.'
        },
        {
            'title': 'Liver & Detox Overload',
            'description': 'Your liver\'s detox pathways may be under strain, which can lead to brain fog, afternoon crashes, and sluggish digestion.',
            'symptoms': ['Fatigue, afternoon crashes, brain fog'],
            'drivers': ['Stress hormones, processed foods'],
            'connection': 'Stress and processed foods put pressure on your detox pathways, leaving you more tired and foggy.'
        }
    ]
    
    return root_causes

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)