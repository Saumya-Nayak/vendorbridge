"""
VendorBridge — Email Helper
Sends transactional emails via SMTP (configurable via .env)
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app


def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> None:
    """
    Send a single email via the configured SMTP server.
    Raises on failure — callers should catch and handle.
    """
    cfg = current_app.config

    if not cfg.get("MAIL_USERNAME") or not cfg.get("MAIL_PASSWORD"):
        current_app.logger.warning("Email not configured — skipping send to %s", to_email)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["MAIL_SENDER"]
    msg["To"]      = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as server:
        server.ehlo()
        if cfg.get("MAIL_USE_TLS"):
            server.starttls()
        server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        server.sendmail(cfg["MAIL_SENDER"], to_email, msg.as_string())


# ------------------------------------------------------------------ #
#  Templated emails
# ------------------------------------------------------------------ #

def send_reset_email(to_email: str, name: str, reset_url: str) -> None:
    subject = "Reset your VendorBridge password"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body {{ font-family: 'DM Sans', Arial, sans-serif; background: #0b0f1a; color: #e2e8f0; margin: 0; padding: 0; }}
        .container {{ max-width: 560px; margin: 40px auto; background: #151b2e; border: 1px solid #1e2d4a; border-radius: 16px; overflow: hidden; }}
        .header {{ background: #4f8ef7; padding: 32px 40px; text-align: center; }}
        .header h1 {{ color: #fff; font-size: 24px; margin: 0; font-weight: 700; }}
        .body {{ padding: 36px 40px; }}
        .body p {{ font-size: 15px; line-height: 1.7; color: #94a3b8; }}
        .body strong {{ color: #e2e8f0; }}
        .btn {{ display: inline-block; background: #4f8ef7; color: #fff !important; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-weight: 700; font-size: 15px; margin: 20px 0; }}
        .note {{ font-size: 13px; color: #64748b; margin-top: 24px; border-top: 1px solid #1e2d4a; padding-top: 20px; }}
        .footer {{ text-align: center; padding: 20px 40px; font-size: 12px; color: #475569; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>🔐 VendorBridge</h1>
        </div>
        <div class="body">
          <p>Hi <strong>{name}</strong>,</p>
          <p>We received a request to reset your VendorBridge password. Click the button below to create a new password. This link is valid for <strong>1 hour</strong>.</p>
          <p style="text-align:center;">
            <a href="{reset_url}" class="btn">Reset My Password</a>
          </p>
          <p>If the button doesn't work, paste this URL into your browser:</p>
          <p style="word-break:break-all; font-size:13px; color:#64748b;">{reset_url}</p>
          <div class="note">
            <p>If you didn't request a password reset, you can safely ignore this email. Your password won't change until you click the link above.</p>
          </div>
        </div>
        <div class="footer">
          &copy; 2025 VendorBridge — Procurement ERP Platform
        </div>
      </div>
    </body>
    </html>
    """

    text = (
        f"Hi {name},\n\n"
        f"Reset your VendorBridge password using this link (valid for 1 hour):\n\n"
        f"{reset_url}\n\n"
        f"If you didn't request this, ignore this email.\n\n"
        f"— VendorBridge Team"
    )

    send_email(to_email, subject, html, text)


def send_welcome_email(to_email: str, name: str, role: str) -> None:
    subject = "Welcome to VendorBridge! 🎉"
    role_label = role.replace("_", " ").title()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body {{ font-family: Arial, sans-serif; background: #0b0f1a; color: #e2e8f0; margin: 0; padding: 0; }}
        .container {{ max-width: 560px; margin: 40px auto; background: #151b2e; border: 1px solid #1e2d4a; border-radius: 16px; overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #4f8ef7, #7c3aed); padding: 32px 40px; text-align: center; }}
        .header h1 {{ color: #fff; font-size: 26px; margin: 0; font-weight: 800; }}
        .body {{ padding: 36px 40px; }}
        .body p {{ font-size: 15px; line-height: 1.7; color: #94a3b8; }}
        .badge {{ display: inline-block; background: rgba(79,142,247,0.15); border: 1px solid rgba(79,142,247,0.3); color: #4f8ef7; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }}
        .btn {{ display: inline-block; background: #4f8ef7; color: #fff !important; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-weight: 700; font-size: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px 40px; font-size: 12px; color: #475569; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header"><h1>Welcome to VendorBridge 🚀</h1></div>
        <div class="body">
          <p>Hi <strong style="color:#e2e8f0">{name}</strong>,</p>
          <p>Your account has been created successfully. You've been assigned the role of <span class="badge">{role_label}</span>.</p>
          <p>You can now sign in and start using VendorBridge to manage procurement workflows.</p>
          <p style="text-align:center;"><a href="http://localhost:5500/frontend/pages/login.html" class="btn">Sign In Now →</a></p>
        </div>
        <div class="footer">&copy; 2025 VendorBridge — Procurement ERP Platform</div>
      </div>
    </body>
    </html>
    """

    send_email(to_email, subject, html)