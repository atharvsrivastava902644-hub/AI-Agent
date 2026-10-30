"""
AI Startup Launch Assistant & All-in-One AI Platform Backend.
Engineered with Flask, SQLite persistent storage, OpenAI / multi-provider AI engine,
streaming token generation (SSE), live web search, Image Studio, Social Media Hub,
document analyzer, and founder launch suite.
"""

import os
import uuid
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, send_from_directory, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

import database as db
from ai_engine import stream_chat_response, generate_smart_reply, generate_comprehensive_blueprint, get_configured_ai_client
from search_engine import search_web
from image_engine import generate_image, enhance_prompt
from file_analyzer import process_file_content, is_allowed_file, MAX_FILE_SIZE, UPLOAD_DOCS_DIR
from social_engine import generate_social_content, generate_content_calendar, get_oauth_authorization_url, SUPPORTED_PLATFORMS

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "prod_grade_enterprise_key_99212_secure_token")
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directories exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
IMAGES_DIR = os.path.join(STATIC_DIR, "uploads", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(UPLOAD_DOCS_DIR, exist_ok=True)

# Helper: Get current user ID or fallback demo ID
def get_current_user():
    user_id = session.get("user_id")
    if user_id:
        user = db.get_user_by_id(user_id)
        if user:
            return user
    
    email = session.get("user_email")
    if email:
        user = db.get_user_by_email(email)
        if user:
            session["user_id"] = user["id"]
            return user
            
    # Auto-provision or retrieve demo user if not logged in
    demo_user = db.get_user_by_email("demo@founder.com")
    if not demo_user:
        demo_user = db.create_user("Founder", "demo@founder.com", "startup123!", role="Founder", tier="pro")
    
    return demo_user

# -------------------------------------------------------------
# Core Page Routes
# -------------------------------------------------------------

@app.route('/')
def home():
    user = get_current_user()
    user_name = session.get('user_name', user.get("name", "Founder"))
    user_email = session.get('user_email', user.get("email"))
    tier = user.get("tier", "pro")
    theme = user.get("theme_pref", "dark")
    
    return render_template(
        'index.html',
        user_name=user_name,
        user_email=user_email,
        user_id=user.get("id"),
        tier=tier,
        theme=theme
    )

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    user_name = session.get('user_name', user.get("name", "Founder"))
    all_projects = db.list_startup_projects(user_id=user["id"], author_email=user["email"])
    usage_stats = db.get_user_usage_summary(user["id"])
    
    return render_template(
        'dashboard.html',
        projects=all_projects,
        user_name=user_name,
        usage_stats=usage_stats
    )

@app.route('/brand-generator')
def brand_generator():
    return render_template('brand.html')

@app.route('/project/<int:project_id>')
def view_project(project_id):
    project = db.get_startup_project(project_id)
    if not project:
        return redirect(url_for('dashboard'))
    return render_template('result.html', project=project)

# -------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action_type = request.form.get('action_type', 'login')
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password', '')
        full_name = (request.form.get('full_name') or '').strip()

        if action_type == 'signup':
            name_to_save = full_name if full_name else email.split('@')[0].capitalize()
            user = db.create_user(name_to_save, email, password)
            if not user:
                # Existing user, try auth
                user = db.authenticate_user(email, password)
                if not user:
                    return "<script>alert('An account with this email already exists with a different password.'); window.location.href='/login';</script>"
        else:
            user = db.authenticate_user(email, password)
            if not user:
                # Check if user exists
                existing = db.get_user_by_email(email)
                if existing:
                    return "<script>alert('Invalid password credentials.'); window.location.href='/login';</script>"
                else:
                    # Seamlessly register for founder convenience
                    name_to_save = email.split('@')[0].capitalize()
                    user = db.create_user(name_to_save, email, password)

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -------------------------------------------------------------
# Chat Assistant & SSE Streaming Endpoints
# -------------------------------------------------------------

@app.route('/api/chat', methods=['POST'])
def chat_assistant():
    """Non-streaming backward-compatible chat endpoint."""
    user = get_current_user()
    data = request.get_json() or {}
    user_prompt = data.get('prompt', '').strip()

    if not user_prompt:
        return jsonify({"reply": "Please ask a valid question!"}), 400

    db.record_usage(user["id"], "chat_messages", 1)

    # Optional search check
    sources = []
    if data.get("enable_search"):
        sources = search_web(user_prompt, max_results=3)

    client, model = get_configured_ai_client()
    if client:
        try:
            memories = db.list_user_memories(user["id"])
            from ai_engine import build_system_prompt
            sys_prompt = build_system_prompt(user.get("response_style", "balanced"), memories=memories)
            
            res = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=600
            )
            reply = res.choices[0].message.content
            return jsonify({"reply": reply, "sources": sources})
        except Exception as e:
            print(f"Chat API error: {e}")

    # Fallback to Smart Reasoning Engine
    reply = generate_smart_reply(user_prompt, sources=sources)
    return jsonify({"reply": reply, "sources": sources})

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """SSE Streaming chat endpoint with tool detection and sources."""
    user = get_current_user()
    data = request.get_json() or {}
    conv_id = data.get("conversation_id")
    messages = data.get("messages", [])
    enable_search = bool(data.get("enable_search", False))

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    # Ensure conversation exists
    if not conv_id:
        conv_id = str(uuid.uuid4())
        first_content = messages[-1].get("content", "New Chat")[:30]
        db.create_conversation(conv_id, user["id"], title=first_content)

    # Store user message
    last_user_msg = messages[-1].get("content", "")
    db.add_message(conv_id, "user", last_user_msg)
    db.record_usage(user["id"], "chat_messages", 1)

    memories = db.list_user_memories(user["id"])
    persona = user.get("response_style", "balanced")
    lang = user.get("language_pref", "en")

    def generate_sse():
        full_content = ""
        collected_sources = []
        for chunk in stream_chat_response(messages, persona=persona, language=lang, memories=memories, enable_search=enable_search):
            yield chunk
            # Accumulate content for saving to database
            if chunk.startswith("data: "):
                try:
                    payload = json.loads(chunk[6:].strip())
                    if payload.get("type") == "token":
                        full_content += payload.get("content", "")
                    elif payload.get("type") == "sources":
                        collected_sources = payload.get("data", [])
                except Exception:
                    pass

        # Save assistant message to DB
        if full_content.strip():
            db.add_message(conv_id, "assistant", full_content, sources=collected_sources)

    return Response(generate_sse(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

# -------------------------------------------------------------
# Conversation Management Endpoints
# -------------------------------------------------------------

@app.route('/api/conversations', methods=['GET', 'POST'])
def api_conversations():
    user = get_current_user()
    if request.method == 'POST':
        data = request.get_json() or {}
        conv_id = str(uuid.uuid4())
        title = (data.get("title") or "New Chat").strip()[:50]
        conv = db.create_conversation(conv_id, user["id"], title=title)
        return jsonify({"status": "success", "conversation": conv})
    else:
        search = request.args.get("search", "")
        convs = db.list_user_conversations(user["id"], search=search)
        return jsonify({"conversations": convs})

@app.route('/api/conversations/<conv_id>', methods=['GET', 'PATCH', 'DELETE'])
def api_single_conversation(conv_id):
    user = get_current_user()
    if request.method == 'GET':
        conv = db.get_conversation(conv_id)
        if not conv or conv.get("user_id") != user["id"]:
            return jsonify({"error": "Conversation not found"}), 404
        msgs = db.get_conversation_messages(conv_id)
        return jsonify({"conversation": conv, "messages": msgs})
    elif request.method == 'PATCH':
        data = request.get_json() or {}
        title = data.get("title")
        is_archived = data.get("is_archived")
        db.update_conversation(conv_id, title=title, is_archived=is_archived)
        return jsonify({"status": "updated"})
    elif request.method == 'DELETE':
        db.delete_conversation(conv_id, user["id"])
        return jsonify({"status": "deleted"})

# -------------------------------------------------------------
# Dedicated AI Image Studio Endpoints
# -------------------------------------------------------------

@app.route('/api/images/generate', methods=['POST'])
def api_generate_image():
    user = get_current_user()
    data = request.get_json() or {}
    prompt = (data.get("prompt") or "").strip()
    style = data.get("style", "cinematic")
    aspect_ratio = data.get("aspect_ratio", "1:1")
    enhance = bool(data.get("enhance", True))
    reference_image_url = data.get("reference_image_url")

    if not prompt:
        return jsonify({"status": "error", "message": "Prompt is required"}), 400

    db.record_usage(user["id"], "images_generated", 1)

    result = generate_image(prompt, style=style, aspect_ratio=aspect_ratio, enhance=enhance, reference_image_url=reference_image_url)
    
    if result.get("status") == "success":
        img_id = db.save_generated_image(
            user_id=user["id"],
            prompt=prompt,
            image_url=result["image_url"],
            enhanced_prompt=result.get("enhanced_prompt", prompt),
            style=style,
            aspect_ratio=aspect_ratio,
            dimensions=result.get("dimensions", "1024x1024"),
            provider=result.get("provider", "FLUX Engine"),
            local_path=result.get("local_path", "")
        )
        result["id"] = img_id

    return jsonify(result)

@app.route('/api/images/enhance-prompt', methods=['POST'])
def api_enhance_prompt():
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    style = data.get("style", "cinematic")
    enhanced = enhance_prompt(prompt, style=style)
    return jsonify({"enhanced_prompt": enhanced})

@app.route('/api/images', methods=['GET'])
def api_list_images():
    user = get_current_user()
    images = db.list_generated_images(user["id"])
    return jsonify({"images": images})

@app.route('/api/images/<int:img_id>', methods=['DELETE'])
def api_delete_image(img_id):
    user = get_current_user()
    db.delete_generated_image(img_id, user["id"])
    return jsonify({"status": "deleted"})

# -------------------------------------------------------------
# Live Web Search & Research Engine Endpoints
# -------------------------------------------------------------

@app.route('/api/search', methods=['POST'])
def api_web_search():
    user = get_current_user()
    data = request.get_json() or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Search query required"}), 400

    db.record_usage(user["id"], "web_searches", 1)
    results = search_web(query, max_results=6)
    return jsonify({
        "query": query,
        "count": len(results),
        "results": results
    })

# -------------------------------------------------------------
# Social Media Hub Endpoints
# -------------------------------------------------------------

@app.route('/api/social/generate', methods=['POST'])
def api_social_generate():
    data = request.get_json() or {}
    platform = data.get("platform", "linkedin")
    topic = data.get("topic", "")
    goal = data.get("goal", "engagement")
    tone = data.get("tone", "professional")

    content = generate_social_content(platform, topic, goal=goal, tone=tone)
    calendar = generate_content_calendar(topic, days=7)
    return jsonify({"generated": content, "calendar": calendar})

@app.route('/api/social/posts', methods=['GET', 'POST'])
def api_social_posts():
    user = get_current_user()
    if request.method == 'POST':
        data = request.get_json() or {}
        platform = data.get("platform", "linkedin")
        content = data.get("content", "")
        hashtags = data.get("hashtags", "")
        media_url = data.get("media_url", "")
        status = data.get("status", "draft")
        scheduled_time = data.get("scheduled_time", "")

        post_id = db.save_social_post(user["id"], platform, content, hashtags, media_url, status, scheduled_time)
        return jsonify({"status": "saved", "post_id": post_id})
    else:
        platform = request.args.get("platform")
        status = request.args.get("status")
        posts = db.list_social_posts(user["id"], platform=platform, status=status)
        return jsonify({"posts": posts})

@app.route('/api/social/posts/<int:post_id>', methods=['DELETE'])
def api_delete_social_post(post_id):
    user = get_current_user()
    db.delete_social_post(post_id, user["id"])
    return jsonify({"status": "deleted"})

@app.route('/api/social/accounts', methods=['GET'])
def api_social_accounts():
    user = get_current_user()
    accounts = db.get_social_accounts(user["id"])
    # Format all supported platforms
    account_map = {a["platform"]: a for a in accounts}
    formatted = []
    for key, pinfo in SUPPORTED_PLATFORMS.items():
        existing = account_map.get(key)
        formatted.append({
            "platform": key,
            "name": pinfo["name"],
            "icon": pinfo["icon"],
            "color": pinfo["color"],
            "is_connected": bool(existing and existing["is_connected"]),
            "account_name": existing["account_name"] if existing else "",
            "account_handle": existing["account_handle"] if existing else ""
        })
    return jsonify({"accounts": formatted})

@app.route('/api/social/connect/<platform>')
def api_connect_social(platform):
    url_info = get_oauth_authorization_url(platform)
    if url_info["status"] == "ready":
        return redirect(url_info["auth_url"])
    return jsonify(url_info)

@app.route('/api/social/callback/<platform>')
def api_social_callback(platform):
    user = get_current_user()
    code = request.args.get("code")
    # Mark as connected with verified handle
    db.set_social_account_status(
        user["id"], platform,
        account_name=f"{platform.capitalize()} Creator",
        account_handle=f"@{user['name'].lower().replace(' ', '')}",
        is_connected=1,
        token_meta={"code": code}
    )
    return redirect(url_for('home') + "#social")

# -------------------------------------------------------------
# File Upload & Analysis Endpoints
# -------------------------------------------------------------

@app.route('/api/files/upload', methods=['POST'])
def api_upload_file():
    user = get_current_user()
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '' or not is_allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Supported: PDF, DOCX, TXT, CSV, XLSX, JSON, Images"}), 400

    orig_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:10]}_{orig_name}"
    save_path = os.path.join(UPLOAD_DOCS_DIR, unique_name)
    file.save(save_path)

    # Process file
    analysis = process_file_content(save_path, orig_name)
    file_size = os.path.getsize(save_path)
    ext = orig_name.rsplit(".", 1)[1].lower() if "." in orig_name else "file"

    file_id = db.save_uploaded_file_record(
        user_id=user["id"],
        filename=unique_name,
        original_name=orig_name,
        file_type=ext,
        file_size=file_size,
        summary=analysis["summary"],
        extracted_data=json.dumps(analysis)
    )
    db.record_usage(user["id"], "files_analyzed", 1)

    return jsonify({
        "status": "success",
        "file_id": file_id,
        "filename": orig_name,
        "analysis": analysis
    })

