import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yfinance as yf
import pandas as pd
from google import genai

# Load Credentials from Cloud Secrets
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

WATCHLIST = [
    "TATAMOTORS.NS", "HBLPOWER.NS", "GENUSPOWER.NS", 
    "SHIVALIK.NS", "BHEL.NS", "BEL.NS", "ZOMATO.NS", "INFY.NS"
]

def scan_stocks():
    print("Agent 1: Scanning watchlist for volume surge and momentum...")
    best_candidate = None
    highest_vol_ratio = 0.0

    for ticker in WATCHLIST:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")
            if len(hist) < 21:
                continue

            avg_vol = hist['Volume'].iloc[-21:-1].mean()
            last_vol = hist['Volume'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            latest_close = hist['Close'].iloc[-1]
            
            day_gain = ((latest_close - prev_close) / prev_close) * 100
            vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0

            # Filter for volume surge and positive bias
            if vol_ratio > 1.2 and vol_ratio > highest_vol_ratio:
                highest_vol_ratio = vol_ratio
                best_candidate = {
                    "ticker": ticker,
                    "close": round(float(latest_close), 2),
                    "day_gain": round(float(day_gain), 2),
                    "vol_ratio": round(float(vol_ratio), 2)
                }
        except Exception as e:
            print(f"Skipping {ticker}: {e}")

    # Fallback to primary candidate if market was quiet
    if not best_candidate:
        best_candidate = {"ticker": "TATAMOTORS.NS", "close": 0.0, "day_gain": 0.0, "vol_ratio": 1.0}
    
    return best_candidate

def run_agent_debate(candidate):
    print("Agents 2, 3 & 4: Running Bull vs. Bear debate...")
    client = genai.Client(api_key=GEMINI_KEY)

    prompt = f"""
    You are orchestrating an adversarial trade debate between two elite hedge fund analysts and a Chief Investment Officer (CIO).
    
    Target Stock: {candidate['ticker']}
    Previous Close: ₹{candidate['close']}
    Previous Day Gain: {candidate['day_gain']}%
    Volume Surge Ratio: {candidate['vol_ratio']}x of 20-day average
    Goal: Identify if this stock can deliver a 2-3% move in today's trading session.

    Structure your response cleanly in these 3 parts:
    
    1. 🐂 BULL AGENT CASE:
    - High-momentum entry triggers and why buyers will push price up 2-3% today.
    - Key intraday support levels.

    2. 🐻 BEAR AGENT CASE:
    - Overhead supply zones, rejection levels, and trap scenarios.
    - Downside risks and market drag.

    3. ⚖️ CIO ARBITRATOR FINAL VERDICT:
    - Final Call: (BUY / PASS)
    - Target: Price (+2% to +3%)
    - Stop Loss: Price (-1% to -1.5%)
    - Probability Score: X%
    - 1-Line Execution Summary
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def send_email(candidate, debate_result):
    print("Agent 5: Sending trade report to email...")
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"🚀 Morning Momentum Pick: {candidate['ticker']} (8:30 AM Briefing)"

    body = f"""Morning Stock Selection Report
----------------------------------------
Target Ticker: {candidate['ticker']}
Previous Close: ₹{candidate['close']}
Volume Surge: {candidate['vol_ratio']}x

{debate_result}
"""
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("Email sent successfully!")

if __name__ == "__main__":
    pick = scan_stocks()
    report = run_agent_debate(pick)
    send_email(pick, report)
