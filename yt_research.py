#!/usr/bin/env python3
"""
AIQ YouTube Research Tool
Orchestrates yt-dlp + youtube-transcript-api to extract, analyse, and synthesise YouTube content.

Usage:
    python3 yt_research.py --url "https://youtube.com/watch?v=..."
    python3 yt_research.py --query "AI agent workflows" --count 10
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(os.environ.get("YT_RESEARCH_OUTPUT", "./yt_research_output"))
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"
RESULTS_DIR = OUTPUT_DIR / "results"


# ── Helpers ───────────────────────────────────────────────────────────────────

def ensure_dirs():
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    print(f"[yt-research] {msg}", flush=True)


def run(cmd: List[str], capture=True) -> Tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=capture, text=True)
    return result.returncode, result.stdout, result.stderr


def sanitise_filename(text: str) -> str:
    return re.sub(r'[^\w\-_]', '_', text)[:60]


def get_transcript(video_id: str) -> str:
    """Fetch transcript using youtube-transcript-api."""
    try:
        ytt = YouTubeTranscriptApi()
        transcript = ytt.fetch(video_id)
        # Join all text segments into a clean string
        return " ".join(chunk.text for chunk in transcript)
    except TranscriptsDisabled:
        log(f"Transcripts disabled for {video_id}")
        return ""
    except NoTranscriptFound:
        log(f"No transcript found for {video_id}")
        return ""
    except Exception as e:
        log(f"Transcript error for {video_id}: {e}")
        return ""


# ── Step 1: Resolve URLs ──────────────────────────────────────────────────────

def search_youtube(query: str, count: int) -> List[str]:
    """Use yt-dlp to search YouTube and return video URLs."""
    log(f"Searching YouTube: '{query}' (top {count})")
    search_query = f"ytsearch{count}:{query}"
    code, out, err = run([
        "yt-dlp",
        "--get-id",
        "--no-playlist",
        search_query
    ])
    if code != 0:
        log(f"Search failed: {err.strip()}")
        sys.exit(1)
    video_ids = [vid.strip() for vid in out.strip().splitlines() if vid.strip()]
    urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
    log(f"Found {len(urls)} videos")
    return urls


# ── Step 2: Extract metadata + transcript ─────────────────────────────────────

def extract_video_data(url: str) -> Optional[Dict]:
    """Pull metadata and transcript for a single video."""
    log(f"Extracting: {url}")

    # Get metadata as JSON
    code, out, err = run([
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        url
    ])
    if code != 0:
        log(f"Metadata failed for {url}: {err.strip()}")
        return None

    try:
        meta = json.loads(out)
    except json.JSONDecodeError:
        log(f"Failed to parse metadata for {url}")
        return None

    video_id    = meta.get("id", "unknown")
    title       = meta.get("title", "Unknown Title")
    channel     = meta.get("uploader", "Unknown Channel")
    view_count  = meta.get("view_count", 0)
    duration    = meta.get("duration", 0)
    upload_date = meta.get("upload_date", "")
    description = meta.get("description", "")[:500]  # First 500 chars only

    # Pull transcript using youtube-transcript-api
    transcript_text = get_transcript(video_id)
    if transcript_text:
        log(f"Transcript extracted: {len(transcript_text)} chars")
    else:
        log(f"No transcript available for {video_id}")

    # Save clean transcript as .txt
    txt_path = TRANSCRIPTS_DIR / f"{video_id}.txt"
    header = (
        f"Title: {title}\n"
        f"Channel: {channel}\n"
        f"URL: {url}\n"
        f"Views: {view_count:,}\n"
        f"Duration: {duration//60}m {duration%60}s\n"
        f"Upload date: {upload_date}\n"
        f"Description: {description}\n"
        f"{'─'*60}\n\n"
    )
    txt_path.write_text(header + transcript_text, encoding="utf-8")
    log(f"Saved: {txt_path.name}")

    return {
        "video_id":    video_id,
        "title":       title,
        "channel":     channel,
        "url":         url,
        "view_count":  view_count,
        "duration":    duration,
        "upload_date": upload_date,
        "transcript":  transcript_text,
        "txt_path":    str(txt_path),
        "has_transcript": bool(transcript_text)
    }


# ── Step 3: NotebookLM synthesis ──────────────────────────────────────────────

def notebooklm_synthesise(txt_paths: List[str], query: str) -> str:
    """
    Upload transcripts to NotebookLM and query for synthesis.
    Requires notebooklm-pi to be installed and authenticated.
    Falls back gracefully if not available.
    """
    try:
        import importlib.util
        if importlib.util.find_spec("notebooklm") is None:
            raise ImportError("notebooklm-pi not installed")
    except ImportError:
        log("notebooklm-pi not found — skipping NotebookLM synthesis")
        log("To enable: pip install notebooklm-pi && notebooklm login")
        return ""

    try:
        import notebooklm  # type: ignore

        notebook_title = f"AIQ Research — {query[:40]} — {datetime.now().strftime('%Y%m%d_%H%M')}"
        log(f"Creating NotebookLM notebook: {notebook_title}")
        nb = notebooklm.create_notebook(title=notebook_title)

        for path in txt_paths:
            log(f"Uploading: {Path(path).name}")
            notebooklm.add_source(nb, file_path=path)

        synthesis_prompt = (
            f"Based on these video transcripts about '{query}', provide:\n"
            f"1. Top 5 key insights or trends\n"
            f"2. Recurring themes across videos\n"
            f"3. Notable quotes or specific claims\n"
            f"4. Gaps or contradictions between sources\n"
            f"Be specific. Reference which videos support each point."
        )

        log("Querying NotebookLM for synthesis...")
        response = notebooklm.query(nb, synthesis_prompt)
        return response

    except Exception as e:
        log(f"NotebookLM error: {e}")
        return ""


# ── Step 4: Build outputs ─────────────────────────────────────────────────────

def build_summary(videos: List[Dict], query: str, notebooklm_synthesis: str) -> str:
    """Produce the summary.md key insights file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# YouTube Research Summary",
        f"",
        f"**Query:** {query}",
        f"**Date:** {timestamp}",
        f"**Videos processed:** {len(videos)}",
        f"",
        f"---",
        f"",
        f"## Videos Analysed",
        f"",
    ]

    for i, v in enumerate(videos, 1):
        duration_str = f"{v['duration']//60}m {v['duration']%60}s"
        transcript_status = "transcript available" if v['has_transcript'] else "no transcript"
        lines.append(
            f"{i}. **{v['title']}**  \n"
            f"   Channel: {v['channel']} | Views: {v['view_count']:,} | "
            f"Duration: {duration_str} | {transcript_status}  \n"
            f"   {v['url']}"
        )
        lines.append("")

    if notebooklm_synthesis:
        lines += [
            f"---",
            f"",
            f"## NotebookLM Synthesis",
            f"",
            notebooklm_synthesis,
            f"",
        ]
    else:
        lines += [
            f"---",
            f"",
            f"## Synthesis",
            f"",
            f"*NotebookLM synthesis not available. "
            f"Transcripts saved to `/transcripts/` for manual upload.*",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## Transcript Files",
        f"",
    ]
    for v in videos:
        if v['has_transcript']:
            lines.append(f"- `transcripts/{Path(v['txt_path']).name}`")

    return "\n".join(lines)


