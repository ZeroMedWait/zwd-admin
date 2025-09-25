import os
from supabase import create_client, Client
from dotenv import load_dotenv
import time

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

def get_supabase_client_with_params(supabase_url, supabase_key):
    """Initialize Supabase client with provided parameters"""
    if not supabase_url or not supabase_key:
        return None
    return create_client(supabase_url, supabase_key)

def list_all_users(supabase_client):
    """List all users (admin function)"""
    try:
        response = supabase_client.auth.admin.list_users()
        return response.users if hasattr(response, 'users') else []
    except Exception as e:
        print(f"❌ Error listing users: {str(e)}")
        return []

def delete_user_by_email(email, supabase_client=None):
    """Delete user by email (admin function)"""
    if not supabase_client:
        supabase_client = get_supabase_client()
    
    if not supabase_client:
        return {"success": False, "message": "Failed to initialize Supabase client"}
    
    try:
        # Get all users
        users = list_all_users(supabase_client)
        
        # Find and delete the user
        for user in users:
            if user.email == email:
                print(f"🗑️ Found user {email} (ID: {user.id}), deleting...")
                delete_response = supabase_client.auth.admin.delete_user(user.id)
                print(f"✅ User {email} deleted successfully")
                time.sleep(1)  # Wait a moment for deletion to propagate
                return {"success": True, "message": f"User {email} deleted successfully"}
        
        return {"success": False, "message": f"User {email} not found"}
        
    except Exception as e:
        error_msg = f"Error deleting user {email}: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "message": error_msg}

def send_invitation(email, role=0, supabase_client=None, redirect_to=None):
    """Send invitation email using Supabase auth"""
    if not supabase_client:
        supabase_client = get_supabase_client()
    
    if not supabase_client:
        return {"success": False, "message": "Failed to initialize Supabase client"}
    
    try:
        response = supabase_client.auth.admin.invite_user_by_email(
            email=email,
            options={
                "redirect_to": redirect_to or "https://app.zeromedwait.com/auth/sign-up",
                "data": {"role": role, "invited_by": "admin"}
            }
        )
        success_msg = f"Invitation sent to {email} with role {role}"
        print(f"✅ {success_msg}")
        return {"success": True, "message": success_msg, "response": response}
    except Exception as e:
        error_msg = f"Error sending invitation to {email}: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "message": error_msg}

def bulk_invite(email_list, default_role=0, supabase_client=None, redirect_to=None):
    """Send invitations to multiple emails"""
    if not supabase_client:
        supabase_client = get_supabase_client()
    
    if not supabase_client:
        return {"success": False, "message": "Failed to initialize Supabase client", "results": []}
    
    results = []
    
    for item in email_list:
        if isinstance(item, tuple) and len(item) == 2:
            email, role = item
        elif isinstance(item, dict):
            email = item.get("email", "")
            role = item.get("role", default_role)
        else:
            email, role = str(item).strip(), default_role
            
        if email:  # Only process non-empty emails
            result = send_invitation(email, role, supabase_client, redirect_to)
            results.append({"email": email, "role": role, **result})
    
    # Summary
    successful = sum(1 for r in results if r.get("success", False))
    failed = len(results) - successful
    
    summary_msg = f"Sent {successful} invitations successfully, {failed} failed"
    print(f"\n📊 Summary: {summary_msg}")
    
    return {
        "success": failed == 0,
        "message": summary_msg,
        "results": results,
        "summary": {"successful": successful, "failed": failed, "total": len(results)}
    }

def main():
    """Main function to run invitation script"""
    print("🔐 Supabase Email Invitation API")
    print("=" * 40)
    
    email = "zed.gta2001@gmail.com"
    
    # Delete user first
    print(f"\n🔍 Checking for existing user: {email}")
    delete_result = delete_user_by_email(email)
    print(delete_result["message"])
    
    # Send invitation
    print(f"\n📧 Sending invitation to {email}...")
    invite_result = send_invitation(email, role=0)
    print(invite_result["message"])

if __name__ == "__main__":
    main()