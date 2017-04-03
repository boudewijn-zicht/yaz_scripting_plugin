import unittest
import asyncio
import yaz

from yaz_scripting_plugin import Scripting, SequentialScripting
from yaz_scripting_plugin.error import InvalidReturnCodeError


class TestScriptingCapture(unittest.TestCase):
    def setUp(self):
        self.scripting = yaz.get_plugin_instance(Scripting)
        self.sequential_scripting = yaz.get_plugin_instance(SequentialScripting)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        asyncio.set_event_loop(None)

    def test_010_cmd(self):
        """Should run a simple shell command"""

        async def test():
            result = await self.scripting.capture("echo -n 'Hello World!'")
            self.assertEqual("Hello World!", result)

        self.loop.run_until_complete(test())

    def test_310_cmd__sequential(self):
        """Should run a simple shell command (sequential)"""
        result = self.sequential_scripting.capture("echo -n 'Hello World!'")
        self.assertEqual("Hello World!", result)

    def test_020_cmd_with_args(self):
        """Should run a simple shell command with arguments"""

        async def test():
            result = await self.scripting.capture("sh -c 'echo -n \"Hello World!\"'")
            self.assertEqual("Hello World!", result)

        self.loop.run_until_complete(test())

    def test_320_cmd_with_args__sequential(self):
        """Should run a simple shell command with arguments (sequential)"""
        result = self.sequential_scripting.capture("sh -c 'echo -n \"Hello World!\"'")
        self.assertEqual("Hello World!", result)

    def test_030_input(self):
        """Should run a simple shell command with stdin"""

        async def test():
            result = await self.scripting.capture("sh", "echo -n \"Hello World!\"")
            self.assertEqual("Hello World!", result)

        self.loop.run_until_complete(test())

    def test_330_input__sequential(self):
        """Should run a simple shell command with stdin (sequential)"""
        result = self.sequential_scripting.capture("sh", "echo -n \"Hello World!\"")
        self.assertEqual("Hello World!", result)

    def test_040_context(self):
        """Should use Jinja to parse context"""

        async def test_cmd_context(message):
            result = await self.scripting.capture("echo -n {% quote %}{{ message }}{% end_quote %}", context={"message": message})
            self.assertEqual(message, result)

            result = await self.scripting.capture("echo -n {{ message|quote }}", context={"message": message})
            self.assertEqual(message, result)

        async def test_input_context(message):
            result = await self.scripting.capture("sh", "echo -n {% quote %}{{ message }}{% end_quote %}", context={"message": message})
            self.assertEqual(message, result)

            result = await self.scripting.capture("sh", "echo -n {{ message|quote }}", context={"message": message})
            self.assertEqual(message, result)

        self.loop.run_until_complete(asyncio.gather(
            test_cmd_context("Hello World!"),
            test_input_context("Hello World!")))

    def test_340_context__sequential(self):
        """Should use Jinja to parse context (sequential)"""
        # test cmd context
        result = self.sequential_scripting.capture("echo -n {% quote %}{{ message }}{% end_quote %}", context={"message": "Hello World!"})
        self.assertEqual("Hello World!", result)

        result = self.sequential_scripting.capture("echo -n {{ message|quote }}", context={"message": "Hello World!"})
        self.assertEqual("Hello World!", result)

        # test input context
        result = self.sequential_scripting.capture("sh", "echo -n {% quote %}{{ message }}{% end_quote %}", context={"message": "Hello World!"})
        self.assertEqual("Hello World!", result)

        result = self.sequential_scripting.capture("sh", "echo -n {{ message|quote }}", context={"message": "Hello World!"})
        self.assertEqual("Hello World!", result)

    def test_050_valid_codes(self):
        """Should throw exception when code not valid"""

        async def test_invalid_code():
            try:
                await self.scripting.capture("sh", "echo -n {% quote %}STDOUT{% end_quote %} && (>&2 echo -n {% quote %}STDERR{% end_quote %}) && exit 1", merge_stderr=False)
                self.assertTrue(False, "Expected a RuntimeError")
            except InvalidReturnCodeError as error:
                self.assertEqual(1, error.get_return_code())
                self.assertEqual(b"STDOUT", error.get_stdout())
                self.assertEqual(b"STDERR", error.get_stderr())

        async def test_valid_code():
            result = await self.scripting.capture("sh", "exit 1", valid_codes=(1,))
            self.assertEqual("", result)

        self.loop.run_until_complete(asyncio.gather(test_invalid_code(), test_valid_code()))

    def test_350_valid_codes__sequential(self):
        """Should throw exception when code not valid (sequential)"""
        # test invalid code
        try:
            self.sequential_scripting.capture("sh", "echo -n {% quote %}STDOUT{% end_quote %} && (>&2 echo -n {% quote %}STDERR{% end_quote %}) && exit 1", merge_stderr=False)
            self.assertTrue(False, "Expected a RuntimeError")
        except InvalidReturnCodeError as error:
            self.assertEqual(1, error.get_return_code())
            self.assertEqual(b"STDOUT", error.get_stdout())
            self.assertEqual(b"STDERR", error.get_stderr())

        # test valid code
        result = self.sequential_scripting.capture("sh", "exit 1", valid_codes=(1,))
        self.assertEqual("", result)

    def test_060_dry_run(self):
        """Should not run when dry_run is enabled"""

        async def test():
            result = await self.scripting.capture("sh", "exit 1", dry_run=True)
            self.assertEqual("", result)

        self.loop.run_until_complete(test())

    def test_360_dry_run__sequential(self):
        """Should not run when dry_run is enabled (sequential)"""
        result = self.sequential_scripting.capture("sh", "exit 1", dry_run=True)
        self.assertEqual("", result)

    def test_070_merge_stderr(self):
        """Should exclude stderr when not merged"""

        script = """
import sys

print("to stderr", file=sys.stderr)
print("to stdout")

exit(0)
        """

        async def test_with_merge():
            result = await self.scripting.capture("python", script)
            self.assertEqual("to stderr\nto stdout\n", result)

        async def test_without_merge():
            result = await self.scripting.capture("python", script, merge_stderr=False)
            self.assertEqual("to stdout\n", result)

        self.loop.run_until_complete(asyncio.gather(test_with_merge(), test_without_merge()))

    def test_370_merge_stderr__sequential(self):
        """Should exclude stderr when not merged (sequential)"""

        script = """
import sys

print("to stderr", file=sys.stderr)
print("to stdout")

exit(0)
            """

        # test with merge
        result = self.sequential_scripting.capture("python", script)
        self.assertEqual("to stderr\nto stdout\n", result)

        # test without merge
        result = self.sequential_scripting.capture("python", script, merge_stderr=False)
        self.assertEqual("to stdout\n", result)
