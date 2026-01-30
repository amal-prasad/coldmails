import smtplib
import ssl
import sys

def verify_gmail(user, password):
    print(f"Attempting to login as: {user}")
    print("Connecting to smtp.gmail.com...")
    
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(user, password)
            print("✅ SUCCESS: Login accepted.")
            return True
    except smtplib.SMTPAuthenticationError:
        print("❌ FAILURE: Authentication failed. Please check your username/password.")
        return False
    except Exception as e:
        print(f"❌ FAILURE: Connection error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_creds.py <email> <password>")
        sys.exit(1)
        
    verify_gmail(sys.argv[1], sys.argv[2])
