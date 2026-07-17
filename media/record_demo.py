"""
Record the ReLoop animated demo as a video using Playwright's screen recorder.
Captures actual CSS animations, typewriter effects, and transitions at 1920x1080.
Output: media/demo.mp4  (~90 seconds)
Run: .venv\Scripts\python media\record_demo.py
"""
import asyncio
import subprocess
import shutil
from pathlib import Path

W, H = 1920, 1080
OUT_DIR  = Path(__file__).parent / "demo_recording"
OUT_MP4  = Path(__file__).parent / "demo.mp4"
HTML     = Path(__file__).parent / "demo.html"
FFMPEG   = Path(__file__).parent.parent / ".venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
DURATION = 92_000  # ms — total demo length (must match demo HTML)


async def record():
    from playwright.async_api import async_playwright

    OUT_DIR.mkdir(exist_ok=True)
    url = HTML.resolve().as_uri()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(OUT_DIR),
            record_video_size={"width": W, "height": H},
        )
        page = await context.new_page()
        await page.goto(url, wait_until="load")
        print(f"Recording demo ({DURATION//1000}s) at {W}x{H}...")
        await page.wait_for_timeout(DURATION)
        print("Done — saving video...")
        await context.close()
        await browser.close()

    # Find the recorded WebM file
    webms = sorted(OUT_DIR.glob("*.webm"))
    if not webms:
        print("ERROR: no webm file found")
        return None
    webm = webms[-1]
    print(f"Recorded: {webm} ({webm.stat().st_size//1024} KB)")
    return webm


def convert(webm: Path):
    cmd = [
        str(FFMPEG), "-y", "-i", str(webm),
        "-vf", f"scale={W}:{H}:flags=lanczos,format=yuv420p",
        "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-movflags", "+faststart", str(OUT_MP4),
    ]
    print("Converting to MP4...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg error:", result.stderr[-600:])
    else:
        mb = OUT_MP4.stat().st_size / 1024 / 1024
        print(f"demo.mp4 ready: {OUT_MP4}  ({mb:.1f} MB)")
    # Clean up temp dir
    shutil.rmtree(OUT_DIR, ignore_errors=True)


async def main():
    webm = await record()
    if webm:
        convert(webm)


if __name__ == "__main__":
    asyncio.run(main())
