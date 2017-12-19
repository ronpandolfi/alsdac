import sys
import trio
from typing import Union, Tuple, List

# arbitrary, but:
# - must be in between 1024 and 65535
# - can't be in use by some other program on your computer
# - must match what we set in our echo server
PORT = 55000
# How much memory to spend (at most) on each call to recv. Pretty arbitrary,
# but shouldn't be too big or too small.
BUFSIZE = 16384

ENCODING = 'ascii'

# SERVER_ADDRESS = "131.243.81.35"  # Dula's sample stage server
# SERVER_ADDRESS = "131.243.81.43" # Dula's primary BCS server
SERVER_ADDRESS = None


def set_server_address(host):
    global SERVER_ADDRESS
    SERVER_ADDRESS = host


def set_port(port):
    global PORT
    PORT = port


def get(data: str) -> bytes:
    """
    Starts sender and receiver asynchronous sockets. The sender sends a tcp/ip command to the LabView host system. The
    receiver waits to receive a response.

    """

    async def _get(data):
        result = None

        async def sender(client_sock, data):
            # print("sender: started!")
            # print("sender: sending {!r}".format(data))
            await client_sock.send_all(bytes(data, ENCODING))

        async def receiver(client_sock):
            # print("receiver: started!")
            _data = await client_sock.receive_some(BUFSIZE)
            # print("receiver: got data {!r}".format(_data))
            if not data:
                # print("receiver: connection closed")
                sys.exit()
            nonlocal result
            result = _data

        # print("parent: connecting to 127.0.0.1:{}".format(PORT))
        with trio.socket.socket() as client_sock:
            await client_sock.connect((SERVER_ADDRESS, PORT))
            client_sock = trio.SocketStream(client_sock)
            async with trio.open_nursery() as nursery:
                # print("parent: spawning sender...")
                nursery.start_soon(sender, client_sock, data)

                # print("parent: spawning receiver...")
                nursery.start_soon(receiver, client_sock)

        return result

    return trio.run(_get, data)


def GetMotorPos(motorname: str) -> float:
    return float(get(f'GetMotorPos({motorname})\r\n'))


def MoveMotor(motorname: str, pos: Union[float, int]) -> bool:
    return bool(get(f'MoveMotor({motorname}, {pos})\r\n'))


def ListAIs() -> List[str]:
    return str(get(f'ListAIs\r\n'), ENCODING).split('\r\n')


def GetSoftLimits(motorname: str) -> Tuple[float, float]:
    return tuple(map(float, get(f'GetSoftLimits({motorname})\r\n').split(b' ')))[:2]  # The 2 just makes pylint happy :)


def StartAcquire(time: float, counts: int):
    return bool(get(f'StartAcquire({time},{counts}\r\n'))


def GetMotorStatus(motorname: str) -> bool:  # returns true if move complete
    return get(f'GetMotorStat({motorname})\r\n').startswith(b'Move finished')
    # TODO: also return the datetime as second value


def ListDIOs() -> List[str]:
    return str(get(f'ListDIOs\r\n'), ENCODING).split('\r\n')


def GetFreerun(ainame) -> float:
    return float(get(f'GetFreerun({ainame})\r\n'))
