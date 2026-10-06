import re
from pathlib import Path

from newsbot.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def test_example_config_loads():
    config = load_config(ROOT / "config.example.yaml")
    assert config.target_channel == "@your_news"
    assert config.owner_id == 123456789
    assert any(donor.username == "sample_donor" and donor.enabled for donor in config.donors)
    assert "реклама" in config.ad_filter.keywords
    assert config.signatures.default in config.signatures.templates
    assert config.rewrite.enabled is True


def test_examples_do_not_contain_live_secrets():
    for name in ("config.example.yaml", ".env.example", "README.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert not re.search(r"\d{6,}:[A-Za-z0-9_-]{20,}", text), name
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    values = {}
    for line in env.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    for key in ("BOT_TOKEN", "TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION", "OPENAI_API_KEY"):
        assert values[key] == ""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert any(line.strip() == ".env" for line in gitignore.splitlines())
    assert any(line.strip() == "config.yaml" for line in gitignore.splitlines())
