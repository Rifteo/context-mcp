import json
from pathlib import Path

CREDENTIALS_FILE = Path.home() / ".auditguard" / "credentials.json"

PLATFORMS = {
    "hackerone": {
        "fields": ["username", "token"],
        "prompts": ["HackerOne username: ", "HackerOne API token: "],
        "help": "Get your token at https://hackerone.com/settings/api_token/edit",
    },
    "bugcrowd": {
        "fields": ["token"],
        "prompts": ["Bugcrowd API token: "],
        "help": "Get your token at https://bugcrowd.com/user/api_tokens",
    },
    "intigriti": {
        "fields": ["token"],
        "prompts": ["Intigriti API token: "],
        "help": "Get your token at https://app.intigriti.com/settings/api",
    },
    "yeswehack": {
        "fields": ["token"],
        "prompts": ["YesWeHack API token: "],
        "help": "Get your token at https://yeswehack.com/settings/api",
    },
}


def load() -> dict:
    if not CREDENTIALS_FILE.exists():
        return {}
    return json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))


def save(data: dict):
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_platform(platform: str) -> dict | None:
    return load().get(platform)


def set_platform(platform: str, values: dict):
    data = load()
    data[platform] = values
    save(data)


def remove_platform(platform: str):
    data = load()
    data.pop(platform, None)
    save(data)
