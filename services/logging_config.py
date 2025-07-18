import logging
import json
import os

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
            "threadName": record.threadName,
            "processName": record.processName,
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_record["stack_info"] = self.formatStack(record.stack_info)
        for key, value in record.__dict__.items():
            if key not in ['name', 'levelname', 'pathname', 'lineno', 'asctime', 'message', 'args',
                           'exc_info', 'exc_text', 'stack_info', 'levelno', 'created', 'msecs',
                           'relativeCreated', 'thread', 'threadName', 'process', 'processName',
                           'funcName', 'filename', 'module', 'lineno', 'msg', 'stack_info', 'sinfo', 'levelname']:
                log_record[key] = value
        
        return json.dumps(log_record)

def setup_logging(service_name: str):
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(level=log_level)
    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)

    console_handler = logging.StreamHandler()
    formatter = JsonFormatter(datefmt='%Y-%m-%dT%H:%M:%SZ')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.propagate = False

    return logger