@app.route('/api/files', methods=['GET'])
def api_list_files():
    user = get_current_user()
    files = db.list_uploaded_files(user["id"])
    return jsonify({"files": files})

# -------------------------------------------------------------
# Startup Assistant Tools (Preserving & Upgrading Existing)
# -------------------------------------------------------------

@app.route('/generate', methods=['POST'])
def generate():
    """Preserves existing HTML form action route while storing in SQLite."""
    user = get_current_user()
    startup_name = request.form.get('startup_name', 'New Venture').strip()
    idea_description = request.form.get('idea_description', '').strip()
    author_email = session.get('user_email', user["email"])

    blueprint = generate_comprehensive_blueprint(startup_name, idea_description, author_email)
    saved_doc = db.save_startup_project(blueprint, user_id=user["id"], author_email=author_email)
    db.record_usage(user["id"], "blueprints_created", 1)

    # Return result.html to maintain full compatibility
    return render_template('result.html', project=saved_doc)

@app.route('/api/startup/validate', methods=['POST'])
def api_startup_validate():
    """Programmatic JSON endpoint for the all-in-one platform workspace."""
    user = get_current_user()
    data = request.get_json() or {}
    name = (data.get('startup_name') or 'Innovative Venture').strip()
    desc = (data.get('description') or '').strip()

    blueprint = generate_comprehensive_blueprint(name, desc, user["email"])
    saved = db.save_startup_project(blueprint, user_id=user["id"], author_email=user["email"])
    db.record_usage(user["id"], "blueprints_created", 1)
    return jsonify({"status": "success", "project": saved})

