import logging
import logging.handlers
import os
import sys
from datetime import datetime
import ebooklib
from ebooklib import epub

from pytz import timezone, utc

"""
ConsoleColor.Black => "\x1B[30m",
            ConsoleColor.DarkRed => "\x1B[31m",
            ConsoleColor.DarkGreen => "\x1B[32m",
            ConsoleColor.DarkYellow => "\x1B[33m",
            ConsoleColor.DarkBlue => "\x1B[34m",
            ConsoleColor.DarkMagenta => "\x1B[35m",
            ConsoleColor.DarkCyan => "\x1B[36m",
            ConsoleColor.Gray => "\x1B[37m",
            ConsoleColor.Red => "\x1B[1m\x1B[31m",
            ConsoleColor.Green => "\x1B[1m\x1B[32m",
            ConsoleColor.Yellow => "\x1B[1m\x1B[33m",
            ConsoleColor.Blue => "\x1B[1m\x1B[34m",
            ConsoleColor.Magenta => "\x1B[1m\x1B[35m",
            ConsoleColor.Cyan => "\x1B[1m\x1B[36m",
            ConsoleColor.White => "\x1B[1m\x1B[37m",
"""

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    green = "\x1B[32m"
    # pathname filename
    #format = "[%(asctime)s|%(name)s|%(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    
    #__format = '[{yellow}%(asctime)s{reset}|{color}%(levelname)s{reset}|{green}%(name)s{reset} %(pathname)s:%(lineno)s] {color}%(message)s{reset}' if os.environ.get('LOGGER_PATHNAME', "False") == "True" else '[{yellow}%(asctime)s{reset}|{color}%(levelname)s{reset}|{green}%(name)s{reset} %(filename)s:%(lineno)s] {color}%(message)s{reset}'

    __format = '[{yellow}%(asctime)s{reset}|%(filename)s:%(lineno)s] {color}%(message)s{reset}' if os.environ.get('LOGGER_PATHNAME', "False") == "True" else '[{yellow}%(asctime)s{reset}|%(filename)s:%(lineno)s] {color}%(message)s{reset}'

    FORMATS = {
        logging.DEBUG: __format.format(color=grey, reset=reset, yellow=yellow, green=green),
        logging.INFO: __format.format(color=green, reset=reset, yellow=yellow, green=green),
        logging.WARNING: __format.format(color=yellow, reset=reset, yellow=yellow, green=green),
        logging.ERROR: __format.format(color=red, reset=reset, yellow=yellow, green=green),
        logging.CRITICAL: __format.format(color=bold_red, reset=reset, yellow=yellow, green=green)
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(name=None, log_path=None, file_logging=None):
    if os.environ.get('FF') == 'true':
        name = 'framework'
    if name == None:
        name = sys.argv[0].rsplit('.', 1)[0]
    logger = logging.getLogger(name)
    if not logger.handlers:
        level = logging.DEBUG
        logger.setLevel(level)
        formatter = logging.Formatter(u'[%(asctime)s|%(levelname)s|%(filename)s:%(lineno)s] %(message)s')
        def customTime(*args):
            utc_dt = utc.localize(datetime.utcnow())
            my_tz = timezone("Asia/Seoul")
            converted = utc_dt.astimezone(my_tz)
            return converted.timetuple()

        formatter.converter = customTime
        file_max_bytes = 1 * 1024 * 1024

        streamHandler = logging.StreamHandler()
        streamHandler.setFormatter(CustomFormatter())
        logger.addHandler(streamHandler)

        # 환경 변수 또는 파라미터로 파일 로깅 제어
        if file_logging is None:
            file_logging = os.environ.get('LOG_FILE', 'true').lower() == 'true'

        if file_logging:
            if log_path == None:
               log_path = os.path.join(os.getcwd(), 'log')
            os.makedirs(log_path, exist_ok=True)
            fileHandler = logging.handlers.RotatingFileHandler(filename=os.path.join(log_path, f'{name}.log'), maxBytes=file_max_bytes, backupCount=5, encoding='utf8', delay=True)
            fileHandler.setFormatter(formatter)
            logger.addHandler(fileHandler)

    return logger

def get_epub_info(epub_path):
    book = epub.read_epub(epub_path)
    
    epub_info = {
        "title": "",
        "author": "",
        "publisher": ""
    }
    
    title = book.get_metadata('DC', 'title')
    if title:
        epub_info["title"] = title[0][0]
    
    creator = book.get_metadata('DC', 'creator')
    if creator:
        epub_info["author"] = creator[0][0]
    
    publisher = book.get_metadata('DC', 'publisher')
    if publisher:
        epub_info["publisher"] = publisher[0][0]
    
    return epub_info


def d(data):
    if type(data) in [type({}), type([])]:
        import json
        try:
            return '\n' + json.dumps(data, indent=4, ensure_ascii=False)
        except:
            return data
    else:
        return str(data)


default_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language' : 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

import time
from functools import wraps

logger = get_logger()

def pt(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        start = time.time()
        logger.debug(f"FUNC START [{f.__name__}]")
        result = f(*args, **kwds)
        elapsed = time.time() - start
        logger.debug(f"FUNC END [{f.__name__}] {elapsed}")
        return result
    return wrapper

def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language' : 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }