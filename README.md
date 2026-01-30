# Cold Email Campaign Bot

## Setup on a New Device

1. **Clone the repository**
   Open a terminal/command prompt and run:
   ```bash
   git clone https://github.com/amal-prasad/coldmails.git
   cd coldmails
   ```

2. **Install Dependencies**
   Make sure you have Python installed. Then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Credentials (IMPORTANT)**
   Because your API keys and passwords are private, they are **NOT** stored in Git for security. You must recreate the secret launcher file on your new device.

   Create a new file named `run_local.bat` in the project folder and paste the following content. **Make sure to fill in your real passwords/keys.**

   ```batch
   @echo off
   :: Ensure we are in the script's directory
   cd /d "%~dp0"

   :: --- YOUR SECRETS GO HERE ---
   set GMAIL_USER=amalprasad1998@gmail.com
   set GMAIL_APP_PASS=paste_your_16_char_app_password_here
   set GROQ_API_KEY=paste_your_groq_api_key_here

   echo Starting Cold Email Campaign...
   python coldmail_to_hr.py
   pause
   ```

   *> Tip: You can locate your `GMAIL_APP_PASS` and `GROQ_API_KEY` on your current computer by right-clicking `run_local.bat` and choosing 'Edit'.*

4. **Run the Bot**
   Double-click `run_local.bat` to start the campaign.
