import logging
from logging import Formatter

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('debug.log.example', mode='a', encoding='UTF-8')
logger.addHandler(handler)
formatter = Formatter(
    '{asctime}, {levelname}, {message}', style='{'
)
handler.setFormatter(formatter)


class FailedRequestApi(Exception):
    """Исключение для неудачного запроса."""
    pass


class MatchNotFound(Exception):
    """Исключение для неудачного сопоставления."""
    pass


class TimeZoneNotFound(Exception):
    """Исключение для отсутствующего ключа."""
    pass
