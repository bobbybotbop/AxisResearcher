"""One-off setting sweep: render the default benchy from the front-right angle,
8 values per user-adjustable setting, all other settings at defaults.

Output: setting-sweeps/<setting>/<setting>_NN_<value>.png
"""

import os
import subprocess
import sys

BLENDER = os.environ.get(
    "BLENDER_PATH", r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
)
SCRIPT = os.path.join("backend", "render", "blender_studio.py")
INPUT = os.path.join("frontend", "public", "render", "3DBenchy.stl")
OUT_ROOT = "setting-sweeps"

# Defaults from backend/constants/render.py
DEFAULTS = {
    "color": (0.051, 0.051, 0.051),  # #0d0d0d
    "roughness": 0.3,
    "resolution": 512,  # 512 to keep 72 renders tractable
    "azimuth": 45.0,    # front-right preset
    "elevation": 0.0,
    "fov": 40.0,
    "finish": "smooth",
    "layer_height_mm": 0.2,
    "layer_depth": 0.4,
    "key_energy": 150.0,
    "fill_energy": 60.0,
    "rim_energy": 250.0,
    "ambient": 0.35,
    "shadow": True,
    "shadow_softness": 1.5,
    "exposure": 1.0,
}

# 8 values per setting, spanning the UI-allowed range (inclusive of default-ish points)
SWEEPS = {
    "key-energy":       ("key_energy",       [0, 50, 100, 150, 300, 600, 1200, 2000]),
    "fill-energy":      ("fill_energy",      [0, 20, 40, 60, 120, 300, 800, 2000]),
    "rim-energy":       ("rim_energy",       [0, 60, 125, 250, 500, 1000, 1500, 2000]),
    "ambient":          ("ambient",          [0.0, 0.1, 0.2, 0.35, 0.6, 1.0, 1.5, 2.0]),
    "shadow-softness":  ("shadow_softness",  [0.1, 0.5, 1.0, 1.5, 2.5, 4.0, 7.0, 10.0]),
    "exposure":         ("exposure",         [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.5, 4.0]),
    "roughness":        ("roughness",        [0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0]),
    "layer-height-mm":  ("layer_height_mm",  [0.08, 0.12, 0.16, 0.2, 0.24, 0.28, 0.34, 0.4]),
    "layer-depth":      ("layer_depth",      [0.0, 0.1, 0.2, 0.3, 0.4, 0.55, 0.75, 1.0]),
}


def fmt(v):
    return f"{v:g}"


def build_cmd(out_path, overrides):
    s = {**DEFAULTS, **overrides}
    cmd = [
        BLENDER, "--background", "--python", SCRIPT, "--",
        "--input", INPUT,
        "--output", out_path,
        "--color", *(fmt(c) for c in s["color"]),
        "--roughness", fmt(s["roughness"]),
        "--resolution", str(s["resolution"]),
        "--azimuth", fmt(s["azimuth"]),
        "--elevation", fmt(s["elevation"]),
        "--fov", fmt(s["fov"]),
        "--finish", "layer-lines" if ("layer_height_mm" in overrides or "layer_depth" in overrides) else s["finish"],
        "--layer-height-mm", fmt(s["layer_height_mm"]),
        "--layer-depth", fmt(s["layer_depth"]),
        "--key-energy", fmt(s["key_energy"]),
        "--fill-energy", fmt(s["fill_energy"]),
        "--rim-energy", fmt(s["rim_energy"]),
        "--ambient", fmt(s["ambient"]),
        "--shadow-softness", fmt(s["shadow_softness"]),
        "--exposure", fmt(s["exposure"]),
        "--shadow" if s["shadow"] else "--no-shadow",
    ]
    return cmd


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    total = sum(len(v[1]) for k, v in SWEEPS.items() if not only or k in only)
    done = 0
    for name, (key, values) in SWEEPS.items():
        if only and name not in only:
            continue
        out_dir = os.path.join(OUT_ROOT, name)
        os.makedirs(out_dir, exist_ok=True)
        for i, value in enumerate(values, 1):
            out_path = os.path.abspath(os.path.join(out_dir, f"{name}_{i:02d}_{fmt(value)}.png"))
            if os.path.exists(out_path):
                done += 1
                continue
            cmd = build_cmd(out_path, {key: value})
            done += 1
            print(f"[{done}/{total}] {name} = {fmt(value)}", flush=True)
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode != 0:
                print(f"  FAILED ({r.returncode}): {r.stdout[-500:]} {r.stderr[-500:]}", flush=True)
    print(f"done: {done}/{total}")


if __name__ == "__main__":
    main()