def build_jarvis_brief(videos: List[Dict], query: str, notebooklm_synthesis: str) -> Dict:
    """Produce the structured JSON brief for Jarvis."""
    return {
        "brief_type": "youtube_research",
        "query": query,
        "generated_at": datetime.now().isoformat(),
        "video_count": len(videos),
        "videos": [
            {
                "title":          v["title"],
                "channel":        v["channel"],
                "url":            v["url"],
                "view_count":     v["view_count"],
                "duration_secs":  v["duration"],
                "upload_date":    v["upload_date"],
                "has_transcript": v["has_transcript"],
                "transcript_file": Path(v["txt_path"]).name if v["has_transcript"] else None
            }
            for v in videos
        ],
        "notebooklm_synthesis": notebooklm_synthesis or None,
        "transcript_dir": str(TRANSCRIPTS_DIR),
        "action_required": (
            "Review summary.md. Transcripts available in transcript_dir. "
            "notebooklm_synthesis contains synthesised insights if available."
        )
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AIQ YouTube Research Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url",   type=str, help="Single YouTube URL")
    group.add_argument("--query", type=str, help="Search query")
    parser.add_argument("--count", type=int, default=5,
                        help="Number of videos to pull for --query (default: 5)")
    parser.add_argument("--no-notebooklm", action="store_true",
                        help="Skip NotebookLM synthesis step")
    args = parser.parse_args()

    ensure_dirs()

    # Resolve URLs
    if args.url:
        urls = [args.url]
        query_label = args.url
    else:
        urls = search_youtube(args.query, args.count)
        query_label = args.query

    # Extract all videos
    videos = []
    for url in urls:
        data = extract_video_data(url)
        if data:
            videos.append(data)

    if not videos:
        log("No videos successfully extracted. Exiting.")
        sys.exit(1)

    log(f"\n{len(videos)} videos extracted. {sum(1 for v in videos if v['has_transcript'])} have transcripts.")

    # NotebookLM synthesis
    notebooklm_result = ""
    if not args.no_notebooklm:
        txt_paths = [v["txt_path"] for v in videos if v["has_transcript"]]
        if txt_paths:
            notebooklm_result = notebooklm_synthesise(txt_paths, query_label)
        else:
            log("No transcripts available for NotebookLM upload.")

    # Write outputs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = sanitise_filename(query_label)

    summary_path = RESULTS_DIR / f"summary_{safe_query}_{timestamp}.md"
    brief_path   = RESULTS_DIR / f"jarvis_brief_{safe_query}_{timestamp}.json"

    summary_path.write_text(
        build_summary(videos, query_label, notebooklm_result),
        encoding="utf-8"
    )
    brief_path.write_text(
        json.dumps(build_jarvis_brief(videos, query_label, notebooklm_result), indent=2),
        encoding="utf-8"
    )

    log(f"\nDone.")
    log(f"  Summary:      {summary_path}")
    log(f"  Jarvis brief: {brief_path}")
    log(f"  Transcripts:  {TRANSCRIPTS_DIR}/")


if __name__ == "__main__":
    main()
