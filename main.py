import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

APP_VERSION = "1.0.0"
OUTPUT_DIR = "./outputs"

app = FastAPI(
    title="Short Agent",
    description="Semi-automatic Shorts/Reels content package generator for DIGI-TV",
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


def get_openai_client() -> Optional[OpenAI]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)


# ─── Models ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    channel_name: str = Field(default="DIGI-TV")
    content_theme: str = Field(
        default="Digital infotainment, technology education, AI, automation, mobility, engineering, and social impact"
    )
    content_pillars: List[str] = Field(
        default=[
            "AI tools and automation",
            "future mobility and self-driving technology",
            "engineering and infrastructure",
            "digital business and creator economy",
            "social impact of technology",
        ]
    )
    number_of_packages: int = Field(default=5, ge=1, le=10)
    duration_seconds: int = Field(default=60, ge=30, le=90)
    language: str = Field(default="English")
    platforms: List[str] = Field(
        default=["YouTube Shorts", "Facebook Reels", "Instagram Reels", "TikTok"]
    )
    extra_instruction: str = Field(
        default="Find relevant trending or evergreen ideas suitable for DIGI-TV."
    )
    save_output: bool = Field(default=True)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    key_set = bool(os.getenv("OPENAI_API_KEY"))
    if key_set:
        return {
            "status": "ok",
            "app": "short-agent",
            "version": APP_VERSION,
            "agent_ready": True,
            "openai_key_set": True,
            "output_dir": OUTPUT_DIR,
        }
    return JSONResponse(
        status_code=200,
        content={
            "status": "warning",
            "app": "short-agent",
            "version": APP_VERSION,
            "agent_ready": False,
            "openai_key_set": False,
            "output_dir": OUTPUT_DIR,
            "message": "OPENAI_API_KEY is missing. Add it to .env.",
        },
    )


@app.get("/app", tags=["Dashboard"], include_in_schema=False)
def dashboard():
    return FileResponse("static/index.html")


@app.post("/generate", tags=["Generate"])
def generate_packages(req: GenerateRequest):
    client = get_openai_client()
    if client is None:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": "OPENAI_API_KEY is not configured. Add it to your .env file.",
            },
        )

    system_prompt = (
        "You are a professional short-form video strategist for DIGI-TV. "
        "Generate original, monetization-safe, useful, short-video production packages. "
        "Return ONLY valid JSON — no markdown fences, no explanation text."
    )

    user_prompt = f"""
Generate {req.number_of_packages} short-video content packages for the channel "{req.channel_name}".

Channel theme: {req.content_theme}
Content pillars: {json.dumps(req.content_pillars)}
Target platforms: {json.dumps(req.platforms)}
Target duration: {req.duration_seconds} seconds
Language: {req.language}
Extra instruction: {req.extra_instruction}

Rules:
- Every topic must fit the DIGI-TV theme: technology, AI, automation, future mobility, engineering, digital business, creator economy, or social impact of technology.
- Do NOT generate random entertainment, politics, gossip, celebrity, adult, medical-claim, or financial-promise content.
- Do NOT suggest copyrighted music or famous songs. Use generic descriptions like "royalty-free futuristic tech beat, 120 BPM".
- Do NOT impersonate real celebrities, politicians, or public figures.
- Avoid misleading synthetic media.
- Write original scripts (not copied text).
- Make content useful enough for YouTube monetization review.
- Scene prompts must be practical for tools like Google Flow / Gemini Veo, Kling, Meta AI, Runway, Canva, CapCut, or similar.
- The hook must work in the first 3 seconds.
- Script must be complete and natural to read aloud in {req.duration_seconds} seconds.

Return a JSON object with this exact structure:
{{
  "packages": [
    {{
      "package_id": "pkg_001",
      "topic": "...",
      "angle": "...",
      "why_this_topic": "...",
      "target_audience": "...",
      "hook": "...",
      "script": "...",
      "voiceover": "...",
      "scene_prompts": ["...", "...", "..."],
      "subtitles": ["...", "...", "..."],
      "title": "...",
      "description": "...",
      "hashtags": ["...", "..."],
      "music_mood": "...",
      "platform_notes": {{
        "YouTube Shorts": "...",
        "Facebook Reels": "...",
        "Instagram Reels": "...",
        "TikTok": "..."
      }},
      "upload_checklist": ["...", "...", "..."],
      "risk_check": "..."
    }}
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=8000,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if model adds them despite instructions
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        packages = data.get("packages", [])

    except json.JSONDecodeError as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": f"Failed to parse JSON from OpenAI response: {str(e)}",
                "raw_response": raw[:2000],
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)},
        )

    generated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_json_file = None
    output_markdown_file = None

    if req.save_output:
        Path(OUTPUT_DIR).mkdir(exist_ok=True)

        json_path = f"{OUTPUT_DIR}/{timestamp}_short_packages.json"
        md_path = f"{OUTPUT_DIR}/{timestamp}_short_packages.md"

        json_payload = {
            "generated_at": generated_at,
            "channel_name": req.channel_name,
            "number_of_packages": len(packages),
            "packages": packages,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2, ensure_ascii=False)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Short Video Packages\n\n")
            f.write(f"Generated: {generated_at}\n")
            f.write(f"Channel: {req.channel_name}\n\n")
            for i, pkg in enumerate(packages, 1):
                f.write(f"---\n\n")
                f.write(f"## Package {i}: {pkg.get('title', pkg.get('topic', ''))}\n\n")
                f.write(f"**Topic:** {pkg.get('topic', '')}\n\n")
                f.write(f"**Angle:** {pkg.get('angle', '')}\n\n")
                f.write(f"**Why this topic:** {pkg.get('why_this_topic', '')}\n\n")
                f.write(f"**Target audience:** {pkg.get('target_audience', '')}\n\n")
                f.write(f"**Hook:** {pkg.get('hook', '')}\n\n")
                f.write(f"**Script:**\n\n{pkg.get('script', '')}\n\n")
                f.write(f"**Voiceover:**\n\n{pkg.get('voiceover', '')}\n\n")
                scenes = pkg.get("scene_prompts", [])
                f.write(f"**Scene prompts:**\n\n")
                for s in scenes:
                    f.write(f"- {s}\n")
                f.write("\n")
                subs = pkg.get("subtitles", [])
                f.write(f"**Subtitles:**\n\n")
                for s in subs:
                    f.write(f"- {s}\n")
                f.write("\n")
                f.write(f"**Title:** {pkg.get('title', '')}\n\n")
                f.write(f"**Description:**\n\n{pkg.get('description', '')}\n\n")
                tags = pkg.get("hashtags", [])
                f.write(f"**Hashtags:** {' '.join(tags)}\n\n")
                f.write(f"**Music mood:** {pkg.get('music_mood', '')}\n\n")
                pn = pkg.get("platform_notes", {})
                if pn:
                    f.write(f"**Platform notes:**\n\n")
                    for platform, note in pn.items():
                        f.write(f"- **{platform}:** {note}\n")
                    f.write("\n")
                checklist = pkg.get("upload_checklist", [])
                f.write(f"**Upload checklist:**\n\n")
                for item in checklist:
                    f.write(f"- [ ] {item}\n")
                f.write("\n")
                f.write(f"**Risk check:** {pkg.get('risk_check', '')}\n\n")

        output_json_file = json_path
        output_markdown_file = md_path

    return {
        "status": "success",
        "generated_at": generated_at,
        "channel_name": req.channel_name,
        "number_of_packages": len(packages),
        "packages": packages,
        "output_json_file": output_json_file,
        "output_markdown_file": output_markdown_file,
        "error": None,
    }
