import random
import smtplib
import ssl
import time
from email.message import EmailMessage
from coldmail_to_hr import ColdEmailCampaign, Groq

# Config
TEST_RECIPIENT = "benedictwelkin1998@gmail.com"
RESUME = "Amal-Prasad-Resume.pdf"
CONTACTS = "Company Wise HR Contacts - HR Contacts (3).pdf"
EMAIL_USER = "amalprasad1998@gmail.com"
EMAIL_PASS = "ozjo dxjo jigk jmou"

def test_5_formatted():
    print("--- 🎨 Testing 5 Random Companies with NEW FORMAT ---")
    bot = ColdEmailCampaign(RESUME, CONTACTS)
    bot.ingest_data()
    
    if not bot.contacts:
        print("❌ No contacts loaded.")
        return

    # Pick 5 random contacts
    targets = random.sample(bot.contacts, 3)
    
    context = ssl.create_default_context()
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context)
    server.login(EMAIL_USER, EMAIL_PASS)
    
    for i, contact in enumerate(targets):
        print(f"\n[{i+1}/5] Generating for: {contact['company']}...")
        
        subject, body = bot.draft_email(contact)
        
        print(f"Subject: {subject}")
        print("Body Snippet (Check spacing):")
        print("\n".join(body.splitlines()[-6:])) # Print just the signature part to verify "Amal"
        
        # Send
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = f"Amal Prasad <{EMAIL_USER}>"
        msg['To'] = TEST_RECIPIENT
        msg.set_content(body)
        
        with open(RESUME, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename="Amal_Prasad_Resume.pdf")
            
        server.send_message(msg)
        print(f"✅ Sent to test inbox")
        
        time.sleep(2)

    server.quit()
    print("\n✨ Batch Test Complete.")

if __name__ == "__main__":
    test_5_formatted()
