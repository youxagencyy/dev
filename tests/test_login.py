from telethon.errors import PhoneCodeInvalidError, SessionPasswordNeededError

from newsbot.login import sign_in_outcome, write_session_env


def test_cloud_password_is_not_an_invalid_code():
    assert sign_in_outcome(SessionPasswordNeededError(request=None)) == "password"
    assert sign_in_outcome(PhoneCodeInvalidError(request=None)) == "bad_code"


def test_session_is_written_to_env_file(tmp_path):
    path = tmp_path / ".env"
    path.write_text("BOT_TOKEN=keep\nTELEGRAM_SESSION=\n", encoding="utf-8")
    write_session_env("session-value", path)
    text = path.read_text(encoding="utf-8")
    assert "TELEGRAM_SESSION=session-value" in text
    assert "BOT_TOKEN=keep" in text
