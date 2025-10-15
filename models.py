"""
from supabase import create_client, Client
from config import Config
import uuid
from datetime import datetime

class Database:
    def __init__(self):
        self.supabase: Client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_KEY
        )
    
    def create_user_profile(self, user_id, email, full_name=None):
       
        try:
            data = {
                'id': user_id,
                'email': email,
                'full_name': full_name or email.split('@')[0],
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('profiles').insert(data).execute()
            return result.data
        except Exception as e:
            print(f"Error creating profile: {e}")
            return None
    
    def get_user_profile(self, user_id):
        
        try:
            result = self.supabase.table('profiles').select("*").eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    def update_user_profile(self, user_id, updates):
    
        try:
            result = self.supabase.table('profiles').update(updates).eq('id', user_id).execute()
            return result.data
        except Exception as e:
            print(f"Error updating profile: {e}")
            return None
    
    def get_user_intake_data(self, user_id):
        
        try:
            result = self.supabase.table('comprehensive_intake').select("*").eq('user_id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting intake data: {e}")
            return None
    
    def save_tally_submission(self, user_id, tally_data):
        
        try:
            data = {
                'user_id': user_id,
                'tally_submission_id': tally_data.get('submission_id'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Check if intake exists
            existing = self.get_user_intake_data(user_id)
            if existing:
                result = self.supabase.table('comprehensive_intake').update(data).eq('user_id', user_id).execute()
            else:
                data['id'] = str(uuid.uuid4())
                data['created_at'] = datetime.utcnow().isoformat()
                result = self.supabase.table('comprehensive_intake').insert(data).execute()
            
            return result.data
        except Exception as e:
            print(f"Error saving Tally submission: {e}")
            return None

"""    

from supabase import create_client, Client
from config import Config
import uuid
from datetime import datetime, timedelta, timezone

class Database:
    def __init__(self):
        self.supabase: Client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_KEY  # Make sure you're using service key, not anon key
        )
    
    def create_user_profile(self, user_id, email, full_name=None):
        """Create a user profile after signup"""
        try:
            print(f"\n=== CREATE_USER_PROFILE ===")
            print(f"Input parameters:")
            print(f"  - user_id: {user_id}")
            print(f"  - email: {email}")
            print(f"  - full_name: '{full_name}' (type: {type(full_name)})")
            
            # Ensure full_name has a proper value
            if not full_name or str(full_name).strip() == '':
                full_name = email.split('@')[0] if email else 'User'
                print(f"  - full_name was empty, using fallback: '{full_name}'")
            else:
                full_name = str(full_name).strip()
                print(f"  - full_name after strip: '{full_name}'")
            
            # Prepare data for insertion
            data = {
                'id': user_id,  # This should match the auth.users.id
                'email': email,
                'full_name': full_name,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            print(f"\nData to insert: {data}")
            
            # First, check if profile already exists (shouldn't happen but let's be safe)
            existing = self.supabase.table('profiles').select("*").eq('id', user_id).execute()
            
            if existing.data:
                print(f"WARNING: Profile already exists for user {user_id}")
                # Update instead of insert
                update_data = {
                    'full_name': full_name,
                    'email': email
                }
                result = self.supabase.table('profiles').update(update_data).eq('id', user_id).execute()
                print(f"Updated existing profile: {result.data}")
            else:
                # Insert new profile
                result = self.supabase.table('profiles').insert(data).execute()
                print(f"Insert result successful: {result.data}")
            
            # Verify the insertion/update
            verification = self.supabase.table('profiles').select("*").eq('id', user_id).execute()
            if verification.data:
                print(f"\nVERIFICATION - Profile after save:")
                for key, value in verification.data[0].items():
                    print(f"  - {key}: {value}")
            
            print("=== END CREATE_USER_PROFILE ===\n")
            return result.data
            
        except Exception as e:
            print(f"\nERROR in create_user_profile:")
            print(f"  - Exception type: {type(e).__name__}")
            print(f"  - Exception message: {str(e)}")
            import traceback
            print(f"  - Traceback: {traceback.format_exc()}")
            return None
    
    def get_user_profile(self, user_id):
        """Get user profile by ID"""
        try:
            result = self.supabase.table('profiles').select("*").eq('id', user_id).execute()
            if result.data:
                print(f"Retrieved profile for {user_id}: {result.data[0]}")
            else:
                print(f"No profile found for user_id: {user_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    def update_user_profile(self, user_id, updates):
        """Update user profile"""
        try:
            print(f"Updating profile {user_id} with: {updates}")
            result = self.supabase.table('profiles').update(updates).eq('id', user_id).execute()
            print(f"Update result: {result.data}")
            return result.data
        except Exception as e:
            print(f"Error updating profile: {e}")
            return None
    
    def get_user_intake_data(self, user_id):
        """Get comprehensive intake data for a user"""
        try:
            result = self.supabase.table('comprehensive_intake').select("*").eq('user_id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting intake data: {e}")
            return None
    
    def save_tally_submission(self, user_id, tally_data):
        """Save Tally form submission ID"""
        try:
            data = {
                'user_id': user_id,
                'tally_submission_id': tally_data.get('submission_id'),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Check if intake exists
            existing = self.get_user_intake_data(user_id)
            if existing:
                result = self.supabase.table('comprehensive_intake').update(data).eq('user_id', user_id).execute()
            else:
                data['id'] = str(uuid.uuid4())
                data['created_at'] = datetime.utcnow().isoformat()
                result = self.supabase.table('comprehensive_intake').insert(data).execute()
            
            return result.data
        except Exception as e:
            print(f"Error saving Tally submission: {e}")
            return None
    
    def debug_check_profile(self, user_id):
        """Debug method to check what's actually in the database"""
        try:
            print(f"\n=== DEBUG CHECK for user {user_id} ===")
            
            # Check profiles table
            profile_result = self.supabase.table('profiles').select("*").eq('id', user_id).execute()
            if profile_result.data:
                profile = profile_result.data[0]
                print(f"Profile found:")
                for key, value in profile.items():
                    print(f"  - {key}: {repr(value)}")
            else:
                print("No profile found in profiles table")
            
            # Also check auth.users if you have access
            try:
                user_result = self.supabase.auth.admin.get_user_by_id(user_id)
                if user_result:
                    print(f"\nAuth user found:")
                    print(f"  - email: {user_result.user.email}")
                    print(f"  - user_metadata: {user_result.user.user_metadata}")
            except:
                print("Could not check auth.users (need admin access)")
            
            print("=== END DEBUG CHECK ===\n")
            
        except Exception as e:
            print(f"Debug check error: {e}")