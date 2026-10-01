#!/usr/bin/env python3
"""
Living still renderer for DroneMill covers.

Turns one still image into a subtly moving shot, so a 2h video does not sit on a frozen
frame. Effects are small and physical (a hand holding a phone, a ship rolling, a lamp
flickering, water shimmering, fog drifting) and every motion is periodic over LOOP_SEC,
so the clip loops seamlessly under a long video.

Usage:
  python3 scripts/living_still.py <image> <recipe> <out.mp4> [seconds] [width]
  python3 scripts/living_still.py <image> auto:<preset>:<category> <out.mp4> [seconds] [width]

Hand-made recipes are defined in RECIPES at the bottom (effects with parameters in normalized
image coordinates 0..1). "auto" builds a recipe for any cover: it finds the light sources
itself and picks the atmosphere from the sound preset and concept category.
"""

import math
import subprocess
import sys

import cv2
import numpy as np

FPS = 24
LOOP_SEC = 60.0  # every periodic motion completes a whole number of cycles in this time


def _period(seconds):
    """Snap a period so it divides LOOP_SEC (keeps the loop seamless)."""
    cycles = max(1, round(LOOP_SEC / seconds))
    return LOOP_SEC / cycles


def _osc(t, seconds, phase=0.0):
    return math.sin(2 * math.pi * t / _period(seconds) + phase)


def _value_noise(t, seconds, seed):
    """Smooth pseudo-random signal in [-1, 1]: a few incommensurate (but loop-safe) sines."""
    rng = np.random.default_rng(seed)
    total = 0.0
    for k, mult in enumerate([1.0, 0.53, 0.29]):
        total += mult * _osc(t, seconds * (1.0 + 0.37 * k), rng.uniform(0, 2 * math.pi))
    return total / 1.82


def _radial_mask(h, w, cx, cy, radius):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w - cx) * (w / h)) ** 2 + (yy / h - cy) ** 2)
    return np.clip(1.0 - d / radius, 0.0, 1.0) ** 2


def _region_mask(h, w, x0, y0, x1, y1, feather=0.06):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xx /= w
    yy /= h
    mx = np.clip(np.minimum(xx - x0, x1 - xx) / feather, 0, 1)
    my = np.clip(np.minimum(yy - y0, y1 - yy) / feather, 0, 1)
    return mx * my


class Scene:
    def __init__(self, image_path, width=1280):
        self.w = width
        self.h = int(round(width * 9 / 16))
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(image_path)
        ih, iw = img.shape[:2]
        scale = max(self.w / iw, self.h / ih)
        img = cv2.resize(img, (int(math.ceil(iw * scale)), int(math.ceil(ih * scale))), interpolation=cv2.INTER_LANCZOS4)
        y0 = (img.shape[0] - self.h) // 2
        x0 = (img.shape[1] - self.w) // 2
        self.base = img[y0:y0 + self.h, x0:x0 + self.w].astype(np.float32) / 255.0
        self.luma = cv2.cvtColor(self.base, cv2.COLOR_BGR2GRAY)
        self.rng = np.random.default_rng(7)
        self.cache = {}


# ---------------------------------------------------------------- geometric effects

def camera(scene, t, p):
    """Handheld / ship motion as one affine warp. p: zoom, sway_px, rot_deg, roll_deg, heave_px,
    roll_sec, push (zoom breathing amount)."""
    h, w = scene.h, scene.w
    zoom = p.get("zoom", 1.06) + p.get("push", 0.0) * (0.5 + 0.5 * _osc(t, 60.0, -math.pi / 2))
    sway = p.get("sway_px", 3.0) * w / 1280
    tx = sway * _value_noise(t, 6.1, 1) + sway * 0.4 * _value_noise(t, 2.3, 2)
    ty = sway * 0.8 * _value_noise(t, 7.3, 3) + sway * 0.3 * _value_noise(t, 1.9, 4)
    rot = p.get("rot_deg", 0.15) * _value_noise(t, 8.7, 5)
    roll = p.get("roll_deg", 0.0)
    if roll:
        rs = p.get("roll_sec", 8.0)
        rot += roll * _osc(t, rs)
        ty += p.get("heave_px", 0.0) * w / 1280 * _osc(t, rs, math.pi / 3)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), rot, zoom)
    m[0, 2] += tx
    m[1, 2] += ty
    return m


