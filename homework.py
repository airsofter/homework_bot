import os
import logging
# from logging.handlers import RotatingFileHandler
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
# from telegram.ext import Updater, CommandHandler
import telegram


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='program.log',
    level=logging.DEBUG
)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверка наличия токенов"""
    check = True
    if not PRACTICUM_TOKEN:
        check = False
        logging.critical('Отсутствуют переменная PRACTICUM_TOKEN')
        raise Exception('Отсутствует PRACTICUM_TOKEN')
    if not TELEGRAM_TOKEN:
        check = False
        logging.critical('Отсутствуют переменная TELEGRAM_TOKEN')
        raise Exception('Отсутствует TELEGRAM_TOKEN')
    if not TELEGRAM_CHAT_ID:
        check = False
        logging.critical('Отсутствуют переменная TELEGRAM_CHAT_ID')
        raise Exception('Отсутствует TELEGRAM_CHAT_ID')

    return check


def send_message(bot, message):
    """Отправка сообщения"""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.debug('Сообщение отправлено')
    except Exception as error:
        logging.error(f'Не удалось отправить сообщение. {error}')


def get_api_answer(timestamp) -> dict:
    """Запрос к API"""
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params={'from_date': timestamp})
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')

    if response.status_code != HTTPStatus.OK:
        logging.error('Нет доступа к API')
        raise requests.RequestException('Нет доступа к API')

    return response.json()


def check_response(response) -> list:
    """Проверка ответа API на соответствие документации"""
    if type(response) is not dict:
        logging.error('Объект response не является словарем')
        raise TypeError('Объект response не является словарем')
    if 'homeworks' not in response.keys():
        logging.error('Нет ключа "homeworks"')
        raise KeyError('Нет ключа "homeworks"')
    if type(response['homeworks']) is not list:
        logging.error('Данные ответа не являются списком')
        raise TypeError('Данные ответа не являются списком')

    return response['homeworks']


def parse_status(homework) -> str:
    """Извлечение информации о домашней работе"""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        logging.error('Отсутствует ключ "homework_name"')
        raise KeyError('Отсутствует ключ "homework_name"')
    if homework_status is None:
        logging.error('Отсутствует ключ "homework_status"')
        raise KeyError('Отсутствует ключ "homework_status"')
    if homework_status not in HOMEWORK_VERDICTS.keys():
        logging.error('Недокументированный статус')
        raise KeyError('Недокументированный статус')

    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        while True:
            try:
                timestamp = int(time.time())
                response = get_api_answer(timestamp)
                homeworks = check_response(response)
                if homeworks:
                    message = parse_status(homeworks[0])
                    send_message(bot, message)
                else:
                    logging.debug('Статус работы не изменился')
                    raise Exception('Статус работы не изменился')

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
            finally:
                time.sleep(RETRY_PERIOD)
    else:
        logging.critical('Отсутствуют переменные окружения')


if __name__ == '__main__':
    main()
