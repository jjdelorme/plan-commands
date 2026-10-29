"""Zero-dependency CLI utility to perform operations on the Gemini Enterprise Agent Platform Skill Registry."""

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
EXCLUDED_FILES = {".DS_Store", "Thumbs.db"}
EXCLUDED_EXTS = {".pyc", ".pyo"}


def _gcloud_config(key):
  try:
    res = subprocess.run(
        ["gcloud", "config", "get-value", key],
        capture_output=True,
        text=True,
        check=True,
    )
    val = res.stdout.strip()
    if val and val != "(unset)":
      return val
  except Exception:
    pass
  return None


def resolve_project(cli_project=None):
  return (
      cli_project
      or os.environ.get("GCP_PROJECT_ID")
      or os.environ.get("GOOGLE_CLOUD_PROJECT")
      or os.environ.get("CLOUDSDK_CORE_PROJECT")
      or _gcloud_config("project")
  )


def resolve_location(cli_location=None):
  return (
      cli_location
      or os.environ.get("GCP_LOCATION")
      or os.environ.get("GOOGLE_CLOUD_REGION")
      or os.environ.get("CLOUDSDK_COMPUTE_REGION")
      or _gcloud_config("ai/region")
      or _gcloud_config("compute/region")
      or "us-central1"
  )


def get_access_token():
  for cmd in (
      ["gcloud", "auth", "print-access-token"],
      ["gcloud", "auth", "application-default", "print-access-token"],
  ):
    try:
      result = subprocess.run(cmd, capture_output=True, text=True, check=True)
      token = result.stdout.strip()
      if token:
        return token
    except Exception:
      pass

  try:
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _ = google.auth.default()
    credentials.refresh(Request())
    if credentials.token:
      return credentials.token
  except Exception as e:
    print(
        f"ERROR: Could not obtain Google Cloud access token via gcloud or google-auth ({e}).\n"
        "Run 'gcloud auth login' or 'gcloud auth application-default login'.",
        file=sys.stderr,
    )
    sys.exit(1)


def get_endpoint(region):
  return f"{region}-aiplatform.googleapis.com"


def http_json(method, url, headers=None, payload=None):
  req_headers = dict(headers or {})
  data = None
  if payload is not None:
    data = json.dumps(payload).encode("utf-8")
    req_headers.setdefault("Content-Type", "application/json")

  req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
  try:
    with urllib.request.urlopen(req, timeout=60) as resp:
      body = resp.read().decode("utf-8")
      return resp.status, body, (json.loads(body) if body else {})
  except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    try:
      parsed = json.loads(body)
    except Exception:
      parsed = None
    return e.code, body, parsed


def build_zip_bytes(zip_path=None, folder_path=None):
  if zip_path:
    with open(zip_path, "rb") as f:
      return f.read()
  if folder_path:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
      for root, dirs, files in os.walk(folder_path):
        dirs[:] = [
            d for d in sorted(dirs)
            if d not in EXCLUDED_DIRS and not d.endswith(".egg-info")
        ]
        for file in sorted(files):
          if file in EXCLUDED_FILES or os.path.splitext(file)[1] in EXCLUDED_EXTS:
            continue
          file_path = os.path.join(root, file)
          arcname = os.path.relpath(file_path, folder_path)
          zf.write(file_path, arcname)
    return zip_buffer.getvalue()
  raise ValueError("Must provide either --zip-file or --folder")


