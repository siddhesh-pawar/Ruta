from functools import wraps
from flask import session, redirect, url_for, flash
from supabase import create_client, Client
from config import Config
import secrets

class Auth:
    def __init__(self):
        self.supabase: Client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_ANON_KEY
        )
    
    def sign_up(self, email, password):
        """Sign up a new user"""
        try:
            response = self.supabase.auth.sign_up({
                'email': email,
                'password': password
            })
            return response
        except Exception as e:
            return {'error': str(e)}
    
    def sign_in(self, email, password):
        """Sign in an existing user"""
        try:
            response = self.supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            return response
        except Exception as e:
            return {'error': str(e)}
    
    def sign_out(self):
        """Sign out the current user"""
        try:
            response = self.supabase.auth.sign_out()
            return response
        except Exception as e:
            return {'error': str(e)}
    
    def get_user(self):
        """Get the current user"""
        try:
            user = self.supabase.auth.get_user()
            return user
        except Exception:
            return None
    
    def verify_email(self, token):
        """Verify email with token"""
        try:
            response = self.supabase.auth.verify_otp({
                'token': token,
                'type': 'email'
            })
            return response
        except Exception as e:
            return {'error': str(e)}

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_verification_token():
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)