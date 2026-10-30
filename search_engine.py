"""
Live Web Search & Research Engine.
Multi-source live research architecture:
1. Tavily API (if configured)
2. Google Custom Search API (if configured)
3. Hacker News Algolia Live Tech & Business Search API (Live startup news, tech benchmarks, external publisher links)
4. Wikipedia Live Knowledge Search API (Factual claims, definitions, domain overviews)
5. DuckDuckGo Instant Answer API
"""

import os
import re
import urllib.parse
import requests

def search_web(query, max_results=5):
    """
    Executes live web search using available multi-source providers.
    Returns real, factual links with titles, domains, and snippets.
    """
    query = (query or "").strip()
    if not query:
        return []

    # 1. Tavily API if configured
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key and not tavily_key.startswith("your_"):
        results = search_tavily(query, tavily_key, max_results)
        if results:
            return results

    # 2. Google Custom Search if configured
    google_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    google_cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if google_key and google_cx and not google_key.startswith("your_"):
        results = search_google(query, google_key, google_cx, max_results)
        if results:
            return results

    # 3. Live Real-Time Multi-Source Web Search
    results = []
    
    # 3a. Hacker News Algolia Live Search (Real-time tech, venture news, actual publisher URLs)
    try:
        hn_url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(query)}&hitsPerPage={max_results}"
        r_hn = requests.get(hn_url, timeout=5)
        if r_hn.status_code == 200:
            hits = r_hn.json().get("hits", [])
            for h in hits:
                title = h.get("title") or h.get("story_title")
                url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
                if title and url:
                    domain = urllib.parse.urlparse(url).netloc or "news.ycombinator.com"
                    snippet = h.get("comment_text") or h.get("story_text") or f"Live tech and venture reference: {title}"
                    clean_snippet = re.sub(r'<[^>]+>', '', snippet)[:220].strip()
                    results.append({
                        "title": title[:90],
                        "url": url,
                        "snippet": clean_snippet,
                        "domain": domain,
                        "source": "Live Tech & Business Web"
                    })
    except Exception as e:
        print(f"HN search error: {e}")

    # 3b. Wikipedia Live Knowledge API (Factual knowledge, encyclopedic background)
    if len(results) < max_results:
        try:
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&utf8="
            headers = {"User-Agent": "StartupAssistant/2.0 (research@venture.com)"}
            r_wiki = requests.get(wiki_url, headers=headers, timeout=5)
            if r_wiki.status_code == 200:
                wiki_results = r_wiki.json().get("query", {}).get("search", [])
                for item in wiki_results[:max_results - len(results)]:
                    w_title = item.get("title")
                    w_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(w_title)}"
                    snippet_html = item.get("snippet", "")
                    clean_snip = re.sub(r'<[^>]+>', '', snippet_html).strip()
                    results.append({
                        "title": w_title,
                        "url": w_url,
                        "snippet": clean_snip or f"Authoritative reference for {w_title}",
                        "domain": "en.wikipedia.org",
                        "source": "Wikipedia Knowledge Base"
                    })
        except Exception as e:
            print(f"Wiki search error: {e}")

    return results[:max_results]

def search_tavily(query, api_key, max_results=5):
    """Executes live web search via Tavily API."""
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"query": query, "search_depth": "basic", "max_results": max_results},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "domain": urllib.parse.urlparse(item.get("url", "")).netloc,
                    "source": "Tavily Search"
                })
            return results
    except Exception as e:
        print(f"Tavily search error: {e}")
    return []

def search_google(query, api_key, cx, max_results=5):
    """Executes search via Google Custom Search JSON API."""
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={urllib.parse.quote(query)}&num={max_results}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "domain": urllib.parse.urlparse(item.get("link", "")).netloc,
                    "source": "Google Custom Search"
                })
            return results
    except Exception as e:
        print(f"Google search error: {e}")
    return []

def format_search_context(results):
    """Formats retrieved web results into clear context for AI prompting."""
    if not results:
        return ""
    formatted = "### LIVE WEB SEARCH RESULTS:\n"
    for idx, r in enumerate(results, 1):
        formatted += f"[{idx}] {r['title']}\n"
        formatted += f"    Source: {r['domain']} | URL: {r['url']}\n"
        formatted += f"    Snippet: {r['snippet']}\n\n"
    return formatted
