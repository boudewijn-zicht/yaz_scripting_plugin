import asyncio
import unittest
import yaz
import yaz_scripting_plugin

class TestShell(unittest.TestCase):
    def setUp(self):
        self.shell = yaz.get_plugin_instance(yaz_scripting_plugin.Shell)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        asyncio.set_event_loop(None)

    def test_010_get(self):
        async def test():
            stdout, stderr = await self.shell.get("python -c {% quote %}import sys; print({% quote %}to stdout{% end_quote %}); print({% quote %}to stderr{% end_quote %}, file=sys.stderr){% end_quote %}")
            self.assertEqual("to stdout\n", stdout)
            self.assertEqual("to stderr\n", stderr)

        self.loop.run_until_complete(test())
