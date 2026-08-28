# Apply this overlay

Copy the contents of this ZIP into the root of `anhpt-official-buckets`
and overwrite existing files.

Then remove the old PowerShell builder:

```bash
git rm scripts/Build-Bucket.ps1
```

Also remove any `bucket-entry.json` files if you created them:

```bash
find main -name bucket-entry.json -delete
```

On Windows PowerShell:

```powershell
Get-ChildItem main -Recurse -Filter bucket-entry.json | Remove-Item
```

The new metadata model is:

- `workout.yaml`: `name`, `description`, `tags` and the actual workout.
- `manifest.json`: package `id`, package `version`, `minAppVersion`.
- `scripts/build_bucket.py`: builds ZIPs, hashes them, and regenerates `main/bucket.json`.
- `.github/workflows/release-bucket.yml`: builds and publishes on every push/merge to `main`.

Local test:

```bash
python -m pip install PyYAML
python scripts/build_bucket.py --release-tag local-test
```