def parse_skill_metadata_from_zip(zip_bytes):
  """Extracts skill_id (name), display_name (# Heading), and description from SKILL.md inside zip_bytes."""
  meta = {"skill_id": None, "display_name": None, "description": None}
  try:
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
      skill_md_name = next(
          (n for n in zf.namelist() if os.path.basename(n) == "SKILL.md"),
          None,
      )
      if not skill_md_name:
        return meta
      content = zf.read(skill_md_name).decode("utf-8", errors="replace")
  except Exception:
    return meta

  fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
  body = content
  if fm_match:
    fm_text, body = fm_match.group(1), fm_match.group(2)
    name_m = re.search(r"^name:\s*['\"]?([^\n'\"]+)['\"]?", fm_text, re.MULTILINE)
    if name_m:
      meta["skill_id"] = name_m.group(1).strip()

    desc_block = re.search(
        r"^description:\s*[>|]-?\s*\n((?:[ \t]+[^\n]+\n?)+)",
        fm_text,
        re.MULTILINE,
    )
    if desc_block:
      lines = [line.strip() for line in desc_block.group(1).splitlines() if line.strip()]
      meta["description"] = " ".join(lines)
    else:
      desc_inline = re.search(
          r"^description:\s*['\"]?([^\n'\"]+)['\"]?", fm_text, re.MULTILINE
      )
      if desc_inline:
        meta["description"] = desc_inline.group(1).strip()

  h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
  if h1_match:
    meta["display_name"] = h1_match.group(1).strip()
  elif meta["skill_id"]:
    meta["display_name"] = meta["skill_id"].replace("-", " ").replace("_", " ").title()

  return meta


def summarize_zip_field(data, include_zip=False, extract_to=None):
  """Summarizes or extracts zippedFilesystem so get/get-revision doesn't flood stdout with base64."""
  if not isinstance(data, dict) or "zippedFilesystem" not in data:
    return data

  b64_str = data.get("zippedFilesystem") or ""
  try:
    raw_bytes = base64.b64decode(b64_str)
    with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
      names = zf.namelist()
      if extract_to:
        os.makedirs(extract_to, exist_ok=True)
        zf.extractall(extract_to)
        print(f"Extracted {len(names)} files ({len(raw_bytes)} bytes) to {extract_to}")
    if not include_zip:
      out = dict(data)
      preview = ", ".join(names[:8]) + (f", ... (+{len(names) - 8} more)" if len(names) > 8 else "")
      out["zippedFilesystem"] = (
          f"<omitted base64 zip: {len(raw_bytes)} bytes, {len(names)} files [{preview}]"
          " (pass --include-zip for raw base64 or --extract-to DIR)>"
      )
      return out
  except Exception:
    pass
  return data


def poll_operation(op_name, location, token, wait=True, timeout=120):
  endpoint = get_endpoint(location)
  op_id = op_name.lstrip("/")
  url = f"https://{endpoint}/v1beta1/{op_id}"
  headers = {"Authorization": f"Bearer {token}"}

  start = time.time()
  while True:
    status, text, data = http_json("GET", url, headers=headers)
    if status >= 400:
      print(f"Error monitoring operation: {status} - {text}", file=sys.stderr)
      sys.exit(1)

    if not wait or (isinstance(data, dict) and data.get("done")):
      print("Operation Result:")
      print(json.dumps(data, indent=2))
      if isinstance(data, dict) and "error" in data:
        sys.exit(1)
      return data

    if time.time() - start >= timeout:
      print(f"Timeout ({timeout}s) waiting for operation {op_name}. Last state:")
      print(json.dumps(data, indent=2))
      sys.exit(1)

    time.sleep(2)


