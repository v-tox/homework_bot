class CodeStatusError(Exception):
    """Hеверный код ответа API."""
    pass


class HTTPError(Exception):
    """Ошибка соединения."""
    pass
