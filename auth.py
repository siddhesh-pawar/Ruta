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

    def send_magic_link(self, email, redirect_url=None):
   
        try:
            body = {
            "email": email,
            "create_user": True,  # make sure Supabase creates new users
        }

    

        # `redirect_to` must be passed separately
            response = self.supabase.auth._request(
            "POST",
            "otp",
            body=body,
            redirect_to=redirect_url or Config.REDIRECT_URL,
            xform=None,  # optional transform
        )

            return response
        except Exception as e:
            print(f"Error sending magic link: {e}")
            return {"error": str(e)}


    def verify_otp(self, email, token):
        """Verify the OTP/magic link token from email"""
        try:
            response = self.supabase.auth.verify_otp({
                'email': email,
                'token': token,
                'type': 'magiclink'
            })
            return response
        except Exception as e:
            return {'error': str(e)}

    def get_user(self):
        """Get the current user session"""
        try:
            user = self.supabase.auth.get_user()
            return user
        except Exception:
            return None

    def sign_out(self):
        """Sign out the user"""
        try:
            self.supabase.auth.sign_out()
            session.pop('user_id', None)
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

def login_required(f):
    """Decorator for routes requiring authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_verification_token():
    """Generate a secure random token (not used by Supabase magic links)"""
    return secrets.token_urlsafe(32)
