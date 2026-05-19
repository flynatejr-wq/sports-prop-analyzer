"""
Alert dispatcher — sends notifications to Discord, Telegram, SMS, and email.
Each channel is independent; failures in one don't block others.
"""
import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings
from app.models.alert import AlertType

logger = logging.getLogger(__name__)


# ── Discord ───────────────────────────────────────────────────────────────────

DISCORD_COLORS = {
    AlertType.HIGH_EV: 0x00FF7F,        # green
    AlertType.LINE_MOVEMENT: 0xFFD700,  # gold
    AlertType.INJURY: 0xFF4444,         # red
    AlertType.STEAM_MOVE: 0xFF8C00,     # orange
    AlertType.STALE_LINE: 0x87CEEB,     # sky blue
    AlertType.PROJECTION_MISMATCH: 0xDA70D6,  # orchid
}


async def send_discord(
    title: str,
    message: str,
    alert_type: AlertType = AlertType.HIGH_EV,
    fields: Optional[List[Dict]] = None,
    webhook_url: Optional[str] = None,
) -> bool:
    url = webhook_url or settings.DISCORD_WEBHOOK_URL
    if not url:
        logger.debug("Discord webhook not configured")
        return False

    color = DISCORD_COLORS.get(alert_type, 0x5865F2)
    embed: Dict[str, Any] = {
        "title": title,
        "description": message,
        "color": color,
        "footer": {"text": "Sports Prop Analyzer • Real-time alerts"},
    }
    if fields:
        embed["fields"] = [
            {"name": f["name"], "value": str(f["value"]), "inline": f.get("inline", True)}
            for f in fields
        ]

    payload = {"embeds": [embed]}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info("Discord alert sent: %s", title)
            return True
    except Exception as exc:
        logger.error("Discord send failed: %s", exc)
        return False


async def send_discord_prop_alert(prop: Dict, threshold_type: str = "HIGH_EV") -> bool:
    """Pre-formatted alert for a high-EV prop."""
    player = prop.get("player_name", "Unknown")
    stat = prop.get("stat_type", "")
    line = prop.get("line", 0)
    sport = prop.get("sport", "")
    ev_over = prop.get("ev_over", 0)
    ev_under = prop.get("ev_under", 0)
    best_direction = "OVER" if ev_over > ev_under else "UNDER"
    best_ev = max(ev_over, ev_under)
    edge_class = prop.get("edge_classification", "")
    consensus = prop.get("consensus_line")

    title = f"🔥 {edge_class} EV: {player} {stat}"
    message = (
        f"**{player}** ({sport}) — {stat}\n"
        f"PP Line: **{line}** | Direction: **{best_direction}**\n"
        f"EV: **+{best_ev:.1f}%**"
    )

    fields = [
        {"name": "PP Line", "value": str(line)},
        {"name": "Consensus", "value": str(round(consensus, 1)) if consensus else "N/A"},
        {"name": "Best Direction", "value": best_direction},
        {"name": "EV%", "value": f"+{best_ev:.1f}%"},
        {"name": "Season Avg", "value": str(prop.get("season_avg") or "N/A")},
        {"name": "Last 5 Avg", "value": str(prop.get("last_5_avg") or "N/A")},
        {"name": "Hit Rate", "value": f"{prop.get('hit_rate_over', 0)*100:.0f}%" if prop.get('hit_rate_over') else "N/A"},
        {"name": "Injury", "value": prop.get("injury_status") or "Healthy"},
    ]

    return await send_discord(title=title, message=message, alert_type=AlertType.HIGH_EV, fields=fields)


# ── Telegram ──────────────────────────────────────────────────────────────────