def upload(args):
  """Uploads a skill (and optionally falls back to update on 409 ALREADY_EXISTS)."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)
  zip_bytes = build_zip_bytes(args.zip_file, args.folder)
  inferred = parse_skill_metadata_from_zip(zip_bytes)

  skill_id = args.skill_id or inferred["skill_id"]
  display_name = args.display_name or inferred["display_name"]
  description = args.description or inferred["description"]

  missing_meta = [
      flag
      for flag, val in (
          ("--skill-id", skill_id),
          ("--display-name", display_name),
          ("--description", description),
      )
      if not val
  ]
  if missing_meta:
    print(
        f"ERROR: Could not infer {', '.join(missing_meta)} from SKILL.md. Please pass explicitly.",
        file=sys.stderr,
    )
    sys.exit(1)

  zipped_filesystem = base64.b64encode(zip_bytes).decode("utf-8")
  headers = {"Authorization": f"Bearer {token}"}
  payload = {
      "displayName": display_name,
      "description": description,
      "zippedFilesystem": zipped_filesystem,
  }

  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills?skillId={skill_id}"
  print(f"Uploading skill '{skill_id}' ({len(zip_bytes)} bytes zipped) to {args.project}/{args.location}...")
  status, text, data = http_json("POST", url, headers=headers, payload=payload)

  if status == 409 and not args.no_upsert:
    print(f"Skill '{skill_id}' already exists (409); automatically updating existing skill...")
    args.skill_id = skill_id
    args.display_name = display_name
    args.description = description
    return update_skill(args, _precomputed_zip_bytes=zip_bytes)

  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  print("Upload initiated:")
  print(json.dumps(data, indent=2))
  if args.wait and isinstance(data, dict) and data.get("name") and not data.get("done"):
    return poll_operation(data["name"], args.location, token, wait=True, timeout=args.timeout)
  return data


def update_skill(args, _precomputed_zip_bytes=None):
  """Updates an existing skill in the Skill Registry."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)

  zip_bytes = _precomputed_zip_bytes
  if zip_bytes is None and (args.zip_file or args.folder):
    zip_bytes = build_zip_bytes(args.zip_file, args.folder)

  inferred = parse_skill_metadata_from_zip(zip_bytes) if zip_bytes else {}
  skill_id = args.skill_id or inferred.get("skill_id")
  if not skill_id:
    print("ERROR: --skill-id is required (or must be present in SKILL.md).", file=sys.stderr)
    sys.exit(1)

  display_name = args.display_name or inferred.get("display_name")
  description = args.description or inferred.get("description")

  update_mask_parts = []
  payload = {}

  if display_name:
    update_mask_parts.append("displayName")
    payload["displayName"] = display_name

  if description:
    update_mask_parts.append("description")
    payload["description"] = description

  if zip_bytes is not None:
    update_mask_parts.append("zippedFilesystem")
    payload["zippedFilesystem"] = base64.b64encode(zip_bytes).decode("utf-8")

  if not update_mask_parts:
    print(
        "Error: must provide at least one field to update (--display-name,"
        " --description, --zip-file, --folder)",
        file=sys.stderr,
    )
    sys.exit(1)

  update_mask = ",".join(update_mask_parts)
  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills/{skill_id}?updateMask={update_mask}"
  headers = {"Authorization": f"Bearer {token}"}

  print(f"Updating skill '{skill_id}' (fields: {update_mask}) at {args.project}/{args.location}...")
  status, text, data = http_json("PATCH", url, headers=headers, payload=payload)

  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  print("Update initiated:")
  print(json.dumps(data, indent=2))
  if args.wait and isinstance(data, dict) and data.get("name") and not data.get("done"):
    return poll_operation(data["name"], args.location, token, wait=True, timeout=args.timeout)
  return data


def search(args):
  """Searches for skills in the Skill Registry."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)
  query_encoded = urllib.parse.quote(args.query)
  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills:retrieve?query={query_encoded}&topK={args.top_k}"
  headers = {"Authorization": f"Bearer {token}"}

  print(f"Searching skills at {args.project}/{args.location} with query '{args.query}'...")
  status, text, data = http_json("GET", url, headers=headers)
  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  print("Response:")
  print(json.dumps(data, indent=2))


def get_skill(args):
  """Gets a skill from the Skill Registry."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)
  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills/{args.skill_id}"
  headers = {"Authorization": f"Bearer {token}"}

  print(f"Getting skill '{args.skill_id}' at {args.project}/{args.location}...")
  status, text, data = http_json("GET", url, headers=headers)
  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  cleaned = summarize_zip_field(
      data, include_zip=args.include_zip, extract_to=args.extract_to
  )
  print("Response:")
  print(json.dumps(cleaned, indent=2))


def list_skills(args):
  """Lists skills in the Skill Registry."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)
  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills"
  headers = {"Authorization": f"Bearer {token}"}

  print(f"Listing skills at {args.project}/{args.location}...")
  status, text, data = http_json("GET", url, headers=headers)
  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  if isinstance(data, dict) and isinstance(data.get("skills"), list):
    data = dict(data)
    data["skills"] = [
        summarize_zip_field(s, include_zip=args.include_zip) for s in data["skills"]
    ]

  print("Response:")
  print(json.dumps(data, indent=2))


def delete_skill(args):
  """Deletes a skill from the Skill Registry."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)
  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills/{args.skill_id}"
  headers = {"Authorization": f"Bearer {token}"}

  print(f"Deleting skill '{args.skill_id}' at {args.project}/{args.location}...")
  status, text, data = http_json("DELETE", url, headers=headers)
  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  print("Delete initiated:")
  print(json.dumps(data, indent=2))
  if args.wait and isinstance(data, dict) and data.get("name") and not data.get("done"):
    return poll_operation(data["name"], args.location, token, wait=True, timeout=args.timeout)
  return data


