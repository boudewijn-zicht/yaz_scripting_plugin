import asyncio
import shlex
import typing
import yaz
import yaz_templating_plugin

from .log import logger
from .error import InvalidReturnCodeError


class Shell(yaz.BasePlugin):
    def __init__(self):
        self._screen_count = 0

    @yaz.dependency
    def set_templating(self, templating: yaz_templating_plugin.Templating):
        self.templating = templating

    async def get(self,
                  cmd: str,
                  input: typing.Optional[str] = None,
                  context: typing.Optional[dict] = None,
                  *,
                  valid_codes: typing.Tuple[int, ...] = (0,)
                  ) -> (str, str):
        """
        Execute and return (stdout, stderr)
        """
        cmd = self.templating.render(cmd, context)
        if input is not None:
            input = self.templating.render(input, context)
        logger.info(self.templating.render("{% if input %}echo {{ input|quote }} | {% endif %}{{ cmd }}", dict(input=input, cmd=cmd)))

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=None if input is None else asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(None if input is None else input.encode())

        if process.returncode not in valid_codes:
            logger.warning("Process [%s] ended with invalid exit code %d", cmd, process.returncode)
            raise InvalidReturnCodeError(process.returncode, stdout, stderr)

        return stdout.decode(), stderr.decode()

    async def run(self,
                  cmd: str,
                  input: typing.Optional[str] = None,
                  context: typing.Optional[dict] = None,
                  *,
                  valid_codes: typing.Tuple[int, ...] = (0,)
                  ):
        """
        Execute and interact in a separate window or screen
        """
        process_exit = asyncio.Event()
        reader, writer = await self._setup_external_screen("{} (yaz)".format(cmd))
        try:
            cmd = self.templating.render(cmd, context)
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )

            if input is None:
                stdin = self._screen_to_process(process_exit, reader, process.stdin)
            else:
                stdin = self._input_to_process(self.templating.render(input, context).encode(), process.stdin)

            stdout = self._process_to_screen(process_exit, process.stdout, writer)
            stderr = self._process_to_screen(process_exit, process.stderr, writer)
            _, _, _, return_code = await asyncio.gather(stdin, stdout, stderr, process.wait())

            if return_code not in valid_codes:
                logger.warning("Process [%s] ended with invalid exit code %d", cmd, return_code)
                raise InvalidReturnCodeError(return_code, None, None)

        finally:
            writer.close()

    @staticmethod
    async def _process_to_screen(event: asyncio.Event, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        while not reader.at_eof():
            writer.write(await reader.read(1024))
            await writer.drain()

        event.set()

    @staticmethod
    async def _screen_to_process(event: asyncio.Event, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        while not event.is_set():
            wait_task = event.wait()
            read_task = reader.read(1024)

            # wait till *either* the event is set *or* there in something to copy from screen to process
            done, pending = await asyncio.wait([wait_task, read_task], return_when=asyncio.FIRST_COMPLETED)

            for task in pending:
                task.cancel()

            for task in done:
                result = task.result()

                if isinstance(result, bytes):
                    writer.write(result)
                    await writer.drain()

        writer.close()

    @staticmethod
    async def _input_to_process(data: bytes, writer: asyncio.StreamWriter):
        writer.write(data)
        await writer.drain()
        writer.close()

    async def _setup_external_screen(self, title: str) -> (asyncio.StreamReader, asyncio.StreamWriter):
        class Container:
            def __init__(self):
                self.event = asyncio.Event()
                self.reader = None
                self.writer = None

            async def incoming_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
                self.reader = reader
                self.writer = writer
                self.event.set()

        container = Container()

        port = 8888 + (self._screen_count % 100)
        while True:
            try:
                server = await asyncio.start_server(container.incoming_connection, "localhost", port)
                logger.debug("Wait for external screen on port %d", port)
                break
            except OSError:
                port += 1

        logger.debug("Start external screen on port %d", port)
        cmd = "screen -t {} /bin/sh -c \"stty -icanon && netcat localhost {}\"".format(shlex.quote(title), port)
        process = await asyncio.create_subprocess_shell(cmd)
        return_code = await process.wait()
        assert return_code == 0, return_code
        await container.event.wait()

        logger.debug("Cleanup external screen server")
        server.close()
        await server.wait_closed()

        return container.reader, container.writer

#
# class Scripting(yaz.BasePlugin):
#     def __init__(self):
#         self.screen_server = Server()
#
#     @yaz.dependency
#     def set_templating(self, templating: yaz_templating_plugin.Templating):
#         self.templating = templating
#
#     async def capture(self,
#                       cmd: str,
#                       input: typing.Optional[str] = None,
#                       context: typing.Optional[dict] = None,
#                       valid_codes: typing.Tuple[int, ...] = (0,),
#                       merge_stderr: bool = True,
#                       dry_run: bool = False,
#                       ) -> (str, str):
#         """Call a subprocess, wait for it to finish, and return the output as a string
#
#         CMD is a string that is interpreted as a shell command and the user is responsible for
#         escaping.  Escaping is done using the template filter and tag 'quote'.
#
#         For example:
#         - await capture("ls -la")
#         - await capture("ls -la {{ filename|quote }}", context=dict(filename="hello world))
#
#         INPUT is an optional string.  When given it will be converted into bytes and send to the
#         subprocess standard input, and the stdin stream is closed.
#
#         For example:
#         - await capture("python3", "import sys; print(sys.version)")
#
#         CONTEXT is a dictionary which is provided to the jinja templating engine when formatting
#         both cmd and input.  The jinja template environment used for the templating contains the
#         filter and tag 'quote'.
#
#         For example:
#         - await capture("cat {{ filename|quote }}", context=dict(filename="hello world.txt"))
#         - await capture("ssh {{ remote|quote }} {% quote %}cd {{ dir|quote }}; ls{% endquote %}", context=dict(...))
#
#         VALID_CODES is a tuple with one or more integers.  When the subprocess has a return code
#         that is not in VALID_CODES, an InvalidReturnCodeError is raised.
#
#         MERGE_STDERR determines if the stderr stream of the process is merged into the result.
#         When False, the stderr stream is ignored.
#
#         DRY_RUN determines if this call is performed.  When set to True the subprocess is not
#         started.
#         """
#         assert isinstance(cmd, str), type(cmd)
#         assert input is None or isinstance(input, str), type(input)
#         assert context is None or isinstance(context, dict), type(context)
#         assert isinstance(valid_codes, tuple), type(valid_codes)
#         assert all(isinstance(valid_code, int) for valid_code in valid_codes), [type(valid_code) for valid_code in valid_codes]
#         assert isinstance(merge_stderr, bool), type(merge_stderr)
#         assert isinstance(dry_run, bool), type(dry_run)
#
#         # cmd = self.templating.render(cmd, context)
#         # if input is not None:
#         #     input = self.templating.render(input, context)
#         # logger.info(self.templating.render("{% if input %}echo {{ input|quote }} | {% endif %}{{ cmd }}", dict(input=input, cmd=cmd)))
#         #
#         # if dry_run:
#         #     stdout = b""
#         #     stderr = b""
#         #     return_code = 0
#         #
#         # else:
#         #     process = await asyncio.create_subprocess_shell(
#         #         cmd,
#         #         stdout=asyncio.subprocess.PIPE,
#         #         stderr=asyncio.subprocess.STDOUT if merge_stderr else asyncio.subprocess.PIPE,
#         #         stdin=None if input is None else asyncio.subprocess.PIPE
#         #     )
#
#         process = await self.call(cmd, input, context, merge_stderr, dry_run)
#         stdout, stderr = await process.communicate(None if input is None else input.encode())
#
#         if process.returncode not in valid_codes:
#             raise InvalidReturnCodeError(process.returncode, stdout, stderr)
#
#         return stdout.decode(), None if merge_stderr else stderr.decode()
#
#     async def call(self,
#                    cmd: str,
#                    input: typing.Optional[str] = None,
#                    context: typing.Optional[dict] = None,
#                    merge_stderr: bool = True,
#                    dry_run: bool = False,
#                    ) -> asyncio.subprocess.Process:
#         """Call a subprocess and provides a Process instance interact with
#
#         CMD is a string that is interpreted as a shell command and the user is responsible for
#         escaping.  Escaping is done using the template filter and tag 'quote'.
#
#         For example:
#         - await call("ls -la")
#         - await call("ls -la {{ filename|quote }}", context=dict(filename="hello world))
#
#         INPUT is an optional string.  When given it will be converted into bytes and send to the
#         subprocess standard input, and the stdin stream is closed.
#
#         For example:
#         - await call("python3", "import sys; print(sys.version)")
#
#         CONTEXT is a dictionary which is provided to the jinja templating engine when formatting
#         both cmd and input.  The jinja template environment used for the templating contains the
#         filter and tag 'quote'.
#
#         For example:
#         - await call("cat {{ filename|quote }}", context=dict(filename="hello world.txt"))
#         - await call("ssh {{ remote|quote }} {% quote %}cd {{ dir|quote }}; ls{% endquote %}", context=dict(...))
#
#         MERGE_STDERR determines if the stderr stream of the process is merged into the result.
#         When False, the stderr stream is ignored.
#
#         DRY_RUN determines if this call is performed.  When set to True the subprocess is not
#         started.
#         """
#         assert isinstance(cmd, str), type(cmd)
#         assert input is None or isinstance(input, str), type(input)
#         assert context is None or isinstance(context, dict), type(context)
#         assert isinstance(merge_stderr, bool), type(merge_stderr)
#         assert isinstance(dry_run, bool), type(dry_run)
#
#         cmd = self.templating.render(cmd, context)
#         if input is not None:
#             input = self.templating.render(input, context)
#         logger.info(self.templating.render("{% if input %}echo {{ input|quote }} | {% endif %}{{ cmd }}", dict(input=input, cmd=cmd)))
#
#         if dry_run:
#             return await asyncio.create_subprocess_shell("")
#
#         else:
#             return await asyncio.create_subprocess_shell(
#                 cmd,
#                 stdout=asyncio.subprocess.PIPE,
#                 stderr=asyncio.subprocess.STDOUT if merge_stderr else asyncio.subprocess.PIPE,
#                 stdin=None if input is None else asyncio.subprocess.PIPE
#             )
#
#     async def interact(self,
#                        cmd: str,
#                        input: typing.Optional[str] = None,
#                        context: typing.Optional[dict] = None,
#                        valid_codes: typing.Tuple[int, ...] = (0,),
#                        dry_run: bool = False,
#                        ) -> int:
#         """Call a subprocess and provide a screen window to interact with it
#
#         CMD is a string that is interpreted as a shell command and the user is responsible for
#         escaping.  Escaping is done using the template filter and tag 'quote'.
#
#         For example:
#         - await interact("ls -la")
#         - await interact("ls -la {{ filename|quote }}", context=dict(filename="hello world))
#
#         INPUT is an optional string.  When given it will be converted into bytes and send to the
#         subprocess standard input, and the stdin stream is closed.
#
#         For example:
#         - await interact("python3", "import sys; print(sys.version)")
#
#         CONTEXT is a dictionary which is provided to the jinja templating engine when formatting
#         both cmd and input.  The jinja template environment used for the templating contains the
#         filter and tag 'quote'.
#
#         For example:
#         - await interact("cat {{ filename|quote }}", context=dict(filename="hello world.txt"))
#         - await interact("ssh {{ remote|quote }} {% quote %}cd {{ dir|quote }}; ls{% endquote %}", context=dict(...))
#
#         VALID_CODES is a tuple with one or more integers.  When the subprocess has a return code
#         that is not in VALID_CODES, an InvalidReturnCodeError is raised.
#
#         DRY_RUN determines if this call is performed.  When set to True the subprocess is not
#         started.
#         """
#
#         # todo: instead of using self.call, just implement the IO here, without the streamer overhead
#         async def read(name, stream_reader: asyncio.StreamReader, stream_writer: asyncio.StreamWriter):
#             assert isinstance(name, str), type(name)
#             assert isinstance(stream_reader, asyncio.StreamReader), type(stream_reader)
#             assert isinstance(stream_writer, asyncio.StreamWriter), type(stream_writer)
#             block = await stream_reader.read(1024 * 5)
#             logger.debug("%s %s bytes (at_eof: %s)", name, len(block), stream_reader.at_eof())
#             logger.debug("%s '%s'", name, block)
#             stream_writer.write(block)
#             return stream_reader.at_eof()
#
#         # Start a screen and the cmd
#         screen_client, process_streamer = await asyncio.gather(
#             self.screen_server.start("yaz {}".format(cmd)),
#             self.call(cmd, input=input, context=context, dry_run=dry_run, merge_stderr=True),
#         )
#
#         at_eof = False
#         while not at_eof:
#             done, running = await asyncio.wait(
#                 (read("Move process -> screen", process_streamer.process.stdout, screen_client.writer),
#                  read("Move screen -> process", screen_client.reader, process_streamer.process.stdin),),
#                 return_when=asyncio.FIRST_COMPLETED)
#
#             for future in done:
#                 at_eof = future.result()
#
#             for future in running:
#                 future.cancel()
#
#         return_code = process_streamer.get_return_code()
#         if return_code not in valid_codes:
#             raise InvalidReturnCodeError(return_code)
#
#         return return_code
