"""Debug probe: render the benchy with layer-lines and measure ridge contrast
on a vertical wall vs a horizontal top surface.

Runs the real blender_studio.py via the Blender CLI, then analyzes the PNG:
for each probe region, compute the std-dev of pixel luminance along the axis
perpendicular to the expected layer ridges. High std = visible ridges.

Usage (Git Bash, from repo root):
  .venv/Scripts/python.exe .scratch/render-profiles/probe_layer_lines.py [extra blender_studio args...]

Prints PASS/FAIL: FAIL when wall ridges are weak relative to top ridges
(the user's symptom). Requires Pillow.
"""

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BLENDER = r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
SCRIPT = REPO / "backend" / "render" / "blender_studio.py"
BENCHY = REPO / "frontend" / "public" / "render" / "3DBenchy.stl"
OUT = REPO / ".scratch" / "render-profiles" / "probe_render.png"

RES = 512  # faster loop than 1024


def render(extra_args):
    cmd = [
        BLENDER, "--background", "--python", str(SCRIPT), "--",
        "--input", str(BENCHY), "--output", str(OUT),
        "--resolution", str(RES),
        *extra_args,
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    dt = time.time() - t0
    if proc.returncode != 0:
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
        raise SystemExit(f"Blender failed ({proc.returncode})")
    print(f"rendered in {dt:.1f}s -> {OUT.name}")


def luminance_std_along_rows(img, box):
    """Std-dev of row-mean luminance within box (x0,y0,x1,y1).

    Ridges running horizontally (layer lines on a wall seen from the side)
    make row means oscillate -> high std. Smooth surface -> low std.
    """
    from PIL import Image
    region = img.crop(box).convert("L")
    w, h = region.size
    px = region.load()
    row_means = [sum(px[x, y] for x in range(w)) / w for y in range(h)]
    mean = sum(row_means) / len(row_means)
    var = sum((v - mean) ** 2 for v in row_means) / len(row_means)
    return var ** 0.5, mean


def main():
    extra = sys.argv[1:] or ["--finish", "layer-lines"]
    render(extra)

    from PIL import Image
    img = Image.open(OUT)
    w, h = img.size
    s = w / 512  # scale probe boxes with resolution

    # Probe boxes tuned for the default 45/28 camera on the benchy at 512px.
    # Wall: front cabin wall (vertical, should show horizontal layer ridges).
    # Roof: cabin roof (horizontal plane; Z-bands make this constant -> smooth).
    wall = (int(200 * s), int(240 * s), int(255 * s), int(300 * s))
    roof = (int(180 * s), int(185 * s), int(300 * s), int(210 * s))

    wall_std, wall_mean = luminance_std_along_rows(img, wall)
    roof_std, roof_mean = luminance_std_along_rows(img, roof)
    print(f"wall  ridge-std={wall_std:6.2f} mean={wall_mean:6.1f}  box={wall}")
    print(f"roof  ridge-std={roof_std:6.2f} mean={roof_mean:6.1f}  box={roof}")

    # Symptom check: user sees lines on top surfaces but not walls.
    if wall_std < 1.0:
        print("FAIL: wall shows no significant ridges (user symptom reproduced)")
        sys.exit(1)
    print("PASS: wall ridges visible")


if __name__ == "__main__":
    main()