def water_shimmer(scene, t, p, frame):
    """Small moving displacement inside a region, weighted toward dark pixels (water),
    so bright solid objects like railings do not wobble."""
    key = ("water", id(p))
    if key not in scene.cache:
        h, w = scene.h, scene.w
        mask = _region_mask(h, w, *p["region"])
        if p.get("dark_only", True):
            mask *= np.clip((0.55 - scene.luma) / 0.35, 0, 1)
        scene.cache[key] = (mask, np.mgrid[0:h, 0:w].astype(np.float32))
    mask, (yy, xx) = scene.cache[key]
    amp = p.get("amp_px", 1.6) * scene.w / 1280
    ph = 2 * math.pi * t / _period(p.get("sec", 3.0))
    dx = amp * mask * np.sin(yy * 0.09 + ph + xx * 0.012)
    dy = amp * 0.6 * mask * np.sin(xx * 0.05 - ph * 1.3 + yy * 0.02)
    return cv2.remap(frame, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------- light effects

def light_flicker(scene, t, p, frame):
    """A lamp or doorway whose brightness wavers, with rare short dips."""
    key = ("flicker", id(p))
    if key not in scene.cache:
        full = _radial_mask(scene.h, scene.w, p["x"], p["y"], p.get("radius", 0.15))
        ys, xs = np.nonzero(full > 1e-4)
        if len(ys) == 0:
            scene.cache[key] = None
        else:
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            scene.cache[key] = (y0, y1, x0, x1, full[y0:y1, x0:x1][..., None])
    if scene.cache[key] is None:
        return frame
    y0, y1, x0, x1, mask = scene.cache[key]
    s = p.get("strength", 0.25)
    wave = 0.6 * _value_noise(t, 1.7, p.get("seed", 11)) + 0.4 * _value_noise(t, 0.37, p.get("seed", 11) + 1)
    dip = 1.0
    if p.get("dips", False):
        phase = (t % _period(9.0)) / _period(9.0)
        if 0.62 < phase < 0.66:
            dip = 0.55
    gain = (1.0 + s * wave) * dip
    out = frame.copy() if frame is scene.base else frame
    out[y0:y1, x0:x1] *= 1.0 + mask * (gain - 1.0)
    return out


def glow_pulse(scene, t, p, frame):
    """Additive colored glow that slowly breathes (light under water, distant beacon)."""
    key = ("glow", id(p))
    if key not in scene.cache:
        m = _radial_mask(scene.h, scene.w, p["x"], p["y"], p.get("radius", 0.2))
        scene.cache[key] = m[..., None] * np.array(p.get("bgr", (0.85, 0.95, 0.6)), np.float32)
    glow = scene.cache[key]
    level = p.get("strength", 0.18) * (0.5 + 0.5 * _osc(t, p.get("sec", 7.0)))
    return frame + glow * level


# ---------------------------------------------------------------- atmosphere

def fog_drift(scene, t, p, frame):
    """Two layers of soft procedural fog sliding at different speeds, screen-blended."""
    key = ("fog", id(p))
    h, w = scene.h, scene.w
    if key not in scene.cache:
        rng = np.random.default_rng(p.get("seed", 21))
        layers = []
        for scale in (0.035, 0.08):
            small = rng.random((max(4, int(h * scale)), max(4, int(2 * w * scale)))).astype(np.float32)
            big = cv2.resize(small, (2 * w, h), interpolation=cv2.INTER_CUBIC)
            big = cv2.GaussianBlur(big, (0, 0), w * 0.02)
            big = (big - big.min()) / (big.max() - big.min() + 1e-6)
            layers.append(np.concatenate([big, big[:, :1]], axis=1))
        band = _region_mask(h, w, 0, p.get("y0", 0.2), 1, p.get("y1", 1.0), feather=0.25)
        scene.cache[key] = (layers, band)
    layers, band = scene.cache[key]
    fog = np.zeros((h, w), np.float32)
    for i, layer in enumerate(layers):
        speed = (i + 1) * w / LOOP_SEC  # one full texture width per loop
        offset = int((t * speed * p.get("speed", 1.0)) % w)
        fog += layer[:, offset:offset + w] * (0.6 if i == 0 else 0.4)
    fog = np.clip((fog - 0.35) * 1.8, 0, 1) * band * p.get("density", 0.25)
    tint = np.array(p.get("bgr", (0.85, 0.88, 0.9)), np.float32)
    return 1.0 - (1.0 - frame) * (1.0 - fog[..., None] * tint)


def dust_motes(scene, t, p, frame):
    """Floating specks lit by the scene, drifting slowly and fading in and out."""
    key = ("dust", id(p))
    h, w = scene.h, scene.w
    if key not in scene.cache:
        rng = np.random.default_rng(p.get("seed", 31))
        n = p.get("count", 70)
        scene.cache[key] = dict(
            x=rng.uniform(0, w, n), y=rng.uniform(0, h, n), r=rng.uniform(0.6, 2.0, n),
            vx=rng.uniform(-6, 6, n), vy=rng.uniform(-4, 3, n), ph=rng.uniform(0, 2 * math.pi, n),
            sec=rng.choice([3.0, 4.0, 5.0, 6.0], n))
    d = scene.cache[key]
    layer = np.zeros((h, w), np.float32)
    for i in range(len(d["x"])):
        x = (d["x"][i] + 12 * math.sin(2 * math.pi * t / _period(d["sec"][i] * 4) + d["ph"][i]) + d["vx"][i] * math.sin(2 * math.pi * t / LOOP_SEC)) % w
        y = (d["y"][i] + 9 * math.cos(2 * math.pi * t / _period(d["sec"][i] * 5) + d["ph"][i]) + d["vy"][i] * math.sin(2 * math.pi * t / LOOP_SEC)) % h
        a = 0.5 + 0.5 * math.sin(2 * math.pi * t / _period(d["sec"][i]) + d["ph"][i])
        cv2.circle(layer, (int(x), int(y)), max(1, int(d["r"][i] * w / 1280)), float(a), -1, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), 1.2)
    lit = 0.3 + scene.luma  # specks show more where the light is
    return frame + (layer * lit * p.get("strength", 0.35))[..., None]


