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

"""
@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        # Sign up user
        response = auth.sign_up(email, password)
        
        if 'error' in response:
            flash(f'Signup failed: {response["error"]}', 'danger')
            return redirect(url_for('signup'))
        
        if response.user:
            # Create user profile
            user_id = response.user.id
            db.create_user_profile(user_id, email, full_name)
            
            # Generate and store verification token
            token = secrets.token_urlsafe(32)
            verification_tokens[token] = {
                'user_id': user_id,
                'email': email,
                'expires': datetime.utcnow() + timedelta(hours=24)
            }
            
            # Send verification email
            if send_verification_email(email, token):
                flash('Account created! Please check your email to verify your account.', 'success')
            else:
                flash('Account created but verification email failed. Please contact support.', 'warning')
            
            return redirect(url_for('login'))
    
    return render_template('signup.html')

"""

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup with email verification"""
    if request.method == 'POST':
        # Debug: Print all form data
        print("=" * 50)
        print("SIGNUP FORM SUBMISSION")
        print("=" * 50)
        print(f"All form data: {dict(request.form)}")
        
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        print(f"Extracted values:")
        print(f"  - Email: {email}")
        print(f"  - Password: {'*' * len(password) if password else 'None'}")
        print(f"  - Full name: '{full_name}' (type: {type(full_name)}, length: {len(full_name) if full_name else 0})")
        
        # Check if full_name is empty
        if not full_name:
            print("WARNING: full_name is None or empty!")
            full_name = email.split('@')[0] if email else "User"
            print(f"Using fallback full_name: {full_name}")
        elif full_name.strip() == '':
            print("WARNING: full_name contains only whitespace!")
            full_name = email.split('@')[0] if email else "User"
            print(f"Using fallback full_name: {full_name}")
        
        # Sign up user with Supabase Auth
        print(f"\nCalling auth.sign_up for email: {email}")
        response = auth.sign_up(email, password)
        
        if 'error' in response:
            print(f"ERROR: Signup failed - {response['error']}")
            flash(f'Signup failed: {response["error"]}', 'danger')
            return redirect(url_for('signup'))
        
        if response.user:
            user_id = response.user.id
            print(f"SUCCESS: User created with ID: {user_id}")
            
            # Create user profile
            print(f"\nCreating profile:")
            print(f"  - user_id: {user_id}")
            print(f"  - email: {email}")
            print(f"  - full_name: '{full_name}'")
            
            profile_result = db.create_user_profile(user_id, email, full_name)
            
            if profile_result:
                print(f"SUCCESS: Profile created - {profile_result}")
                
                # Verify what was actually saved
                saved_profile = db.get_user_profile(user_id)
                if saved_profile:
                    print(f"\nVERIFICATION - Profile in database:")
                    print(f"  - id: {saved_profile.get('id')}")
                    print(f"  - email: {saved_profile.get('email')}")
                    print(f"  - full_name: '{saved_profile.get('full_name')}'")
                    print(f"  - created_at: {saved_profile.get('created_at')}")
            else:
                print("ERROR: Failed to create profile!")
            
            # Generate and store verification token
            token = secrets.token_urlsafe(32)
            verification_tokens[token] = {
                'user_id': user_id,
                'email': email,
                'expires': datetime.utcnow() + timedelta(hours=24)
            }
            
            # Send verification email
            if send_verification_email(email, token):
                flash('Account created! Please check your email to verify your account.', 'success')
            else:
                flash('Account created but verification email failed. Please contact support.', 'warning')
            
            print("=" * 50)
            print("SIGNUP COMPLETE")
            print("=" * 50)
            
            return redirect(url_for('login'))
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        response = auth.sign_in(email, password)
        
        if 'error' in response:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
        
        if response.user:
            session['user_id'] = response.user.id
            session['email'] = response.user.email
            session['access_token'] = response.session.access_token
            
            # Check if user has completed intake form
            intake_data = db.get_user_intake_data(response.user.id)
            
            if not intake_data:
                # First time user - redirect to Tally form
                return redirect(url_for('tally_form'))
            else:
                # Returning user - go to home
                return redirect(url_for('home'))
    
    return render_template('login.html')

@app.route('/verify-email/<token>')
def verify_email(token):
    """Verify email with token"""
    if token in verification_tokens:
        token_data = verification_tokens[token]
        
        # Check if token expired
        if datetime.utcnow() > token_data['expires']:
            del verification_tokens[token]
            flash('Verification link has expired. Please sign up again.', 'danger')
            return redirect(url_for('signup'))
        
        # Mark user as verified (update profile)
        db.update_user_profile(token_data['user_id'], {'email_verified': True})
        
        # Send welcome email
        send_welcome_email(token_data['email'], token_data['email'].split('@')[0])
        
        # Clean up token
        del verification_tokens[token]
        
        flash('Email verified successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    flash('Invalid verification link.', 'danger')
    return redirect(url_for('signup'))

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
    intake_data = db.get_user_intake_data(user_id)
    
    # Generate root cause analysis
    root_causes = analyze_root_causes(intake_data)
    
    return render_template('profile.html', profile=profile, root_causes=root_causes)

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
    

# def process_tally_data(user_id, tally_data):
#     """Process and save Tally form data to comprehensive_intake table"""
#     try:
#         # Extract all fields from Tally response
#         fields = tally_data.get('fields', {})
        
#         intake_data = {
#             'user_id': user_id,
#             'preferred_name': fields.get('preferred_name', {}).get('value'),
#             'birthday': fields.get('birthday', {}).get('value'),
#             'location': fields.get('location', {}).get('value'),
#             'biological_sex': fields.get('biological_sex', {}).get('value'),
#             'goals': fields.get('goals', {}).get('value'),
#             'chronic_conditions': fields.get('chronic_conditions', {}).get('value'),
#             'medications_supplements': fields.get('medications_supplements', {}).get('value'),
#             'pregnancy_status': fields.get('pregnancy_status', {}).get('value'),
#             'has_menstrual_cycle': fields.get('has_menstrual_cycle', {}).get('value'),
#             'menstrual_symptoms': fields.get('menstrual_symptoms', {}).get('value'),
#             'bowel_movement_frequency': fields.get('bowel_movement_frequency', {}).get('value'),
#             'bowel_movement_type': fields.get('bowel_movement_type', {}).get('value'),
#             'digestive_symptoms': fields.get('digestive_symptoms', {}).get('value'),
#             'other_symptoms': fields.get('other_symptoms', {}).get('value'),
#             'body_temperature': fields.get('body_temperature', {}).get('value'),
#             'nervous_system_signs': fields.get('nervous_system_signs', {}).get('value'),
#             'energy_pattern': fields.get('energy_pattern', {}).get('value'),
#             'sleep_pattern': fields.get('sleep_pattern', {}).get('value'),
#             'movement_level': fields.get('movement_level', {}).get('value'),
#             'appetite_pattern': fields.get('appetite_pattern', {}).get('value'),
#             'diet_type': fields.get('diet_type', {}).get('value'),
#             'food_allergies': fields.get('food_allergies', {}).get('value'),
#             'emotional_patterns': fields.get('emotional_patterns', {}).get('value'),
#             'birth_history': fields.get('birth_history', {}).get('value'),
#             'past_medications': fields.get('past_medications', {}).get('value'),
#             'significant_history': fields.get('significant_history', {}).get('value'),
#             'updated_at': datetime.utcnow().isoformat()
#         }
        
#         # Update comprehensive_intake table
#         existing = db.get_user_intake_data(user_id)
#         if existing:
#             db.supabase.table('comprehensive_intake').update(intake_data).eq('user_id', user_id).execute()
#         else:
#             intake_data['id'] = str(uuid.uuid4())
#             intake_data['created_at'] = datetime.utcnow().isoformat()
#             db.supabase.table('comprehensive_intake').insert(intake_data).execute()
        
#     except Exception as e:
#         print(f"Error processing Tally data: {e}")

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