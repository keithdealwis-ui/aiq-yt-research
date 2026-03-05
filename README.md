# AIQ YouTube Research Tool

Part of the Ascendancy IQ (AIQ) autonomous agent stack.

Pulls YouTube transcripts and metadata via yt-dlp and youtube-transcript-api,
then synthesises findings natively through Claude Code. No external APIs.
No NotebookLM dependency. No API keys required.

## What it does

- Search YouTube by topic and return the top N videos
- Research a specific video by URL
- Extract full transcripts (works even when creators disable captions)
- Save raw transcripts locally as .txt files
- Claude Code reads and synthesises natively — key insights, recurring themes,
  contradictions, standout claims, recommended action
- Outputs a structured Jarvis brief (JSON) ready to assign via the AIQ bridge

## Stack

- yt-dlp — search and metadata extraction
- youtube-transcript-api — transcript extraction
- Claude Code — native synthesis layer

## Usage

Search by topic:
```
/yt-research --query "AI agent workflows" --count 5
```

Research a specific video:
```
/yt-research --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Setup

```bash
pip install yt-dlp youtube-transcript-api
```

Drop SKILL.md into your Claude Code workspace and tell Claude Code:
"Read SKILL.md and implement the yt-research skill."

## Output

```
yt_research_output/
  transcripts/
    {video_id}.txt        # transcript + metadata header per video
  results/
    summary_*.md          # key insights synthesis
    jarvis_brief_*.json   # structured brief for Jarvis
```

## Part of AIQ

- Main repo: github.com/keithdealwis-ui/jarvis-archie-bridge
- Architecture: ascendencyiq.ai/architecture

