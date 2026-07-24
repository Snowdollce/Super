#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI News Automation & Email Dispatch Script
===========================================
- Fetches daily AI news from global and Thai RSS sources.
- Cleans and categorizes news items with '💡 นวัตกรรม & ข่าวสาร AI ทั่วไป' first.
- Formats text using 'TH Sarabun New' font, size 16pt.
- Summarizes into concise Thai bullet points focusing on core key points.
- Sends email via local Outlook Desktop client (passwordless) or SMTP fallback.
"""

import os
import sys
import re
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import argparse
import json
import hashlib


# --- CONFIGURATION LOADER ---
def load_env(env_file="config.env"):
    """Loads environment variables from config.env and os.environ."""
    config = {
        "SMTP_SERVER": "smtp.office365.com",
        "SMTP_PORT": "587",
        "USE_TLS": "True",
        "SENDER_EMAIL": "your_email@ftpi.or.th",
        "SENDER_PASSWORD": "",
        "RECIPIENT_EMAIL": "jantakarn@ftpi.or.th",
        "GEMINI_API_KEY": ""
    }
    
    # Read from environment variables first (such as Render environment variables)
    for key in config.keys():
        val = os.environ.get(key)
        if val is not None:
            config[key] = val
            
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, env_file)
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
    return config

# --- RSS NEWS SOURCES ---
RSS_SOURCES = [
    {
        "name": "Google News AI (Global)",
        "url": "https://news.google.com/rss/search?q=Artificial+Intelligence+AI+technology&hl=en-US&gl=US&ceid=US:en",
        "lang": "en"
    },
    {
        "name": "Google News AI (Thai)",
        "url": "https://news.google.com/rss/search?q=" + urllib.parse.quote("AI ปัญญาประดิษฐ์") + "&hl=th&gl=TH&ceid=TH:th",
        "lang": "th"
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "lang": "en"
    }
]

def clean_html(text):
    """Remove HTML tags and clean up whitespace."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def fetch_rss_items(source_url, max_items=6):
    """Fetch RSS feed items using standard urllib."""
    items = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        req = urllib.request.Request(source_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            for item in root.findall('.//item')[:max_items]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                pubdate_elem = item.find('pubDate')
                
                title = clean_html(title_elem.text) if title_elem is not None else ""
                link = link_elem.text.strip() if link_elem is not None else "#"
                desc = clean_html(desc_elem.text) if desc_elem is not None else ""
                pubdate = pubdate_elem.text.strip() if pubdate_elem is not None else ""
                
                if title:
                    items.append({
                        "title": title,
                        "link": link,
                        "desc": desc,
                        "pubdate": pubdate
                    })
    except Exception as e:
        print(f"[!] Warning: Could not fetch from {source_url}: {e}")
    return items

def translate_and_summarize_title(title, desc=""):
    """
    Translates foreign news titles into clear, concise Thai key points.
    Formats summary into crisp, professional Thai bullets.
    """
    replacements = [
        ("artificial intelligence", "ปัญญาประดิษฐ์ (AI)"),
        ("generative ai", "Generative AI"),
        ("large language model", "โมเดลภาษาขนาดใหญ่ (LLM)"),
        ("large language models", "โมเดลภาษาขนาดใหญ่ (LLM)"),
        ("open-source", "โอเพ่นซอร์ส"),
        ("cybersecurity", "ความปลอดภัยทางไซเบอร์"),
        ("data center", "ศูนย์ข้อมูล (Data Center)"),
        ("data centers", "ศูนย์ข้อมูล (Data Center)"),
        ("healthcare", "การแพทย์และสาธารณสุข"),
        ("launches", "เปิดตัว"),
        ("unveils", "เปิดตัว"),
        ("announces", "ประกาศ"),
        ("releases", "ปล่อยอัปเดต"),
        ("introduces", "แนะนำ"),
        ("partners with", "จับมือร่วมกับ"),
        ("invests", "ลงทุน"),
        ("raises", "ระดมทุนได้"),
        ("billion", "พันล้านดอลลาร์"),
        ("million", "ล้านดอลลาร์"),
        ("threatens", "ส่งผลกระทบต่อ"),
        ("rattling", "สะเทือน"),
        ("stocks sink", "หุ้นกลุ่มเทคโนโลยีปรับตัวลดลง"),
        ("lawsuit", "ข้อพิพาททางกฎหมาย"),
    ]
    
    is_thai = any('\u0e00' <= char <= '\u0e7f' for char in title)
    
    if is_thai:
        summary_bullet = title
    else:
        summary_bullet = title
        for eng, th in replacements:
            summary_bullet = re.sub(re.escape(eng), th, summary_bullet, flags=re.IGNORECASE)
        summary_bullet = summary_bullet.strip()
    
    cleaned_desc = clean_html(desc) if desc else ""
    if cleaned_desc and len(cleaned_desc) > 30:
        if len(cleaned_desc) > 130:
            cleaned_desc = cleaned_desc[:130] + "..."
        return summary_bullet, cleaned_desc
    
    return summary_bullet, ""

def summarize_batch_with_gemini(items, api_key):
    """
    Summarizes a batch of news items using a single Gemini API call to avoid rate limits.
    """
    if not api_key or not items:
        return []
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
    
    # Format the input items for the prompt
    formatted_items = []
    for i, item in enumerate(items):
        formatted_items.append(f"--- Article {i} ---\nTitle: {item['title']}\nDescription: {item['desc']}")
    
    input_text = "\n\n".join(formatted_items)
    
    prompt = f"""
    You are an expert AI news translator and summarizer.
    Translate and summarize the following list of news articles into professional, concise Thai.
    
    {input_text}
    
    Guidelines:
    1. Translate the Title of each article into a clear, professional Thai headline. Keep it under 100 characters.
    2. Summarize the Description/Content of each article into a single concise Thai bullet point (max 150 characters) focusing on the absolute key takeaway.
    3. Output the result strictly in JSON format as a list of objects with the keys "title_summary" and "desc_summary" in the exact same order as the input:
       [
         {{
           "title_summary": "Headline 0...",
           "desc_summary": "Summary 0..."
         }},
         {{
           "title_summary": "Headline 1...",
           "desc_summary": "Summary 1..."
         }}
       ]
    Do not include any other text or markdown block backticks around the JSON.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            response_body = res.read().decode("utf-8")
            res_json = json.loads(response_body)
            text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
    except Exception as e:
        print(f"[!] Gemini batch translation failed: {e}")
    return []

def save_news_data(news_list, filename="news_data.json"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    
    existing_news = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for article in data:
                        existing_news[article["id"]] = article
                elif isinstance(data, dict):
                    existing_news = data
        except Exception as e:
            print(f"[!] Error loading existing news: {e}")
            
    for article in news_list:
        existing_news[article["id"]] = article
        
    sorted_news = sorted(existing_news.values(), key=lambda x: x.get("pubdate", ""), reverse=True)
    trimmed_news = sorted_news[:50]
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(trimmed_news, f, ensure_ascii=False, indent=2)
        print(f"[✓] Successfully saved {len(trimmed_news)} news items to {file_path}")
    except Exception as e:
        print(f"[!] Error saving news database: {e}")


def categorize_items(news_items, api_key=None):
    """
    Categorizes news items into structured sections.
    """
    categories = {
        "💡 นวัตกรรม & ข่าวสาร AI ทั่วไป": [],
        "🤖 การพัฒนาโมเดล & เทคโนโลยี AI ใหม่": [],
        "💼 การประยุกต์ใช้ในธุรกิจ & อุตสาหกรรม": [],
        "🛡️ นโยบาย ความปลอดภัย & ธรรมาภิบาล AI": []
    }
    
    # 1. Filter unique items
    unique_items = []
    seen_titles = set()
    for item in news_items:
        title = item["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        unique_items.append(item)
        
    # 2. Translate in batches of 8 to prevent oversized prompt or payload errors (8 is very safe)
    summaries = []
    if api_key and unique_items:
        batch_size = 8
        for i in range(0, len(unique_items), batch_size):
            batch = unique_items[i:i+batch_size]
            print(f"[*] Batch translating {len(batch)} items with Gemini API (Batch {i//batch_size + 1})...")
            batch_summaries = summarize_batch_with_gemini(batch, api_key)
            # Make sure we got a valid response list of the same length
            if len(batch_summaries) == len(batch):
                summaries.extend(batch_summaries)
            else:
                # Fallback to local translation for this batch
                print(f"[!] Warning: Batch translation returned mismatched length. Using local fallback.")
                for b_item in batch:
                    t_sum, d_sum = translate_and_summarize_title(b_item["title"], b_item["desc"])
                    summaries.append({"title_summary": t_sum, "desc_summary": d_sum})
                    
    # If no api_key or failed entirely
    if len(summaries) < len(unique_items):
        # Fill rest with local translation
        start_idx = len(summaries)
        for b_item in unique_items[start_idx:]:
            t_sum, d_sum = translate_and_summarize_title(b_item["title"], b_item["desc"])
            summaries.append({"title_summary": t_sum, "desc_summary": d_sum})

    # 3. Categorize and build bullet items
    for idx, item in enumerate(unique_items):
        t_summary = summaries[idx]["title_summary"]
        desc_summary = summaries[idx]["desc_summary"]
        
        article_id = hashlib.md5(item["link"].encode('utf-8')).hexdigest()[:8]
        
        bullet_item = {
            "id": article_id,
            "title_summary": t_summary,
            "desc_summary": desc_summary,
            "original_title": item["title"],
            "original_desc": item["desc"],
            "link": item["link"]
        }
        
        t_lower = item["title"].lower()
        if any(k in t_lower for k in ["model", "gpt", "claude", "gemini", "llama", "grok", "deepseek", "chip", "nvidia", "silicon", "agent"]):
            categories["🤖 การพัฒนาโมเดล & เทคโนโลยี AI ใหม่"].append(bullet_item)
        elif any(k in t_lower for k in ["business", "enterprise", "market", "revenue", "startup", "invest", "stock", "company", "work", "job"]):
            categories["💼 การประยุกต์ใช้ในธุรกิจ & อุตสาหกรรม"].append(bullet_item)
        elif any(k in t_lower for k in ["law", "policy", "security", "eu ai act", "government", "regulation", "ethics", "safety"]):
            categories["🛡️ นโยบาย ความปลอดภัย & ธรรมาภิบาล AI"].append(bullet_item)
        else:
            categories["💡 นวัตกรรม & ข่าวสาร AI ทั่วไป"].append(bullet_item)
            
    return categories

def generate_html_digest(categories, recipient_email):
    """
    Generates a responsive HTML email digest using TH Sarabun New font (16pt).
    """
    today_str = datetime.now().strftime("%d/%m/%Y")
    
    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>สรุปข่าวสาร AI ประจำวัน</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        body {{
            font-family: 'TH Sarabun New', 'Sarabun', 'Segoe UI', Tahoma, sans-serif;
            font-size: 16pt;
            line-height: 1.6;
            background-color: #f4f6f9;
            margin: 0;
            padding: 20px;
            color: #222222;
        }}
        .container {{
            max-width: 720px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            font-family: 'TH Sarabun New', 'Sarabun', 'Segoe UI', sans-serif;
        }}
        .header {{
            background: linear-gradient(135deg, #0f4c81 0%, #1b6ca8 100%);
            color: #ffffff;
            padding: 25px 30px;
            text-align: left;
        }}
        .header h1 {{
            margin: 0 0 6px 0;
            font-size: 22pt;
            font-weight: 700;
            font-family: 'TH Sarabun New', 'Sarabun', sans-serif;
        }}
        .header p {{
            margin: 0;
            font-size: 14pt;
            opacity: 0.95;
            font-family: 'TH Sarabun New', 'Sarabun', sans-serif;
        }}
        .content {{
            padding: 25px 30px;
            font-size: 16pt;
            font-family: 'TH Sarabun New', 'Sarabun', sans-serif;
        }}
        .category-title {{
            font-size: 18pt;
            font-weight: 700;
            color: #0f4c81;
            border-bottom: 2px solid #0f4c81;
            padding-bottom: 4px;
            margin-top: 22px;
            margin-bottom: 14px;
            font-family: 'TH Sarabun New', 'Sarabun', sans-serif;
        }}
        .bullet-list {{
            padding-left: 24px;
            margin: 0;
        }}
        .bullet-item {{
            margin-bottom: 12px;
            line-height: 1.6;
            font-size: 16pt;
            font-family: 'TH Sarabun New', 'Sarabun', sans-serif;
        }}
        .bullet-item strong {{
            color: #111111;
            font-weight: 700;
        }}
        .bullet-desc {{
            color: #444444;
            font-size: 15pt;
            margin-top: 2px;
            display: block;
            font-family: 'TH Sarabun New', 'Sarabun', sans-serif;
        }}
        .source-link {{
            display: inline-block;
            font-size: 14pt;
            color: #1b6ca8;
            text-decoration: none;
            margin-left: 4px;
            font-family: 'TH Sarabun New', 'Sarabun', sans-serif;
        }}
        .source-link:hover {{
            text-decoration: underline;
        }}
        .footer {{
            background-color: #f8f9fa;
            border-top: 1px solid #e9ecef;
            padding: 16px 30px;
            font-size: 14pt;
            color: #555555;
            text-align: center;
            line-height: 1.5;
            font-family: 'TH Sarabun New', 'Sarabun', sans-serif;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 สรุปข่าวสาร & ความเคลื่อนไหว AI ประจำวัน</h1>
            <p>รายงานสรุปสาระสำคัญประจำวันที่ {today_str} | นำส่งอัตโนมัติเวลา 09.00 น.</p>
        </div>
        <div class="content">
"""

    total_articles = sum(len(items) for items in categories.values())

    if total_articles == 0:
        html += "<p style='text-align: center; color: #777;'>ไม่พบข่าวสารใหม่ในรอบ 24 ชั่วโมงที่ผ่านมา</p>"
    else:
        for cat_name, items in categories.items():
            if not items:
                continue
            html += f'<div class="category-title">{cat_name}</div>'
            html += '<ul class="bullet-list">'
            for item in items:
                html += f'<li class="bullet-item" style="margin-bottom: 18px;">'
                html += f'<strong>{item["title_summary"]}</strong>'
                if item["desc_summary"]:
                    html += f'<span class="bullet-desc" style="display: block; margin-top: 4px; color: #555; font-size: 15pt;">• {item["desc_summary"]}</span>'
                html += f'<div style="margin-top: 6px; margin-bottom: 6px;">'
                html += f'  <a href="{item["link"]}" class="source-link" target="_blank" style="color: #1b6ca8; text-decoration: none; font-size: 14pt; margin-right: 15px; font-weight: 600;">📄 อ่านข่าวต้นฉบับ</a>'
                html += f'  <a href="http://localhost:5000/?news_id={item["id"]}" target="_blank" style="display: inline-block; background-color: #0f4c81; color: #ffffff; text-decoration: none; padding: 3px 12px; border-radius: 5px; font-size: 13pt; font-weight: bold; border: 1px solid #0f4c81; font-family: \'Sarabun\', \'Segoe UI\', sans-serif;">🚀 สร้างโพสต์ Facebook</a>'
                html += f'</div>'
                html += '</li>'
            html += '</ul>'

    html += f"""
        </div>
        <div class="footer">
            นำส่งถึง: <strong>{recipient_email}</strong><br>
            ระบบติดตามข่าวสาร AI และสรุปอัตโนมัติ | สถาบันเพิ่มผลผลิตแห่งชาติ (FTPI)
        </div>
    </div>
</body>
</html>
"""
    return html

def send_email(config, subject, html_content):
    """Sends HTML email using SMTP (primary) or Outlook COM (fallback)."""
    sender_email = config.get("SENDER_EMAIL", "").strip()
    sender_password = config.get("SENDER_PASSWORD", "").strip()
    recipient_email = config.get("RECIPIENT_EMAIL", "jantakarn@ftpi.or.th").strip()
    smtp_server = config.get("SMTP_SERVER", "smtp.office365.com").strip()
    smtp_port = int(config.get("SMTP_PORT", 587))
    use_tls = config.get("USE_TLS", "True").lower() == "true"

    has_credentials = (
        sender_email 
        and "your_email" not in sender_email 
        and sender_password 
        and "your_password" not in sender_password
    )

    # 1. Primary Method: SMTP Dispatch when credentials are set in config.env
    if has_credentials:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email
        part_html = MIMEText(html_content, "html", "utf-8")
        msg.attach(part_html)

        try:
            print(f"[*] Connecting to SMTP server {smtp_server}:{smtp_port} for {sender_email}...")
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            if use_tls:
                server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())
            server.quit()
            print(f"[✓] SUCCESS: Email sent to {recipient_email} via SMTP!")
            return True
        except Exception as ex:
            print(f"[!] SMTP Error: Could not send email: {ex}")
            print("[*] Attempting fallback methods...")

    # 2. Fallback: Outlook COM Integration
    try:
        import win32com.client
        print("[*] Attempting fallback via Outlook Desktop...")
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = recipient_email
        mail.Subject = subject
        mail.HTMLBody = html_content
        mail.Send()
        print(f"[✓] Email sent to {recipient_email} via Outlook Desktop!")
        return True
    except Exception as e:
        print(f"[!] Outlook notice: {e}")

    if not has_credentials:
        print("\n[!] SMTP credentials are not configured in config.env.")
        print("[!] Please edit config.env and set SENDER_EMAIL and SENDER_PASSWORD.")
        return False

    return False

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="AI News Automation & Daily Email Dispatcher")
    parser.add_argument("--dry-run", action="store_true", help="Fetch news and generate HTML output without sending email")
    parser.add_argument("--send-test", action="store_true", help="Send test email immediately using config credentials")
    args = parser.parse_args()

    config = load_env()
    print("=" * 60)
    print(" [AI News] Daily Automation & Email Dispatcher")
    print(f" Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_raw_items = []
    for source in RSS_SOURCES:
        print(f"[*] Fetching from {source['name']}...")
        items = fetch_rss_items(source['url'], max_items=6)
        all_raw_items.extend(items)

    print(f"[*] Retrieved {len(all_raw_items)} total raw articles.")

    api_key = config.get("GEMINI_API_KEY", "").strip()
    categories = categorize_items(all_raw_items, api_key)

    # Collect and save processed news items
    all_processed_items = []
    for cat_name, items in categories.items():
        for item in items:
            all_processed_items.append({
                "id": item["id"],
                "title": item["original_title"],
                "link": item["link"],
                "desc": item["original_desc"],
                "pubdate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title_summary": item["title_summary"],
                "desc_summary": item["desc_summary"],
                "category": cat_name
            })
    save_news_data(all_processed_items)

    recipient = config.get("RECIPIENT_EMAIL", "jantakarn@ftpi.or.th")
    html_content = generate_html_digest(categories, recipient)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    summary_path = os.path.join(script_dir, "latest_summary.html")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[✓] Saved local HTML preview to: {summary_path}")

    today_str = datetime.now().strftime("%d/%m/%Y")
    subject = f"🤖 [AI News Update] สรุปข่าวสาร & ความเคลื่อนไหว AI ประจำวันที่ {today_str}"

    if args.dry_run:
        print("\n--- [DRY RUN MODE] Printing Summary Preview ---")
        for cat_name, items in categories.items():
            if items:
                print(f"\n{cat_name}:")
                for item in items:
                    print(f" • {item['title_summary']}")
        print("\n[✓] Dry run complete. No email was sent.")
        return

    print(f"[*] Preparing to send email digest to {recipient}...")
    send_email(config, subject, html_content)

if __name__ == "__main__":
    main()
