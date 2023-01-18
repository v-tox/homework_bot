class NotForSending(Exception):
    """Не для пересылки."""
    pass


class TelegramMessageSendError(NotForSending):
    """Ошибка на стороне Telegram."""
    pass


class ConnectionError(Exception):
    """Ошибка, неверный код ответа от API."""
    pass


class EmptyResponseFromAPI(Exception):
    """Пустой ответ от API."""
    pass
