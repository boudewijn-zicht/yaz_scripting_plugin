import asyncio
from typing import Optional

import yaz
from yaz_templating_plugin import Templating

from .log import logger
from .error import InvalidReturnCodeError
from .streamer import BaseStreamer, DummyStreamer, Streamer
from .screen import Server, Client


class Scripting(yaz.BasePlugin):
    def __init__(self):
        self.screen_server = Server()

    @yaz.dependency
    def set_templating(self, templating: Templating):
        self.templating = templating

    async def capture(self,
                      cmd: str,
                      input: Optional[str] = None,
                      context: Optional[dict] = None,
                      valid_codes=(0,),
                      merge_stderr: bool = True,
                      dry_run: bool = False,
                      ) -> str:
        """Call a subprocess, wait for it to finish, and return the output as a string

        CMD is a string that is interpreted as a shell command and the user is responsible for
        escaping.  Escaping is done using the template filter and tag 'quote'.

        For example:
        - await capture("ls -la")
        - await capture("ls -la {{ filename|quote }}", context=dict(filename="hello world))

        INPUT is an optional string.  When given it will be converted into bytes and send to the
        subprocess standard input, and the stdin stream is closed.

        For example:
        - await capture("python3", "import sys; print(sys.version)")

        CONTEXT is a dictionary which is provided to the jinja templating engine when formatting
        both cmd and input.  The jinja template environment used for the templating contains the
        filter and tag 'quote'.

        For example:
        - await capture("cat {{ filename|quote }}", context=dict(filename="hello world.txt"))
        - await capture("ssh {{ remote|quote }} {% quote %}cd {{ dir|quote }}; ls{% endquote %}", context=dict(...))

        VALID_CODES is a tuple with one or more integers.  When the subprocess has a return code
        that is not in VALID_CODES, an InvalidReturnCodeError is raised.

        MERGE_STDERR determines if the stderr stream of the process is merged into the result.
        When False, the stderr stream is ignored.

        DRY_RUN determines if this call is performed.  When set to True the subprocess is not
        started.
        """
        cmd = self.templating.render(cmd, context)
        if input is not None:
            input = self.templating.render(input, context)
        logger.info(self.templating.render("{% if input %}echo {{ input|quote }} | {% endif %}{{ cmd }}", dict(input=input, cmd=cmd)))

        if dry_run:
            stdout = b""
            stderr = b""
            return_code = 0

        else:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT if merge_stderr else asyncio.subprocess.PIPE,
                stdin=None if input is None else asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate(None if input is None else input.encode())
            return_code = process.returncode

        if return_code not in valid_codes:
            raise InvalidReturnCodeError(return_code, stdout, stderr)

        return stdout.decode()

    async def interact(self,
                       cmd: str,
                       input: Optional[str] = None,
                       context: Optional[dict] = None,
                       valid_codes=(0,),
                       dry_run: bool = False,
                       ) -> int:
        """Call a subprocess and provide a screen window to interact with it

        CMD is a string that is interpreted as a shell command and the user is responsible for
        escaping.  Escaping is done using the template filter and tag 'quote'.

        For example:
        - await interact("ls -la")
        - await interact("ls -la {{ filename|quote }}", context=dict(filename="hello world))

        INPUT is an optional string.  When given it will be converted into bytes and send to the
        subprocess standard input, and the stdin stream is closed.

        For example:
        - await interact("python3", "import sys; print(sys.version)")

        CONTEXT is a dictionary which is provided to the jinja templating engine when formatting
        both cmd and input.  The jinja template environment used for the templating contains the
        filter and tag 'quote'.

        For example:
        - await interact("cat {{ filename|quote }}", context=dict(filename="hello world.txt"))
        - await interact("ssh {{ remote|quote }} {% quote %}cd {{ dir|quote }}; ls{% endquote %}", context=dict(...))

        VALID_CODES is a tuple with one or more integers.  When the subprocess has a return code
        that is not in VALID_CODES, an InvalidReturnCodeError is raised.

        DRY_RUN determines if this call is performed.  When set to True the subprocess is not
        started.
        """

        # Start a screen and the cmd
        screen_client, streamer = await asyncio.gather(
            self.screen_server.register(Client("yaz {}".format(cmd))),
            self.call(cmd, input=input, context=context, dry_run=dry_run, merge_stderr=True),
        )

        # todo we are reading lines, should probably change that into reading data, but without blocking...
        async for output in streamer.iter_lines(False):
            screen_client.writer.write(output.value)

        await self.screen_server.un_register(screen_client)

        return_code = streamer.get_return_code()
        if return_code not in valid_codes:
            raise InvalidReturnCodeError(return_code)

        return return_code

    async def call(self,
                   cmd: str,
                   input: Optional[str] = None,
                   context: Optional[dict] = None,
                   merge_stderr: bool = True,
                   dry_run: bool = False,
                   ) -> BaseStreamer:
        """Call a subprocess and provide streams for stdin, stdout, and stderr to interact with

        CMD is a string that is interpreted as a shell command and the user is responsible for
        escaping.  Escaping is done using the template filter and tag 'quote'.

        For example:
        - await call("ls -la")
        - await call("ls -la {{ filename|quote }}", context=dict(filename="hello world))

        INPUT is an optional string.  When given it will be converted into bytes and send to the
        subprocess standard input, and the stdin stream is closed.

        For example:
        - await call("python3", "import sys; print(sys.version)")

        CONTEXT is a dictionary which is provided to the jinja templating engine when formatting
        both cmd and input.  The jinja template environment used for the templating contains the
        filter and tag 'quote'.

        For example:
        - await call("cat {{ filename|quote }}", context=dict(filename="hello world.txt"))
        - await call("ssh {{ remote|quote }} {% quote %}cd {{ dir|quote }}; ls{% endquote %}", context=dict(...))

        MERGE_STDERR determines if the stderr stream of the process is merged into the result.
        When False, the stderr stream is ignored.

        DRY_RUN determines if this call is performed.  When set to True the subprocess is not
        started.
        """
        cmd = self.templating.render(cmd, context)
        if input is not None:
            input = self.templating.render(input, context)
        logger.info(self.templating.render("{% if input %}echo {{ input|quote }} | {% endif %}{{ cmd }}",
                                           dict(input=input, cmd=cmd)))

        streamer = DummyStreamer() if dry_run else Streamer()
        await streamer.create(cmd, True, merge_stderr)

        if input:
            await streamer.write(input.encode(), True)

        return streamer
