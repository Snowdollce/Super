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
import subprocess
import sys
import re
import hashlib
from datetime import datetime

PORT = 5000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(DIRECTORY, "web")
SAVED_IDEAS_FILE = os.path.join(DIRECTORY, "saved_ideas.json")

def load_saved_ideas():
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
    """Loads environment variables from config.env."""
    config = {}
    env_path = os.path.join(DIRECTORY, "config.env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
    return config

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
    1. Tone & Persona: Female narrator/storyteller (ผู้หญิงเล่าเรื่อง). Speak in a friendly "friend telling news" style (เพื่อนบอกข่าว) - conversational, engaging, friendly, easy to understand, yet professional and credible. Use polite female sentence-ending particles: "ค่ะ" (kha) and "นะคะ" (na-kha) instead of masculine ones like "ครับ" (krub). Never use "ครับ" in the posts.
    2. Hook: Must have a strong, eye-catching hook in the very first line (Hook ตั้งแต่บรรทัดแรก) to grab readers' attention immediately.
    3. Structure: Use emojis appropriately, format with clear paragraph breaks, and include relevant hashtags (e.g., #AI #Technology #ความรู้AI).
    4. Content: Explain the core essence of the news and why the reader should care, keeping it concise but informative.
    5. Offer 3-5 different angles/styles (e.g., Angle 1: Mind-blowing/Exciting, Angle 2: Practical/Business impact, Angle 3: Question/Discussion starter, Angle 4: Fun/Informative).
    
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
    with urllib.request.urlopen(req, timeout=30) as res:
        response_body = res.read().decode("utf-8")
        res_json = json.loads(response_body)
        text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
        return json.loads(text)

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
                "recipient_email": recipient
            }).encode("utf-8"))
            return
            
        elif self.path == "/api/saved-ideas":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            ideas = load_saved_ideas()
            self.wfile.write(json.dumps(ideas, ensure_ascii=False).encode("utf-8"))
            return

        # Serve static HTML/JS/CSS from 'web' directory
        parsed_path = urllib.parse.urlparse(self.path)
        rel_path = parsed_path.path.lstrip("/")
        
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
            
        elif self.path == "/api/save-idea":
            content = req_data.get("content", "").strip()
            if not content:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Content is required"}).encode("utf-8"))
                return
                
            ideas = load_saved_ideas()
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
            
            ideas = [i for i in ideas if i["id"] != idea_id]
            ideas.insert(0, new_idea)
            save_saved_ideas(ideas)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "idea_id": idea_id}).encode("utf-8"))
            return
            
        elif self.path == "/api/update-idea-status":
            idea_id = req_data.get("idea_id", "").strip()
            status = req_data.get("status", "").strip()
            
            ideas = load_saved_ideas()
            updated = False
            for idea in ideas:
                if idea["id"] == idea_id:
                    idea["status"] = status
                    updated = True
                    break
                    
            if updated:
                save_saved_ideas(ideas)
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": updated}).encode("utf-8"))
            return
            
        elif self.path == "/api/delete-idea":
            idea_id = req_data.get("idea_id", "").strip()
            ideas = load_saved_ideas()
            filtered_ideas = [i for i in ideas if i["id"] != idea_id]
            save_saved_ideas(filtered_ideas)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
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
            article_id = req_data.get("article_id", "").strip()
            if not article_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "article_id is required"}).encode("utf-8"))
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
                
            config = load_config()
            api_key = config.get("GEMINI_API_KEY", "").strip()
            if not api_key:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Gemini API Key is not configured. Please set it in Settings."}).encode("utf-8"))
                return
                
            try:
                # Use description or summary
                content_to_use = article.get("desc", "") or article.get("desc_summary", "")
                if not content_to_use:
                    content_to_use = article.get("title", "")
                    
                generated_result = call_gemini_api(
                    api_key=api_key,
                    title=article["title"],
                    desc=content_to_use,
                    link=article["link"]
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
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping server...")
        httpd.server_close()
        print("[SUCCESS] Server stopped.")

if __name__ == "__main__":
    run()


