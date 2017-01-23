import asyncio
from typing import Optional

from yaz.plugin import Plugin
from yaz_templating_plugin import Templating

from .log import logger
from .error import InvalidReturnCodeError
from .streamer import BaseStreamer, DummyStreamer, Streamer
from .screen import Server, Client


class Scripting(Plugin):
    def __init__(self, templating: Templating):
        self.templating = templating
        self.screen_server = Server()

    async def capture(self,
                      cmd: str,
                      input: str = "",
                      context: Optional[dict] = None,
                      valid_codes=(0,),
                      dry_run: bool = False,
                      merge_stderr: bool = True,
                      manage_encoding: bool = True
                      ) -> str:
        """Call a subprocess, wait for it to finish, and return the output

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

        DRY_RUN determines if this call is performed.  When set to True the subprocess is not
        started.

        MERGE_STDERR determines if the stderr stream of the process is merged into the result.
        When False, the stderr stream is ignored.

        MANAGE_ENCODING determines the return type.  When True, the process output is returned
        as a string, otherwise bytes are returned.
        """
        streamer = await self.call(cmd, input=input, context=context, dry_run=dry_run, merge_stderr=merge_stderr, manage_encoding=False)

        # collect output streams
        results = {"stdout": [], "stderr": []}
        async for output in streamer.iter():
            results[output.source].append(output.value)

        stdout = b"".join(results["stdout"])
        if manage_encoding:
            stdout = stdout.decode()

        return_code = streamer.get_return_code()
        if return_code not in valid_codes:
            stderr = b"".join(results["stderr"])
            if manage_encoding:
                stderr = stderr.decode()
            raise InvalidReturnCodeError(return_code, stderr=stderr, stdout=stdout)

        return stdout

    async def interact(self,
                       cmd: str,
                       input: str = "",
                       context: Optional[dict] = None,
                       valid_codes=(0,),
                       dry_run: bool = False
                       ):
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
            self.call(cmd, input=input, context=context, dry_run=dry_run, merge_stderr=True, manage_encoding=False),
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
                   input: str = "",
                   context: Optional[dict] = None,
                   dry_run: bool = False,
                   merge_stderr: bool = True,
                   manage_encoding: bool = True
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

        DRY_RUN determines if this call is performed.  When set to True the subprocess is not
        started.

        MERGE_STDERR determines if the stderr stream of the process is merged into the result.
        When False, the stderr stream is ignored.

        MANAGE_ENCODING determines the return type.  When True, the process output is returned
        as a string, otherwise bytes are returned.
        """
        cmd = self.templating.render(cmd, context)
        input = self.templating.render(input, context)
        logger.info(self.templating.render("{% if input %}echo {{ input|quote }} | {% endif %}{{ cmd }}",
                                           dict(input=input, cmd=cmd)))

        # streamer = DummyStreamer() if dry_run else Streamer(bool(input), merge_stderr, manage_encoding)
        streamer = DummyStreamer() if dry_run else Streamer(True, merge_stderr, manage_encoding)
        await streamer.create(cmd)

        if input:
            await streamer.write(input.encode(), True)

        return streamer
