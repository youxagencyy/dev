from newsbot.commands import BUTTON_ACTIONS, OWNER_BUTTONS, START_TEXT, bot_commands, owner_keyboard


def test_command_menu_is_russian_and_includes_start():
    commands = bot_commands()
    names = [item.command for item in commands]
    assert names[:6] == ["start", "status", "donors", "pause", "resume", "help"]
    assert all(item.description for item in commands)
    assert "Бот на связи" in commands[0].description


def test_owner_keyboard_is_persistent_and_resized():
    markup = owner_keyboard()
    assert markup.resize_keyboard is True
    assert markup.is_persistent is True
    labels = [button.text for row in markup.keyboard for button in row]
    assert labels == list(OWNER_BUTTONS)
    assert set(BUTTON_ACTIONS) == set(OWNER_BUTTONS)
    assert BUTTON_ACTIONS["Помощь"] == "help"
    assert BUTTON_ACTIONS["Статус"] == "status"


def test_start_text_explains_review_buttons():
    assert START_TEXT.startswith("Бот на связи")
    assert "Отправить" in START_TEXT
    assert "Редактировать" in START_TEXT
    assert "Отклонить" in START_TEXT
