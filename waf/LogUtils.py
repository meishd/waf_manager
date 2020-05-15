import logging
from logging.handlers import RotatingFileHandler
import os

log_dir = os.getenv('LOG_DIR')
log_level = os.getenv('LOG_LEVEL')
log_file_error = os.path.join(log_dir, 'error.log')
log_file_info = os.path.join(log_dir, 'info.log')
log_file_maxbytes = 100 * 1024 * 1024


class InfoFilter(logging.Filter):
    def filter(self, record):
        if logging.INFO <= record.levelno < logging.ERROR:
            return super().filter(record)
        else:
            return 0

class LogUtils():

    @classmethod
    def init_app(cls,app):
        logging.basicConfig(level=logging.INFO)
        formatter_info = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        formatter_error = logging.Formatter('%(asctime)s %(levelname)s %(pathname)s %(lineno)s %(message)s')

        # FileHandler Info
        file_handler_info = RotatingFileHandler(filename=log_file_info)
        file_handler_info.setFormatter(formatter_info)
        file_handler_info.setLevel(logging.INFO)
        info_filter = InfoFilter()
        file_handler_info.addFilter(info_filter)
        app.logger.addHandler(file_handler_info)

        # FileHandler Error
        file_handler_error = RotatingFileHandler(filename=log_file_error)
        file_handler_error.setFormatter(formatter_error)
        file_handler_error.setLevel(logging.ERROR)
        app.logger.addHandler(file_handler_error)
