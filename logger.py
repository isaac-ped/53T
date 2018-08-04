import logging

def init_logfile(filename):
    logging.basicConfig(filename=filename,level=logging.DEBUG)

def init_stdoutlog():
    logging.basicConfig(level=logging.DEBUG)

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
