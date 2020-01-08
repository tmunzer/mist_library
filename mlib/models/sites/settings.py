import json
from .rogue import Rogue

try:
    from config import log_level
except:
    log_level = 6
finally:
    from mlib.__debug import Console
    console = Console(log_level)


class Settings:

    def __init__(self):
        self.rogue = Rogue()

        
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__)