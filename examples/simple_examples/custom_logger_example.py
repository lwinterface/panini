import logging
from panini import app as panini_app
from panini.utils.logger import get_logger
from panini.utils.logger import _get_logger_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = panini_app.App(
    service_name="custom_logger_example",
    host="127.0.0.1",
    port=4222,
    custom_logger=logger
)

log = app.logger

# will log to logger_example.log
log.debug("Debug text (not shown in console)")
log.info("Info text")
log.warning("Warning text")
log.error("Error text")  # will be also logged to errors.log
try:
    a = 1 // 0
except ZeroDivisionError:
    log.exception("Exception method will show traceback")

app_log = get_logger("panini")

app_log.info("Log to panini.log")


if __name__ == "__main__":
    app.start()  # not important here, only important for logger_in_separate_process
