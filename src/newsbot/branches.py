"""Owner-managed feeds. No Telegram calls.

A branch is a name, a donor list, a publish channel, and a review channel.
The legacy ``target`` / ``log`` / ``donors`` keys are the first branch, «Новости».
Callback data stays inside Telegram's 64-byte limit by carrying a list index,
not the branch name.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import yaml
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from newsbot.config import Branch, Config, ConfigError, Donor
from newsbot.donors import commit_config, donor_mapping

CALLBACK_LIMIT = 64
_ACTIONS = {"add": "a", "publish": "p", "review": "v", "switch": "s"}
_BY_CODE = {code: name for name, code in _ACTIONS.items()}
_CALLBACK_RE = re.compile(r"^br:([apsv])(?::(\d{1,4}))?$")
_NUMERIC_RE = re.compile(r"-?\d{6,20}")


class DestinationError(ValueError):
    """The owner did not send a public @username or a numeric channel id."""


class BranchNameError(ValueError):
    """The owner did not send a usable branch name."""


def materialize_branches(config: Config) -> tuple[Branch, ...]:
    if config.branches:
        return config.branches
    name = config.current_branch or "Новости"
    return (
        Branch(
            name=name,
            publish_channel=config.target_channel,
            review_channel=config.log_channel,
            donors=config.donors,
        ),
    )


def current_branch(config: Config) -> Branch:
    branches = materialize_branches(config)
    for branch in branches:
        if branch.name == config.current_branch:
            return branch
    return branches[0]


def apply_branches(config: Config, branches: tuple[Branch, ...], current_name: str) -> Config:
    current = next(branch for branch in branches if branch.name == current_name)
    return replace(
        config,
        branches=branches,
        current_branch=current.name,
        target_channel=current.publish_channel,
        log_channel=current.review_channel,
        donors=current.donors,
    )


def parse_branch_name(raw: str) -> str:
    name = " ".join((raw or "").split())
    if not name or len(name) > 40:
        raise BranchNameError("Название ветки: от 1 до 40 символов.")
    if name.startswith("/"):
        raise BranchNameError("Название не должно начинаться с /.")
    return name


def parse_destination(raw: str) -> str:
    """Return ``@username`` or a numeric channel id.

    A public ``t.me`` link is accepted as that username. Invite links are not.
    """
    from newsbot.donors import DonorRefError, parse_donor_ref

    text = (raw or "").strip()
    if _NUMERIC_RE.fullmatch(text):
        return text
    try:
        username = parse_donor_ref(text)
    except DonorRefError as exc:
        raise DestinationError("Пришлите @username или числовой id канала.") from exc
    return f"@{username}"


def pack_branch_callback(action: str, index: int | None = None) -> str:
    if action not in _ACTIONS:
        raise ValueError(action)
    if action == "switch":
        if index is None or index < 0 or index > 9999:
            raise ValueError("index required")
        data = f"br:{_ACTIONS[action]}:{index}"
    else:
        if index is not None:
            raise ValueError("index not allowed")
        data = f"br:{_ACTIONS[action]}"
    if len(data.encode("utf-8")) > CALLBACK_LIMIT:
        raise ValueError("callback data exceeds 64 bytes")
    return data


def parse_branch_callback(data: str | None) -> tuple[str, int | None] | None:
    match = _CALLBACK_RE.fullmatch(data or "")
    if not match:
        return None
    action = _BY_CODE[match.group(1)]
    raw_index = match.group(2)
    if action == "switch":
        if raw_index is None:
            return None
        return action, int(raw_index)
    if raw_index is not None:
        return None
    return action, None


def format_branch_list(config: Config) -> str:
    current = current_branch(config)
    lines = [
        f"Текущая ветка: {current.name}",
        f"Куда публиковать: {current.publish_channel}",
        f"Канал проверки: {current.review_channel}",
        "",
    ]
    for branch in materialize_branches(config):
        mark = "• " if branch.name == current.name else ""
        lines.append(
            f"{mark}{branch.name}: публикация {branch.publish_channel}, "
            f"проверка {branch.review_channel}, доноров {len(branch.donors)}"
        )
    return "\n".join(lines)


def format_current_donors(config: Config) -> str:
    from newsbot.donors import format_donor_list

    branch = current_branch(config)
    return f"Ветка: {branch.name}\n\n{format_donor_list(branch.donors)}"


def branches_keyboard(config: Config) -> InlineKeyboardMarkup:
    current = current_branch(config)
    rows: list[list[InlineKeyboardButton]] = []
    for index, branch in enumerate(materialize_branches(config)):
        label = branch.name if branch.name != current.name else f"✓ {branch.name}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label[:64],
                    callback_data=pack_branch_callback("switch", index),
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Куда публиковать",
                callback_data=pack_branch_callback("publish"),
            ),
            InlineKeyboardButton(
                text="Канал проверки",
                callback_data=pack_branch_callback("review"),
            ),
        ]
    )
    rows.append(
        [InlineKeyboardButton(text="Добавить ветку", callback_data=pack_branch_callback("add"))]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def select_branch(config: Config, index: int) -> tuple[Config, str | None]:
    branches = materialize_branches(config)
    if index < 0 or index >= len(branches):
        return config, "Такой ветки нет."
    return apply_branches(config, branches, branches[index].name), None


def add_branch(config: Config, name: str, publish: str, review: str) -> tuple[Config, str | None]:
    branches = list(materialize_branches(config))
    if any(branch.name.casefold() == name.casefold() for branch in branches):
        return config, "Ветка с таким названием уже есть."
    branches.append(Branch(name=name, publish_channel=publish, review_channel=review, donors=()))
    return apply_branches(config, tuple(branches), name), None


def set_branch_channel(config: Config, kind: str, channel: str) -> Config:
    if kind not in {"publish", "review"}:
        raise ValueError(kind)
    current = current_branch(config)
    updated: list[Branch] = []
    for branch in materialize_branches(config):
        if branch.name != current.name:
            updated.append(branch)
            continue
        if kind == "publish":
            updated.append(replace(branch, publish_channel=channel))
        else:
            updated.append(replace(branch, review_channel=channel))
    return apply_branches(config, tuple(updated), current.name)


def set_branch_template(config: Config, template: str) -> Config:
    current = current_branch(config)
    updated: list[Branch] = []
    for branch in materialize_branches(config):
        if branch.name == current.name:
            updated.append(replace(branch, template=template.strip()))
        else:
            updated.append(branch)
    return apply_branches(config, tuple(updated), current.name)


def format_template(config: Config) -> str:
    branch = current_branch(config)
    body = branch.template.strip() or "Шаблон пуст."
    return f"Ветка: {branch.name}\n\nШаблон:\n{body}"


def template_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Изменить", callback_data="tm:e"),
                InlineKeyboardButton(text="Очистить", callback_data="tm:c"),
            ]
        ]
    )


def replace_current_donors(config: Config, donors: tuple[Donor, ...]) -> Config:
    current = current_branch(config)
    updated: list[Branch] = []
    for branch in materialize_branches(config):
        if branch.name == current.name:
            updated.append(replace(branch, donors=donors))
        else:
            updated.append(branch)
    return apply_branches(config, tuple(updated), current.name)


def yaml_channel(value: str) -> str | int:
    text = value.strip()
    if text.lstrip("-").isdigit():
        return int(text)
    return text


def branch_mapping(branch: Branch) -> dict[str, object]:
    return {
        "name": branch.name,
        "publish": yaml_channel(branch.publish_channel),
        "review": yaml_channel(branch.review_channel),
        "template": branch.template,
        "donors": [donor_mapping(donor) for donor in branch.donors],
    }


def save_branches(path: str | Path, config: Config) -> Config:
    """Write branches and mirror the current one into target, log, and donors."""
    target = Path(path)
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError("Корень config.yaml должен быть словарём")
    branches = materialize_branches(config)
    current = current_branch(config)
    data["current_branch"] = current.name
    data["branches"] = [branch_mapping(branch) for branch in branches]
    target_raw = data.get("target")
    if not isinstance(target_raw, dict):
        target_raw = {}
    target_raw["channel"] = yaml_channel(current.publish_channel)
    data["target"] = target_raw
    log_raw = data.get("log")
    if not isinstance(log_raw, dict):
        log_raw = {}
    log_raw["channel"] = yaml_channel(current.review_channel)
    data["log"] = log_raw
    data["donors"] = [donor_mapping(donor) for donor in current.donors]
    return commit_config(target, data)
