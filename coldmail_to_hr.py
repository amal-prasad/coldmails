import os
import time
import random
import smtplib
import ssl
import json
import logging
import mimetypes
from email.message import EmailMessage
import getpass
import pandas as pd
import pdfplumber
from collections import deque
from datetime import datetime
try:
    from groq import Groq
except ImportError:
    Groq = None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("campaign_log.txt"),
        logging.StreamHandler()
    ]
)

# --- CONFIGURATION (Groq) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Safety Limits (Groq 100k Tokens/Day guardrail)
LIMIT_RPM = 24  # Max 30
LIMIT_RPD = 110 # Reduced to 110 for extra safety (approx 82k tokens)

class RateLimiter:
    def __init__(self, usage_file="groq_usage.json"):
        self.usage_file = usage_file
        self.rpm_window = deque(maxlen=LIMIT_RPM + 5) # Track timestamps
        self.today_date = datetime.now().strftime("%Y-%m-%d")
        self.daily_count = 0
        self._load_usage()

    def _load_usage(self):
        if os.path.exists(self.usage_file):
            try:
                with open(self.usage_file, 'r') as f:
                    data = json.load(f)
                    if data.get("date") == self.today_date:
                        self.daily_count = data.get("count", 0)
                    else:
                        self.daily_count = 0 # New day
            except Exception:
                self.daily_count = 0
        else:
            self.daily_count = 0

    def _save_usage(self):
        with open(self.usage_file, 'w') as f:
            json.dump({
                "date": self.today_date,
                "count": self.daily_count
            }, f)

    def check_and_record(self):
        """Checks limits and records usage. pauses/stops if needed."""
        # Check Daily Limit
        if self.daily_count >= LIMIT_RPD:
            raise Exception(f"DAILY LIMIT REACHED ({self.daily_count}/{LIMIT_RPD}). Stopping campaign for safety.")

        # Check RPM
        now = time.time()
        # Remove timestamps older than 60s
        while self.rpm_window and now - self.rpm_window[0] > 60:
            self.rpm_window.popleft()
        
        if len(self.rpm_window) >= LIMIT_RPM:
            logging.warning(f"RPM Limit Hit ({len(self.rpm_window)}/{LIMIT_RPM}). Cooling down for 60s...")
            time.sleep(60)
            # Recursively check again after sleep
            return self.check_and_record()
            
        # Record this request
        self.rpm_window.append(now)
        self.daily_count += 1
        self._save_usage()
        return True

