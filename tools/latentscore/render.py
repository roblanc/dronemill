import argparse
import json
from pathlib import Path

import latentscore as ls


def main():
    parser = argparse.ArgumentParser(description="Render title-conditioned ambient audio.")
    parser.add_argument("prompt")
    parser.add_argument("output")
    parser.add_argument("--duration", type=float, default=180)
    args = parser.parse_args()

    update = ls.MusicConfigUpdate(
        tempo="very_slow",
        brightness="very_dark",
        space="vast",
        density=3,
        motion="slow",
        stereo="wide",
        echo="heavy",
    )
    audio = ls.render(args.prompt, update=update, duration=args.duration)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    audio.save(str(output))

    metadata = {
        "prompt": args.prompt,
        "duration_seconds": args.duration,
        "sample_rate": ls.SAMPLE_RATE,
        "generator": "latentscore 0.1.8",
        "reproducible": False,
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
