# import unittest
# import asyncio
# import yaz
#
# from yaz_scripting_plugin import Scripting, SequentialScripting
# from yaz_scripting_plugin.error import InvalidReturnCodeError
#
#
# class TestScriptingCapture(unittest.TestCase):
#     def setUp(self):
#         self.scripting = yaz.get_plugin_instance(Scripting)
#         self.sequential_scripting = yaz.get_plugin_instance(SequentialScripting)
#         self.loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(self.loop)
#
#     def tearDown(self):
#         asyncio.set_event_loop(None)
#
#     def test_010_cmd(self):
#         """Should run a simple shell command"""
#
#         async def test():
#             stdout, stderr = await self.scripting.capture("echo -n 'Hello World!'")
#             self.assertEqual("Hello World!", stdout)
#             self.assertIsNone(stderr)
#
#         self.loop.run_until_complete(test())
#
#     def test_310_cmd__sequential(self):
#         """Should run a simple shell command (sequential)"""
#         stdout, stderr = self.sequential_scripting.capture("echo -n 'Hello World!'")
#         self.assertEqual("Hello World!", stdout)
#         self.assertIsNone(stderr)
#
#     def test_020_cmd_with_args(self):
#         """Should run a simple shell command with arguments"""
#
#         async def test():
#             stdout, stderr = await self.scripting.capture("sh -c 'echo -n \"Hello World!\"'")
#             self.assertEqual("Hello World!", stdout)
#             self.assertIsNone(stderr)
#
#         self.loop.run_until_complete(test())
#
#     def test_320_cmd_with_args__sequential(self):
#         """Should run a simple shell command with arguments (sequential)"""
#         stdout, stderr = self.sequential_scripting.capture("sh -c 'echo -n \"Hello World!\"'")
#         self.assertEqual("Hello World!", stdout)
#         self.assertIsNone(stderr)
#
#     def test_030_input(self):
#         """Should run a simple shell command with stdin"""
#
#         async def test():
#             stdout, stderr = await self.scripting.capture("sh", "echo -n \"Hello World!\"")
#             self.assertEqual("Hello World!", stdout)
#             self.assertIsNone(stderr)
#
#         self.loop.run_until_complete(test())
#
#     def test_330_input__sequential(self):
#         """Should run a simple shell command with stdin (sequential)"""
#         stdout, stderr = self.sequential_scripting.capture("sh", "echo -n \"Hello World!\"")
#         self.assertEqual("Hello World!", stdout)
#         self.assertIsNone(stderr)
#
#     def test_040_context(self):
#         """Should use Jinja to parse context"""
#
#         async def test_cmd_context(message):
#             stdout, stderr = await self.scripting.capture("echo -n {% quote %}{{ message }}{% end_quote %}", context={"message": message})
#             self.assertEqual(message, stdout)
#             self.assertIsNone(stderr)
#
#             stdout, stderr = await self.scripting.capture("echo -n {{ message|quote }}", context={"message": message})
#             self.assertEqual(message, stdout)
#             self.assertIsNone(stderr)
#
#         async def test_input_context(message):
#             stdout, stderr = await self.scripting.capture("sh", "echo -n {% quote %}{{ message }}{% end_quote %}", context={"message": message})
#             self.assertEqual(message, stdout)
#             self.assertIsNone(stderr)
#
#             stdout, stderr = await self.scripting.capture("sh", "echo -n {{ message|quote }}", context={"message": message})
#             self.assertEqual(message, stdout)
#             self.assertIsNone(stderr)
#
#         self.loop.run_until_complete(asyncio.gather(
#             test_cmd_context("Hello World!"),
#             test_input_context("Hello World!")))
#
#     def test_340_context__sequential(self):
#         """Should use Jinja to parse context (sequential)"""
#         # test cmd context
#         stdout, stderr = self.sequential_scripting.capture("echo -n {% quote %}{{ message }}{% end_quote %}", context={"message": "Hello World!"})
#         self.assertEqual("Hello World!", stdout)
#         self.assertIsNone(stderr)
#
#         stdout, stderr = self.sequential_scripting.capture("echo -n {{ message|quote }}", context={"message": "Hello World!"})
#         self.assertEqual("Hello World!", stdout)
#         self.assertIsNone(stderr)
#
#         # test input context
#         stdout, stderr = self.sequential_scripting.capture("sh", "echo -n {% quote %}{{ message }}{% end_quote %}", context={"message": "Hello World!"})
#         self.assertEqual("Hello World!", stdout)
#         self.assertIsNone(stderr)
#
#         stdout, stderr = self.sequential_scripting.capture("sh", "echo -n {{ message|quote }}", context={"message": "Hello World!"})
#         self.assertEqual("Hello World!", stdout)
#         self.assertIsNone(stderr)
#
#     def test_050_valid_codes(self):
#         """Should throw exception when code not valid"""
#
#         async def test_invalid_code():
#             with self.assertRaises(InvalidReturnCodeError) as context:
#                 await self.scripting.capture("sh", "echo -n {% quote %}STDOUT{% end_quote %} && (>&2 echo -n {% quote %}STDERR{% end_quote %}) && exit 1", merge_stderr=False)
#
#             error = context.exception
#             self.assertEqual(1, error.get_return_code())
#             self.assertEqual(b"STDOUT", error.get_stdout())
#             self.assertEqual(b"STDERR", error.get_stderr())
#
#         async def test_valid_code():
#             stdout, stderr = await self.scripting.capture("sh", "exit 1", valid_codes=(1,))
#             self.assertEqual("", stdout)
#             self.assertIsNone(stderr)
#
#         self.loop.run_until_complete(asyncio.gather(test_invalid_code(), test_valid_code()))
#
#     def test_350_valid_codes__sequential(self):
#         """Should throw exception when code not valid (sequential)"""
#         # test invalid code
#         with self.assertRaises(InvalidReturnCodeError) as context:
#             self.sequential_scripting.capture("sh", "echo -n {% quote %}STDOUT{% end_quote %} && (>&2 echo -n {% quote %}STDERR{% end_quote %}) && exit 1", merge_stderr=False)
#
#         error = context.exception
#         self.assertEqual(1, error.get_return_code())
#         self.assertEqual(b"STDOUT", error.get_stdout())
#         self.assertEqual(b"STDERR", error.get_stderr())
#
#         # test valid code
#         stdout, stderr = self.sequential_scripting.capture("sh", "exit 1", valid_codes=(1,))
#         self.assertEqual("", stdout)
#         self.assertIsNone(stderr)
#
#     def test_060_dry_run(self):
#         """Should not run when dry_run is enabled"""
#
#         async def test():
#             stdout, stderr = await self.scripting.capture("sh", "exit 1", dry_run=True)
#             self.assertEqual("", stdout)
#             self.assertIsNone(stderr)
#
#         self.loop.run_until_complete(test())
#
#     def test_360_dry_run__sequential(self):
#         """Should not run when dry_run is enabled (sequential)"""
#         stdout, stderr = self.sequential_scripting.capture("sh", "exit 1", dry_run=True)
#         self.assertEqual("", stdout)
#         self.assertIsNone(stderr)
#
#     def test_070_no_merge_stderr(self):
#         """Should exclude stderr when not merged"""
#
#         script = """
# import sys
#
# print("to stderr", file=sys.stderr)
# print("to stdout")
#
# exit(0)
#         """
#
#         async def test_with_merge():
#             stdout, stderr = await self.scripting.capture("python", script)
#             self.assertEqual("to stderr\nto stdout\n", stdout)
#             self.assertIsNone(stderr)
#
#         async def test_without_merge():
#             stdout, stderr = await self.scripting.capture("python", script, merge_stderr=False)
#             self.assertEqual("to stdout\n", stdout)
#             self.assertEqual("to stderr\n", stderr)
#
#         self.loop.run_until_complete(asyncio.gather(test_with_merge(), test_without_merge()))
#
#     def test_370_no_merge_stderr__sequential(self):
#         """Should exclude stderr when not merged (sequential)"""
#
#         script = """
# import sys
#
# print("to stderr", file=sys.stderr)
# print("to stdout")
#
# exit(0)
#             """
#
#         # test with merge
#         stdout, stderr = self.sequential_scripting.capture("python", script)
#         self.assertEqual("to stderr\nto stdout\n", stdout)
#         self.assertIsNone(stderr)
#
#         # test without merge
#         stdout, stderr = self.sequential_scripting.capture("python", script, merge_stderr=False)
#         self.assertEqual("to stdout\n", stdout)
#         self.assertEqual("to stderr\n", stderr)
