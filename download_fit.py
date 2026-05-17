#!/usr/bin/env python3
"""Download the FIT file for your latest Garmin Connect activity."""

import argparse
import getpass
import os
import sys

from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectTooManyRequestsError

TOKEN_DIR = os.path.expanduser("~/.garminconnect")

# Cloudflare TLS fingerprinting blocks garth's default mobile User-Agent;
# a browser UA bypasses it. See: https://github.com/matin/garth/discussions/222
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download the FIT file for your latest Garmin Connect activity."
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("GARMIN_EMAIL"),
        help="Garmin Connect email (or set GARMIN_EMAIL env var)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("GARMIN_PASSWORD"),
        help="Garmin Connect password (or set GARMIN_PASSWORD env var)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: <activity_id>.fit)",
    )
    parser.add_argument(
        "--reauth",
        action="store_true",
        help="Force re-authentication even if cached tokens exist",
    )
    return parser.parse_args()


def prompt_credentials(email, password):
    if not email:
        email = input("Garmin Connect email: ").strip()
    if not password:
        password = getpass.getpass("Garmin Connect password: ")
    return email, password


def login_with_credentials(email, password):
    api = Garmin(email=email, password=password, is_cn=False, return_on_mfa=True)
    api.garth.sess.headers.update({"User-Agent": BROWSER_UA})

    result, data = api.login()

    if result == "needs_mfa":
        mfa_code = input("MFA/2FA code: ").strip()
        api.resume_login(data, mfa_code)

    os.makedirs(TOKEN_DIR, exist_ok=True)
    api.garth.dump(TOKEN_DIR)
    print(f"Tokens cached to {TOKEN_DIR}")
    return api


def load_cached_tokens():
    api = Garmin()
    api.garth.load(TOKEN_DIR)
    api.garth.sess.headers.update({"User-Agent": BROWSER_UA})
    return api


def get_api(args):
    if not args.reauth and os.path.isdir(TOKEN_DIR) and os.listdir(TOKEN_DIR):
        try:
            print(f"Loading cached tokens from {TOKEN_DIR}...")
            return load_cached_tokens()
        except Exception:
            print("Cached tokens invalid or expired — logging in fresh.")

    email, password = prompt_credentials(args.email, args.password)
    print("Logging in to Garmin Connect...")
    try:
        return login_with_credentials(email, password)
    except GarminConnectAuthenticationError as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)
    except GarminConnectTooManyRequestsError:
        print("Too many requests — try again later.", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    api = get_api(args)

    print("Fetching latest activity...")
    activities = api.get_activities(0, 1)
    if not activities:
        print("No activities found.", file=sys.stderr)
        sys.exit(1)

    activity = activities[0]
    activity_id = activity["activityId"]
    activity_name = activity.get("activityName", "Unknown")
    activity_date = activity.get("startTimeLocal", "Unknown date")
    print(f"Latest activity: {activity_name} ({activity_date}), ID: {activity_id}")

    print("Downloading FIT file...")
    fit_data = api.download_activity(activity_id, dl_fmt=api.ActivityDownloadFormat.ORIGINAL)

    output_path = args.output or f"{activity_id}.fit"
    with open(output_path, "wb") as f:
        f.write(fit_data)

    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
