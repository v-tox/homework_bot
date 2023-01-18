import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем, что токены доступны."""
    return all((TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляем сообщение в чат."""
    try:
        logging.debug('Тестовая отправка')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Отправлено сообщение {message}')
    except Exception as error:
        logging.error(f'Ошибка {error}')
        raise exceptions.TelegramMessageSendError(
            f'Ошибка отправки {error}'
        )


def get_api_answer(timestamp):
    """Запрос к эндпоинту API."""
    timestamp = int(time.time())
    params_request_api = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    message = (
        'Запрос к API: {url}, {headers}, {params}.'
    ).format(**params_request_api)
    logging.info(message)
    try:
        response = requests.get(**params_request_api)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.ConnectionError(
                f'API не возвращает 200 '
                f'Код ответа: {response.status_code}. '
                f'Причина: {response.reason}. '
                f'Текст: {response.text}.'
            )
        return response.json()
    except Exception as error:
        message = (
            'API не возвращает 200. Запрос: {url}, {headers}, {params}.'
        ).format(**params_request_api)
        raise exceptions.ConnectionError(message, error)


def check_response(response):
    """Проверяем, что ответ API корректен."""
    logging.debug('Начало проверки')
    if not isinstance(response, dict):
        raise TypeError('Неверный тип ответа API')
    if 'homeworks' not in response or 'current_date' not in response:
        raise exceptions.EmptyResponseFromAPI('Пустой ответ API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    return homeworks


def parse_status(homework):
    """Распарсить ответ."""
    if 'homework_name' not in homework:
        raise KeyError(
            'В ответе нетт homework_name'
        )
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {homework_status}')
    return ('Изменился статус проверки работы "{homework_name}" {verdict}'
            ).format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS[homework_status]
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствие обязательных переменных окружения'
        )
        sys.exit('Завершение работы')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                status = parse_status(homeworks[0])
                send_message(bot, status)
            timestamp = response['current_date']
        except exceptions.TelegramMessageSendError:
            logging.error('Ошибка при отправке сообщения в Telegram')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='homework.log',
        format='%(asctime)s, %(levelname)s, '
               '%(message)s, %(funcName)s, %(lineno)d'
    )
    handler = (
        logging.FileHandler('output.log'),
        logging.StreamHandler(sys.stdout)
    )
    main()
