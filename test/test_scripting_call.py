import unittest
import asyncio
from yaz_scripting_plugin import Scripting
from yaz_scripting_plugin.streamer import Output


class TestScriptingCall(unittest.TestCase):
    def setUp(self):
        self.scripting = Scripting()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def test_010_read_line(self):
        """Should read lines from stream"""

        async def test():
            streamer = await self.scripting.call("python -c {% quote %}for i in range(42): print(i){% end_quote %}")

            for i in range(42):
                output = await streamer.read_line()
                self.assertEqual("stdout", output.source)
                self.assertEqual(str(i), output.value)
                self.assertTrue(output.has_more)
                self.assertTrue(output)

            output = await streamer.read_line()
            self.assertEqual("return_code", output.source)
            self.assertEqual(0, output.value)
            self.assertFalse(output.has_more)
            self.assertFalse(output)

        self.loop.run_until_complete(test())

    def test_020_iter_lines(self):
        """Should iterate over lines in stream"""

        async def test():
            streamer = await self.scripting.call("python -c {% quote %}for i in range(42): print(i){% end_quote %}")

            i = 0
            async for output in streamer.iter_lines():
                self.assertIsInstance(output, Output)
                self.assertEqual("stdout", output.source)
                self.assertEqual(str(i), output.value)
                i += 1

        self.loop.run_until_complete(test())

    def test_030_write_lines(self):
        """Should write lines to stream"""

        async def test():
            # streamer = await self.scripting.call("python -c {% quote %}import sys; for line in sys.stdin: print(line){% end_quote %}")
            streamer = await self.scripting.call("cat")
            await streamer.write_lines([b"Hello\n", b"World\n", b"!\n"], True)

            output = await streamer.read_line(False)
            self.assertIsInstance(output, Output)
            self.assertEqual("stdout", output.source)
            self.assertEqual("Hello\n", output.value)

            output = await streamer.read_line(False)
            self.assertIsInstance(output, Output)
            self.assertEqual("stdout", output.source)
            self.assertEqual("World\n", output.value)

            output = await streamer.read_line(False)
            self.assertIsInstance(output, Output)
            self.assertEqual("stdout", output.source)
            self.assertEqual("!\n", output.value)

            output = await streamer.read_line(False)
            self.assertIsInstance(output, Output)
            self.assertEqual("return_code", output.source)
            self.assertEqual(0, output.value)

            self.assertEqual(0, streamer.get_return_code())

        self.loop.run_until_complete(test())