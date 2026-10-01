#!/usr/bin/env python3
"""
Cover image generation for DroneMill with a fallback chain.

Tries several image models in order:
- cf:<model>  Cloudflare Workers AI. Free up to 10,000 neurons a day (one cover uses about
              1,400 with flux-2-klein, 4,000 with lucid-origin). Needs CLOUDFLARE_ACCOUNT_ID
              and CLOUDFLARE_API_TOKEN (Workers AI permission) in .env.
- or:<model>  OpenRouter, paid from prepaid credit. Needs OPENROUTER_API_KEY.
A provider without credentials is skipped, a model OpenRouter no longer lists is skipped,
a failing model falls through to the next one, and an exhausted OpenRouter balance or
Cloudflare daily allowance stops that provider. The caller falls back to the cover bank in
images/fresh when this returns None.

Order comes from IMAGE_MODELS in .env (comma separated) or DEFAULT_CHAIN below.

Usage:
  python3 scripts/cover_generator.py --check                 # models available + credit left
  python3 scripts/cover_generator.py "<prompt>" out.png      # generate one cover
"""

import base64
import json
import os
import re
import subprocess
import sys
import time

import requests

DEFAULT_CHAIN = [
    "cf:@cf/black-forest-labs/flux-2-klein-9b",  # free daily allowance, 1536x864
    "cf:@cf/leonardo/lucid-origin",              # free daily allowance, photoreal, 1344x768
    "or:google/gemini-3.1-flash-image",          # paid: stable release of the Gemini image model
    "or:google/gemini-3.1-flash-lite-image",     # paid: cheaper Gemini
    "or:openai/gpt-5-image-mini",                # paid: different provider, in case Google is down
]
CF_SIZES = {
    "@cf/black-forest-labs/flux-2-klein-9b": (1536, 864),
    "@cf/leonardo/lucid-origin": (1344, 768),
}
MIN_WIDTH = 1024
LOW_CREDIT_USD = 1.0


def _key():
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def _cf_creds():
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    return (acct, token) if acct and token else (None, None)


def _cf_creds_problem():
    """Describe a misconfiguration without ever printing the values."""
    acct, token = _cf_creds()
    if acct is None:
        return None
    if not re.fullmatch(r"[0-9a-f]{32}", acct):
        return ("CLOUDFLARE_ACCOUNT_ID is not an account ID (expected 32 hex characters"
                + ("; it looks like an API token" if acct.startswith("cf") and "_" in acct else "") + ")")
    if re.fullmatch(r"[0-9a-f]{32}", token):
        return "CLOUDFLARE_API_TOKEN looks like an account ID; the two values may be swapped"
    return None


def _cf_error(res):
    """Cloudflare error code and message only; the response can echo the request path."""
    try:
        errs = res.json().get("errors") or []
        msg = "; ".join(f"{e.get('code')}: {e.get('message', '')}" for e in errs)
    except ValueError:
        msg = res.text
    acct, token = _cf_creds()
    for secret in (acct, token):
        if secret:
            msg = msg.replace(secret, "<redacted>")
    return re.sub(r"/accounts/[^/\s]+", "/accounts/<redacted>", msg)[:160]


def model_chain():
    env = os.environ.get("IMAGE_MODELS", "").strip()
    chain = [m.strip() for m in env.split(",") if m.strip()] if env else list(DEFAULT_CHAIN)
    # entries without a provider prefix are OpenRouter ids (older .env files)
    return [m if m.startswith(("cf:", "or:")) else f"or:{m}" for m in chain]


def listed_models():
    """Image-capable model ids OpenRouter lists right now, or None if the list is unreachable."""
    try:
        res = requests.get("https://openrouter.ai/api/v1/models", timeout=20)
        res.raise_for_status()
        ids = set()
        for m in res.json().get("data", []):
            if "image" in ((m.get("architecture") or {}).get("output_modalities") or []):
                ids.add(m["id"])
        return ids
    except Exception:
        return None


def credits_left():
    """Remaining OpenRouter credit in USD, or None if it cannot be read."""
    if not _key():
        return None
    try:
        res = requests.get("https://openrouter.ai/api/v1/credits",
                           headers={"Authorization": f"Bearer {_key()}"}, timeout=20)
        res.raise_for_status()
        d = res.json().get("data", {})
        return float(d.get("total_credits", 0)) - float(d.get("total_usage", 0))
    except Exception:
        return None


def health(log=print):
    """One line per issue: no provider configured, OpenRouter model gone, low credit.
    Returns True if at least one provider can generate."""
    chain = model_chain()
    problem = _cf_creds_problem()
    if problem:
        log(f"🛑 Covers: {problem}. Fix .env; Cloudflare is skipped until then.")
    cf_ok = _cf_creds()[0] is not None and not problem and any(m.startswith("cf:") for m in chain)
    or_ok = bool(_key()) and any(m.startswith("or:") for m in chain)
    if not cf_ok and not or_ok:
        log("🛑 Covers: no image provider configured (CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN or "
            "OPENROUTER_API_KEY in .env); only the images/fresh bank can be used.")
        return False
    if or_ok:
        listed = listed_models()
        or_models = [m[3:] for m in chain if m.startswith("or:")]
        if listed is not None:
            gone = [m for m in or_models if m not in listed]
            if gone:
                log(f"⚠️ Covers: no longer listed on OpenRouter, will be skipped: {', '.join(gone)}")
        left = credits_left()
        if left is not None and left < LOW_CREDIT_USD:
            log(f"⚠️ Covers: only ${left:.2f} OpenRouter credit left"
                + ("; Cloudflare stays the primary provider." if cf_ok else ". Top up to keep covers generating."))
    return True


