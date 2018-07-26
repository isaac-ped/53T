import logging

logging.basicConfig(filename='53T.log',level=logging.DEBUG)

def log(msg, *args, **kwargs):
    try:
        logging.debug(msg, *args, **kwargs)
    except Exception as e:
        logging.warn("Error logging")

def log_warn(*args, **kwargs):
    try:
        logging.warn(*args, **kwargs)
    except Exception as e:
        logging.warn("Error logging: %s", args)
