# YouTube Research Skill

Use this skill when Keith runs `/yt-research` or asks you to research YouTube content,
find transcripts, analyse a video, or pull trends from YouTube.

---

## Commands

### Search by topic
```
/yt-research --query "AI agent workflows" --count 10
```
Searches YouTube, pulls the top N videos, extracts transcripts, synthesises via NotebookLM.

### Research a specific video
```
/yt-research --url "https://www.youtube.com/watch?v=VIDEO_ID"
```
Extracts transcript + metadata for one video, synthesises via NotebookLM.

### Skip NotebookLM (transcript only)
```
/yt-research --query "topic" --count 5 --no-notebooklm
```
Pulls transcripts and saves locally. No NotebookLM step.

---

## What You Do When Keith Runs This

1. **Run the script** from the project root:
   ```bash
   python3 yt_research.py [args]
   ```

2. **Monitor output** — the script logs progress for each video.

3. **On completion**, read and present:
   - `yt_research_output/results/summary_*.md` — key insights
   - `yt_research_output/results/jarvis_brief_*.json` — structured brief

4. **Summarise findings** to Keith in his voice: direct, specific, no filler.
   Lead with the most interesting insight. Flag anything that contradicts
   expectations or stands out.

5. **If asked to forward to Jarvis**, read the `jarvis_brief_*.json` and assign
   it as a task via the AIQ bridge.

---

## Output Structure

```
yt_research_output/
  transcripts/
    {video_id}.txt        ← clean transcript + metadata header per video
  results/
    summary_{query}_{ts}.md         ← key insights + NotebookLM synthesis
    jarvis_brief_{query}_{ts}.json  ← structured JSON for Jarvis
```

---

## NotebookLM Setup (one-time, on Mac)

If notebooklm-pi is not yet installed:

```bash
pip install notebooklm-pi
notebooklm login
```

`notebooklm login` opens a Chrome window for Google auth. Complete it once.
The session persists. All future runs are fully automated.

If NotebookLM auth fails or the library isn't installed, the script continues
without it — transcripts are saved locally and synthesis is skipped gracefully.

---

## Dependencies

```bash
pip install yt-dlp notebooklm-pi
```

yt-dlp is the only hard dependency. notebooklm-pi is optional but recommended.

---

## Environment Variable

Set `YT_RESEARCH_OUTPUT` to change where files are saved:
```bash
export YT_RESEARCH_OUTPUT="/path/to/your/research/folder"
```
Default: `./yt_research_output` relative to where the script is run.

---

## What the Jarvis Brief Contains

```json
{
  "brief_type": "youtube_research",
  "query": "...",
  "generated_at": "ISO timestamp",
  "video_count": 5,
  "videos": [ { title, channel, url, view_count, duration_secs, has_transcript } ],
  "notebooklm_synthesis": "...",
  "transcript_dir": "/path/to/transcripts",
  "action_required": "..."
}
```

Jarvis can use this brief to: write content, extract competitive intelligence,
generate a Sunday Blueprint post, or brief Archie to build something based on findings.

---

## Error Handling

| Error | What happens |
|-------|-------------|
| Video has no captions | Skipped gracefully, metadata still saved |
| notebooklm-pi not installed | Synthesis skipped, transcripts saved locally |
| YouTube search returns no results | Script exits with clear message |
| Single URL is private/unavailable | Script exits with clear message |