def _image_width(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return 0


def _save_checked(raw, out_path):
    with open(out_path, "wb") as f:
        f.write(raw)
    width = _image_width(out_path)
    if width < MIN_WIDTH:
        os.remove(out_path)
        return False, f"image too small ({width}px wide)"
    return True, "ok"


FLUX_STYLE = ("amateur iPhone photo, candid snapshot, slightly tilted horizon, slight motion blur, "
              "high ISO grain, uneven light, unedited, realistic textures")


def flux_prompt(prompt):
    """FLUX models follow short, concrete, positive descriptions and tend to draw whatever a
    negation mentions ("no people" adds people). Keep the scene, drop the long style block and
    every negative sentence, then add a short snapshot style."""
    if not prompt.strip().startswith("Take the phone out of your pocket"):
        return prompt  # older themes keep their own (cinematic) style untouched
    scene = re.sub(r"^Take the phone out of your pocket and snap a quick photo of\s*", "", prompt.strip())
    scene = scene.split("Simple iPhone")[0]
    keep = []
    for sentence in re.split(r"(?<=\.)\s+", scene):
        low = sentence.strip().lower()
        if not low or low.startswith(("no ", "not ", "more felt than seen", "face not visible")):
            continue
        keep.append(sentence.strip().rstrip("."))
    scene = ", ".join(keep)
    scene = re.sub(r",?\s*face not visible", "", scene)
    return f"{scene}. {FLUX_STYLE}."


def _try_cloudflare(model, prompt, out_path):
    """Returns (ok, reason). reason 'credits' means the free daily allowance is used up."""
    acct, token = _cf_creds()
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {token}"}
    width, height = CF_SIZES.get(model, (1344, 768))
    if "flux" in model:
        prompt = flux_prompt(prompt)
    try:
        if "flux-2" in model:
            # FLUX.2 models take multipart form data
            fields = {"prompt": (None, prompt), "width": (None, str(width)), "height": (None, str(height))}
            res = requests.post(url, headers=headers, files=fields, timeout=180)
        else:
            res = requests.post(url, headers=headers, json={"prompt": prompt, "width": width, "height": height,
                                                            "steps": 24}, timeout=180)
    except requests.RequestException as e:
        return False, f"network: {e}"
    if res.status_code == 429 or ("neurons" in res.text.lower() and res.status_code >= 400):
        return False, "credits"
    if res.status_code >= 400:
        return False, f"http {res.status_code}: {_cf_error(res)}"
    try:
        image_b64 = res.json()["result"]["image"]
    except (KeyError, ValueError, TypeError):
        return False, "response had no image"
    return _save_checked(base64.b64decode(image_b64), out_path)


def _try_model(model, prompt, out_path):
    """OpenRouter. Returns (ok, reason). reason 'credits' stops the provider."""
    data = {
        "model": model,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": "16:9"},
    }
    headers = {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"}
    for attempt in range(2):
        try:
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=180)
        except requests.RequestException as e:
            return False, f"network: {e}"
        if res.status_code == 402:
            return False, "credits"
        if res.status_code == 429 and attempt == 0:
            time.sleep(20)
            continue
        if res.status_code >= 400:
            return False, f"http {res.status_code}: {res.text[:160]}"
        try:
            message = res.json()["choices"][0]["message"]
            url = message["images"][0]["image_url"]["url"]
        except (KeyError, IndexError, ValueError):
            return False, "response had no image"
        raw = base64.b64decode(url.split(",", 1)[1]) if url.startswith("data:") else requests.get(url, timeout=60).content
        return _save_checked(raw, out_path)
    return False, "rate limited"


def generate_cover(prompt, out_path, log=print):
    """Generate a cover with the first model in the chain that works. Returns (path, model) or (None, None)."""
    listed = None
    exhausted = set()
    for entry in model_chain():
        provider, model = entry.split(":", 1)
        if provider in exhausted:
            continue
        if provider == "cf":
            if _cf_creds()[0] is None or _cf_creds_problem():
                continue
            ok, reason = _try_cloudflare(model, prompt, out_path)
        else:
            if not _key():
                continue
            if listed is None:
                listed = listed_models() or set()
            if listed and model not in listed:
                continue
            ok, reason = _try_model(model, prompt, out_path)
        if ok:
            log(f"🖼️ Cover generated with {entry} -> {out_path}")
            return out_path, entry
        log(f"WARN: cover model {entry} failed ({reason})")
        if reason == "credits":
            exhausted.add(provider)
            log("⚠️ Covers: " + ("Cloudflare free daily allowance used up" if provider == "cf"
                                 else "OpenRouter credit exhausted") + "; skipping that provider.")
    return None, None


if __name__ == "__main__":
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_file = os.path.join(root, ".env")
    if os.path.exists(env_file):
        for line in open(env_file, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        listed = listed_models()
        cf = _cf_creds()[0] is not None
        problem = _cf_creds_problem()
        for m in model_chain():
            if m.startswith("cf:"):
                print(f"{m}: {('MISCONFIGURED' if problem else 'configured') if cf else 'no Cloudflare credentials'}")
            else:
                state = "unknown" if listed is None else ("listed" if m[3:] in listed else "NOT LISTED")
                print(f"{m}: {state}{'' if _key() else ' (no OpenRouter key)'}")
        left = credits_left()
        print("OpenRouter credit left:", "unknown (no key?)" if left is None else f"${left:.2f}")
        health()
    elif len(sys.argv) > 2:
        path, model = generate_cover(sys.argv[1], sys.argv[2])
        print(json.dumps({"path": path, "model": model}))
    else:
        print(__doc__)
