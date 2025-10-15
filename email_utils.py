from flask_mail import Mail, Message
from flask import url_for
import secrets

mail = Mail()

def send_verification_email(email, token):
    """Send email verification"""
    try:
        msg = Message(
            'Verify your Ruta Health account',
            recipients=[email]
        )
        
        verification_url = url_for('verify_email', token=token, _external=True)
        
        msg.html = f"""
        <h2>Welcome to Ruta Health!</h2>
        <p>Thank you for signing up. Please verify your email address by clicking the link below:</p>
        <p><a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
        <p>If you didn't create an account, please ignore this email.</p>
        <p>Best regards,<br>The Ruta Health Team</p>
        """
        
        msg.body = f"""
        Welcome to Ruta Health!
        
        Please verify your email address by visiting:
        {verification_url}
        
        If you didn't create an account, please ignore this email.
        
        Best regards,
        The Ruta Health Team
        """
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_welcome_email(email, name):
    """Send welcome email after verification"""
    try:
        msg = Message(
            'Welcome to Ruta Health - Your Journey Begins!',
            recipients=[email]
        )
        
        msg.html = f"""
        <h2>Welcome aboard, {name}!</h2>
        <p>Your email has been verified and your account is now active.</p>
        <p>Next step: Complete your comprehensive health intake form to get personalized recommendations.</p>
        <p>We're excited to be part of your holistic health journey!</p>
        <p>Best regards,<br>The Ruta Health Team</p>
        """
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        return False