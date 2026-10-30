"""
Social Media Hub Engine.
Generates platform-tailored copy, hashtags, calendars, YouTube SEO, and handles OAuth connection flows.
Supports Instagram, Facebook, YouTube, LinkedIn, X, and Pinterest with draft review and schedule management.
"""

import os
import json
import urllib.parse
from datetime import datetime, timedelta

SUPPORTED_PLATFORMS = {
    "instagram": {"name": "Instagram", "icon": "fa-brands fa-instagram", "color": "#E1306C"},
    "facebook": {"name": "Facebook", "icon": "fa-brands fa-facebook", "color": "#1877F2"},
    "youtube": {"name": "YouTube", "icon": "fa-brands fa-youtube", "color": "#FF0000"},
    "linkedin": {"name": "LinkedIn", "icon": "fa-brands fa-linkedin", "color": "#0A66C2"},
    "x": {"name": "X (Twitter)", "icon": "fa-brands fa-x-twitter", "color": "#000000"},
    "pinterest": {"name": "Pinterest", "icon": "fa-brands fa-pinterest", "color": "#BD081C"}
}

def generate_social_content(platform, topic, goal="engagement", tone="professional"):
    """
    Generates high-performing, platform-specific content tailored to the medium's best practices.
    """
    topic_clean = (topic or "").strip()
    if not topic_clean:
        topic_clean = "Announcing our new AI startup platform"

    if platform == "linkedin":
        return _generate_linkedin(topic_clean, tone)
    elif platform == "x":
        return _generate_x_thread(topic_clean, tone)
    elif platform == "youtube":
        return _generate_youtube_seo(topic_clean)
    elif platform == "instagram":
        return _generate_instagram(topic_clean, tone)
    elif platform == "facebook":
        return _generate_facebook(topic_clean, tone)
    elif platform == "pinterest":
        return _generate_pinterest(topic_clean)
    else:
        return _generate_instagram(topic_clean, tone)

def _generate_linkedin(topic, tone):
    hook = f"Most founders struggle with {topic}. Here is what changed everything for us:"
    body = (
        f"{hook}\n\n"
        f"Over the last quarter, we studied how the top 1% of operators approach {topic}.\n\n"
        "Here are 3 critical lessons we documented:\n\n"
        f"1. Velocity beats perfection: Iterate on your {topic} strategy daily, not quarterly.\n"
        "2. Leverage intelligence: Let automated AI workflows handle the repetitive operational overhead.\n"
        "3. Focus on distribution: Having a great product without a pipeline is a fatal bottleneck.\n\n"
        "What is your #1 challenge when executing this in your organization? Drop your thoughts below 👇"
    )
    hashtags = "#Startup #Leadership #Innovation #Productivity #AI #Entrepreneurship"
    return {
        "platform": "linkedin",
        "content": body,
        "hashtags": hashtags,
        "media_suggestion": "Single-image infographic or 5-slide PDF carousel with clear contrast typography",
        "best_posting_time": "Tuesday & Thursday at 8:30 AM EST"
    }

def _generate_x_thread(topic, tone):
    body = (
        f"How to master {topic} in 2026 (without wasting 6 months of trial and error):\n\n"
        "A 4-part breakdown 🧵👇\n\n"
        f"1/ The foundation: Start with clear problem validation. If users aren't desperate for a solution, pivot fast.\n\n"
        f"2/ The engine: Deploy modern AI tools to compress weeks of work into hours.\n\n"
        f"3/ The feedback loop: Talk to 5 customers every week. No vanity metrics.\n\n"
        "4/ If you found this valuable:\n"
        "• Retweet the first tweet\n"
        "• Follow for weekly deep dives into high-velocity startup execution."
    )
    hashtags = "#Tech #Startups #BuildInPublic #AI"
    return {
        "platform": "x",
        "content": body,
        "hashtags": hashtags,
        "media_suggestion": "Clean 16:9 chart or punchy quote visual",
        "best_posting_time": "Weekdays at 12:00 PM and 5:00 PM EST"
    }

def _generate_youtube_seo(topic):
    title = f"The Ultimate Guide to {topic} (Step-by-Step Blueprint)"
    alt_titles = [
        f"How I Mastered {topic} in 30 Days",
        f"Stop Doing {topic} The Wrong Way in 2026",
        f"{topic}: Everything You Need to Know (Full Masterclass)"
    ]
    description = (
        f"In this video, we break down the exact framework for {topic} step-by-step.\n\n"
        "⏱️ TIMESTAMPS:\n"
        "0:00 - Introduction & The Big Problem\n"
        "2:15 - Core Framework Breakdown\n"
        "6:30 - Real-World Case Study\n"
        "10:45 - The 3 Mistakes to Avoid\n"
        "14:20 - Next Action Steps\n\n"
        "🔔 Don't forget to Subscribe and hit the notification bell for more high-impact startup growth tutorials!"
    )
    tags = f"{topic}, startup guide, growth strategy, ai automation, tech entrepreneurship, business tutorial"
    thumbnail_concept = "Split-screen high contrast visual: Left side frustrated face with red 'Before', right side high-tech glowing dashboard with green 'After', bold 3-word headline."
    return {
        "platform": "youtube",
        "title": title,
        "alt_titles": alt_titles,
        "content": description,
        "hashtags": tags,
        "media_suggestion": thumbnail_concept,
        "best_posting_time": "Friday at 3:00 PM EST or Saturday at 10:00 AM EST"
    }

