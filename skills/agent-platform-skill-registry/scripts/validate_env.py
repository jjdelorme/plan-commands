"""Validates or auto-discovers required environment variables and credentials."""

import os
import subprocess
import sys


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


def validate_env():
  print("Validating core environment and configuration...")
  project = resolve_project()
  location = resolve_location()

  if not project:
    print(
        "ERROR: Could not determine GCP Project ID. Set GCP_PROJECT_ID or run"
        " 'gcloud config set project <PROJECT_ID>'."
    )
    sys.exit(1)

  print(f"SUCCESS: Resolved project='{project}', location='{location}'.")
  return project, location


if __name__ == "__main__":
  validate_env()
