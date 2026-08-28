#!/usr/bin/env python3
"""Fetch YouTube transcript via terminal."""
import subprocess
import sys

def fetch_transcript(youtube_url):
    """Fetch transcript for a YouTube URL."""
    result = subprocess.run(
        ["python", "-m", "youtube_transcript_api", youtube_url],
        capture_output=True, text=True
    )
    return result.stdout

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fetch_transcript.py <youtube_url>")
        sys.exit(1)
    print(fetch_transcript(sys.argv[1]))