def _generate_instagram(topic, tone):
    caption = (
        f"Save this for your next project 📌✨\n\n"
        f"Everything you need to know about {topic} summarized in 3 key steps:\n\n"
        f"⚡ 01. Validate early before spending a single dollar.\n"
        f"⚡ 02. Automate repetitive tasks using modern AI.\n"
        f"⚡ 03. Focus relentlessly on customer retention.\n\n"
        "Double tap if this resonates with your goals! ❤️\n"
        "Comment 'STARTUP' below and we'll send you our launch checklist."
    )
    hashtags = "#StartupLife #EntrepreneurMindset #ProductivityHacks #TechCommunity #Innovation #DesignInspiration"
    return {
        "platform": "instagram",
        "content": caption,
        "hashtags": hashtags,
        "media_suggestion": "1080x1350 (4:5) carousel post with gradient accents and punchy headlines",
        "best_posting_time": "Wednesday at 11:00 AM and 7:00 PM EST"
    }

def _generate_facebook(topic, tone):
    content = (
        f"📢 Exciting update: We're tackling {topic} head-on!\n\n"
        "Whether you're starting from scratch or scaling an existing team, here is what we discovered works best:\n\n"
        f"• Clear milestones beat vague aspirations.\n"
        f"• Continuous feedback prevents expensive mistakes.\n\n"
        "Have you encountered this challenge recently? Let's discuss in the comments below!"
    )
    return {
        "platform": "facebook",
        "content": content,
        "hashtags": "#Business #Tech #Community #Growth",
        "media_suggestion": "Landscape 1200x630 banner with logo watermark",
        "best_posting_time": "Monday through Wednesday at 1:00 PM EST"
    }

def _generate_pinterest(topic):
    title = f"{topic} Strategy Checklist for Founders"
    desc = f"Discover actionable strategies and tools for {topic}. Pin this to your business board for quick reference later."
    return {
        "platform": "pinterest",
        "title": title,
        "content": desc,
        "hashtags": "#BusinessTips #StartupStrategy #Productivity #Infographic",
        "media_suggestion": "Vertical 1000x1500 pin with clean infographic layout",
        "best_posting_time": "Saturday evening between 8:00 PM and 11:00 PM EST"
    }

def generate_content_calendar(topic, days=7):
    """Generates a structured weekly campaign schedule."""
    calendar = []
    today = datetime.now()
    themes = [
        ("Monday", "Vision & High-Level Philosophy", "linkedin", "Thought Leadership Post"),
        ("Tuesday", "Behind The Scenes / Building in Public", "x", "Twitter / X Thread"),
        ("Wednesday", "Tutorial & Practical Framework", "instagram", "Carousel Infographic"),
        ("Thursday", "Deep Dive Video / Masterclass", "youtube", "Comprehensive Guide"),
        ("Friday", "Weekly Wins & Community Shoutouts", "facebook", "Community Update"),
        ("Saturday", "Resource Roundup / Pin of the Week", "pinterest", "Infographic Pin"),
        ("Sunday", "Weekly Review & Monday Kickoff", "x", "Reflective Tweet")
    ]
    for i in range(min(days, len(themes))):
        day_date = today + timedelta(days=i)
        day_name, theme, platform, format_type = themes[i]
        calendar.append({
            "day": day_name,
            "date": day_date.strftime("%b %d, %Y"),
            "theme": theme,
            "platform": platform,
            "format": format_type,
            "suggested_topic": f"{topic} - {theme}"
        })
    return calendar

def get_oauth_authorization_url(platform, client_id=None, redirect_uri=None):
    """
    Generates official OAuth 2.0 authorization URL for supported platforms.
    If developer app credentials are configured in environment variables, directs to official OAuth dialog;
    otherwise provides a clear configuration notice.
    """
    redirect_uri = redirect_uri or "http://localhost:5000/api/social/callback/" + platform
    
    oauth_endpoints = {
        "linkedin": "https://www.linkedin.com/oauth/v2/authorization",
        "facebook": "https://www.facebook.com/v18.0/dialog/oauth",
        "instagram": "https://api.instagram.com/oauth/authorize",
        "x": "https://twitter.com/i/oauth2/authorize",
        "youtube": "https://accounts.google.com/o/oauth2/v2/auth",
        "pinterest": "https://www.pinterest.com/oauth/"
    }

    env_key = f"{platform.upper()}_CLIENT_ID"
    cid = client_id or os.getenv(env_key)
    
    if not cid or cid.startswith("your_"):
        return {
            "status": "config_required",
            "message": f"To connect your official {SUPPORTED_PLATFORMS.get(platform, {}).get('name', platform)} account, configure {env_key} in your .env file with your developer app credentials.",
            "auth_url": None
        }

    scopes = {
        "linkedin": "openid profile email w_member_social",
        "facebook": "public_profile,pages_show_list,pages_read_engagement,pages_manage_posts",
        "instagram": "instagram_basic,instagram_content_publish",
        "x": "tweet.read tweet.write users.read offline.access",
        "youtube": "https://www.googleapis.com/auth/youtube.upload",
        "pinterest": "boards:read,pins:read,pins:write"
    }

    params = {
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "scope": scopes.get(platform, "read"),
        "state": f"social_auth_{platform}"
    }

    url = f"{oauth_endpoints.get(platform)}?{urllib.parse.urlencode(params)}"
    return {
        "status": "ready",
        "auth_url": url
    }
