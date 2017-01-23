import asyncio
import typing

from .log import logger


class Output:
    def __init__(self, source, value, has_more):
        self.source = source
        self.value = value
        self.has_more = has_more

    def __bool__(self):
        return self.has_more


class BaseStreamer:
    async def create(self, cmd: str, can_write: bool, merge_stderr: bool):
        pass

    async def read(self, n: int = -1) -> Output:
        return Output("return_code", 0, False)

    async def read_line(self) -> Output:
        return Output("return_code", 0, False)

    def iter(self, n: int = -1):
        class OutputGenerator:
            def __init__(self, streamer: BaseStreamer):
                self.streamer = streamer

            async def __aiter__(self):
                return self

            async def __anext__(self):
                output = await self.streamer.read(n)
                if not output.has_more:
                    raise StopAsyncIteration
                return output

        return OutputGenerator(self)

    def iter_lines(self):
        class OutputGenerator:
            def __init__(self, streamer: BaseStreamer):
                self.streamer = streamer

            async def __aiter__(self):
                return self

            async def __anext__(self):
                output = await self.streamer.read_line()
                if not output.has_more:
                    raise StopAsyncIteration
                return output

        return OutputGenerator(self)

    async def write(self, input: bytes, close: bool = False):
        pass

    async def write_lines(self, lines: typing.List[bytes], close: bool = False):
        pass

    def get_return_code(self):
        return 0


class DummyStreamer(BaseStreamer):
    pass


class Streamer(BaseStreamer):
    def __init__(self):
        self._process = None
        self._streams = []

    async def create(self, cmd: str, can_write: bool, merge_stderr: bool):
        """Wait until the process is created"""
        assert isinstance(cmd, str), type(cmd)
        assert isinstance(can_write, bool), type(can_write)
        assert isinstance(merge_stderr, bool), type(merge_stderr)

        self._process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT if merge_stderr else asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if can_write else None
        )

        self._streams = [("stdout", self._process.stdout)]
        if not merge_stderr:
            self._streams.insert(0, ("stderr", self._process.stderr))

    async def read(self, n: int = -1) -> Output:
        for source, stream in self._streams:
            if not stream.at_eof():
                data = await stream.read(n)
                logger.debug("Streamer read %s bytes from %s", len(data), source)
                if len(data):
                    return Output(source, data, True)

        return_code = await self._process.wait()
        return Output('return_code', return_code, False)

    async def read_line(self) -> Output:
        for source, stream in self._streams:
            if not stream.at_eof():
                data = await stream.readline()
                logger.debug("Streamer read %s bytes from %s", len(data), source)
                if len(data):
                    return Output(source, data, True)

        return_code = await self._process.wait()
        return Output('return_code', return_code, False)

    async def write(self, input: bytes, close: bool = False):
        assert isinstance(input, bytes), type(input)
        assert isinstance(close, bool), type(close)
        assert self._process.stdin is not None, "The process was either created using can_write = False or the stdin has been closed"

        self._process.stdin.write(input)
        await self._process.stdin.drain()
        logger.debug("Streamer wrote %s bytes", len(input))

        if close:
            self._process.stdin.close()

    async def write_lines(self, lines: typing.List[bytes], close: bool = False):
        assert isinstance(lines, list), type(lines)
        assert all(isinstance(input, bytes) for input in lines), [type(input) for input in lines]
        assert isinstance(close, bool), type(close)
        assert self._process.stdin is not None, "The process was either created using can_write = False or the stdin has been closed"

        self._process.stdin.writelines(lines)
        await self._process.stdin.drain()
        logger.debug("Streamer wrote %s bytes", sum(len(line) for line in lines))

        if close:
            self._process.stdin.close()

    def get_return_code(self):
        return self._process.returncode