class ColdEmailCampaign:
    def __init__(self, resume_path, contacts_path):
        self.resume_path = resume_path
        self.contacts_path = contacts_path
        self.contacts = []
        self.sent_log = self._load_sent_log()
        self.daily_limit = 110 # Matches Reduced Token Limit
        
        # Init Groq
        self.groq_client = None
        self.limiter = RateLimiter()
        if Groq and GROQ_API_KEY:
            try:
                self.groq_client = Groq(api_key=GROQ_API_KEY)
                logging.info("Groq Client Initialized.")
            except Exception as e:
                logging.error(f"Failed to init Groq: {e}")
        
        self.github_link = "https://github.com/amal-prasad"
        
    def _load_sent_log(self):
        if os.path.exists("sent_log.json"):
            with open("sent_log.json", "r") as f:
                return json.load(f)
        return []

    def _save_sent_log(self):
        with open("sent_log.json", "w") as f:
            json.dump(self.sent_log, f, indent=4)

    def ingest_data(self):
        """Extracts and normalizes data using specific column knowledge."""
        logging.info(f"Ingesting contacts from {self.contacts_path}")
        try:
            with pdfplumber.open(self.contacts_path) as pdf:
                all_tables = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        all_tables.extend(table)
            
            if not all_tables:
                logging.error("No tables found.")
                return

            # Known columns: SNo, Name, Email, Title, Company
            headers = all_tables[0]
            df = pd.DataFrame(all_tables[1:], columns=headers)
            df.columns = [c.strip() for c in df.columns]
            
            valid_contacts = []
            for _, row in df.iterrows():
                email = str(row.get('Email', '')).strip()
                if '@' not in email: continue
                
                name = row.get('Name', '')
                company = row.get('Company', '')
                title = row.get('Title', '')
                
                name = self._clean_name(name, email)
                company = company.replace('\n', ' ').strip()
                if not company: company = "your company"
                
                valid_contacts.append({
                    "name": name,
                    "email": email,
                    "company": company,
                    "recruiter_title": title
                })
            
            self.contacts = valid_contacts
            logging.info(f"Loaded {len(self.contacts)} valid contacts.")

        except Exception as e:
            logging.critical(f"Data ingestion failed: {e}")
            raise

    def _clean_name(self, raw_name, email):
        clean = str(raw_name).replace('\n', ' ').strip()
        if len(clean) > 1 and clean.lower() not in ['nan', 'none']:
            return clean.title()
        local = email.split('@')[0]
        if '.' in local: return local.split('.')[0].title()
        return local.title()

    def generate_smart_content(self, company, recipient_first_name):
        """Generates Full Email Content using Groq."""
        if not self.groq_client:
            return None, None
            
        user_context = """
        Currently I am running my family business and am looking to get into the IT field since the business is running smoothly and is now able to run without my involvement.

        Before that I was employed at Capgemini for 2 years where I was working as a DevOps engineer. During my 2 years at Capgemini, I architected GCP/AWS deployments and reduced deployment time by using Kubernetes and Docker,

        Recently, I pivoted to applying that engineering rigor to AI. I have built several projects which you can check out in my Github profile. For example, I built a RAG-based chatbot for RBI regulations, processing complex document chunks using LangChain, ChromaDB, and OpenAI models. I also developed projects on Energy Consumption Reduction, Supermarket Basket Analysis, and a Trading Engine. I understand both the "Dev" (Python, Transformers) and the "Ops" (CI/CD, Containerization) required to ship reliable AI products.

        I believe I can bring a unique perspective to your team as I have experience in both the technical and operational aspects of AI/ML, DevOps and enterprising.
        """

        prompt = f"""
        You are an expert cold email copywriter. 
        Task: Write a cold email to {company} for an ML Associate role.
        
        FORMATTING RULES (CRITICAL):
        1. After "Hi {recipient_first_name}," there MUST be exactly ONE blank line.
        2. Between every paragraph, there MUST be exactly ONE blank line (not two, not zero).
        3. Short, punchy paragraphs (max 2 sentences each).
        4. Force line breaks within sentences if becoming too long (20 words).
        5. Always the tex should start from the leftmost side and no indentation.
        6. Check if the visual and aesthetic of the email is good. after drafting and then send.
        
        TONE (IMPORTANT):
        - Professional, positive, cheerful, yet confident.
        - Sound like a dependable person who is easy to work with.
        - *Conversational and natural*, NOT robotic.
        - The jokes should feel human and not AI.
        - The jokes should be light-hearted and not too nerdy.
        - Organic mail, not at all robotic is the motto.

        LANGUAGE SAFETY (STRICT):
        - NEVER use negative, strong, derogatory, personal, sexual, or cocky words.
        - Use positive framing only.
        - Jokes must be SAFE, work-appropriate, and light-hearted.
        - Ban: "I hope this finds you well", meeting in person.
        
        VARIETY (MIX IT UP):
        - Do NOT always use the same opening hook. Be creative with different transitions from DevOps to AI.
        - Do NOT always use the same closing joke. Vary the tech metaphor (servers, merge conflicts, uptime, deployments, etc), not always tech, but safe jokes(like about their busy schedule or SEARCH the WEB for safe joke u can use(judge by urself)) Use tech jokes sometimes, other times normal jokes..
        - Each email should feel fresh and unique.
        
        STRUCTURE (follow this flow):
        1. **Subject Line**: Funny/witty/*cheeky*(not derogatory or negative), grabs attention, always refers to company's mission statement.
        2. **First Sentence (Hook)**: Engaging opener that transitions from DevOps stability to AI innovation with a bit of warmth and humour.
        3. **Segue to Me**: How I can bring value to {company} Research about the company thoroughly and find a way to connect with the company, always mention the company name and what it does and connect it to me in your conversational joking opener. *ALWAYS mention what they do in the opener somehow for the connection.*
        4. **Tech Stack Line (USE THIS EXACT PHRASING)**: "Familiar tech stacks are mentioned in my resume, and you can find my projects at {self.github_link}."
        5. **Closing (End with a joke)**: Light, safe tech joke about THEIR busy schedule and genuinely funny(not nerdy).
        6. **ALWAYS MENTION THe SPECIFIC MISSION STATEMENT OF THE COMPANY IN THE FIRST LINE OF THE EMAIL**
        
        Medium size email(upto 60 words). Not too long but should do the trick. Use context and see if you can fit in a conversational way without expanding the mail too much.
        
        TEMPLATE:
        Hi {recipient_first_name},
        
        [Hook: "Creative DevOps -> *AI* transition". Mention both DevOps and AI keywords.How I can help {company}.]

        Experience from Capgemini and *managing my family business* (find in context above)(reword in conversation precise which drives the point home.)
        

        say - Familiar tech stacks are mentioned in my resume, ALWAYS MENTION one of my AI PROJECTS in {user_context} above and say you can find my OTHER projects at {self.github_link}.        
        
        [Call to Action + Light tech joke about THEIR inbox/schedule]
        
        Best regards,
        Amal Prasad
        
        Output Format: JSON with keys "subject" and "body".
        
        Template is not absolute, you can play with it, as our ultimate goal is to make a funny, eye-catching, cozy,humane yet professional email.

        """

        
        
        try:
            # Check Limits First
            self.limiter.check_and_record()
            
            completion = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7, 
                max_completion_tokens=400,
                top_p=1,
                response_format={"type": "json_object"}
            )
            
            content = completion.choices[0].message.content
            # Clean up potential Markdown wrappers
            content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            subject = data.get("subject")
            body = data.get("body")
            
            # Post-Processing: Fix AI Hallucinations
            if body:
                body = body.replace("[Your Name]", "Amal Prasad")
                body = body.replace("[Name]", recipient_first_name)
                body = body.replace("Dear Hiring Manager", f"Hi {recipient_first_name}")
                if "coffee" in body.lower():
                     body = body.replace("coffee", "a call")
                
                # Normalize sign-off: remove duplicate/varied sign-offs
                import re
                # Remove any existing sign-offs like "Best, Amal" or "Best regards, Amal Prasad"
                body = re.sub(r'\n*(Best,?\s*\n*Amal\s*Prasad?)\s*$', '', body, flags=re.IGNORECASE)
                body = re.sub(r'\n*(Best regards,?\s*\n*Amal\s*Prasad?)\s*$', '', body, flags=re.IGNORECASE)
                body = body.rstrip()
                
                # Add the canonical sign-off
                body += "\n\nBest regards,\nAmal Prasad"
                
                # Cleanup triple newlines to single blank line
                body = body.replace("\n\n\n", "\n\n")

            return subject, body
            
        except Exception as e:
            logging.warning(f"Groq GenAI Failed: {e}. Falling back to static.")
            return None, None

    def draft_email(self, contact):
        user_name = "Amal Prasad"
        github_link = "https://github.com/amal-prasad"
        
        # Extract Recipient First Name
        first_name = contact['name'].split()[0]
        
        # 1. Try GenAI Full Body
        ai_subject, ai_body = self.generate_smart_content(contact['company'], first_name)
        
        if ai_subject and ai_body:
            return ai_subject, ai_body

        # 2. Fallback Static (If API fails) - Short <60 Words Version
        subject = f"ML Associate Application - {user_name} (Co-Founder exp)"
        
        body = f"""Hi {first_name},

Are you leveraging AI to its full potential at {contact['company']}?

I might help with my expertise in DevOps paired with my keen interest and work in AI (Energy Consumption, Trading Engines) which you can find in my github: {github_link}.

Are you open to a brief chat next week? (I'm sure your inbox is wild!)

Resume attached.

Best regards,

{user_name}
GitHub: {github_link}
(Included: Resume)
"""
        return subject, body

    def execute_campaign(self, email_user, email_password, dry_run=False):
        if not self.contacts:
            logging.warning("No contacts.")
            return

        logging.info(f"Starting campaign. Dry Run: {dry_run}")
        
        server = None
        if not dry_run:
            context = ssl.create_default_context()
            try:
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context)
                server.login(email_user, email_password)
            except Exception as e:
                logging.critical(f"SMTP Login failed: {e}")
                return

        sent_count = 0
        try:
            for i, contact in enumerate(self.contacts):
                try:
                    if sent_count >= self.daily_limit:
                        logging.warning("Daily Gmail limit reached.")
                        break
                    
                    if contact['email'] in self.sent_log:
                        continue

                    subject, body = self.draft_email(contact)
                    
                    # Dry Run Output
                    if dry_run:
                        print(f"[{i+1}/{len(self.contacts)}] would send to: {contact['email']}")
                        print(f"Company: {contact['company']}")
                        print(f"Subject: {subject}")
                        print(f"Opener: {body.splitlines()[2]}") # Print just the opener
                        print("-" * 30)
                        continue

                    # Real Send
                    msg = EmailMessage()
                    msg['Subject'] = subject
                    msg['From'] = f"Amal Prasad <{email_user}>"
                    msg['To'] = contact['email']
                    msg.set_content(body)

                    if os.path.exists(self.resume_path):
                        with open(self.resume_path, 'rb') as f:
                            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename="Amal_Prasad_Resume.pdf")
                    
                    server.send_message(msg)
                    self.sent_log.append(contact['email'])
                    self._save_sent_log()
                    sent_count += 1
                    logging.info(f"Sent to {contact['email']}")
                    
                    # Jitter
                    sleep_s = random.uniform(5, 15)
                    time.sleep(sleep_s)
                    
                except Exception as loop_e:
                    logging.error(f"Error processing {contact['email']}: {loop_e}")
                    # Continue to next contact (unless it was a critical Groq stop limit which raises up? No, groq limit exception should probably stop us.)
                    if "DAILY LIMIT REACHED" in str(loop_e):
                        logging.critical("Groq Daily Limit Reached. Stopping Campaign.")
                        break

        except KeyboardInterrupt:
            logging.warning("Campaign interrupted by user.")
        finally:
            if server:
                server.quit()
        
        print(f"\nSummary: {sent_count} emails sent.")

if __name__ == "__main__":
    RESUME = "Amal-Prasad-Resume.pdf"
    CONTACTS = "Company Wise HR Contacts - HR Contacts (3).pdf"
    
    EMAIL_USER = os.environ.get("GMAIL_USER")
    EMAIL_PASS = os.environ.get("GMAIL_APP_PASS")
    
    DRY_RUN = True
    if EMAIL_USER and EMAIL_PASS:
        DRY_RUN = False
        print("Credentials found. Starting LIVE campaign in 5 seconds... (Ctrl+C to cancel)")
        time.sleep(5)
    else:
        print("No GMAIL_USER/GMAIL_APP_PASS found. Defaulting to DRY RUN.")

    bot = ColdEmailCampaign(RESUME, CONTACTS)
    bot.ingest_data()
    bot.execute_campaign(EMAIL_USER, EMAIL_PASS, dry_run=DRY_RUN)