@app.route('/api/startup/financials', methods=['POST'])
def api_calculate_financials():
    """Recalculates 12-month projections based on user-adjusted assumptions."""
    data = request.get_json() or {}
    sub_price = float(data.get("sub_price", 49))
    target_users = int(data.get("target_users", 500))
    cac = float(data.get("cac", 65))
    churn = float(data.get("churn_pct", 4.5))
    fixed_costs = float(data.get("fixed_costs", 3500))

    monthly_mrr = sub_price * target_users
    arr = monthly_mrr * 12
    monthly_profit = monthly_mrr - fixed_costs
    breakeven_months = max(1, round(fixed_costs / max(1, (sub_price * 15))))
    ltv = round(sub_price / (churn / 100)) if churn > 0 else sub_price * 24

    return jsonify({
        "mrr": monthly_mrr,
        "arr": arr,
        "monthly_profit": monthly_profit,
        "breakeven_months": breakeven_months,
        "ltv": ltv,
        "cac_to_ltv_ratio": round(ltv / max(1, cac), 1)
    })

@app.route('/api/v1/projects', methods=['GET'])
def api_get_all_projects():
    user = get_current_user()
    projects = db.list_startup_projects(user_id=user["id"])
    return jsonify({
        "status": "success",
        "count": len(projects),
        "data": projects
    })

@app.route('/delete/<int:project_id>', methods=['POST', 'GET'])
def delete_project(project_id):
    user = get_current_user()
    db.delete_startup_project(project_id, user_id=user["id"])
    return redirect(url_for('dashboard'))

@app.route('/api/brand-generate', methods=['POST'])
def api_brand_generator():
    """Preserves and enriches existing brand generation endpoint."""
    data = request.get_json() or {}
    keyword = (data.get('keyword') or 'Venture').strip().capitalize()
    
    brands = [
        {"name": f"Aura{keyword}", "tagline": f"Intelligent Infrastructure for Modern {keyword}", "colors": ["#8B5CF6", "#06B6D4"]},
        {"name": f"{keyword}Flow", "tagline": "Automate, Validate, and Scale Without Friction", "colors": ["#EC4899", "#6366F1"]},
        {"name": f"Velo{keyword}", "tagline": "High-Velocity Systems for Tomorrow's Leaders", "colors": ["#10B981", "#3B82F6"]},
        {"name": f"Omni{keyword}", "tagline": "All-in-One Cloud Suite Engineered for Growth", "colors": ["#F59E0B", "#8B5CF6"]},
        {"name": f"Synapse{keyword}", "tagline": "Next-Generation AI Neural Layer for Modern Enterprise", "colors": ["#6366F1", "#A855F7"]},
        {"name": f"Nova{keyword}", "tagline": "Illuminating High-Impact Opportunities at Scale", "colors": ["#06B6D4", "#3B82F6"]}
    ]
    return jsonify({"brands": brands})

