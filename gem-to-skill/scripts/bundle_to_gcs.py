#!/usr/bin/env python3
"""Bundle a generated skill folder and upload it to Google Cloud Storage.

This is the final step of the gem-to-skill workflow: take a converted skill
(e.g. `converted-skills/<name>/`), zip it into a single bundle, and store it in
a GCS bucket the user names with a `gs://` path.

It is designed to run inside the agent's code sandbox. GCS upload needs either
the Google client library or the gcloud CLI, so the script tries them in order
and falls back gracefully:

    1. `google-cloud-storage` Python library (uses Application Default Creds)
    2. `gcloud storage cp`
    3. `gsutil cp`

Everything else is stdlib only.

Usage:
    # interactive — prompts for the gs:// destination
    python bundle_to_gcs.py converted-skills/hr-onboarding-drive

    # non-interactive (for the agent) — destination supplied
    python bundle_to_gcs.py converted-skills/hr-onboarding-drive \
        --dest gs://my-bucket/skills/

    # name the bundle yourself, or use the .skill extension
    python bundle_to_gcs.py <skill_dir> --dest gs://my-bucket/skills/ --ext skill

Destination semantics:
    gs://bucket/prefix/          -> object = gs://bucket/prefix/<name>.<ext>
    gs://bucket/path/file.zip    -> object = exactly that
    gs://bucket                  -> object = gs://bucket/<name>.<ext>
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

GS_RE = re.compile(r"^gs://([a-z0-9][-_.a-z0-9]{1,221})(/.*)?$")


def parse_gs_uri(uri: str):
    """Validate a gs:// URI and split it into (bucket, object_prefix)."""
    m = GS_RE.match(uri.strip())
    if not m:
        raise ValueError(
            f"Not a valid GCS path: {uri!r}. Expected gs://bucket or gs://bucket/path/"
        )
    bucket = m.group(1)
    obj = (m.group(2) or "").lstrip("/")
    return bucket, obj


def resolve_object_name(obj_prefix: str, default_filename: str) -> str:
    """Decide the final object name from the user's prefix + a default name."""
    if not obj_prefix or obj_prefix.endswith("/"):
        return obj_prefix + default_filename
    # If it already looks like a bundle filename, use it as-is; else treat as a
    # prefix and append the default filename.
    if obj_prefix.lower().endswith((".zip", ".skill", ".tar.gz", ".tgz")):
        return obj_prefix
    return obj_prefix + "/" + default_filename


def make_bundle(skill_dir: str, ext: str) -> str:
    """Zip the skill folder into a temp file. The archive's top-level entry is
    the skill folder name, so unzipping yields a clean, named skill folder.

    `ext` is just the file extension on the bundle (`zip` or `skill`); a
    `.skill` file is a zip, so the archive format is identical either way.
    """
    skill_dir = os.path.abspath(skill_dir.rstrip("/"))
    if not os.path.isdir(skill_dir):
        raise NotADirectoryError(f"Not a skill folder: {skill_dir}")
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        raise FileNotFoundError(f"No SKILL.md found in {skill_dir} — is this a skill folder?")

    name = os.path.basename(skill_dir)
    tmp_dir = tempfile.mkdtemp(prefix="gem-skill-bundle-")
    bundle_path = os.path.join(tmp_dir, f"{name}.{ext}")

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(skill_dir):
            for fn in files:
                abs_path = os.path.join(root, fn)
                # arcname keeps the skill folder as the top-level directory.
                arcname = os.path.join(name, os.path.relpath(abs_path, skill_dir))
                zf.write(abs_path, arcname)
    return bundle_path


# --- Upload backends --------------------------------------------------------

def _upload_with_library(bundle_path, bucket, object_name) -> bool:
    try:
        from google.cloud import storage  # type: ignore
    except Exception:
        return False
    client = storage.Client()
    blob = client.bucket(bucket).blob(object_name)
    blob.upload_from_filename(bundle_path)
    return True


def _upload_with_cli(bundle_path, dest_uri) -> bool:
    for cmd in (["gcloud", "storage", "cp"], ["gsutil", "cp"]):
        if shutil.which(cmd[0]) is None:
            continue
        try:
            subprocess.run(cmd + [bundle_path, dest_uri], check=True)
            return True
        except subprocess.CalledProcessError as exc:
            print(f"  {cmd[0]} failed (exit {exc.returncode}); trying next backend.",
                  file=sys.stderr)
    return False


def upload(bundle_path, bucket, object_name) -> str:
    """Upload the bundle, returning the final gs:// URI. Tries library then CLI."""
    dest_uri = f"gs://{bucket}/{object_name}"
    if _upload_with_library(bundle_path, bucket, object_name):
        return dest_uri
    if _upload_with_cli(bundle_path, dest_uri):
        return dest_uri
    raise RuntimeError(
        "Could not upload to GCS. None of these were usable:\n"
        "  - the `google-cloud-storage` Python library (pip install google-cloud-storage)\n"
        "  - the `gcloud` CLI\n"
        "  - the `gsutil` CLI\n"
        "Also make sure credentials are available (Application Default Credentials,\n"
        "e.g. `gcloud auth application-default login`, or a service account in the sandbox)."
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bundle a skill folder and upload it to GCS.")
    ap.add_argument("skill_dir", help="Path to the generated skill folder (contains SKILL.md).")
    ap.add_argument("--dest", help="GCS destination, e.g. gs://my-bucket/skills/ . "
                                   "If omitted, you'll be prompted.")
    ap.add_argument("--ext", choices=["zip", "skill"], default="zip",
                    help="Bundle extension (default: zip). A .skill file is just a zip.")
    ap.add_argument("--keep-local", metavar="DIR",
                    help="Also copy the bundle to this local directory before uploading.")
    args = ap.parse_args(argv)

    dest = args.dest
    if not dest:
        try:
            dest = input("Enter the GCS destination (gs://bucket/path/): ").strip()
        except EOFError:
            ap.error("No --dest given and no interactive input available.")

    bucket, obj_prefix = parse_gs_uri(dest)

    bundle_path = make_bundle(args.skill_dir, args.ext)
    default_filename = os.path.basename(bundle_path)
    object_name = resolve_object_name(obj_prefix, default_filename)

    print(f"Bundled {args.skill_dir} -> {os.path.basename(bundle_path)} "
          f"({os.path.getsize(bundle_path)} bytes)")

    if args.keep_local:
        os.makedirs(args.keep_local, exist_ok=True)
        local_copy = os.path.join(args.keep_local, default_filename)
        shutil.copy2(bundle_path, local_copy)
        print(f"Local copy: {local_copy}")

    final_uri = upload(bundle_path, bucket, object_name)
    print(f"Uploaded: {final_uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
