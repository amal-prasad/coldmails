@echo off
:: Cold Email Campaign Launcher
:: double-click this file to run your daily batch of emails.

cd /d "e:\Cold mails"

:: Credentials (Saved for automation)
:: set GMAIL_USER=your_email@gmail.com
:: set GMAIL_APP_PASS=your_app_pass
:: set GROQ_API_KEY=your_groq_key

echo Starting Cold Email Campaign...
echo Limit: ~450 emails per run.
echo Press Ctrl+C to stop manually.
echo.

python coldmail_to_hr.py

pause
