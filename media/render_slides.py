"""Render intro.html slides to 1920x1080 PNG frames using headless Chromium,
then encode to MP4 with ffmpeg.
Run from the project root:
    .venv\Scripts\python media\render_slides.py
"""
import asyncio
import os
import subprocess
from pathlib import Path

# Slide durations in seconds (must match intro.html durations array)
DURATIONS = [9, 11, 11, 11, 10, 11, 9, 8]

W, H = 1920, 1080
FRAMES_DIR = Path(__file__).parent / "frames"
CONCAT_FILE = FRAMES_DIR / "concat.txt"
OUT_MP4 = Path(__file__).parent / "intro.mp4"
HTML_PATH = Path(__file__).parent / "intro.html"
FFMPEG = Path(__file__).parent.parent / ".venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"


async def render():
    from playwright.async_api import async_playwright

    FRAMES_DIR.mkdir(exist_ok=True)
    url = HTML_PATH.resolve().as_uri()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": W, "height": H})
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(500)

        # Stop auto-advance and hide UI chrome
        await page.evaluate("""() => {
            let id = setTimeout(() => {}, 0);
            while (id--) clearTimeout(id);
            const p = document.querySelector('.progress'); if (p) p.style.display='none';
            const h = document.querySelector('.hint'); if (h) h.style.display='none';
            const l = document.querySelector('.logo'); if (l) l.style.display='none';
        }""")

        n = await page.evaluate("document.querySelectorAll('.slide').length")
        print(f"Found {n} slides, rendering at {W}x{H}...")

        for i in range(n):
            await page.evaluate(f"""(idx) => {{
                const slides = document.querySelectorAll('.slide');
                slides.forEach(s => {{ s.classList.remove('active'); s.style.transition='none'; }});
                slides[idx].classList.add('active');
            }}""", i)
            await page.wait_for_timeout(600)
            path = FRAMES_DIR / f"slide_{i:02d}.png"
            await page.screenshot(path=str(path), clip={"x": 0, "y": 0, "width": W, "height": H})
            print(f"  Captured slide {i+1}/{n}: {path.name}")

        await browser.close()

    print("All frames captured.")


def encode():
    # Write concat list
    lines = []
    for i, dur in enumerate(DURATIONS):
        lines.append(f"file '{(FRAMES_DIR / f'slide_{i:02d}.png').as_posix()}'")
        lines.append(f"duration {dur}")
    # Duplicate last frame (ffmpeg concat demuxer requirement)
    lines.append(f"file '{(FRAMES_DIR / f'slide_{len(DURATIONS)-1:02d}.png').as_posix()}'")
    CONCAT_FILE.write_text("\n".join(lines))

    cmd = [
        str(FFMPEG), "-y",
        "-f", "concat", "-safe", "0", "-i", str(CONCAT_FILE),
        "-vf", f"scale={W}:{H}:flags=lanczos,format=yuv420p",
        "-r", "30", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-movflags", "+faststart",
        str(OUT_MP4),
    ]
    print("Encoding MP4...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg error:", result.stderr[-800:])
    else:
        size_mb = OUT_MP4.stat().st_size / 1024 / 1024
        print(f"MP4 ready: {OUT_MP4}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    asyncio.run(render())
    encode()
