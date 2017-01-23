from typing import Optional


class InvalidReturnCodeError(RuntimeError):
    def __init__(self, return_code: int, stdout: Optional[bytes] = None, stderr: Optional[bytes] = None):
        assert isinstance(return_code, int), type(return_code)
        assert stdout is None or isinstance(stdout, bytes), type(stdout)
        assert stderr is None or isinstance(stderr, bytes), type(stderr)
        super().__init__("Invalid return code {}".format(return_code))
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

    def get_return_code(self) -> int:
        return self.return_code

    def get_stdout(self) -> Optional[bytes]:
        return self.stdout

    def get_stderr(self) -> Optional[bytes]:
        return self.stderr
