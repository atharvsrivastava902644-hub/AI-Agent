"""
Database management for AI Startup Launch Assistant & All-in-One AI Platform.
Uses SQLite by default for zero-friction out-of-the-box operation with zero external daemon requirements.
Also supports PostgreSQL / MongoDB if configured via environment variables.
"""

import os
import sqlite3
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "startup_platform.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'Founder',
        tier TEXT DEFAULT 'pro',
        avatar_url TEXT DEFAULT '',
        theme_pref TEXT DEFAULT 'dark',
        response_style TEXT DEFAULT 'balanced',
        language_pref TEXT DEFAULT 'en',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Conversations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        title TEXT NOT NULL,
        is_archived INTEGER DEFAULT 0,
        system_prompt TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Messages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        sources TEXT DEFAULT '[]',
        tool_calls TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    )
    """)

    # Startup Blueprints / Projects Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS startup_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        author_email TEXT,
        startup_name TEXT NOT NULL,
        description TEXT NOT NULL,
        industry TEXT DEFAULT 'Technology',
        feasibility_score INTEGER DEFAULT 88,
        market_potential TEXT DEFAULT 'High',
        competition_risk TEXT DEFAULT 'Moderate',
        roadmap TEXT DEFAULT '',
        swot TEXT DEFAULT '{}',
        lean_canvas TEXT DEFAULT '{}',
        financials TEXT DEFAULT '{}',
        pitch_deck TEXT DEFAULT '{}',
        branding TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """)

    # Generated Images Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generated_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        prompt TEXT NOT NULL,
        enhanced_prompt TEXT DEFAULT '',
        style TEXT DEFAULT 'cinematic',
        aspect_ratio TEXT DEFAULT '1:1',
        dimensions TEXT DEFAULT '1024x1024',
        image_url TEXT NOT NULL,
        local_path TEXT DEFAULT '',
        provider TEXT DEFAULT 'Pollinations AI',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Social Posts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS social_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        platform TEXT NOT NULL,
        content TEXT NOT NULL,
        hashtags TEXT DEFAULT '',
        media_url TEXT DEFAULT '',
        status TEXT DEFAULT 'draft',
        scheduled_time TEXT DEFAULT '',
        engagement TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Social Accounts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS social_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        platform TEXT NOT NULL,
        account_name TEXT NOT NULL,
        account_handle TEXT DEFAULT '',
        is_connected INTEGER DEFAULT 0,
        connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        token_meta TEXT DEFAULT '{}',
        UNIQUE(user_id, platform),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # User Memories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT DEFAULT 'general',
        fact_text TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Uploaded Files Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uploaded_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        summary TEXT DEFAULT '',
        extracted_data TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Usage Tracking Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usage_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        metric_name TEXT NOT NULL,
        metric_value INTEGER DEFAULT 1,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

# Initialize tables immediately
init_db()

# --- User Operations ---

def create_user(name, email, password, role="Founder", tier="pro"):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role, tier) VALUES (?, ?, ?, ?, ?)",
            (name, email.strip().lower(), password_hash, role, tier)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def authenticate_user(email, password):
    user = get_user_by_email(email)
    if not user:
        return None
    if check_password_hash(user["password_hash"], password):
        return user
    return None

def update_user_preferences(user_id, theme_pref=None, response_style=None, language_pref=None, name=None):
    conn = get_connection()
    cursor = conn.cursor()
    updates = []
    params = []
    if theme_pref is not None:
        updates.append("theme_pref = ?")
        params.append(theme_pref)
    if response_style is not None:
        updates.append("response_style = ?")
        params.append(response_style)
    if language_pref is not None:
        updates.append("language_pref = ?")
        params.append(language_pref)
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if updates:
        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return get_user_by_id(user_id)

# --- Conversation & Message Operations ---

def create_conversation(conv_id, user_id, title="New Chat", system_prompt=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (id, user_id, title, system_prompt) VALUES (?, ?, ?, ?)",
        (conv_id, user_id, title, system_prompt)
    )
    conn.commit()
    conn.close()
    return get_conversation(conv_id)

def get_conversation(conv_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def list_user_conversations(user_id, include_archived=False, search=""):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM conversations WHERE user_id = ?"
    params = [user_id]
    if not include_archived:
        query += " AND is_archived = 0"
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")
    query += " ORDER BY updated_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_conversation(conv_id, title=None, is_archived=None):
    conn = get_connection()
    cursor = conn.cursor()
    updates = ["updated_at = CURRENT_TIMESTAMP"]
    params = []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if is_archived is not None:
        updates.append("is_archived = ?")
        params.append(1 if is_archived else 0)
    params.append(conv_id)
    cursor.execute(f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()

def delete_conversation(conv_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))
    conn.commit()
    conn.close()

def add_message(conv_id, role, content, sources=None, tool_calls=None):
    conn = get_connection()
    cursor = conn.cursor()
    sources_json = json.dumps(sources or [])
    tools_json = json.dumps(tool_calls or [])
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, sources, tool_calls) VALUES (?, ?, ?, ?, ?)",
        (conv_id, role, content, sources_json, tools_json)
    )
    cursor.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conv_id,))
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def get_conversation_messages(conv_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conv_id,))
    rows = cursor.fetchall()
    conn.close()
    messages = []
    for r in rows:
        d = dict(r)
        d["sources"] = json.loads(d["sources"] or "[]")
        d["tool_calls"] = json.loads(d["tool_calls"] or "[]")
        messages.append(d)
    return messages

# --- Startup Projects Operations ---