def list_skill_revision(args):
  """Lists revisions of a skill in the Skill Registry."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)
  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills/{args.skill_id}/revisions"
  headers = {"Authorization": f"Bearer {token}"}

  print(f"Listing revisions for skill '{args.skill_id}' at {args.project}/{args.location}...")
  status, text, data = http_json("GET", url, headers=headers)
  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  print("Response:")
  print(json.dumps(data, indent=2))


def get_skill_revision(args):
  """Gets a specific revision of a skill from the Skill Registry."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)
  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills/{args.skill_id}/revisions/{args.revision_id}"
  headers = {"Authorization": f"Bearer {token}"}

  print(
      f"Getting skill '{args.skill_id}' revision '{args.revision_id}' at"
      f" {args.project}/{args.location}..."
  )
  status, text, data = http_json("GET", url, headers=headers)
  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  cleaned = summarize_zip_field(
      data, include_zip=args.include_zip, extract_to=args.extract_to
  )
  print("Response:")
  print(json.dumps(cleaned, indent=2))


def install_skill(args):
  """Downloads and extracts a skill from the Skill Registry into ~/.gemini/skills or .agents/skills."""
  token = get_access_token()
  endpoint = get_endpoint(args.location)
  url = f"https://{endpoint}/v1beta1/projects/{args.project}/locations/{args.location}/skills/{args.skill_id}"
  headers = {"Authorization": f"Bearer {token}"}

  if args.dest:
    target_dir = os.path.expanduser(args.dest)
  elif args.scope == "workspace":
    target_dir = os.path.join(os.getcwd(), ".agents", "skills", args.skill_id)
  else:
    target_dir = os.path.expanduser(f"~/.gemini/skills/{args.skill_id}")

  print(f"Fetching skill '{args.skill_id}' from {args.project}/{args.location}...")
  status, text, data = http_json("GET", url, headers=headers)
  if status >= 400:
    print(f"Error: {status} - {text}", file=sys.stderr)
    sys.exit(1)

  b64_str = (data or {}).get("zippedFilesystem")
  if not b64_str:
    print(f"Error: Skill '{args.skill_id}' response did not contain zippedFilesystem.", file=sys.stderr)
    sys.exit(1)

  raw_bytes = base64.b64decode(b64_str)
  os.makedirs(target_dir, exist_ok=True)
  with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
    names = zf.namelist()
    zf.extractall(target_dir)

  print(f"SUCCESS: Installed '{args.skill_id}' ({len(names)} files, {len(raw_bytes)} bytes) -> {target_dir}")
  for name in names:
    print(f"  - {os.path.join(target_dir, name)}")


def monitor(args):
  """Monitors the status of a long-running operation."""
  token = get_access_token()
  print(f"Monitoring operation {args.operation_id}...")
  poll_operation(
      args.operation_id,
      args.location,
      token,
      wait=args.wait,
      timeout=args.timeout,
  )


def _add_wait_flags(subparser):
  subparser.add_argument(
      "--wait",
       dest="wait",
      action="store_true",
      default=True,
      help="Poll the Long-Running Operation until completion (default: True).",
  )
  subparser.add_argument(
      "--no-wait",
      dest="wait",
      action="store_false",
      help="Return immediately after starting the Long-Running Operation.",
  )
  subparser.add_argument(
      "--timeout",
      type=int,
      default=120,
      help="Max seconds to wait when polling an LRO (default: 120).",
  )