async def send_telegram(
    message: str,
    parse_mode: str = "Markdown",
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> bool:
    token = bot_token or settings.TELEGRAM_BOT_TOKEN
    cid = chat_id or settings.TELEGRAM_CHAT_ID
    if not token or not cid:
        logger.debug("Telegram not configured")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": cid, "text": message, "parse_mode": parse_mode}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("Telegram send failed: %s", exc)
        return False


async def send_telegram_prop_alert(prop: Dict) -> bool:
    player = prop.get("player_name", "Unknown")
    stat = prop.get("stat_type", "")
    line = prop.get("line", 0)
    sport = prop.get("sport", "")
    ev_over = prop.get("ev_over", 0)
    ev_under = prop.get("ev_under", 0)
    best_direction = "OVER" if ev_over > ev_under else "UNDER"
    best_ev = max(ev_over, ev_under)

    msg = (
        f"🎯 *High EV Prop Alert*\n\n"
        f"*{player}* ({sport})\n"
        f"Stat: {stat}\n"
        f"PP Line: `{line}` → *{best_direction}*\n"
        f"EV: `+{best_ev:.1f}%`\n"
        f"Season Avg: `{prop.get('season_avg', 'N/A')}`\n"
        f"Consensus: `{prop.get('consensus_line', 'N/A')}`"
    )
    return await send_telegram(msg)


# ── SMS (Twilio) ──────────────────────────────────────────────────────────────

async def send_sms(message: str, to_numbers: Optional[List[str]] = None) -> bool:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.debug("Twilio not configured")
        return False

    numbers = to_numbers or settings.alert_phones
    if not numbers:
        return False

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        for number in numbers:
            client.messages.create(
                body=message[:1600],  # SMS char limit
                from_=settings.TWILIO_FROM_NUMBER,
                to=number,
            )
        return True
    except ImportError:
        logger.warning("twilio package not installed — SMS disabled")
        return False
    except Exception as exc:
        logger.error("SMS send failed: %s", exc)
        return False


# ── Email ─────────────────────────────────────────────────────────────────────

async def send_email(
    subject: str,
    body_html: str,
    recipients: Optional[List[str]] = None,
) -> bool:
    recips = recipients or settings.alert_emails
    if not recips or not settings.SMTP_USER:
        logger.debug("Email not configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = ", ".join(recips)
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.SMTP_USER, recips, msg.as_string())
        return True
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return False


async def send_email_prop_alert(prop: Dict) -> bool:
    player = prop.get("player_name", "Unknown")
    stat = prop.get("stat_type", "")
    line = prop.get("line", 0)
    ev_over = prop.get("ev_over", 0)
    ev_under = prop.get("ev_under", 0)
    best_direction = "OVER" if ev_over > ev_under else "UNDER"
    best_ev = max(ev_over, ev_under)

    subject = f"🎯 High EV Alert: {player} {stat} {best_direction}"
    html = f"""
    <html><body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:20px">
    <h2 style="color:#00ff7f">🔥 High EV Prop Alert</h2>
    <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:8px;color:#94a3b8">Player</td><td style="padding:8px;font-weight:bold">{player}</td></tr>
        <tr><td style="padding:8px;color:#94a3b8">Stat</td><td style="padding:8px">{stat}</td></tr>
        <tr><td style="padding:8px;color:#94a3b8">PP Line</td><td style="padding:8px">{line}</td></tr>
        <tr><td style="padding:8px;color:#94a3b8">Direction</td><td style="padding:8px;color:#00ff7f;font-weight:bold">{best_direction}</td></tr>
        <tr><td style="padding:8px;color:#94a3b8">EV%</td><td style="padding:8px;color:#00ff7f;font-weight:bold">+{best_ev:.1f}%</td></tr>
        <tr><td style="padding:8px;color:#94a3b8">Season Avg</td><td style="padding:8px">{prop.get('season_avg','N/A')}</td></tr>
        <tr><td style="padding:8px;color:#94a3b8">Consensus Line</td><td style="padding:8px">{prop.get('consensus_line','N/A')}</td></tr>
        <tr><td style="padding:8px;color:#94a3b8">Hit Rate (Over)</td><td style="padding:8px">{f"{prop.get('hit_rate_over',0)*100:.0f}%" if prop.get('hit_rate_over') else 'N/A'}</td></tr>
    </table>
    <p style="color:#475569;margin-top:20px;font-size:12px">Sports Prop Analyzer — automated alert</p>
    </body></html>
    """
    return await send_email(subject, html)


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def dispatch_prop_alert(prop: Dict, channels: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Send a prop alert to all configured channels simultaneously.
    channels: subset of ['discord', 'telegram', 'sms', 'email'] — defaults to all.
    Returns {channel: success} map.
    """
    if channels is None:
        channels = ["discord", "telegram", "sms", "email"]

    tasks = {}
    if "discord" in channels:
        tasks["discord"] = send_discord_prop_alert(prop)
    if "telegram" in channels:
        tasks["telegram"] = send_telegram_prop_alert(prop)
    if "sms" in channels:
        player = prop.get("player_name", "")
        stat = prop.get("stat_type", "")
        line = prop.get("line", 0)
        ev_val = max(prop.get("ev_over", 0), prop.get("ev_under", 0))
        direction = "OVER" if prop.get("ev_over", 0) > prop.get("ev_under", 0) else "UNDER"
        tasks["sms"] = send_sms(f"ALERT: {player} {stat} {direction} {line} | EV: +{ev_val:.1f}%")
    if "email" in channels:
        tasks["email"] = send_email_prop_alert(prop)

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return {
        channel: (result is True)
        for channel, result in zip(tasks.keys(), results)
    }
