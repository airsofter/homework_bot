import logging
import logging.config
import time
from http import HTTPStatus

import requests
import telegram

from config import (PRACTICUM_TOKEN, TELEGRAM_TOKEN,
                    TELEGRAM_CHAT_ID, RETRY_PERIOD,
                    ENDPOINT, HEADERS,
                    HOMEWORK_VERDICTS,)


logging.config.fileConfig('logger.conf', disable_existing_loggers=False)

logger = logging.getLogger(__name__)


def check_tokens() -> bool:
    """Проверка наличия токенов."""
    check = True
    if not PRACTICUM_TOKEN:
        check = False
        logger.critical('Отсутствуют переменная PRACTICUM_TOKEN')
        raise Exception('Отсутствует PRACTICUM_TOKEN')
    if not TELEGRAM_TOKEN:
        check = False
        logger.critical('Отсутствуют переменная TELEGRAM_TOKEN')
        raise Exception('Отсутствует TELEGRAM_TOKEN')
    if not TELEGRAM_CHAT_ID:
        check = False
        logger.critical('Отсутствуют переменная TELEGRAM_CHAT_ID')
        raise Exception('Отсутствует TELEGRAM_CHAT_ID')
    return check


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug('Сообщение отправлено')
    except Exception as error:
        logger.error(f'Не удалось отправить сообщение. {error}')


def get_api_answer(timestamp):
    """Запрос к API."""
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params={'from_date': timestamp})
    except Exception as error:
        logger.error(f'Ошибка при запросе к основному API: {error}. '
                     f'Данные: ENDPOINT={ENDPOINT}, '
                     f'headers={HEADERS}, '
                     f'from_date={timestamp}')

    if response.status_code != HTTPStatus.OK:
        logger.error(f'Нет доступа к API. Код ответа: {response.status_code}')
        raise requests.RequestException('Нет доступа к API')
    try:
        return response.json()  # вынес в try возвращение json
    except Exception as error:
        logger.error(f'Ответ сервера не в формате json. {error}')


def check_response(response) -> list:
    """Проверка ответа API на соответствие документации."""
    if type(response) is not dict:
        logger.error('Объект response не является словарем')
        raise TypeError('Объект response не является словарем')
    if 'homeworks' not in response.keys():
        logger.error('Нет ключа "homeworks"')
        raise KeyError('Нет ключа "homeworks"')
    if type(response['homeworks']) is not list:
        logger.error('Данные ответа не являются списком')
        raise TypeError('Данные ответа не являются списком')
    return response['homeworks']


def parse_status(homework) -> str:
    """Извлечение информации о домашней работе."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        logger.error('Отсутствует ключ "homework_name". '
                     f'homework_name={homework_name}')
        raise KeyError('Отсутствует ключ "homework_name"')
    if homework_status is None:
        logger.error('Отсутствует ключ "homework_status". '
                     f'homework_status={homework_status}')
        raise KeyError('Отсутствует ключ "homework_status"')
    if homework_status not in HOMEWORK_VERDICTS.keys():
        logger.error(
            f'Недокументированный статус. homework_status={homework_status}'
        )
        raise KeyError('Недокументированный статус')

    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        error_message = ''
        while True:
            try:
                timestamp = int(time.time())
                response = get_api_answer(timestamp)
                homeworks = check_response(response)
                if homeworks:
                    message = parse_status(homeworks[0])
                    send_message(bot, message)
                else:
                    logger.debug('Статус работы не изменился')
                    raise Exception('Статус работы не изменился')

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                if message != error_message:
                    error_message = message
                    send_message(bot, message)
            finally:
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
