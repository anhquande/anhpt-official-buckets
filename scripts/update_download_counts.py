#!/usr/bin/env python3
import argparse
import json
import os
import urllib.request
from pathlib import Path


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def fetch_releases(repository: str, token: str | None) -> list[dict]:
    releases = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repository}/releases"
            f"?per_page=100&page={page}"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "anhpt-download-stats",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise SystemExit("GitHub releases API returned an unexpected response")
        releases.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return releases


def match_workout_id(asset_name: str, workout_ids: list[str]) -> str | None:
    if not asset_name.endswith(".anhpt.zip"):
        return None
    matches = [
        workout_id
        for workout_id in workout_ids
        if asset_name.startswith(f"{workout_id}-")
    ]
    if not matches:
        return None
    return max(matches, key=len)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate GitHub Release asset downloads into bucket.json"
    )
    parser.add_argument("--bucket", default="main/bucket.json")
    parser.add_argument(
        "--repository",
        default=os.environ.get(
            "GITHUB_REPOSITORY", "anhquande/anhpt-official-buckets"
        ),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    bucket_path = repo_root / args.bucket
    bucket = load_json(bucket_path)
    workouts = bucket.get("workouts")
    if not isinstance(workouts, list):
        raise SystemExit("bucket.json must contain a workouts list")

    workout_ids = [
        workout.get("id")
        for workout in workouts
        if isinstance(workout, dict) and isinstance(workout.get("id"), str)
    ]
    counts = {workout_id: 0 for workout_id in workout_ids}

    releases = fetch_releases(args.repository, os.environ.get("GH_TOKEN"))
    for release in releases:
        assets = release.get("assets", []) if isinstance(release, dict) else []
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = asset.get("name")
            count = asset.get("download_count")
            if not isinstance(name, str) or not isinstance(count, int):
                continue
            workout_id = match_workout_id(name, workout_ids)
            if workout_id is not None:
                counts[workout_id] += count

    for workout in workouts:
        if isinstance(workout, dict) and workout.get("id") in counts:
            workout["downloadCount"] = counts[workout["id"]]

    bucket_path.write_text(
        json.dumps(bucket, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for workout_id in sorted(counts):
        print(f"{workout_id}: {counts[workout_id]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
