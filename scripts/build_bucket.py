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


def media_type(path: str) -> str:
    extension = Path(path).suffix.lower()
    if extension == ".gif":
        return "animation"
    if extension in {".jpg", ".jpeg", ".png", ".webp"}:
        return "image"
    return "video"


def artwork_category(tags: list) -> str:
    first_tag = str(tags[0]).strip().lower() if tags else ""
    categories = {
        "yoga": "yoga",
        "yogo": "yoga",
        "mobility": "yoga",
        "hiit": "hiit",
        "cardio": "hiit",
        "meditation": "meditation",
        "mediation": "meditation",
        "thiền": "meditation",
        "thien": "meditation",
        "breathing": "meditation",
        "tabata": "tabata",
        "interval": "tabata",
        "karate": "martial-arts",
        "martial": "martial-arts",
        "martial-arts": "martial-arts",
        "kata": "martial-arts",
    }
    return categories.get(first_tag, "strength")


def demonstration_assets(workout_dir: Path, workout: dict) -> list[dict]:
    assets = []
    seen = set()
    exercises = workout.get("exercises") or []
    if not isinstance(exercises, list):
        fail(f"{workout_dir / 'workout.yaml'}: exercises must be a list")

    for raw_exercise in exercises:
        if not isinstance(raw_exercise, dict):
            continue
        reference = raw_exercise.get("demo_media") or raw_exercise.get("demo_video")
        if not isinstance(reference, str) or reference.startswith("sha256:"):
            continue
        normalized = reference.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            fail(f"Unsafe demonstration media path: {reference}")
        if normalized in seen:
            continue
        media_path = workout_dir / normalized
        if not media_path.is_file():
            fail(f"Demonstration media not found: {media_path}")
        digest = sha256(media_path)
        assets.append({
            "id": f"sha256:{digest}",
            "reference": reference,
            "type": media_type(reference),
            "path": normalized,
        })
        seen.add(normalized)
    return assets


def package_assets(
    source_dir: Path,
    output_file: Path,
    manifest: dict,
    workout: dict,
    workout_file: str,
    excluded_files: set[str],
) -> None:
    package_manifest = dict(manifest)
    assets = demonstration_assets(source_dir, workout)
    if assets:
        package_manifest["assets"] = assets

    with zipfile.ZipFile(
        output_file,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source_dir).as_posix()
            if (
                path.name in {"generate_media.py", "manifest.json"}
                or relative == workout_file
                or relative in excluded_files
            ):
                continue
            archive.write(path, relative)
        archive.writestr(
            "manifest.json",
            json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n",
        )


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

        artifact_stem = f"{package_id}-{package_version}"
        workout_name = f"{artifact_stem}.workout.yaml"
        assets_name = f"{artifact_stem}.assets.zip"
        category = artwork_category(tags)
        custom_artwork = {
            "thumbnail": manifest.get("thumbnailFile"),
            "featureImage": manifest.get("featureImageFile"),
        }
        artwork_sources = {}
        excluded_files = set()
        for artwork, configured in custom_artwork.items():
            relative = str(configured) if configured else None
            if relative is None:
                folder = "thumbnail" if artwork == "thumbnail" else "feature"
                artwork_sources[artwork] = (
                    repo_root / "defaults" / "workout_artwork" / folder / f"{category}.webp"
                )
                continue
            normalized = relative.replace("\\", "/")
            if normalized.startswith("/") or ".." in normalized.split("/"):
                fail(f"Unsafe {artwork} path: {relative}")
            source = workout_dir / normalized
            if not source.is_file():
                fail(f"{artwork} file not found: {source}")
            if source.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                fail(f"{artwork} must be a JPG, PNG, or WebP image: {source}")
            artwork_sources[artwork] = source
            excluded_files.add(normalized)
        workout_output_path = output_root / workout_name
        assets_output_path = output_root / assets_name

        print(f"Building {workout_name} and {assets_name}")
        shutil.copyfile(workout_path, workout_output_path)
        package_assets(
            workout_dir,
            assets_output_path,
            manifest,
            workout,
            workout_file,
            excluded_files,
        )

        release_base = (
            f"https://github.com/{args.repository}/releases/download/"
            f"{args.release_tag}"
        )

        entry = {
            "id": package_id,
            "name": name,
            "description": description,
            "version": package_version,
            "workoutUrl": f"{release_base}/{workout_name}",
            "workoutSha256": sha256(workout_output_path),
            "workoutSize": workout_output_path.stat().st_size,
            "assetsUrl": f"{release_base}/{assets_name}",
            "assetsSha256": sha256(assets_output_path),
            "assetsSize": assets_output_path.stat().st_size,
            "tags": [str(tag) for tag in tags],
            "minAppVersion": min_app_version,
            "downloadCount": download_counts.get(package_id, 0),
        }

        if manifest.get("author"):
            entry["author"] = str(manifest["author"])

        for artwork, source in artwork_sources.items():
            if not source.is_file():
                fail(f"Default {artwork} file not found: {source}")
            suffix = source.suffix.lower()
            artwork_name = f"{artifact_stem}.{artwork}{suffix}"
            artwork_output = output_root / artwork_name
            shutil.copyfile(source, artwork_output)
            entry[f"{artwork}Url"] = f"{release_base}/{artwork_name}"
            entry[f"{artwork}Sha256"] = sha256(artwork_output)
            entry[f"{artwork}Size"] = artwork_output.stat().st_size

        entries.append(entry)

    if not entries:
        fail("No workouts found")

    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        fail("Duplicate workout id found in manifests")

    bucket = {
        "schemaVersion": 2,
        "name": "AnhPT Official Workouts",
        "workouts": sorted(entries, key=lambda item: item["id"]),
    }

    bucket_path.write_text(
        json.dumps(bucket, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {bucket_path}")
    for artifact in sorted(output_root.iterdir()):
        print(f"Generated {artifact}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
