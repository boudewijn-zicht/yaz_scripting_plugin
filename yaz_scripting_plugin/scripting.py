import subprocess

from yaz.plugin import Plugin
from yaz_templating_plugin import Templating

class Scripting(Plugin):
    def __init__(self, templating:Templating):
        self.templating = templating

    def call(self, args, context={}, input="", capture=True, timeout=-1.0, valid_codes=(0,), dry_run=False):
        """Call a subprocess.

        ARGS is a string that is interpreted as a shell command and the user is responsible for
        escaping.  Escaping is done using the template filter and tag 'quote'.

        For example:
        - _call("ls -la")
        - _call("ls -la {{ filename|quote }}", dict(filename="hello world))

        CONTEXT is a dictionary which is provided to the jinja templating engine when formatting
        both args and input.  The jinja template environment used for the templating contains the
        filter and tag 'quote'.

        For example:
        - _call("cat {{ filename|quote }}", dict(filename="hello world.txt"))
        - _call("ssh {{ remote|quote }} {% quote %}cd {{ dir|quote }}; ls{% endquote %}", dict(...))

        INPUT is an optional string.  When given it will be send to the subprocess standard input
        (stdin).  When INPUT is give, then CAPTURE is automatically set to True.

        For example:
        - _call("python3", "import sys; print(sys.version)")

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
        assert isinstance(args, str), type(args)
        assert isinstance(context, dict), type(context)
        assert isinstance(input, str), type(input)
        assert isinstance(capture, bool), type(capture)
        assert isinstance(timeout, float), type(timeout)
        assert isinstance(valid_codes, tuple), type(valid_codes)
        assert len(valid_codes) > 0, len(valid_codes)
        assert all(isinstance(code, int) for code in valid_codes), [type(code) for code in valid_codes]
        assert isinstance(dry_run, bool), type(dry_run)

        args = self.templating.render(args, context)
        input = self.templating.render(input, context)
        output = ""

        if dry_run:
            print(self.templating.render("{% if input %}echo {{ input|quote }} | {% endif %}{{ args }}", dict(input=input, args=args)))

        else:
            kwargs = dict(shell=True, universal_newlines=True, stderr=subprocess.STDOUT)
            if input:
                kwargs.update(dict(input=input))
            if timeout >= 0.0:
                kwargs.update(dict(timeout=timeout))

            try:
                if capture or input:
                    output = subprocess.check_output(args, **kwargs)
                else:
                    subprocess.check_call(args, **kwargs)
            except subprocess.CalledProcessError as error:
                output = error.output
                if not error.returncode in valid_codes:
                    raise

        return output
