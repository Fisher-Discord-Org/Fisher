import logging


class ColorFormatter(logging.Formatter):
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD_RED = "\033[1;31m"
    BLUE = "\033[94m"
    RESET = "\033[0m"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datefmt = self.GREEN + self.datefmt + self.RESET
        self.datefmt = self.datefmt.replace("%Z", self.RESET + "%Z" + self.GREEN)
        self._colors = {
            "DEBUG": self.BLUE,
            "INFO": self.GREEN,
            "WARNING": self.YELLOW,
            "ERROR": self.RED,
            "CRITICAL": self.BOLD_RED,
        }

    def format(self, record):
        record.name = self.YELLOW + record.name + self.RESET
        record.levelname = (
            self._colors[record.levelname] + record.levelname + self.RESET
        )
        return super().format(record)
