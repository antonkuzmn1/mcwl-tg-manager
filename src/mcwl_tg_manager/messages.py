"""User-requested Russian help and Telegram command-menu descriptions."""

HELP_MESSAGE = (
    "/server_start — запустить сервер.\n"
    "/server_stop — остановить сервер.\n"
    "/wl_list — вайтлист.\n"
    "/wl_add <ник> — добавить игрока.\n"
    "/wl_remove <ник> — убрать игрока.\n"
    "/help — список команд."
)

COMMAND_DESCRIPTIONS = (
    ("help", "Список команд"),
    ("server_start", "Запустить Minecraft-сервер"),
    ("server_stop", "Остановить Minecraft-сервер"),
    ("wl_list", "Посмотреть вайтлист"),
    ("wl_add", "Добавить игрока в вайтлист"),
    ("wl_remove", "Убрать игрока из вайтлиста"),
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

WHITELIST_EMPTY = "Вайтлист пуст."
WHITELIST_HEADER = "Вайтлист ({count}):"
WHITELIST_INVALID_NAME = "Ник: от 1 до 16 латинских букв, цифр или символов _."
WHITELIST_USAGE = {
    "list": "Использование: /wl_list",
    "add": "Использование: /wl_add <ник>",
    "remove": "Использование: /wl_remove <ник>",
}
WHITELIST_RESULTS = {
    "added": "{player} добавлен в вайтлист.",
    "already_listed": "{player} уже в вайтлисте.",
    "removed": "{player} удалён из вайтлиста.",
    "not_listed": "{player} нет в вайтлисте.",
}
WHITELIST_FAILED = "Не удалось получить ответ сервера. Проверьте его состояние и доступность RCON."
WHITELIST_ERRORS = {
    "whitelist_not_running": "Сначала запустите сервер: /server_start.",
    "whitelist_busy": "Другая операция ещё выполняется. Попробуйте чуть позже.",
    "whitelist_unknown_player": "Игрок не найден. Проверьте ник.",
    "whitelist_unexpected_response": "Сервер вернул неожиданный ответ. Результат не подтверждён; проверьте /wl_list.",
}
