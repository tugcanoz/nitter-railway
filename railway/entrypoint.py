"""Generate private Nitter runtime files from Railway environment variables."""
import json
import os
from pathlib import Path
import re
import sys


def required(env, key):
    value = env.get(key, "").strip()
    if not value:
        raise ValueError(f"Missing required variable: {key}")
    return value


def integer(value, name, low=1, high=65535):
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be an integer") from None
    if not low <= number <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return str(number)


def quote(value):
    # Nim parsecfg understands quoted strings and backslash escapes.
    if any(ord(c) < 32 for c in value):
        raise ValueError("Configuration values cannot contain control characters")
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def sessions(env):
    raw = env.get("NITTER_SESSIONS", "").strip()
    if raw:
        try:
            items = [json.loads(line) for line in raw.splitlines() if line.strip()]
        except json.JSONDecodeError:
            raise ValueError("NITTER_SESSIONS must be JSONL: one JSON object per line") from None
    else:
        items = [{"kind": "cookie", "username": required(env, "X_USERNAME"),
                  "id": env.get("X_USER_ID", "0"),
                  "auth_token": required(env, "X_AUTH_TOKEN"),
                  "ct0": required(env, "X_CT0")}]
    for item in items:
        if not isinstance(item, dict) or item.get("kind") != "cookie":
            raise ValueError("Every session must be a cookie session with kind=cookie")
        for key in ("username", "auth_token", "ct0"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Every session requires a nonempty {key}")
        item["id"] = integer(item.get("id", "0"), "session id", 0, 2**63 - 1)
    return "".join(json.dumps(item, ensure_ascii=True) + "\n" for item in items)


def configuration(env, template):
    hostname = env.get("NITTER_HOSTNAME") or required(env, "RAILWAY_PUBLIC_DOMAIN")
    if not re.fullmatch(r"[A-Za-z0-9.-]+(?::[0-9]+)?", hostname):
        raise ValueError("NITTER_HOSTNAME must be a hostname, without https:// or a path")
    hmac = required(env, "NITTER_HMAC_KEY")
    if len(hmac) < 32:
        raise ValueError("NITTER_HMAC_KEY must contain at least 32 characters")
    https = env.get("NITTER_HTTPS", "true").lower()
    if https not in ("true", "false"):
        raise ValueError("NITTER_HTTPS must be true or false")
    values = {
        "hostname": quote(hostname), "replaceTwitter": quote(hostname),
        "address": quote("0.0.0.0"),
        "port": integer(env.get("PORT", "8080"), "PORT"), "https": https,
        "hmacKey": quote(hmac),
        "redisHost": quote(required(env, "REDISHOST")),
        "redisPort": integer(env.get("REDISPORT", "6379"), "REDISPORT"),
        "redisPassword": quote(env.get("REDISPASSWORD", "")),
        "rssMinutes": integer(env.get("RSS_CACHE_MINUTES", "15"), "RSS_CACHE_MINUTES", 1, 1440),
        "enableDebug": "false",
    }
    for name in ("enableRSS", "enableRSSUserTweets", "enableRSSUserReplies",
                 "enableRSSUserMedia", "enableRSSUserArticles", "enableRSSSearch", "enableRSSList"):
        values[name] = "true"
    for key, value in values.items():
        template, count = re.subn(r"(?m)^" + re.escape(key) + r"\s*=.*$",
                                 lambda match: key + " = " + value, template)
        if count != 1:
            raise ValueError(f"Expected exactly one config entry for {key}")
    return template


def prepare(env, template_path, runtime):
    # Validate everything before writing; never print credentials.
    config = configuration(env, template_path.read_text(encoding="utf-8"))
    session_data = sessions(env)
    os.umask(0o077)
    runtime.mkdir(parents=True, exist_ok=True)
    config_path = runtime / "nitter.conf"
    sessions_path = runtime / "sessions.jsonl"
    for path, data in ((config_path, config), (sessions_path, session_data)):
        path.write_text(data, encoding="utf-8")
        path.chmod(0o600)
    return config_path, sessions_path


def main():
    try:
        conf, accounts = prepare(os.environ, Path("/src/nitter.example.conf"), Path("/src/runtime"))
    except (ValueError, OSError) as error:
        print(f"Nitter configuration error: {error}", file=sys.stderr)
        return 1
    env = dict(os.environ, NITTER_CONF_FILE=str(conf), NITTER_SESSIONS_FILE=str(accounts))
    for key in ("NITTER_SESSIONS", "X_AUTH_TOKEN", "X_CT0", "NITTER_HMAC_KEY", "REDISPASSWORD"):
        env.pop(key, None)
    os.chdir("/src")
    os.execve("/src/nitter", ["/src/nitter"], env)


if __name__ == "__main__":
    sys.exit(main())