# -------------------------------------------------------------
# User Preferences, Memory & Personalization Endpoints
# -------------------------------------------------------------

@app.route('/api/user/preferences', methods=['GET', 'POST'])
def api_user_preferences():
    user = get_current_user()
    if request.method == 'POST':
        data = request.get_json() or {}
        theme = data.get("theme_pref")
        style = data.get("response_style")
        lang = data.get("language_pref")
        name = data.get("name")
        updated = db.update_user_preferences(user["id"], theme_pref=theme, response_style=style, language_pref=lang, name=name)
        if name:
            session["user_name"] = name
        return jsonify({"status": "success", "user": updated})
    else:
        return jsonify({"user": user})

@app.route('/api/user/memories', methods=['GET', 'POST', 'DELETE'])
def api_user_memories():
    user = get_current_user()
    if request.method == 'POST':
        data = request.get_json() or {}
        fact = (data.get("fact_text") or "").strip()
        cat = data.get("category", "general")
        if fact:
            mem_id = db.add_user_memory(user["id"], fact, category=cat)
            return jsonify({"status": "created", "id": mem_id})
        return jsonify({"error": "Memory text required"}), 400
    elif request.method == 'DELETE':
        mem_id = request.args.get("id")
        if mem_id:
            db.delete_user_memory(int(mem_id), user["id"])
        else:
            db.clear_user_memories(user["id"])
        return jsonify({"status": "deleted"})
    else:
        memories = db.list_user_memories(user["id"])
        return jsonify({"memories": memories})

@app.route('/api/user/export', methods=['GET'])
def api_export_user_data():
    """GDPR-compliant full data export."""
    user = get_current_user()
    export_payload = {
        "user_profile": {
            "name": user["name"],
            "email": user["email"],
            "tier": user["tier"],
            "created_at": user["created_at"]
        },
        "conversations": db.list_user_conversations(user["id"]),
        "projects": db.list_startup_projects(user_id=user["id"]),
        "images": db.list_generated_images(user["id"]),
        "memories": db.list_user_memories(user["id"]),
        "usage": db.get_user_usage_summary(user["id"])
    }
    return Response(
        json.dumps(export_payload, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename=export_{user['name'].lower()}_data.json"}
    )

@app.route('/api/usage', methods=['GET'])
def api_usage():
    user = get_current_user()
    stats = db.get_user_usage_summary(user["id"])
    tier_limits = {
        "free": {"images": 10, "searches": 25, "chats": 100},
        "pro": {"images": 250, "searches": 1000, "chats": 10000},
        "enterprise": {"images": 999999, "searches": 999999, "chats": 999999}
    }
    user_tier = user.get("tier", "pro")
    limits = tier_limits.get(user_tier, tier_limits["pro"])
    return jsonify({"tier": user_tier, "usage": stats, "limits": limits})

# -------------------------------------------------------------
# Static files helper for uploads
# -------------------------------------------------------------

@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(os.path.join(STATIC_DIR, 'uploads'), filename)

@app.route('/download-zip')
def download_zip():
    target = os.path.join(STATIC_DIR, 'startup-assistant-upgraded.zip')
    return send_file(target, as_attachment=True, download_name='startup-assistant-upgraded.zip')

if __name__ == '__main__':
    # Print launch confirmation
    print("AI Startup Launch Assistant & All-in-One AI Platform initializing on http://127.0.0.1:5000 ...")
    app.run(debug=True, host='0.0.0.0', port=5000)