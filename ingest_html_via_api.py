"""
Ingest HTML articles using the app's database connection.
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import hashlib
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

# Import app's database
from app.database import get_supabase_client


def extract_article_data(html_content: str, filename: str) -> dict:
    """Extract article data from Stratechery webpage HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract title from <title> tag or filename
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text()
        # Clean up title - remove " – Stratechery by Ben Thompson"
        title = re.sub(r'\s*[–-]\s*Stratechery by Ben Thompson\s*$', '', title)
        title = title.strip()
    else:
        # Fall back to filename
        title = filename.replace('.html', '').replace(' – Stratechery by Ben Thompson', '')

    # Extract publication date from first <time datetime="...">
    time_tag = soup.find('time', datetime=True)
    pub_date = None
    if time_tag:
        datetime_str = time_tag.get('datetime')
        try:
            # Parse ISO format datetime
            pub_date = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass

    # Extract canonical URL
    canonical = soup.find('link', rel='canonical')
    canonical_url = canonical.get('href') if canonical else ''

    # Extract main content from entry-content div
    content_div = soup.find('div', class_=re.compile(r'entry-content'))

    if content_div:
        # Remove unwanted elements
        for unwanted in content_div.find_all(['script', 'style', 'nav', 'aside']):
            unwanted.decompose()

        # Remove "Related Articles" section
        for related in content_div.find_all(class_=re.compile(r'related|jp-relatedposts')):
            related.decompose()

        # Get text
        clean_text = content_div.get_text(separator='\n', strip=True)
    else:
        # Fallback: try article tag
        article = soup.find('article')
        if article:
            clean_text = article.get_text(separator='\n', strip=True)
        else:
            clean_text = soup.get_text(separator='\n', strip=True)

    # Clean up text
    # Remove excessive newlines
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    # Remove common footer patterns
    clean_text = re.sub(r'(?i)share this:.*$', '', clean_text, flags=re.DOTALL)
    clean_text = clean_text.strip()

    # Generate content hash
    content_hash = hashlib.sha256(clean_text.encode('utf-8')).hexdigest()

    return {
        'title': title,
        'publication_date': pub_date.isoformat() if pub_date else None,
        'cleaned_text': clean_text,
        'raw_html': html_content,
        'canonical_url': canonical_url,
        'word_count': len(clean_text.split()),
        'content_hash': content_hash,
    }


def ingest_html_files(directory: str):
    """Ingest all HTML files from a directory."""
    supabase = get_supabase_client()
    directory = Path(directory)

    html_files = sorted(directory.glob('*.html'))
    print(f"Found {len(html_files)} HTML files in {directory}")
    print("-" * 60)

    successful = 0
    skipped = 0
    failed = 0

    for i, file_path in enumerate(html_files, 1):
        print(f"\n[{i}/{len(html_files)}] {file_path.name[:60]}...")

        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Extract data
            data = extract_article_data(html_content, file_path.name)
            print(f"  Title: {data['title'][:50]}...")
            print(f"  Date: {data['publication_date']}")
            print(f"  Words: {data['word_count']}")

            # Check for duplicates by content hash
            existing = supabase.table("stratechery_issues")\
                .select("issue_id")\
                .eq("content_hash", data['content_hash'])\
                .limit(1)\
                .execute()

            if existing.data:
                print(f"  - Skipped: Duplicate content hash")
                skipped += 1
                continue

            # Check for duplicate title
            existing_title = supabase.table("stratechery_issues")\
                .select("issue_id")\
                .eq("title", data['title'])\
                .limit(1)\
                .execute()

            if existing_title.data:
                print(f"  - Skipped: Title already exists")
                skipped += 1
                continue

            # Insert into database
            response = supabase.table("stratechery_issues").insert({
                'title': data['title'],
                'publication_date': data['publication_date'],
                'cleaned_text': data['cleaned_text'],
                'raw_html': data['raw_html'],
                'canonical_url': data['canonical_url'],
                'word_count': data['word_count'],
                'content_hash': data['content_hash'],
            }).execute()

            if response.data:
                print(f"  ✓ Ingested! issue_id: {response.data[0].get('issue_id')}")
                successful += 1
            else:
                print(f"  ✗ Failed: No data returned")
                failed += 1

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total:      {len(html_files)}")
    print(f"Successful: {successful}")
    print(f"Skipped:    {skipped}")
    print(f"Failed:     {failed}")

    return successful


if __name__ == '__main__':
    directory = sys.argv[1] if len(sys.argv) > 1 else 'new_articles'
    ingest_html_files(directory)
