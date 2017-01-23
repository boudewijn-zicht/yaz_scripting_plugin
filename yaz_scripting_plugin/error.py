class InvalidReturnCodeError(RuntimeError):
    def __init__(self, return_code: int, stderr = None, stdout = None):
        assert isinstance(return_code, int), type(return_code)
        super().__init__("Invalid return code {}".format(return_code))
        self.return_code = return_code
        self.stderr = stderr
        self.stdout = stdout

    def get_return_code(self):
        return self.return_code

    def get_stderr(self):
        return self.stderr

    def get_stdout(self):
        return self.stdout
