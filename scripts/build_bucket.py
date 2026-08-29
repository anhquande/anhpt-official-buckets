#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import yaml


def fail(message: str) -> None:
    raise SystemExit(message)


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Failed to read {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path} must contain a JSON object")
    return data


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Failed to read {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path} must contain a YAML object at the root")
    return data


def require(mapping: dict, key: str, source: Path):
    value = mapping.get(key)
    if value is None or value == "":
        fail(f"{source} is missing required field '{key}'")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_directory(source_dir: Path, output_file: Path) -> None:
    with zipfile.ZipFile(
        output_file,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name == "generate_media.py":
                continue
            archive.write(path, path.relative_to(source_dir).as_posix())


def existing_download_counts(bucket_path: Path) -> dict[str, int]:
    if not bucket_path.is_file():
        return {}
    try:
        bucket = json.loads(bucket_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    workouts = bucket.get("workouts", []) if isinstance(bucket, dict) else []
    counts = {}
    for workout in workouts:
        if not isinstance(workout, dict):
            continue
        workout_id = workout.get("id")
        count = workout.get("downloadCount", 0)
        if isinstance(workout_id, str) and isinstance(count, int) and count >= 0:
            counts[workout_id] = count
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build AnhPT workout packages and main/bucket.json"
    )
    parser.add_argument("--source-dir", default="main")
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument(
        "--repository",
        default="anhquande/anhpt-official-buckets",
    )
    parser.add_argument("--release-tag", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    source_root = repo_root / args.source_dir
    output_root = repo_root / args.output_dir
    bucket_path = source_root / "bucket.json"

    if not source_root.is_dir():
        fail(f"Source directory not found: {source_root}")

    download_counts = existing_download_counts(bucket_path)

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    entries = []

    for workout_dir in sorted(p for p in source_root.iterdir() if p.is_dir()):
        manifest_path = workout_dir / "manifest.json"
        if not manifest_path.is_file():
            print(
                f"Skipping {workout_dir.name}: manifest.json not found",
                file=sys.stderr,
            )
            continue

        manifest = load_json(manifest_path)
        workout_file = str(manifest.get("workoutFile", "workout.yaml"))
        workout_path = workout_dir / workout_file
        if not workout_path.is_file():
            fail(f"Workout file not found: {workout_path}")

        workout = load_yaml(workout_path)

        package_id = str(require(manifest, "id", manifest_path))
        package_version = str(require(manifest, "version", manifest_path))
        min_app_version = str(require(manifest, "minAppVersion", manifest_path))

        name = str(require(workout, "name", workout_path))
        description = str(workout.get("description") or "")
        tags = workout.get("tags") or []
        if not isinstance(tags, list):
            fail(f"{workout_path}: tags must be a list")

        package_name = f"{package_id}-{package_version}.anhpt.zip"
        package_path = output_root / package_name

        print(f"Building {package_name}")
        package_directory(workout_dir, package_path)

        entry = {
            "id": package_id,
            "name": name,
            "description": description,
            "version": package_version,
            "packageUrl": (
                f"https://github.com/{args.repository}/releases/download/"
                f"{args.release_tag}/{package_name}"
            ),
            "sha256": sha256(package_path),
            "size": package_path.stat().st_size,
            "tags": [str(tag) for tag in tags],
            "minAppVersion": min_app_version,
            "downloadCount": download_counts.get(package_id, 0),
        }

        if manifest.get("author"):
            entry["author"] = str(manifest["author"])

        entries.append(entry)

    if not entries:
        fail("No workouts found")

    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        fail("Duplicate workout id found in manifests")

    bucket = {
        "schemaVersion": 1,
        "name": "AnhPT Official Workouts",
        "workouts": sorted(entries, key=lambda item: item["id"]),
    }

    bucket_path.write_text(
        json.dumps(bucket, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {bucket_path}")
    for package in sorted(output_root.glob("*.anhpt.zip")):
        print(f"Generated {package}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
