import os
from supabase import create_client, Client
from dotenv import load_dotenv
import time
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

def get_supabase_client():
    """Initialize Supabase client using environment variables or secrets"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Please set SUPABASE_URL and SUPABASE_KEY environment variables")
        return None
    
    return create_client(supabase_url, supabase_key)

def delete_user_by_email(email):
    """Delete user by email (admin function)"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Get all users
        response = supabase.auth.admin.list_users()
        users = response.users if hasattr(response, 'users') else []
        
        # Find and delete the user
        for user in users:
            if user.email == email:
                print(f"🗑️ Found user {email} (ID: {user.id}), deleting...")
                delete_response = supabase.auth.admin.delete_user(user.id)
                print(f"✅ User {email} deleted successfully")
                time.sleep(1)  # Wait a moment for deletion to propagate
                return True
        
        print(f"ℹ️ User {email} not found in user list")
        return False
        
    except Exception as e:
        print(f"❌ Error deleting user {email}: {str(e)}")
        return False

def send_invitation(email, role=0):
    """Send invitation email using Supabase auth"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        response = supabase.auth.admin.invite_user_by_email(
            email=email,
            options={
                "redirect_to": "https://app.zeromedwait.com/auth/sign-up?invite=true",
                "data": {
                    "role": role, 
                    "invited_by": "admin",
                    "invited_at": datetime.now().isoformat()
                }
            }
        )
        print(f"✅ Invitation sent to {email}")
        print(f"⏰ Link expires in 1 hour (default Supabase setting)")
        return True
    except Exception as e:
        print(f"❌ Error sending invitation: {str(e)}")
        return False

def resend_invitation(email, role=0):
    """Resend invitation if previous one expired"""
    print(f"🔄 Resending invitation to {email}...")
    
    # Delete existing user if they were created but didn't complete signup
    delete_result = delete_user_by_email(email)
    if delete_result:
        print(f"🗑️ Removed incomplete user record for {email}")
    
    # Send fresh invitation
    return send_invitation(email, role)

def main():
    """Main function to run invitation script"""
    print("🔐 Supabase Email Invitation API")
    print("=" * 40)
    
    email = "zed.gta2001@gmail.com"
    
    print(f"\n📧 Resending fresh invitation to {email}...")
    resend_invitation(email, role=0)

if __name__ == "__main__":
    main()