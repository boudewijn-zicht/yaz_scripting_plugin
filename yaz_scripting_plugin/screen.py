import os
import asyncio
import hashlib
import shlex

from .log import logger


class State:
    """Maintains a 'state' value"""

    def __init__(self, initial_state: str, name: str = "State"):
        """Initialize state to INITIAL_STATE

        INITIAL_STATE is a string giving the initial state.
        NAME is an optional string used for logging purposes.
        """
        self._state = initial_state
        self._name = name

    def check(self, state: str):
        """Returns true when the current state equals STATE"""
        return self._state == state

    def change(self, from_state: str, to_state: str) -> bool:
        """Try to change the state

        When the current state equals FROM_STATE the state is set to TO_STATE and True is returned.  Otherwise, False is returned.
        """
        if self._state == from_state:
            logger.debug("%s %s -> %s", self._name, from_state, to_state)
            self._state = to_state
            return True
        return False

    def require(self, from_state: str, to_state: str) -> bool:
        """Change the state or raise an exception

        When the current state equals FROM_STATE the state is set to TO_STATE and True is returned.  Otherwise, a RuntimeError is raised.
        """
        if not self.change(from_state, to_state):
            raise RuntimeError("{} invalid state transition {} -> {}, actual state {}".format(self._name, from_state, to_state, self._state))
        return True


class Client:
    def __init__(self, shell_title: str):
        self._security_key = hashlib.sha512(b"::".join([b"security-key", shell_title.encode(), os.urandom(512)])).hexdigest()
        self._title = shell_title
        self.reader = None
        self.writer = None
        self._state = State("CLOSED", "Client state")

    def get_title(self) -> str:
        return self._title

    def get_security_key(self) -> str:
        return self._security_key

    def attach(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._state.require("CLOSED", "CONNECTED")
        self.reader = reader
        self.writer = writer

    def detach(self):
        self._state.require("CONNECTED", "CLOSED")
        self.writer.close()


class Server:
    def __init__(self):
        self._state = State("CLOSED", "Server state")
        self._clients = {}

    async def _incoming_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        line = await reader.readline()
        security_key = line[:-1].decode()

        logger.debug("Server received connection with security key: %s", security_key)
        event, client = self._clients.pop(security_key)
        if event:
            client.attach(reader, writer)
            self._clients[security_key] = (None, client)
            event.set()
        else:
            logger.warning("Server closing unregistered incoming connection")
            await writer.close()

    async def _start(self):
        if (self._state.change("CLOSED", "STARTING")):
            self._server = await asyncio.start_server(self._incoming_connection, "localhost", 8888)
            self._state.require("STARTING", "STARTED")

    async def _stop(self):
        if (self._state.change("STARTED", "CLOSING")):
            self._server.close()
            await self._server.wait_closed()
            self._state.require("CLOSING", "CLOSED")

    async def register(self, client: Client):
        await self._start()
        security_key = client.get_security_key()
        logger.debug("Server waiting for connection with security key: %s", security_key)
        event = asyncio.Event()
        self._clients[security_key] = (event, client)

        cmd = "screen -t {} /bin/sh -c \"echo {} | netcat localhost 8888\"".format(shlex.quote(client.get_title()), security_key)
        process = await asyncio.create_subprocess_shell(cmd)
        await process.wait()
        await event.wait()

        return client

    async def un_register(self, client: Client):
        event, client = self._clients.pop(client.get_security_key())
        if event:
            event.set()
        if client:
            client.detach()
        if not self._clients:
            await self._stop()
