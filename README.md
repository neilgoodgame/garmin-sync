# garmin-sync

CLI tool to download the FIT file for your latest Garmin Connect activity.

## Installation

```bash
pip install -e .
```

## Usage

```bash
garmin-sync [--email EMAIL] [--password PASSWORD] [--output FILE] [--reauth]
```

Credentials can also be provided via environment variables:

```bash
export GARMIN_EMAIL=you@example.com
export GARMIN_PASSWORD=yourpassword
garmin-sync
```

By default the output file is named `<activity_id>.fit` in the current directory. Use `-o` to specify a different path:

```bash
garmin-sync -o my_run.fit
```

### Options

| Flag | Description |
|------|-------------|
| `--email` | Garmin Connect email (or `GARMIN_EMAIL` env var) |
| `--password` | Garmin Connect password (or `GARMIN_PASSWORD` env var) |
| `-o`, `--output` | Output file path (default: `<activity_id>.fit`); ignored when `--recent` > 1 |
| `--recent N` | Download the N most recent activities (default: 1) |
| `--reauth` | Force re-authentication, ignoring cached tokens |

## Authentication

On first login, tokens are cached to `~/.garminconnect` so subsequent runs don't require credentials. If your account uses two-factor authentication, you will be prompted for an MFA code.

Use `--reauth` to clear the cached session and log in again.

## Requirements

- Python 3.12+
- [garminconnect](https://github.com/cyberjunky/python-garminconnect)