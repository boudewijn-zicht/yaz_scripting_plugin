import asyncio
from yaz.plugin import Plugin
from .scripting import Scripting


class SequentialScripting(Plugin):
    def __init__(self, scripting: Scripting):
        self.scripting = scripting

    def capture(self, *args, **kwargs):
        """Sequential version of the Scripting.capture method"""
        current_loop = asyncio.get_event_loop()
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(self.scripting.capture(*args, **kwargs))
        finally:
            asyncio.set_event_loop(current_loop)

    def interact(self, *args, **kwargs):
        """Sequential version of the Scripting.interact method"""
        current_loop = asyncio.get_event_loop()
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(self.scripting.interact(*args, **kwargs))
        finally:
            asyncio.set_event_loop(current_loop)

    def call(self, *args, **kwargs):
        """Sequential version of the Scripting.call method"""
        current_loop = asyncio.get_event_loop()
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(self.scripting.call(*args, **kwargs))
        finally:
            asyncio.set_event_loop(current_loop)
