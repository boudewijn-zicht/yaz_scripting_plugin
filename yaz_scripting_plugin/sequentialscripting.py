import asyncio

from .scripting import Scripting

class SequentialScripting(Plugin):
    def __init__(self, scripting: Scripting):
        self.scripting = scripting

    def call(self, *args, **kwargs):
        """Sequential version of the Scripting.call method"""
        current_loop = asyncio.get_event_loop()
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(self.scripting.call(*args, **kwargs))
        finally:
            asyncio.set_event_loop(current_loop)

    def raw(self, *args, **kwargs):
        """Sequential version of the Scripting.raw method"""
        current_loop = asyncio.get_event_loop()
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(self.scripting.raw(*args, **kwargs))
        finally:
            asyncio.set_event_loop(current_loop)
