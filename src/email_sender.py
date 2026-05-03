"""
Email sending utilities for Job Scout AI.
Uses Python's built-in smtplib — no extra dependencies required.

Gmail setup:
  1. Enable 2-Step Verification on your Google account.
  2. Go to https://myaccount.google.com/apppasswords
  3. Generate an App Password for "Mail".
  4. Set SMTP_USER and SMTP_PASS in your .env.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_verification_email(to_email: str, token: str) -> None:
    """
    Send a verification email with a one-time activation link.
    Reads config from environment variables.
    """
    base_url = os.environ.get("APP_BASE_URL", "http://localhost:8000")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    email_from = os.environ.get("EMAIL_FROM", f"Job Scout AI <{smtp_user}>")

    # The link should point to the frontend (root), not the API.
    # main.js will detect the ?token= and call the API for us.
    verify_link = f"{base_url}/?token={token}"

    # ── Plain-text fallback ──────────────────────────────────────────────────
    text_body = (
        "Welcome to Job Scout AI!\n\n"
        "Please verify your email address by visiting the link below:\n\n"
        f"{verify_link}\n\n"
        "If you didn't create an account, you can safely ignore this email.\n"
    )

    # ── HTML version ─────────────────────────────────────────────────────────
    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <table width="500" cellpadding="0" cellspacing="0"
               style="background:#1a1a2e;border-radius:12px;overflow:hidden;
                      border:1px solid rgba(108,99,255,0.3);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6c63ff,#4ecdc4);
                       padding:32px;text-align:center;">
              <h1 style="margin:0;color:#fff;font-size:24px;font-weight:700;
                         letter-spacing:-0.5px;">
                🚀 Job Scout AI
              </h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:36px 40px;">
              <h2 style="margin:0 0 16px;color:#e8e8f0;font-size:20px;">
                Verify your email address
              </h2>
              <p style="margin:0 0 24px;color:#a0a0c0;font-size:15px;line-height:1.6;">
                Thanks for registering! Click the button below to activate your
                account and start hunting for jobs.
              </p>
              <div style="text-align:center;margin:32px 0;">
                <a href="{verify_link}"
                   style="display:inline-block;padding:14px 36px;
                          background:linear-gradient(135deg,#6c63ff,#4ecdc4);
                          color:#fff;text-decoration:none;border-radius:8px;
                          font-weight:600;font-size:15px;letter-spacing:0.3px;">
                  Activate My Account
                </a>
              </div>
              <p style="margin:0;color:#606080;font-size:13px;line-height:1.6;">
                Or paste this URL into your browser:<br>
                <a href="{verify_link}"
                   style="color:#6c63ff;word-break:break-all;">{verify_link}</a>
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px;border-top:1px solid rgba(255,255,255,0.06);
                       text-align:center;">
              <p style="margin:0;color:#404060;font-size:12px;">
                If you didn't create a Job Scout AI account, you can safely
                ignore this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    # ── Build MIME message ───────────────────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Job Scout AI account"
    msg["From"] = email_from
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # ── Send via SMTP (Gmail uses STARTTLS on port 587) ──────────────────────
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
