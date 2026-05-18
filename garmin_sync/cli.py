#!/usr/bin/env python3
"""Download the FIT file for your latest Garmin Connect activity."""

import argparse
import getpass
import io
import os
import sys
import zipfile

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
        "--output", "-o",
        default=None,
        help="Output file path (default: <activity_id>.fit); ignored when --recent > 1",
    )
    parser.add_argument(
        "--recent",
        type=int,
        default=1,
        metavar="N",
        help="Download the N most recent activities (default: 1)",
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


def get_api(args):
    tokenstore = None if args.reauth else TOKEN_DIR
    has_tokens = bool(tokenstore and os.path.isdir(tokenstore) and os.listdir(tokenstore))

    if has_tokens:
        email, password = args.email or "", args.password or ""
    else:
        email, password = prompt_credentials(args.email, args.password)

    api = Garmin(email=email, password=password, return_on_mfa=True)
    api.client.cs.headers.update({"User-Agent": BROWSER_UA})

    print("Logging in to Garmin Connect...")
    try:
        result, data = api.login(tokenstore=tokenstore)
    except GarminConnectAuthenticationError as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)
    except GarminConnectTooManyRequestsError:
        print("Too many requests — try again later.", file=sys.stderr)
        sys.exit(1)

    if result == "needs_mfa":
        mfa_code = input("MFA/2FA code: ").strip()
        api.resume_login(data, mfa_code)

    os.makedirs(TOKEN_DIR, exist_ok=True)
    api.client.dump(TOKEN_DIR)
    print(f"Tokens cached to {TOKEN_DIR}")

    return api


def main():
    args = parse_args()
    api = get_api(args)

    print(f"Fetching {args.recent} most recent activit{'y' if args.recent == 1 else 'ies'}...")
    activities = api.get_activities(0, args.recent)
    if not activities:
        print("No activities found.", file=sys.stderr)
        sys.exit(1)

    for i, activity in enumerate(activities):
        activity_id = activity["activityId"]
        activity_name = activity.get("activityName", "Unknown")
        activity_date = activity.get("startTimeLocal", "Unknown date")
        print(f"[{i + 1}/{len(activities)}] {activity_name} ({activity_date}), ID: {activity_id}")

        print("  Downloading FIT file...")
        zip_data = api.download_activity(activity_id, dl_fmt=api.ActivityDownloadFormat.ORIGINAL)

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            fit_names = [n for n in zf.namelist() if n.lower().endswith(".fit")]
            if not fit_names:
                print(f"  No .fit file found in archive for activity {activity_id}.", file=sys.stderr)
                continue
            fit_data = zf.read(fit_names[0])

        output_path = (args.output if args.recent == 1 else None) or f"{activity_id}.fit"
        with open(output_path, "wb") as f:
            f.write(fit_data)
        print(f"  Saved to: {output_path}")


if __name__ == "__main__":
    main()
