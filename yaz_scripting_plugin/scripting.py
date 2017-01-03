import asyncio
import subprocess

from yaz.plugin import Plugin
from yaz_templating_plugin import Templating

class Scripting(Plugin):
    def __init__(self, templating:Templating):
        self.templating = templating

    async def call(self, cmd, input="", context={}, capture=True, timeout=None, valid_codes=(0,), dry_run=False):
        """Call a subprocess.

        CMD is a string that is interpreted as a shell command and the user is responsible for
        escaping.  Escaping is done using the template filter and tag 'quote'.

        For example:
        - await call("ls -la")
        - await call("ls -la {{ filename|quote }}", dict(filename="hello world))

        INPUT is an optional string.  When given it will be converted into bytes and send to the
        subprocess standard input.  When INPUT is give, then CAPTURE is automatically set to True.

        For example:
        - await call("python3", "import sys; print(sys.version)")

        CONTEXT is a dictionary which is provided to the jinja templating engine when formatting
        both args and input.  The jinja template environment used for the templating contains the
        filter and tag 'quote'.

        For example:
        - await call("cat {{ filename|quote }}", dict(filename="hello world.txt"))
        - await call("ssh {{ remote|quote }} {% quote %}cd {{ dir|quote }}; ls{% endquote %}", dict(...))

        CAPTURE is an optional boolean.  When True the standard output and standard error of the
        subprocess are captured and returned as a single string.  When False, which is the default,
        the standard output and standard error are passed to the main process' standard output and
        standard error respectively.  When INPUT is give, then CAPTURE is automatically set to True.

        TIMEOUT is an optional floating point number.  When zero or higher the subprocess will be
        killed after TIMEOUT seconds and a subprocess.TimeoutExpired exception will be raised.

        VALID_CODES is a tuple with one or more integers.  When the subprocess has a return code
        that is not in VALID_CODES, a subprocess.CalledProcessError exception will be raised.

        DRY_RUN determines if this call is performed.  When set to True the subprocess is not
        started and an empty string is returned.  Otherwise the subprocess is called normally.

        """
        assert isinstance(cmd, str), type(args)
        assert isinstance(input, str), type(input)
        assert isinstance(context, dict), type(context)
        assert isinstance(capture, bool), type(capture)
        assert timeout is None or isinstance(timeout, float), type(timeout)
        assert isinstance(valid_codes, tuple), type(valid_codes)
        assert len(valid_codes) > 0, len(valid_codes)
        assert all(isinstance(code, int) for code in valid_codes), [type(code) for code in valid_codes]
        assert isinstance(dry_run, bool), type(dry_run)

        cmd = self.templating.render(cmd, context)
        input = self.templating.render(input, context)

        if dry_run:
            print(self.templating.render("{% if input %}echo {{ input|quote }} | {% endif %}{{ cmd }}", dict(input=input, cmd=cmd)))
            return_code, stdout, stderr = 0, b"", b""

        else:
            try:
                return_code, stdout, stderr = await asyncio.wait_for(self.raw(cmd, input.encode("utf-8")), timeout=timeout)

            except asyncio.TimeoutError as error:
                raise RuntimeError("Timeout after {} seconds".format(timeout))

        if not return_code in valid_codes:
            raise RuntimeError("Invalid return code {}".format(return_code))

        return (return_code, stdout, stderr)

    async def raw(self, cmd, stdin=b""):
        """Call a subprocess.

        CMD is a string that is interpreted as a shell command and the user is responsible for
        escaping.

        For example:
        - await raw("ls -la")
        - await raw("cat 'hello world.txt'")

        STDIN are optional bytes.  When given it will be send to the subprocess standard input.

        For example:
        - await raw("python3", b"import sys; print(sys.version)")
        """
        assert isinstance(cmd, str), type(cmd)
        assert isinstance(stdin, bytes), type(stdin)

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin else None
        )

        stdout, stderr = await process.communicate(input=stdin if stdin else None)

        return process.returncode, stdout, stderr