def particles(scene, t, p, frame):
    """Falling snow or rising embers. Each particle crosses its band a whole number of times
    per loop, so the loop stays seamless. p: count, x_range, y_range, direction (+1 down,
    -1 up), cycles (min, max per loop), size, bgr, alpha, fade_with_travel."""
    key = ("particles", id(p))
    h, w = scene.h, scene.w
    if key not in scene.cache:
        rng = np.random.default_rng(p.get("seed", 61))
        n = p.get("count", 150)
        x0, x1 = p.get("x_range", (0.0, 1.0))
        scene.cache[key] = dict(
            x=rng.uniform(x0, x1, n), y=rng.uniform(0, 1, n), cyc=rng.integers(*p.get("cycles", (4, 9)), n),
            sway=rng.uniform(0.002, 0.01, n), ph=rng.uniform(0, 2 * math.pi, n),
            r=rng.uniform(*p.get("size", (0.8, 2.2)), n), a=rng.uniform(0.4, 1.0, n))
    d = scene.cache[key]
    y0, y1 = p.get("y_range", (0.0, 1.0))
    direction = p.get("direction", 1)
    h, w = scene.h // 2, scene.w // 2  # draw at half resolution, upscale once
    layer = np.zeros((h, w), np.float32)
    for i in range(len(d["x"])):
        travel = (d["y"][i] + d["cyc"][i] * t / LOOP_SEC) % 1.0
        yy = y0 + (y1 - y0) * (travel if direction > 0 else 1.0 - travel)
        xx = d["x"][i] + d["sway"][i] * math.sin(2 * math.pi * t / _period(6.0) + d["ph"][i]) * 3
        a = d["a"][i]
        if p.get("fade_with_travel"):
            a *= max(0.0, 1.0 - travel) ** 1.5
        cv2.circle(layer, (int(xx * w), int(yy * h)), max(1, int(d["r"][i] * w / 640 + 0.5)), float(a), -1, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), p.get("blur", 0.9) / 2 + 0.3)
    layer = cv2.resize(layer, (scene.w, scene.h), interpolation=cv2.INTER_LINEAR)
    color = np.array(p.get("bgr", (1.0, 1.0, 1.0)), np.float32) * p.get("alpha", 0.6)
    out = frame.copy() if frame is scene.base else frame
    out += layer[..., None] * color
    return out


