"""
BigQuery Release Notes Hub & Tweet Composer
===========================================
Backend server powering the BigQuery release feed parser, tweet composer, 
and analytics dashboard.

Built during Google x Kaggle AI Course.
"""

from flask import Flask, render_template, jsonify, request
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import time
from datetime import datetime
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data')
cache_file_path = os.path.join(data_dir, 'feed_cache.json')

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, 'templates'),
    static_folder=os.path.join(base_dir, 'static')
)

FEED_URL = os.environ.get("FEED_URL", "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml")
CACHE_TTL = int(os.environ.get("CACHE_TTL", 300))  # 5 minutes in seconds

# In-memory cache for feed data
FEED_CACHE = {
    'data': None,
    'last_updated': 0
}


def get_http_session():
    """Returns a requests Session equipped with retry logic and connection pooling."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def save_disk_cache(data, timestamp):
    """Persists feed cache to disk for offline resilience and cold-start fallback."""
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(cache_file_path, 'w', encoding='utf-8') as f:
            json.dump({'last_updated': timestamp, 'data': data}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Could not persist disk cache: {e}")


def load_disk_cache():
    """Loads fallback cache from disk if available."""
    if os.path.exists(cache_file_path):
        try:
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
                return payload.get('data'), payload.get('last_updated', 0)
        except Exception as e:
            logging.warning(f"Could not read disk cache: {e}")
    return None, 0


def fetch_and_parse_feed():
    """Fetches Google BigQuery Atom feed and decomposes daily dumps into distinct update items."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (BigQueryReleaseNotesHub/1.0; +https://github.com/RJ1899157)'
    }
    
    session = get_http_session()
    response = session.get(FEED_URL, headers=headers, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entries = root.findall('atom:entry', ns)

    updates = []

    for entry in entries:
        title_el = entry.find('atom:title', ns)
        date_str = title_el.text.strip() if title_el is not None and title_el.text else "Recent"
        
        id_el = entry.find('atom:id', ns)
        entry_id = id_el.text.strip() if id_el is not None and id_el.text else str(time.time())
        
        content_element = entry.find('atom:content', ns)
        if content_element is None or not content_element.text:
            continue

        html_content = content_element.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Sanitize links: ensure external targets and fix relative Google paths
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if href.startswith('/'):
                a['href'] = f"https://cloud.google.com{href}"
            a['target'] = '_blank'
            a['rel'] = 'noopener noreferrer'

        # Split by h3 headers (standard Google Cloud release note format)
        headers_tags = soup.find_all('h3')

        if not headers_tags:
            updates.append({
                'id': entry_id,
                'date': date_str,
                'type': 'Update',
                'html': str(soup),
                'text': ' '.join(soup.get_text().split())
            })
            continue

        for i, header in enumerate(headers_tags):
            update_type = header.get_text().strip()
            sibling_html = []
            sibling_text = []
            sibling = header.next_sibling

            while sibling and sibling.name != 'h3':
                if sibling.name:
                    # Sanitize any nested links in siblings
                    for a in sibling.find_all('a'):
                        href = a.get('href', '')
                        if href.startswith('/'):
                            a['href'] = f"https://cloud.google.com{href}"
                        a['target'] = '_blank'
                        a['rel'] = 'noopener noreferrer'
                    sibling_html.append(str(sibling))
                    sibling_text.append(sibling.get_text())
                sibling = sibling.next_sibling

            html_snippet = "".join(sibling_html)
            text_snippet = ' '.join(" ".join(sibling_text).split())
            sub_id = f"{entry_id}#{i}"

            updates.append({
                'id': sub_id,
                'date': date_str,
                'type': update_type,
                'html': html_snippet,
                'text': text_snippet
            })

    return updates


def get_updates(force_refresh=False):
    """Retrieves updates using in-memory caching, network fetch, and disk-cache fallback."""
    now = time.time()
    
    # 1. Return in-memory cache if valid and refresh not forced
    if not force_refresh and FEED_CACHE['data'] and (now - FEED_CACHE['last_updated'] < CACHE_TTL):
        return FEED_CACHE['data'], FEED_CACHE['last_updated']

    # 2. Attempt live network fetch
    try:
        data = fetch_and_parse_feed()
        FEED_CACHE['data'] = data
        FEED_CACHE['last_updated'] = now
        save_disk_cache(data, now)
        return data, now
    except Exception as network_err:
        logging.error(f"Live feed fetch failed: {network_err}")
        # 3. Fallback to existing memory cache
        if FEED_CACHE['data']:
            logging.info("Serving stale in-memory cache.")
            return FEED_CACHE['data'], FEED_CACHE['last_updated']
        # 4. Fallback to disk cache
        disk_data, disk_time = load_disk_cache()
        if disk_data:
            logging.info("Serving persistent disk cache fallback.")
            FEED_CACHE['data'] = disk_data
            FEED_CACHE['last_updated'] = disk_time
            return disk_data, disk_time
        # Re-raise if no cache exists at all
        raise network_err


@app.route('/')
def index():
    """Serves the main release notes dashboard."""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint for container probes and uptime monitors."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'cache_entries': len(FEED_CACHE['data']) if FEED_CACHE['data'] else 0
    })


@app.route('/api/releases')
def releases():
    """API endpoint providing structured release notes with optional server-side filtering."""
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    category_filter = request.args.get('category', '').lower().strip()
    search_query = request.args.get('q', '').lower().strip()

    try:
        data, last_updated = get_updates(force_refresh=force_refresh)

        # Apply optional server-side filters if query params are present
        filtered_data = data
        if category_filter and category_filter != 'all':
            filtered_data = [
                u for u in filtered_data 
                if category_filter in u['type'].lower()
            ]
        if search_query:
            filtered_data = [
                u for u in filtered_data
                if search_query in u['text'].lower() 
                or search_query in u['date'].lower() 
                or search_query in u['type'].lower()
            ]

        dt = datetime.fromtimestamp(last_updated)
        formatted_time = dt.strftime('%Y-%m-%d %I:%M:%S %p')

        return jsonify({
            'success': True,
            'total_count': len(data),
            'filtered_count': len(filtered_data),
            'updates': filtered_data,
            'last_updated': formatted_time
        })
    except Exception as e:
        logging.error(f"Error serving releases API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    app.run(host=host, port=port, debug=debug)
