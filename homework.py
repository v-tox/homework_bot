import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import CodeStatusError, HTTPError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: int = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверить, что токены доступны."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message: str):
    """Отправить сообщений в ТГ."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Бот отправил сообщение в чат')
    except Exception:
        logging.error('Сбой при отправке сообщения в чат')


def get_api_answer(timestamp):
    """Сделать запрос к эндпоинту API."""
    logging.debug('Запрос к API')
    arguments = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        response = requests.get(**arguments)
    except Exception as error:
        text = (
            'Код ответа не 200. Запрос: {url}, {headers}, {params}.'
        ).format(**arguments)
        raise CodeStatusError(text, error)
    if response.status_code != HTTPStatus.OK:
        raise HTTPError(f'Ошибка соединения {response.status_code},'
                        f'{response.text}')
    return response.json()


def check_response(response):
    """Проверить ответ API."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип ответа')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError(f'Ключ не найден в {response}')
    homeworks = response.get('homeworks')
    if not isinstance(response["homeworks"], list):
        raise TypeError('Ключ homeworks это не список')
    if not homeworks:
        raise KeyError('В ключе нет значений')
    return homeworks


def parse_status(homework):
    """Получить инф о статусе домашки."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутствует')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if not status:
        raise KeyError('Ключ status отсутствует')
    if status not in (HOMEWORK_VERDICTS):
        logging.error('Неизвестный статус домашки')
        raise ValueError('Неизвестный статус домашки')
    verdict = HOMEWORK_VERDICTS[homework.get('status')]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствуют переменные окружения')
        sys.exit('Отсутствуют переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homeworks = check_response(response)
            if not homeworks:
                logging.debug('Нет новых статусов')
            else:
                message = parse_status(homeworks[0])
                if message:
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
