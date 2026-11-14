"""User-requested Russian help and Telegram command-menu descriptions."""

HELP_MESSAGE = (
    "/server_start — запустить сервер.\n"
    "/server_stop — остановить сервер.\n"
    "/help — список команд."
)

COMMAND_DESCRIPTIONS = (
    ("help", "Список команд"),
    ("server_start", "Запустить Minecraft-сервер"),
    ("server_stop", "Остановить Minecraft-сервер"),
)

SERVER_STARTING = "Сервер запускается. Сообщу, когда можно будет играть."
SERVER_READY = "Сервер запущен, можно играть!"
READINESS_ERRORS = {
    "readiness_check_failed": "Не удалось проверить готовность сервера. Попросите оператора проверить сервис управления и логи Minecraft.",
    "readiness_timeout": "Сервер не загрузился за 5 минут. Проверьте логи Minecraft; он может продолжать запускаться.",
    "readiness_stopped": "Сервер остановился до завершения загрузки. Проверьте логи Minecraft.",
    "readiness_restarted": "Во время загрузки сервер перезапустился. Повторите /server_start для проверки нового запуска.",
}

SERVER_STOPPING = "Сервер останавливается…"
SERVER_STOPPED = "Сервер остановлен."
SERVER_ALREADY_STOPPED = "Сервер уже остановлен."
SERVER_STOP_FAILED = "Не удалось подтвердить остановку сервера. Попросите администратора проверить его состояние."
COMMAND_USAGE = "Использование: /{command}"
