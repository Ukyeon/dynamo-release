import functools
import logging
from contextlib import contextmanager
import time


def silence_logger(name):
    """Given a logger name, silence it completely.

    :param name: name of the logger
    :type name: str
    """
    package_logger = logging.getLogger(name)
    package_logger.setLevel(logging.CRITICAL + 100)
    package_logger.propagate = False


def format_logging_message(msg, logging_level, indent_level=1, indent_space_num=6):
    indent_str = "-" * indent_space_num
    prefix = indent_str * indent_level
    prefix = "|" + prefix[1:]
    if logging_level == logging.INFO:
        prefix += ">"
    elif logging_level == logging.WARNING:
        prefix += "?"
    elif logging_level == logging.CRITICAL:
        prefix += "!!"
    new_msg = prefix + " " + str(msg)
    return new_msg


class Logger:
    """Dynamo-specific logger that sets up logging for the entire package."""

    FORMAT = "%(message)s"

    def __init__(self, namespace="main", level=None):

        self.namespace = namespace
        self.logger = logging.getLogger(namespace)
        self.previous_timestamp = time.time()  # in seconds
        self.time_passed = 0

        # To-do: add file handler in future
        # e.g. logging.StreamHandler(None) if log_file_path is None else logging.FileHandler(name)
        self.logger_stream_handler = logging.StreamHandler()
        self.logger_stream_handler.setFormatter(logging.Formatter(self.FORMAT))

        # ensure only one stream handler exisits in the logger
        if len(self.logger.handlers) == 0:
            self.logger.addHandler(self.logger_stream_handler)

        self.logger.propagate = False

        # Other global initialization
        silence_logger("anndata")
        silence_logger("h5py")
        silence_logger("numba")
        silence_logger("pysam")
        silence_logger("pystan")

        if not (level is None):
            self.logger.setLevel(level)
        else:
            self.logger.setLevel(logging.INFO)

    def namespaced(self, namespace):
        """Function decorator to set the logging namespace for the duration of
        the function.

        :param namespace: the namespace
        :type namespace: str
        """

        def wrapper(func):
            @functools.wraps(func)
            def inner(*args, **kwargs):
                previous = self.namespace
                try:
                    self.namespace = namespace
                    return func(*args, **kwargs)
                finally:
                    self.namespace = previous

            return inner

        return wrapper

    @contextmanager
    def namespaced_context(self, namespace):
        """Context manager to set the logging namespace.

        :param namespace: the namespace
        :type namespace: str
        """
        previous = self.namespace
        self.namespace = namespace
        yield
        self.namespace = previous

    def namespace_message(self, message):
        """Add namespace information at the beginning of the logging message.

        :param message: the logging message
        :type message: str

        :return: namespaced message
        :rtype: string
        """
        return f"[{self.namespace}] {message}"

    def setLevel(self, *args, **kwargs):
        return self.logger.setLevel(*args, **kwargs)

    def debug(self, message, indent_level=1, *args, **kwargs):
        message = format_logging_message(message, logging.DEBUG, indent_level=indent_level)
        return self.logger.debug(message, *args, **kwargs)

    def info(self, message, indent_level=1, *args, **kwargs):
        message = format_logging_message(message, logging.INFO, indent_level=indent_level)
        return self.logger.info(message, *args, **kwargs)

    def warning(self, message, indent_level=1, *args, **kwargs):
        message = format_logging_message(message, logging.WARNING, indent_level=indent_level)
        return self.logger.warning(message, *args, **kwargs)

    def exception(self, message, indent_level=1, *args, **kwargs):
        message = format_logging_message(message, logging.ERROR, indent_level=indent_level)
        return self.logger.exception(message, *args, **kwargs)

    def critical(self, message, indent_level=1, *args, **kwargs):
        message = format_logging_message(message, logging.CRITICAL, indent_level=indent_level)
        return self.logger.critical(message, *args, **kwargs)

    def error(self, message, indent_level=1, *args, **kwargs):
        message = format_logging_message(message, logging.ERROR, indent_level=indent_level)
        return self.logger.error(message, *args, **kwargs)

    def info_insert_adata(self, key, adata_attr="obsm", indent_level=1, *args, **kwargs):
        message = "<insert> %s to %s in AnnData Object." % (key, adata_attr)
        message = format_logging_message(message, logging.INFO, indent_level=indent_level)
        return self.logger.error(message, *args, **kwargs)

    def log_time(self):
        now = time.time()
        self.time_passed = now - self.previous_timestamp
        self.previous_timestamp = now
        return self.time_passed

    def report_progress(self, percent):
        saved_terminator = self.logger_stream_handler.terminator
        self.logger_stream_handler.terminator = ""
        message = "\r" + format_logging_message(f"in progress: {percent}%", logging_level=logging.INFO)
        self.logger.info(message)
        self.logger_stream_handler.flush()
        self.logger_stream_handler.terminator = saved_terminator

    def finish_progress(self, progress_name="", time_unit="s"):
        self.log_time()
        self.logger.info("\r")

        if time_unit == "s":
            self.info("%s finished [%.4fs]" % (progress_name, self.time_passed))
        elif time_unit == "ms":
            self.info("%s finished [%.4fms]" % (progress_name, self.time_passed * 1e3))
        else:
            raise NotImplementedError
        self.logger_stream_handler.flush()


class LoggerManager:

    main_logger = Logger("Dynamo")

    @staticmethod
    def get_main_logger():
        return LoggerManager.main_logger

    @staticmethod
    def get_logger(namespace):
        return Logger(namespace)