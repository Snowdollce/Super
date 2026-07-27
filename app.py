#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI News Web Server Backend
===========================
- Self-contained Python HTTP server (standard library only, no pip dependencies).
- Exposes API endpoints for reading news, manual fetch, saving API key, and post generation.
- Serves the frontend SPA from the 'web' folder.
"""

import http.server
import socketserver
import json
import os
import urllib.request
import urllib.error
import time
import subprocess
import sys
import re
import hashlib
import threading
import base64
from datetime import datetime

PORT = 5000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(DIRECTORY, "web")
SAVED_IDEAS_FILE = os.path.join(DIRECTORY, "saved_ideas.json")
SAVED_IMAGES_FILE = os.path.join(DIRECTORY, "saved_images.json")

def load_saved_images_list():
    if os.path.exists(SAVED_IMAGES_FILE):
        try:
            with open(SAVED_IMAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading saved images:", e)
    return []

def save_saved_images_list(images):
    try:
        with open(SAVED_IMAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(images, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Error saving images list:", e)
    return False

def save_config_keys_to_env(new_settings):
    env_path = os.path.join(DIRECTORY, "config.env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    for key, val in new_settings.items():
        key_exists = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={val}\n"
                key_exists = True
                break
        if not key_exists:
            lines.append(f"{key}={val}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True

def load_saved_ideas():
    supabase = get_supabase_config()
    if supabase:
        url, key = supabase
        req_url = f"{url}/rest/v1/saved_ideas?select=*&order=saved_at.desc"
        req = urllib.request.Request(
            req_url,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return json.loads(res.read().decode("utf-8"))
        except Exception as e:
            print("Error loading from Supabase:", e)
            
    if os.path.exists(SAVED_IDEAS_FILE):
        try:
            with open(SAVED_IDEAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading saved ideas:", e)
    return []

def save_saved_ideas(ideas):
    try:
        with open(SAVED_IDEAS_FILE, "w", encoding="utf-8") as f:
            json.dump(ideas, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Error writing saved ideas:", e)
    return False

def load_config():
    """Loads environment variables from config.env and os.environ."""
    config = {}
    # Read from environment variables first (such as Render environment variables)
    keys_to_read = [
        "GEMINI_API_KEY", "SMTP_SERVER", "SMTP_PORT", "USE_TLS", 
        "SENDER_EMAIL", "SENDER_PASSWORD", "RECIPIENT_EMAIL", 
        "SUPABASE_URL", "SUPABASE_KEY", "FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"
    ]
    for key in keys_to_read:
        val = os.environ.get(key)
        if val is not None:
            config[key] = val

    env_path = os.path.join(DIRECTORY, "config.env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
                    
    # Force fallback override for expired Render token
    token = config.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if token.startswith("EAAgnh6DxJrYBSFnKmc") or not token:
        config["FB_PAGE_ID"] = "1228647806999414"
        config["FB_PAGE_ACCESS_TOKEN"] = "EAAgnh6DxJrYBSJIUSwlEfOv6QlZBI0dUIDHZCX3yIhZBzpXpyARrBKzAI53MNuulZCjpal7mm17OyOeKrtSWcl9BvF06S1U9vNpe98Fh9ZAmZBo9LMdN7XnP4feeKZCzlT5gw2IklQaK5Si6ZCzxcxRYEg2aHEaG8lr80AZBK7ijbV5j4LpJ4jVpZAQ06yOO8Dlswjea1NQHVJE55UfJjxECXKZBiq1yLqeJng2yYdtZCOcZD"
        
    return config

def get_supabase_config():
    config = load_config()
    url = config.get("SUPABASE_URL", "").strip()
    key = config.get("SUPABASE_KEY", "").strip()
    if url and key:
        return url, key
    return None

def save_saved_ideas_supabase(idea):
    supabase = get_supabase_config()
    if not supabase:
        return False
    url, key = supabase
    req_url = f"{url}/rest/v1/saved_ideas?on_conflict=id"
    payload = json.dumps(idea).encode("utf-8")
    req = urllib.request.Request(
        req_url,
        data=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return True
    except Exception as e:
        print("Error saving to Supabase:", e)
        return False

def update_saved_idea_status_supabase(idea_id, status):
    supabase = get_supabase_config()
    if not supabase:
        return False
    url, key = supabase
    req_url = f"{url}/rest/v1/saved_ideas?id=eq.{idea_id}"
    payload = json.dumps({"status": status}).encode("utf-8")
    req = urllib.request.Request(
        req_url,
        data=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        method="PATCH"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return True
    except Exception as e:
        print("Error updating status in Supabase:", e)
        return False

def delete_saved_idea_supabase(idea_id):
    supabase = get_supabase_config()
    if not supabase:
        return False
    url, key = supabase
    req_url = f"{url}/rest/v1/saved_ideas?id=eq.{idea_id}"
    req = urllib.request.Request(
        req_url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}"
        },
        method="DELETE"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return True
    except Exception as e:
        print("Error deleting from Supabase:", e)
        return False

def save_api_key_to_env(api_key):
    """Saves the Gemini API key to config.env."""
    env_path = os.path.join(DIRECTORY, "config.env")
    lines = []
    key_exists = False
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            if line.strip().startswith("GEMINI_API_KEY="):
                lines[i] = f"GEMINI_API_KEY={api_key}\n"
                key_exists = True
                break
                
    if not key_exists:
        lines.append(f"\n# Gemini API Key for high quality translation and FB post generation\nGEMINI_API_KEY={api_key}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True

def upload_photo_to_facebook(page_id, access_token, img_data, caption, filename):
    url = f"https://graph.facebook.com/v20.0/{page_id}/photos"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    content_type = "image/jpeg"
    if filename.lower().endswith(".png"):
        content_type = "image/png"
    elif filename.lower().endswith(".gif"):
        content_type = "image/gif"
        
    parts = []
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(b'Content-Disposition: form-data; name="caption"')
    parts.append(b'')
    parts.append(caption.encode("utf-8"))
    
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(b'Content-Disposition: form-data; name="access_token"')
    parts.append(b'')
    parts.append(access_token.encode("utf-8"))
    
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(f'Content-Disposition: form-data; name="source"; filename="{filename}"'.encode("utf-8"))
    parts.append(f'Content-Type: {content_type}'.encode("utf-8"))
    parts.append(b'')
    parts.append(img_data)
    
    parts.append(f"--{boundary}--".encode("utf-8"))
    parts.append(b'')
    
    body = b"\r\n".join(parts)
    
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": len(body)
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return True, res_data.get("id")
    except Exception as e:
        err_msg = str(e)
        if hasattr(e, 'read'):
            try:
                err_msg += " - " + e.read().decode('utf-8')
            except Exception:
                pass
        return False, f"Facebook Photo API error: {err_msg}"

def publish_to_facebook(idea):
    config = load_config()
    page_id = config.get("FB_PAGE_ID", "").strip()
    access_token = config.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not access_token:
        return False, "Facebook Page ID or Access Token is missing in configuration."
        
    message = idea.get("content", "")
    image_id = idea.get("selected_image_id", "")
    
    if image_id:
        images = load_saved_images_list()
        image = next((img for img in images if img["id"] == image_id), None)
        if image:
            local_path = os.path.join(DIRECTORY, "web", "uploads", image_id)
            if os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f:
                        img_data = f.read()
                    return upload_photo_to_facebook(page_id, access_token, img_data, message, image_id)
                except Exception as e:
                    return False, f"Failed to read local image: {e}"
            else:
                return False, f"Local image file not found on disk: {image_id}"
                
    url = f"https://graph.facebook.com/v20.0/{page_id}/feed"
    payload = urllib.parse.urlencode({
        "message": message,
        "access_token": access_token
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return True, res_data.get("id")
    except Exception as e:
        err_msg = str(e)
        if hasattr(e, 'read'):
            try:
                err_msg += " - " + e.read().decode('utf-8')
            except Exception:
                pass
        return False, f"Facebook API error: {err_msg}"

def upload_temp_photo_to_facebook(page_id, access_token, img_data, filename):
    url = f"https://graph.facebook.com/v20.0/{page_id}/photos"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    content_type = "image/jpeg"
    if filename.lower().endswith(".png"):
        content_type = "image/png"
    elif filename.lower().endswith(".gif"):
        content_type = "image/gif"
        
    parts = []
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(b'Content-Disposition: form-data; name="published"')
    parts.append(b'')
    parts.append(b'false')
    
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(b'Content-Disposition: form-data; name="temporary"')
    parts.append(b'')
    parts.append(b'true')
    
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(b'Content-Disposition: form-data; name="access_token"')
    parts.append(b'')
    parts.append(access_token.encode("utf-8"))
    
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(f'Content-Disposition: form-data; name="source"; filename="{filename}"'.encode("utf-8"))
    parts.append(f'Content-Type: {content_type}'.encode("utf-8"))
    parts.append(b'')
    parts.append(img_data)
    
    parts.append(f"--{boundary}--".encode("utf-8"))
    parts.append(b'')
    
    body = b"\r\n".join(parts)
    
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": len(body)
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return True, res_data.get("id")
    except Exception as e:
        err_msg = str(e)
        if hasattr(e, 'read'):
            try:
                err_msg += " - " + e.read().decode('utf-8')
            except Exception:
                pass
        return False, f"Facebook Photo Upload error: {err_msg}"

def schedule_to_facebook(idea, scheduled_time_str):
    config = load_config()
    page_id = config.get("FB_PAGE_ID", "").strip()
    access_token = config.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not access_token:
        return False, "Facebook Page ID or Access Token is missing in configuration."
        
    try:
        dt = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
        timestamp = int(dt.timestamp())
    except Exception as e:
        return False, f"Invalid date format: {e}"
        
    message = idea.get("content", "")
    image_id = idea.get("selected_image_id", "")
    
    photo_id = None
    if image_id:
        images = load_saved_images_list()
        image = next((img for img in images if img["id"] == image_id), None)
        if image:
            local_path = os.path.join(DIRECTORY, "web", "uploads", image_id)
            if os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f:
                        img_data = f.read()
                    success, res_val = upload_temp_photo_to_facebook(page_id, access_token, img_data, image_id)
                    if not success:
                        return False, f"Failed to upload photo for scheduling: {res_val}"
                    photo_id = res_val
                except Exception as e:
                    return False, f"Failed to read/upload local image: {e}"
            else:
                return False, f"Local image file not found on disk: {image_id}"
                
    url = f"https://graph.facebook.com/v20.0/{page_id}/feed"
    params = {
        "message": message,
        "published": "false",
        "scheduled_publish_time": str(timestamp),
        "unpublished_content_type": "SCHEDULED",
        "access_token": access_token
    }
    if photo_id:
        params["attached_media[0]"] = json.dumps({"media_fbid": photo_id})
        
    payload = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return True, res_data.get("id")
    except Exception as e:
        err_msg = str(e)
        if hasattr(e, 'read'):
            try:
                err_msg += " - " + e.read().decode('utf-8')
            except Exception:
                pass
        return False, f"Facebook API error: {err_msg}"

def delete_facebook_post(post_id):
    config = load_config()
    access_token = config.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not access_token:
        return False, "Facebook Access Token is missing."
        
    url = f"https://graph.facebook.com/v20.0/{post_id}"
    payload = urllib.parse.urlencode({
        "access_token": access_token
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return res_data.get("success", False), ""
    except Exception as e:
        err_msg = str(e)
        if hasattr(e, 'read'):
            try:
                err_msg += " - " + e.read().decode('utf-8')
            except Exception:
                pass
        return False, f"Facebook API delete error: {err_msg}"

def scheduler_loop():
    print("[*] Background scheduler thread started.")
    while True:
        try:
            ideas = load_saved_ideas()
            updated = False
            for idea in ideas:
                if idea.get("status") == "Scheduled" and idea.get("scheduled_time"):
                    sched_time = idea.get("scheduled_time")
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sched_min = sched_time[:16]
                    now_min = now_str[:16]
                    if now_min >= sched_min:
                        if idea.get("facebook_post_id"):
                            print(f"[*] Scheduled idea {idea['id']} was already scheduled on Facebook (ID: {idea['facebook_post_id']}). Marking as Used.")
                            idea["status"] = "Used"
                            idea["posted_at"] = sched_time
                        else:
                            print(f"[*] Posting scheduled idea {idea['id']} to Facebook (scheduled: {sched_time}, now: {now_str})")
                            idea["status"] = "Posting"
                            if get_supabase_config():
                                update_saved_idea_status_supabase(idea["id"], "Posting")
                            else:
                                save_saved_ideas(ideas)
                                
                            success, post_id_or_err = publish_to_facebook(idea)
                            if success:
                                idea["status"] = "Used"
                                idea["facebook_post_id"] = post_id_or_err
                                idea["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                print(f"[SUCCESS] Posted idea {idea['id']} to FB Page. Post ID: {post_id_or_err}")
                            else:
                                idea["status"] = "Failed"
                                idea["post_error"] = post_id_or_err
                                print(f"[ERROR] Failed to post scheduled idea {idea['id']}: {post_id_or_err}")
                            
                        if get_supabase_config():
                            save_saved_ideas_supabase(idea)
                        else:
                            save_saved_ideas(ideas)
                        updated = True
            
        except Exception as e:
            print("[Scheduler Exception]:", e)
        time.sleep(30)

def call_gemini_api(api_key, title, desc, link):
    """Calls Gemini API to generate Facebook post ideas and image prompt."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
    
    prompt = f"""
    You are an expert social media manager and copywriter who writes high-converting Facebook posts.
    Your task is to create 3 to 5 post ideas in Thai based on this news article, plus 1 image generation prompt in English.
    
    News Title: {title}
    News Details: {desc}
    Original Link: {link}
    
    Guidelines for the Facebook post ideas:
    1. Tone & Persona: Speak in a friendly "friend telling news" style (เพื่อนบอกข่าว) - conversational, engaging, friendly, easy to understand, yet professional and credible. Do NOT use polite sentence-ending particles like "ค่ะ" (kha), "นะคะ" (na-kha), or "ครับ" (krub). Ensure the text reads naturally and professionally without these particles.
    2. Hook: Every idea MUST start with a strong, eye-catching hook as the very first sentence (วาง Hook ไว้เป็นประโยคแรกเสมอ) to grab readers' attention immediately.
    3. Structure: Use emojis appropriately, format with clear paragraph breaks, and you MUST always include the hashtags: #จันนิใช้เอไอ #AIbyJannie along with other relevant hashtags (e.g., #AI #Technology).
    4. Content: Explain the core essence of the news and why the reader should care.
       - Idea 1 (ไอเดียที่ 1): Must be in an educational/informative style (สไตล์ให้ความรู้) and its length must not exceed 250 words (ความยาวไม่เกิน 250 คำ).
       - Other Ideas (e.g., Idea 2, 3, etc.): Can offer different angles/styles (e.g., Practical/Business impact, Question/Discussion starter, Fun/Informative).
    
    Guidelines for the Image Prompt:
    Generate one highly detailed prompt (in English) for an AI image generator (such as Midjourney, DALL-E 3, or Stable Diffusion) to create a matching illustration or conceptual image for this post. The image should look premium, modern, and conceptual. Avoid text in the image. Format: "A futuristic/conceptual illustration of... style: clean, modern tech, 3d render/digital art, vibrant lighting, highly detailed --ar 16:9"
    
    Return the output as a clean JSON object containing:
    {{
      "news_title": "...",
      "ideas": [
        {{
          "id": 1,
          "angle": "...",
          "content": "..."
        }},
        ...
      ],
      "image_prompt": "..."
    }}
    Do not include any markdown backticks around the JSON.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                response_body = res.read().decode("utf-8")
                res_json = json.loads(response_body)
                text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                return json.loads(text)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 3  # sleep 3s, then 6s
                print(f"[!] Gemini API returned 429 (Rate Limit). Retrying in {sleep_time} seconds (Attempt {attempt+1}/{max_retries})...")
                time.sleep(sleep_time)
                continue
            raise e

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Allow CORS for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # API Routes
        if self.path == "/api/news":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            
            news_path = os.path.join(DIRECTORY, "news_data.json")
            if os.path.exists(news_path):
                with open(news_path, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(json.dumps([]).encode("utf-8"))
            return
            
        elif self.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            
            config = load_config()
            has_key = bool(config.get("GEMINI_API_KEY", "").strip())
            recipient = config.get("RECIPIENT_EMAIL", "")
            self.wfile.write(json.dumps({
                "has_gemini_key": has_key,
                "recipient_email": recipient,
                "fb_page_id": config.get("FB_PAGE_ID", ""),
                "fb_page_access_token": config.get("FB_PAGE_ACCESS_TOKEN", ""),
                "google_api_key": config.get("GOOGLE_API_KEY", ""),
                "gd_folder_id": config.get("GD_FOLDER_ID", "1Yw-r-tMVphny6fAkaTgSD9w812WC8dsy")
            }, ensure_ascii=False).encode("utf-8"))
            return
            
        elif self.path == "/api/saved-ideas":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            ideas = load_saved_ideas()
            self.wfile.write(json.dumps(ideas, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/images":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            images = load_saved_images_list()
            self.wfile.write(json.dumps(images, ensure_ascii=False).encode("utf-8"))
            return

        # Serve static HTML/JS/CSS from 'web' directory
        parsed_path = urllib.parse.urlparse(self.path)
        rel_path = urllib.parse.unquote(parsed_path.path.lstrip("/"))
        
        # If accessing the root, serve index.html
        if rel_path == "" or rel_path == "index.html":
            file_path = os.path.join(WEB_DIR, "index.html")
        else:
            file_path = os.path.join(WEB_DIR, rel_path)
            
        # Security: Prevent escaping from WEB_DIR
        normalized_path = os.path.abspath(file_path)
        if not normalized_path.startswith(os.path.abspath(WEB_DIR)):
            self.send_error(403, "Forbidden")
            return
            
        if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
            self.send_response(200)
            
            # Content-type mapping
            if normalized_path.endswith(".html"):
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif normalized_path.endswith(".css"):
                self.send_header("Content-Type", "text/css")
            elif normalized_path.endswith(".js"):
                self.send_header("Content-Type", "application/javascript")
            elif normalized_path.endswith(".json"):
                self.send_header("Content-Type", "application/json")
            elif normalized_path.endswith(".png"):
                self.send_header("Content-Type", "image/png")
            elif normalized_path.endswith(".jpg") or normalized_path.endswith(".jpeg"):
                self.send_header("Content-Type", "image/jpeg")
            elif normalized_path.endswith(".svg"):
                self.send_header("Content-Type", "image/svg+xml")
            
            self.end_headers()
            with open(normalized_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            # Fallback to index.html for Single Page Routing
            fallback_path = os.path.join(WEB_DIR, "index.html")
            if os.path.exists(fallback_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(fallback_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File Not Found")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            req_data = json.loads(post_data.decode('utf-8'))
        except Exception:
            req_data = {}
            
        if self.path == "/api/save-key":
            api_key = req_data.get("api_key", "").strip()
            if not api_key:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "API Key is required"}).encode("utf-8"))
                return
                
            save_api_key_to_env(api_key)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return
            
        elif self.path == "/api/save-config":
            api_key = req_data.get("api_key", "").strip()
            fb_page_id = req_data.get("fb_page_id", "").strip()
            fb_page_access_token = req_data.get("fb_page_access_token", "").strip()
            google_api_key = req_data.get("google_api_key", "").strip()
            gd_folder_id = req_data.get("gd_folder_id", "").strip()
            
            settings = {}
            if api_key:
                settings["GEMINI_API_KEY"] = api_key
            settings["FB_PAGE_ID"] = fb_page_id
            settings["FB_PAGE_ACCESS_TOKEN"] = fb_page_access_token
            settings["GOOGLE_API_KEY"] = google_api_key
            settings["GD_FOLDER_ID"] = gd_folder_id
            
            success = save_config_keys_to_env(settings)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success}).encode("utf-8"))
            return

        elif self.path == "/api/images/upload":
            filename = req_data.get("filename", "").strip()
            base64_data = req_data.get("data", "").strip()
            
            if not filename or not base64_data:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "filename and data are required"}).encode("utf-8"))
                return
                
            uploads_dir = os.path.join(DIRECTORY, "web", "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]
                
            try:
                img_bytes = base64.b64decode(base64_data)
                name_parts = os.path.splitext(filename)
                unique_filename = f"{name_parts[0]}_{int(time.time())}{name_parts[1]}"
                file_path = os.path.join(uploads_dir, unique_filename)
                
                with open(file_path, "wb") as f:
                    f.write(img_bytes)
                    
                images = load_saved_images_list()
                new_image = {
                    "id": unique_filename,
                    "name": filename,
                    "url": f"/uploads/{unique_filename}",
                    "source": "local",
                    "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                images.insert(0, new_image)
                save_saved_images_list(images)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "image": new_image}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Failed to upload image: {e}"}).encode("utf-8"))
            return

        elif self.path == "/api/schedule-post":
            idea_id = req_data.get("idea_id", "").strip()
            scheduled_time = req_data.get("scheduled_time", "").strip()
            selected_image_id = req_data.get("selected_image_id", "").strip()
            
            if not idea_id or not scheduled_time:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "idea_id and scheduled_time are required"}).encode("utf-8"))
                return
                
            ideas = load_saved_ideas()
            success = False
            error_msg = ""
            for idea in ideas:
                if idea["id"] == idea_id:
                    old_fb_id = idea.get("facebook_post_id")
                    if old_fb_id:
                        try:
                            delete_facebook_post(old_fb_id)
                        except Exception as e:
                            print(f"Warning: Failed to delete old scheduled post {old_fb_id}: {e}")
                            
                    idea["scheduled_time"] = scheduled_time
                    idea["selected_image_id"] = selected_image_id
                    
                    fb_success, fb_res = schedule_to_facebook(idea, scheduled_time)
                    if fb_success:
                        idea["status"] = "Scheduled"
                        idea["facebook_post_id"] = fb_res
                        if "post_error" in idea:
                            del idea["post_error"]
                        success = True
                    else:
                        error_msg = fb_res
                        idea["status"] = "Failed"
                        idea["post_error"] = fb_res
                        
                    if get_supabase_config():
                        save_saved_ideas_supabase(idea)
                    break
                    
            if success:
                if not get_supabase_config():
                    save_saved_ideas(ideas)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            else:
                if not get_supabase_config():
                    save_saved_ideas(ideas)
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": error_msg or "Failed to schedule on Facebook"}).encode("utf-8"))
            return

        elif self.path == "/api/cancel-post":
            idea_id = req_data.get("idea_id", "").strip()
            
            if not idea_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "idea_id is required"}).encode("utf-8"))
                return
                
            ideas = load_saved_ideas()
            success = False
            for idea in ideas:
                if idea["id"] == idea_id:
                    old_fb_id = idea.get("facebook_post_id")
                    if old_fb_id:
                        try:
                            delete_facebook_post(old_fb_id)
                        except Exception as e:
                            print(f"Warning: Failed to delete Facebook post on cancel: {e}")
                    idea["status"] = "Waiting List"
                    idea["scheduled_time"] = ""
                    if "facebook_post_id" in idea:
                        del idea["facebook_post_id"]
                    if "post_error" in idea:
                        del idea["post_error"]
                    success = True
                    if get_supabase_config():
                        save_saved_ideas_supabase(idea)
                    break
                    
            if success and not get_supabase_config():
                save_saved_ideas(ideas)
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success}).encode("utf-8"))
            return

        elif self.path == "/api/publish-now":
            idea_id = req_data.get("idea_id", "").strip()
            
            if not idea_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "idea_id is required"}).encode("utf-8"))
                return
                
            ideas = load_saved_ideas()
            target_idea = None
            for idea in ideas:
                if idea["id"] == idea_id:
                    target_idea = idea
                    break
                    
            if not target_idea:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Idea not found"}).encode("utf-8"))
                return
                
            old_fb_id = target_idea.get("facebook_post_id")
            if old_fb_id:
                try:
                    delete_facebook_post(old_fb_id)
                except Exception as e:
                    print(f"Warning: Failed to delete scheduled post before publish-now: {e}")
                    
            success, post_id_or_err = publish_to_facebook(target_idea)
            if success:
                target_idea["status"] = "Used"
                target_idea["facebook_post_id"] = post_id_or_err
                target_idea["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if "post_error" in target_idea:
                    del target_idea["post_error"]
            else:
                target_idea["status"] = "Failed"
                target_idea["post_error"] = post_id_or_err
                
            if get_supabase_config():
                save_saved_ideas_supabase(target_idea)
            else:
                save_saved_ideas(ideas)
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "error": post_id_or_err if not success else None, "post_id": post_id_or_err if success else None}).encode("utf-8"))
            return
            
        elif self.path == "/api/save-idea":
            content = req_data.get("content", "").strip()
            if not content:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Content is required"}).encode("utf-8"))
                return
                
            idea_id = hashlib.md5(content.encode("utf-8")).hexdigest()[:10]
            new_idea = {
                "id": idea_id,
                "news_id": req_data.get("news_id", ""),
                "news_title": req_data.get("news_title", ""),
                "news_link": req_data.get("news_link", ""),
                "news_category": req_data.get("news_category", ""),
                "angle": req_data.get("angle", ""),
                "content": content,
                "image_prompt": req_data.get("image_prompt", ""),
                "status": "Waiting List",
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            success = False
            if get_supabase_config():
                success = save_saved_ideas_supabase(new_idea)
            else:
                ideas = load_saved_ideas()
                ideas = [i for i in ideas if i["id"] != idea_id]
                ideas.insert(0, new_idea)
                success = save_saved_ideas(ideas)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "idea_id": idea_id}).encode("utf-8"))
            return
            
        elif self.path == "/api/update-idea-status":
            idea_id = req_data.get("idea_id", "").strip()
            status = req_data.get("status", "").strip()
            
            success = False
            if get_supabase_config():
                success = update_saved_idea_status_supabase(idea_id, status)
            else:
                ideas = load_saved_ideas()
                for idea in ideas:
                    if idea["id"] == idea_id:
                        idea["status"] = status
                        success = True
                        break
                if success:
                    save_saved_ideas(ideas)
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success}).encode("utf-8"))
            return
            
        elif self.path == "/api/delete-idea":
            idea_id = req_data.get("idea_id", "").strip()
            
            success = False
            if get_supabase_config():
                success = delete_saved_idea_supabase(idea_id)
            else:
                ideas = load_saved_ideas()
                filtered_ideas = [i for i in ideas if i["id"] != idea_id]
                success = save_saved_ideas(filtered_ideas)
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": success}).encode("utf-8"))
            return
            
        elif self.path == "/api/fetch":
            # Run ai_news_fetcher.py script
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            
            try:
                # Running the scraper using python executable
                script_path = os.path.join(DIRECTORY, "ai_news_fetcher.py")
                cmd = [sys.executable, script_path, "--dry-run"]
                print(f"[*] Triggering fetch command: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
                
                # Reload news data
                news_path = os.path.join(DIRECTORY, "news_data.json")
                news_items = []
                if os.path.exists(news_path):
                    with open(news_path, "r", encoding="utf-8") as f:
                        news_items = json.load(f)
                
                self.wfile.write(json.dumps({
                    "success": True, 
                    "stdout": result.stdout,
                    "news": news_items
                }).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({
                    "success": False, 
                    "error": str(e)
                }).encode("utf-8"))
            return
            
        elif self.path == "/api/generate":
            title = req_data.get("title", "").strip()
            desc = req_data.get("desc", "").strip()
            link = req_data.get("link", "").strip()
            
            # If full article data is not sent, fallback to loading by article_id from news_data.json
            if not title:
                article_id = req_data.get("article_id", "").strip()
                if not article_id:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "article_id or full article data (title) is required"}).encode("utf-8"))
                    return
                    
                # Load article details from json
                news_path = os.path.join(DIRECTORY, "news_data.json")
                article = None
                if os.path.exists(news_path):
                    with open(news_path, "r", encoding="utf-8") as f:
                        news_data = json.load(f)
                        for item in news_data:
                            if item["id"] == article_id:
                                article = item
                                break
                                
                if not article:
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Article not found"}).encode("utf-8"))
                    return
                title = article.get("title", "")
                desc = article.get("desc", "") or article.get("desc_summary", "")
                link = article.get("link", "")
                
            config = load_config()
            api_key = config.get("GEMINI_API_KEY", "").strip()
            if not api_key:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Gemini API Key is not configured. Please set it in Settings."}).encode("utf-8"))
                return
                
            try:
                content_to_use = desc if desc else title
                generated_result = call_gemini_api(
                    api_key=api_key,
                    title=title,
                    desc=content_to_use,
                    link=link
                )
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(generated_result, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run(server_class=http.server.HTTPServer, handler_class=CustomHTTPRequestHandler):
    # Ensure web folder exists
    os.makedirs(WEB_DIR, exist_ok=True)
    
    # Configure stdout to handle UTF-8 safely on Windows
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
            
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    print(f"\n============================================================")
    print(f" [SUCCESS] AI News Automation Server Running on Port {PORT}")
    print(f" Access URL: http://localhost:{PORT}")
    print(f"============================================================\n")
    
    # Start background scheduler daemon thread
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping server...")
        httpd.server_close()
        print("[SUCCESS] Server stopped.")

if __name__ == "__main__":
    run()