def save_startup_project(data, user_id=None, author_email=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO startup_projects 
        (user_id, author_email, startup_name, description, industry, feasibility_score, 
         market_potential, competition_risk, roadmap, swot, lean_canvas, financials, pitch_deck, branding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        author_email or "founder@venture.com",
        data.get("startup_name", "Untitled Venture"),
        data.get("description", ""),
        data.get("industry", "Technology"),
        data.get("feasibility_score", 88),
        data.get("market_potential", "High"),
        data.get("competition_risk", "Moderate"),
        data.get("roadmap", ""),
        json.dumps(data.get("swot", {})),
        json.dumps(data.get("lean_canvas", {})),
        json.dumps(data.get("financials", {})),
        json.dumps(data.get("pitch_deck", {})),
        json.dumps(data.get("branding", {}))
    ))
    conn.commit()
    project_id = cursor.lastrowid
    conn.close()
    return get_startup_project(project_id)

def get_startup_project(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM startup_projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for field in ["swot", "lean_canvas", "financials", "pitch_deck", "branding"]:
        d[field] = json.loads(d[field] or "{}")
    d["_id"] = str(d["id"])  # Backward compatibility with existing templates
    return d

def list_startup_projects(user_id=None, author_email=None):
    conn = get_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM startup_projects WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    elif author_email:
        cursor.execute("SELECT * FROM startup_projects WHERE author_email = ? ORDER BY created_at DESC", (author_email,))
    else:
        cursor.execute("SELECT * FROM startup_projects ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    projects = []
    for r in rows:
        d = dict(r)
        for field in ["swot", "lean_canvas", "financials", "pitch_deck", "branding"]:
            d[field] = json.loads(d[field] or "{}")
        d["_id"] = str(d["id"])
        projects.append(d)
    return projects

def delete_startup_project(project_id, user_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("DELETE FROM startup_projects WHERE id = ? AND user_id = ?", (project_id, user_id))
    else:
        cursor.execute("DELETE FROM startup_projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

# --- Generated Images Operations ---

def save_generated_image(user_id, prompt, image_url, enhanced_prompt="", style="cinematic", aspect_ratio="1:1", dimensions="1024x1024", provider="Pollinations AI", local_path=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO generated_images 
        (user_id, prompt, enhanced_prompt, style, aspect_ratio, dimensions, image_url, local_path, provider)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, prompt, enhanced_prompt, style, aspect_ratio, dimensions, image_url, local_path, provider))
    conn.commit()
    img_id = cursor.lastrowid
    conn.close()
    return img_id

def list_generated_images(user_id, limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM generated_images WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_generated_image(img_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM generated_images WHERE id = ? AND user_id = ?", (img_id, user_id))
    conn.commit()
    conn.close()

# --- Social Operations ---

def save_social_post(user_id, platform, content, hashtags="", media_url="", status="draft", scheduled_time=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO social_posts (user_id, platform, content, hashtags, media_url, status, scheduled_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, platform, content, hashtags, media_url, status, scheduled_time))
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id

def list_social_posts(user_id, platform=None, status=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM social_posts WHERE user_id = ?"
    params = [user_id]
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_social_post(post_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM social_posts WHERE id = ? AND user_id = ?", (post_id, user_id))
    conn.commit()
    conn.close()

def get_social_accounts(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM social_accounts WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def set_social_account_status(user_id, platform, account_name, account_handle, is_connected=1, token_meta=None):
    conn = get_connection()
    cursor = conn.cursor()
    token_json = json.dumps(token_meta or {})
    cursor.execute("""
        INSERT INTO social_accounts (user_id, platform, account_name, account_handle, is_connected, token_meta)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, platform) DO UPDATE SET 
            account_name=excluded.account_name,
            account_handle=excluded.account_handle,
            is_connected=excluded.is_connected,
            token_meta=excluded.token_meta,
            connected_at=CURRENT_TIMESTAMP
    """, (user_id, platform, account_name, account_handle, is_connected, token_json))
    conn.commit()
    conn.close()

# --- Memory Operations ---

def add_user_memory(user_id, fact_text, category="general"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_memories (user_id, fact_text, category) VALUES (?, ?, ?)", (user_id, fact_text, category))
    conn.commit()
    mem_id = cursor.lastrowid
    conn.close()
    return mem_id

def list_user_memories(user_id, active_only=True):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM user_memories WHERE user_id = ?"
    params = [user_id]
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_user_memory(mem_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_memories WHERE id = ? AND user_id = ?", (mem_id, user_id))
    conn.commit()
    conn.close()

def clear_user_memories(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- Uploaded Files Operations ---

def save_uploaded_file_record(user_id, filename, original_name, file_type, file_size, summary="", extracted_data=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO uploaded_files (user_id, filename, original_name, file_type, file_size, summary, extracted_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, filename, original_name, file_type, file_size, summary, extracted_data))
    conn.commit()
    file_id = cursor.lastrowid
    conn.close()
    return file_id

def list_uploaded_files(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, filename, original_name, file_type, file_size, summary, created_at FROM uploaded_files WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_uploaded_file(file_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM uploaded_files WHERE id = ? AND user_id = ?", (file_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# --- Usage Tracking Operations ---

def record_usage(user_id, metric_name, value=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usage_stats (user_id, metric_name, metric_value) VALUES (?, ?, ?)", (user_id, metric_name, value))
    conn.commit()
    conn.close()

def get_user_usage_summary(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT metric_name, SUM(metric_value) as total 
        FROM usage_stats 
        WHERE user_id = ? 
        GROUP BY metric_name
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    stats = {
        "chat_messages": 0,
        "web_searches": 0,
        "images_generated": 0,
        "files_analyzed": 0,
        "blueprints_created": 0
    }
    for r in rows:
        stats[r["metric_name"]] = r["total"]
    return stats
