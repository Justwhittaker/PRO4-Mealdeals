#!/usr/bin/env python3
"""Telegram slash-command bot for NUC Celery repair ($0 — no LLM).

Commands: /status /pull /deploy /restart /logs /disk /help
Only TELEGRAM_ALLOWED_USER_IDS may use the bot.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow `python -m repair_agent.bot` from scripts/ or package dir.
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from repair_agent.config import Config
from repair_agent import tools

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("repair_agent")

HELP_TEXT = """MealDeals NUC repair bot (no AI — slash commands only)

/status — Docker + Celery ping
/pull — git fetch + ff-only pull (master)
/deploy — /pull then recreate celery-worker
/restart — recreate celery-worker (rate-limited)
/logs — last container log lines
/disk — disk + memory
/help — this message
"""


def _allowed(update: Update, cfg: Config) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return user.id in cfg.allowed_user_ids


async def _deny(update: Update) -> None:
    if update.message:
        uid = update.effective_user.id if update.effective_user else "?"
        await update.message.reply_text(
            f"Unauthorized.\nYour Telegram user id is: {uid}\n"
            "Put that number in TELEGRAM_ALLOWED_USER_IDS in repair-agent.env"
        )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.application.bot_data["cfg"]
    if not _allowed(update, cfg):
        await _deny(update)
        return
    await update.message.reply_text(HELP_TEXT)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.application.bot_data["cfg"]
    if not _allowed(update, cfg):
        await _deny(update)
        return
    await update.message.reply_text("Checking…")
    result = tools.celery_status(cfg)
    prefix = "OK" if result.ok else "FAIL"
    await update.message.reply_text(f"{prefix}\n{result.text}"[:4000])


async def cmd_pull(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.application.bot_data["cfg"]
    if not _allowed(update, cfg):
        await _deny(update)
        return
    await update.message.reply_text(
        f"Pulling {cfg.git_remote}/{cfg.git_branch}…"
    )
    result = tools.git_pull(cfg)
    prefix = "OK" if result.ok else "FAIL"
    await update.message.reply_text(f"{prefix}\n{result.text}"[:4000])


async def cmd_deploy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.application.bot_data["cfg"]
    if not _allowed(update, cfg):
        await _deny(update)
        return
    await update.message.reply_text(
        f"Deploying ({cfg.git_remote}/{cfg.git_branch} + restart)…"
    )
    result = tools.git_pull_and_restart(cfg)
    prefix = "OK" if result.ok else "FAIL"
    await update.message.reply_text(f"{prefix}\n{result.text}"[:4000])


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.application.bot_data["cfg"]
    if not _allowed(update, cfg):
        await _deny(update)
        return
    await update.message.reply_text("Restarting celery-worker…")
    result = tools.celery_restart(cfg)
    prefix = "OK" if result.ok else "FAIL"
    await update.message.reply_text(f"{prefix}\n{result.text}"[:4000])


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.application.bot_data["cfg"]
    if not _allowed(update, cfg):
        await _deny(update)
        return
    result = tools.celery_logs(cfg)
    prefix = "OK" if result.ok else "FAIL"
    # Telegram hard limit 4096; keep headroom
    body = f"{prefix}\n{result.text}"
    await update.message.reply_text(body[-4000:])


async def cmd_disk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.application.bot_data["cfg"]
    if not _allowed(update, cfg):
        await _deny(update)
        return
    result = tools.disk_memory(cfg)
    prefix = "OK" if result.ok else "FAIL"
    await update.message.reply_text(f"{prefix}\n{result.text}"[:4000])


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.application.bot_data["cfg"]
    if not _allowed(update, cfg):
        await _deny(update)
        return
    await update.message.reply_text(
        "No free-text AI on this bot. Use /status /pull /deploy /restart /logs /disk /help"
    )


def main() -> None:
    cfg = Config.from_env()
    app = (
        Application.builder()
        .token(cfg.telegram_bot_token)
        .build()
    )
    app.bot_data["cfg"] = cfg

    app.add_handler(CommandHandler(["start", "help"], cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("pull", cmd_pull))
    app.add_handler(CommandHandler(["deploy", "update"], cmd_deploy))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("disk", cmd_disk))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info(
        "Starting repair bot (container=%s repo=%s %s/%s pull_cd=%ss restart_cd=%ss)",
        cfg.container,
        cfg.repo_dir,
        cfg.git_remote,
        cfg.git_branch,
        cfg.pull_cooldown_secs,
        cfg.restart_cooldown_secs,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
