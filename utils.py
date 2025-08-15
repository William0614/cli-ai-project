import sys
import itertools
import threading
import time
from colorama import Fore, init

init(autoreset=True)

class Spinner:
    def __init__(self, message: str):
        self.spinner = itertools.cycle(["-", "/", "|", "\\"])
        self.message = message
        self.running = False
        self.thread = None

    def _spin(self):
        while self.running:
            sys.stdout.write(f"\r{Fore.YELLOW}{self.message} {next(self.spinner)}")
            sys.stdout.flush()
            time.sleep(0.1)
        # Clear the line completely after stopping
        sys.stdout.write(f"\r{' ' * (len(self.message) + 2)}\r")
        sys.stdout.flush()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def set_message(self, message: str):
        self.message = message

