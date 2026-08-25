#!/usr/bin/env python3
"""
Periodic external uptime check against the live site's /health/ endpoint.
Emails an alert on failure and a follow-up on recovery — deliberately does
NOT import Django (which would load the ML model on every run) to stay fast
enough to run every few minutes via cron.
"""
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"
STATE_FILE = PROJECT_DIR / "logs" / ".healthcheck_state"
HEALTH_URL = "https://livwa-cedat.mak.ac.ug/health/"
ALERT_TO = "livwateam@gmail.com"
TIMEOUT_SECONDS = 15


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def check_site():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=TIMEOUT_SECONDS) as resp:
            if resp.status == 200:
                return True, f"HTTP {resp.status}"
            return False, f"HTTP {resp.status}"
    except urllib.error.URLError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def send_alert(env, subject, body):
    user = env.get("EMAIL_HOST_USER")
    password = env.get("EMAIL_HOST_PASSWORD")
    if not user or not password:
        print("No email credentials configured — skipping alert email.", file=sys.stderr)
        return
    host = env.get("EMAIL_HOST", "smtp.gmail.com")
    port = int(env.get("EMAIL_PORT", "587"))
    from_addr = env.get("DEFAULT_FROM_EMAIL", user)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ALERT_TO

    with smtplib.SMTP(host, port, timeout=TIMEOUT_SECONDS) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(user, password)
        smtp.sendmail(from_addr, [ALERT_TO], msg.as_string())


def read_last_state():
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return "UP"


def write_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(state)


def main():
    ok, detail = check_site()
    last_state = read_last_state()
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC")

    if ok:
        if last_state == "DOWN":
            env = load_env()
            send_alert(
                env,
                "LIVWA is back up",
                f"{HEALTH_URL} is responding again as of {now} ({detail}).",
            )
            print(f"{now} recovered ({detail})")
        write_state("UP")
    else:
        if last_state == "UP":
            env = load_env()
            send_alert(
                env,
                "LIVWA site is DOWN",
                f"{HEALTH_URL} failed at {now}: {detail}\n\n"
                f"This alert only fires once per outage — you won't get another "
                f"until it recovers and fails again.",
            )
            print(f"{now} DOWN ({detail}) — alert sent")
        else:
            print(f"{now} still DOWN ({detail}) — already alerted")
        write_state("DOWN")


if __name__ == "__main__":
    main()