def rain_streaks(scene, t, p, frame):
    """Fine, fast diagonal streaks at low opacity (drizzle in front of the lens)."""
    key = ("rain", id(p))
    h, w = scene.h, scene.w
    if key not in scene.cache:
        rng = np.random.default_rng(p.get("seed", 41))
        tile = np.zeros((h * 2, w), np.float32)
        angle = p.get("angle", 0.18)
        for _ in range(p.get("count", 260)):
            x, y = rng.uniform(0, w), rng.uniform(0, 2 * h)
            length = rng.uniform(14, 34) * w / 1280
            cv2.line(tile, (int(x), int(y)), (int(x + angle * length), int(y + length)), float(rng.uniform(0.3, 1.0)), 1, cv2.LINE_AA)
        tile = cv2.GaussianBlur(tile, (0, 0), 0.7)
        scene.cache[key] = np.concatenate([tile, tile], axis=0)
    tile = scene.cache[key]
    speed = 2 * h * p.get("cycles", 30) / LOOP_SEC
    off = int((-t * speed) % (2 * h))
    streaks = tile[off:off + h]
    return frame + (streaks * p.get("strength", 0.10))[..., None]


def finish(scene, t, p, frame):
    """Phone-camera finish: sensor grain, a faint breathing vignette, slight exposure drift."""
    h, w = scene.h, scene.w
    if "vignette" not in scene.cache:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        scene.cache["vignette"] = (np.clip(r - 0.35, 0, 1) ** 1.5)[..., None].astype(np.float32)
        # 12 grain frames reused in rotation: per-frame noise generation was a large share of render time
        scene.cache["grain"] = [scene.rng.normal(0.0, 1.0, (h, w, 1)).astype(np.float32) for _ in range(12)]
    v = scene.cache["vignette"]
    k = p.get("vignette", 0.22) * (1.0 + 0.08 * _osc(t, 12.0))
    exposure = 1.0 + p.get("exposure", 0.015) * _value_noise(t, 5.0, 51)
    out = frame * exposure
    out *= 1.0 - k * v
    out += scene.cache["grain"][int(round(t * FPS)) % 12] * p.get("grain", 0.018)
    return out


# ---------------------------------------------------------------- automatic recipes

def detect_lights(scene, max_n=3):
    """Small, very bright regions (lamps, windows, fires) as (x, y, radius, warm) in 0..1 coords.
    Big bright areas such as sky are ignored."""
    h, w = scene.h, scene.w
    luma = cv2.GaussianBlur(scene.luma, (0, 0), 3)
    thresh = max(0.80, float(np.percentile(luma, 99.6)))
    mask = (luma >= thresh).astype(np.uint8)
    n, _, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    found = []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA] / float(w * h)
        if not 0.00003 <= area <= 0.02:
            continue
        x0, y0, bw, bh = stats[i, :4]
        patch = scene.base[y0:y0 + bh, x0:x0 + bw]
        b, g, r = [float(c) for c in patch.reshape(-1, 3).mean(0)]
        found.append((area, centroids[i][0] / w, centroids[i][1] / h, r - b > 0.12))
    found.sort(reverse=True)
    return [(x, y, float(np.clip(math.sqrt(a) * 3.5, 0.04, 0.14)), warm) for a, x, y, warm in found[:max_n]]


def auto_recipe(scene, preset="", category=""):
    """Recipe for a cover nobody has looked at: light sources found automatically, atmosphere
    chosen from the sound preset and the concept category."""
    cat = category.lower()
    lights = detect_lights(scene)
    recipe = {"camera": {"zoom": 1.06, "sway_px": 2.5, "rot_deg": 0.12}, "pre": [], "post": [],
              "finish": {"grain": 0.010, "vignette": 0.26}}
    for i, (x, y, r, warm) in enumerate(lights):
        recipe["pre"].append(("light_flicker", {"x": x, "y": y, "radius": r, "strength": 0.45 if warm else 0.2,
                                                "dips": (not warm) and i == 0, "seed": 20 + i}))
        if warm and preset == "fantasy":
            recipe["post"].append(("particles", {"count": 22, "direction": -1, "x_range": (x - 0.03, x + 0.03),
                                                 "y_range": (max(0.0, y - 0.45), min(1.0, y + 0.02)), "cycles": (12, 20),
                                                 "size": (0.6, 1.4), "alpha": 0.9, "bgr": (0.25, 0.6, 1.0),
                                                 "fade_with_travel": True, "blur": 0.6, "seed": 40 + i}))
    if preset == "lovecraft" or "eldritch" in cat or "maritime" in cat:
        recipe["post"] += [("fog_drift", {"y0": 0.05, "y1": 0.8, "density": 0.2, "speed": 0.8}),
                           ("rain_streaks", {"count": 110, "strength": 0.04, "angle": 0.3})]
    elif preset == "fantasy":
        recipe["post"].insert(0, ("particles", {"count": 200, "direction": 1, "cycles": (4, 9), "size": (0.8, 2.0),
                                                "alpha": 0.5, "seed": 62}))
    elif "cosmic" in cat or "deep space" in cat:
        recipe["camera"].update({"sway_px": 1.2, "push": 0.025})
    else:  # historical, liminal, academia, retro, prehistoric
        recipe["camera"]["push"] = 0.02
        recipe["post"].append(("dust_motes", {"count": 40, "strength": 0.22}))
    return recipe