def main():
  parser = argparse.ArgumentParser(
      description="Skill Registry Operations Utility (zero external dependencies)"
  )
  parser.add_argument(
      "--project",
      default=None,
      help="GCP Project ID (falls back to GCP_PROJECT_ID / gcloud config).",
  )
  parser.add_argument(
      "--location",
      default=None,
      help="GCP Region (falls back to GCP_LOCATION / gcloud config / us-central1).",
  )

  subparsers = parser.add_subparsers(dest="action", required=True)

  upload_parser = subparsers.add_parser(
      "upload",
      help="Upload a skill (auto-infers metadata from SKILL.md and upserts on 409).",
  )
  upload_parser.add_argument("--skill-id", required=False, help="Skill ID (inferred from SKILL.md name if omitted).")
  upload_parser.add_argument("--display-name", required=False, help="Display name (inferred from SKILL.md # Title if omitted).")
  upload_parser.add_argument("--description", required=False, help="Description (inferred from SKILL.md frontmatter if omitted).")
  upload_parser.add_argument(
      "--no-upsert",
      action="store_true",
      help="Fail on 409 ALREADY_EXISTS instead of automatically updating.",
  )
  group = upload_parser.add_mutually_exclusive_group(required=True)
  group.add_argument("--zip-file")
  group.add_argument("--folder")
  _add_wait_flags(upload_parser)

  search_parser = subparsers.add_parser("search")
  search_parser.add_argument("--query", required=True)
  search_parser.add_argument("--top-k", type=int, default=5)

  get_parser = subparsers.add_parser("get")
  get_parser.add_argument("--skill-id", required=True)
  get_parser.add_argument("--include-zip", action="store_true", help="Include raw base64 zippedFilesystem in output.")
  get_parser.add_argument("--extract-to", default=None, help="Optional directory to extract the skill archive into.")

  list_parser = subparsers.add_parser("list")
  list_parser.add_argument("--include-zip", action="store_true", help="Include raw base64 zippedFilesystem in output.")

  delete_parser = subparsers.add_parser("delete")
  delete_parser.add_argument("--skill-id", required=True)
  _add_wait_flags(delete_parser)

  update_parser = subparsers.add_parser("update")
  update_parser.add_argument("--skill-id", required=False, help="Skill ID (inferred from SKILL.md name if omitted).")
  update_parser.add_argument("--display-name", required=False)
  update_parser.add_argument("--description", required=False)
  update_group = update_parser.add_mutually_exclusive_group(required=False)
  update_group.add_argument("--zip-file")
  update_group.add_argument("--folder")
  _add_wait_flags(update_parser)

  list_rev_parser = subparsers.add_parser("list-revision")
  list_rev_parser.add_argument("--skill-id", required=True)

  get_rev_parser = subparsers.add_parser("get-revision")
  get_rev_parser.add_argument("--skill-id", required=True)
  get_rev_parser.add_argument("--revision-id", required=True)
  get_rev_parser.add_argument("--include-zip", action="store_true")
  get_rev_parser.add_argument("--extract-to", default=None)

  monitor_parser = subparsers.add_parser("monitor")
  monitor_parser.add_argument("--operation-id", required=True)
  _add_wait_flags(monitor_parser)

  install_parser = subparsers.add_parser(
      "install",
      help="Download and install a skill from the registry into ~/.gemini/skills or .agents/skills.",
  )
  install_parser.add_argument("--skill-id", required=True, help="Skill ID to download and install.")
  install_parser.add_argument(
      "--scope",
      choices=["user", "workspace"],
      default="user",
      help="Install to ~/.gemini/skills/<id> (user) or ./.agents/skills/<id> (workspace).",
  )
  install_parser.add_argument(
      "--dest",
      default=None,
      help="Explicit destination folder (overrides --scope).",
  )

  args = parser.parse_args()
  args.project = resolve_project(args.project)
  args.location = resolve_location(args.location)

  if not args.project:
    print(
        "ERROR: Could not resolve GCP Project ID. Pass --project, set"
        " GCP_PROJECT_ID, or run 'gcloud config set project <PROJECT_ID>'.",
        file=sys.stderr,
    )
    sys.exit(1)

  dispatch = {
      "upload": upload,
      "search": search,
      "get": get_skill,
      "list": list_skills,
      "delete": delete_skill,
      "update": update_skill,
      "list-revision": list_skill_revision,
      "get-revision": get_skill_revision,
      "monitor": monitor,
      "install": install_skill,
  }
  dispatch[args.action](args)


if __name__ == "__main__":
  main()