# ---------------------------------------------------------------- render

def render(image_path, recipe, out_path, seconds=10.0, width=1280):
    scene = Scene(image_path, width)
    if recipe.startswith("auto"):
        _, preset, category = (recipe.split(":", 2) + ["", ""])[:3]
        steps = auto_recipe(scene, preset, category)
    else:
        steps = RECIPES[recipe]
    cam = steps.get("camera", {})
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
         "-s", f"{scene.w}x{scene.h}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "26", "-maxrate", "4M", "-bufsize", "8M", "-g", "48", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", out_path],
        stdin=subprocess.PIPE)
    for i in range(int(seconds * FPS)):
        t = i / FPS
        frame = scene.base
        for name, p in steps.get("pre", []):
            frame = EFFECTS[name](scene, t, p, frame)
        m = camera(scene, t, cam)
        frame = cv2.warpAffine(frame, m, (scene.w, scene.h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        for name, p in steps.get("post", []):
            frame = EFFECTS[name](scene, t, p, frame)
        frame = finish(scene, t, steps.get("finish", {}), frame)
        proc.stdin.write((np.clip(frame, 0, 1) * 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()


EFFECTS = {
    "water_shimmer": water_shimmer, "light_flicker": light_flicker, "glow_pulse": glow_pulse,
    "fog_drift": fog_drift, "dust_motes": dust_motes, "rain_streaks": rain_streaks,
    "particles": particles,
}

# "pre" effects are painted onto the scene (they move with the camera);
# "post" effects sit in front of the lens (fog, dust, rain stay screen-relative).
RECIPES = {
    "hotel_corridor": {
        "camera": {"zoom": 1.05, "sway_px": 3.0, "rot_deg": 0.12},
        "pre": [("light_flicker", {"x": 0.49, "y": 0.43, "radius": 0.10, "strength": 0.35, "seed": 3}),
                ("light_flicker", {"x": 0.48, "y": 0.08, "radius": 0.22, "strength": 0.12, "dips": True, "seed": 4})],
        "post": [("dust_motes", {"count": 45, "strength": 0.25})],
        "finish": {"grain": 0.014},
    },
    "ferry_night": {
        "camera": {"zoom": 1.07, "sway_px": 2.5, "roll_deg": 0.7, "heave_px": 6, "roll_sec": 8.6},
        "pre": [("water_shimmer", {"region": (0.30, 0.15, 1.0, 0.85), "amp_px": 2.2, "sec": 3.3}),
                ("glow_pulse", {"x": 0.66, "y": 0.30, "radius": 0.24, "strength": 0.16, "sec": 7.5, "bgr": (0.8, 0.95, 0.55)})],
        "post": [("rain_streaks", {"count": 140, "strength": 0.05})],
        "finish": {"grain": 0.016, "vignette": 0.28},
    },
    "north_atlantic_1915": {
        "camera": {"zoom": 1.08, "sway_px": 2.0, "roll_deg": 1.1, "heave_px": 9, "roll_sec": 9.2},
        "pre": [("water_shimmer", {"region": (0.32, 0.38, 1.0, 1.0), "amp_px": 2.6, "sec": 2.7, "dark_only": False})],
        "post": [("fog_drift", {"y0": 0.15, "y1": 0.6, "density": 0.22, "speed": 1.0}),
                 ("rain_streaks", {"count": 180, "strength": 0.06, "angle": 0.35})],
        "finish": {"grain": 0.014},
    },
    "fern_fog": {
        "camera": {"zoom": 1.06, "sway_px": 1.5, "rot_deg": 0.08, "push": 0.03},
        "pre": [],
        "post": [("fog_drift", {"y0": 0.1, "y1": 0.95, "density": 0.32, "speed": 0.6, "bgr": (0.9, 0.95, 0.92)}),
                 ("dust_motes", {"count": 60, "strength": 0.3, "seed": 33}),
                 ("rain_streaks", {"count": 120, "strength": 0.05, "angle": 0.05})],
        "finish": {"grain": 0.013},
    },
    "second_moon": {
        "camera": {"zoom": 1.05, "sway_px": 1.2, "rot_deg": 0.05, "push": 0.025},
        "pre": [("light_flicker", {"x": 0.33, "y": 0.29, "radius": 0.07, "strength": 0.3, "seed": 6}),
                ("light_flicker", {"x": 0.77, "y": 0.40, "radius": 0.06, "strength": 0.4, "dips": True, "seed": 7}),
                ("glow_pulse", {"x": 0.48, "y": 0.46, "radius": 0.05, "strength": 0.10, "sec": 10.0, "bgr": (0.9, 0.92, 1.0)})],
        "post": [],
        "finish": {"grain": 0.014},
    },
    "eldritch_lighthouse": {
        "camera": {"zoom": 1.06, "sway_px": 3.0, "rot_deg": 0.15},
        "pre": [("light_flicker", {"x": 0.477, "y": 0.247, "radius": 0.07, "strength": 0.5, "dips": True, "seed": 12}),
                ("glow_pulse", {"x": 0.65, "y": 0.28, "radius": 0.05, "strength": 0.09, "sec": 9.0, "bgr": (0.75, 0.95, 1.0)}),
                ("water_shimmer", {"region": (0.30, 0.48, 1.0, 0.78), "amp_px": 2.4, "sec": 3.1, "dark_only": False})],
        "post": [("fog_drift", {"y0": 0.05, "y1": 0.75, "density": 0.24, "speed": 0.8, "bgr": (0.85, 0.88, 0.9)}),
                 ("rain_streaks", {"count": 140, "strength": 0.05, "angle": 0.3})],
        "finish": {"grain": 0.016, "vignette": 0.28},
    },
    "chapel_fire": {
        "camera": {"zoom": 1.05, "sway_px": 2.0, "rot_deg": 0.1},
        "pre": [("light_flicker", {"x": 0.42, "y": 0.80, "radius": 0.45, "strength": 0.16, "seed": 13}),
                ("light_flicker", {"x": 0.40, "y": 0.84, "radius": 0.07, "strength": 0.45, "seed": 14}),
                ("glow_pulse", {"x": 0.40, "y": 0.82, "radius": 0.22, "strength": 0.05, "sec": 2.5, "bgr": (0.2, 0.5, 1.0)})],
        "post": [("particles", {"count": 240, "direction": 1, "cycles": (4, 9), "size": (0.8, 2.2), "alpha": 0.55, "seed": 62}),
                 ("particles", {"count": 26, "direction": -1, "x_range": (0.37, 0.44), "y_range": (0.35, 0.86),
                                "cycles": (12, 20), "size": (0.6, 1.4), "alpha": 0.9, "bgr": (0.25, 0.6, 1.0),
                                "fade_with_travel": True, "blur": 0.6, "seed": 63})],
        "finish": {"grain": 0.016, "vignette": 0.3},
    },
    "indoor_pool": {
        "camera": {"zoom": 1.05, "sway_px": 2.5, "rot_deg": 0.1},
        "pre": [("water_shimmer", {"region": (0.30, 0.32, 0.98, 0.80), "amp_px": 1.8, "sec": 4.0}),
                ("light_flicker", {"x": 0.32, "y": 0.60, "radius": 0.08, "strength": 0.35, "dips": True, "seed": 8})],
        "post": [("dust_motes", {"count": 35, "strength": 0.2, "seed": 35})],
        "finish": {"grain": 0.016, "vignette": 0.3},
    },
}


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    render(sys.argv[1], sys.argv[2], sys.argv[3],
           float(sys.argv[4]) if len(sys.argv) > 4 else 10.0,
           int(sys.argv[5]) if len(sys.argv) > 5 else 1280)
