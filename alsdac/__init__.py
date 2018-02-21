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

"""
Motor Controls.
"""
def AtPreset(presetname: str) -> bool:
    return bool(get(f'AtPreset({presetname})\r\n'))


def AtTrajectory(trajname: str) -> bool:
    return bool(get(f'AtTrajectory({trajname})\r\n'))


def DisableMotor(motorname: str) -> bool:
    return bool(get(f'DisableMotor({motorname})\r\n'))


def EnableMotor(motorname: str) -> bool:
    return bool(get(f'EnableMotor({motorname})\r\n'))


def GetMotor(motorname: str):
    return (get(f'GetMotor({motorname})\r\n'))
# TODO: also return the datetime as second value


def GetMotorPos(motorname: str) -> float:
    return float(get(f'GetMotorPos({motorname})\r\n'))


def GetMotorStatus(motorname: str) -> bool:  # returns true if move complete
    return get(f'GetMotorStat({motorname})\r\n').startswith(b'Move finished')


def GetSoftLimits(motorname: str) -> Tuple[float, float]:
    return tuple(map(float, get(f'GetSoftLimits({motorname})\r\n').split(b' ')))[:2]  # The 2 just makes pylint happy :)


def GetFlyingPositions(motorname: str) -> str:
    return str(get(f'GetFlyingPositions({motorname})\r\n'))


# def GetFlyingPositions(motorname: str) -> array:
#   return array(get(f'GetFlyingPositions({motorname})\r\n'))
# TODO: Duplicate calls with differing outputs.


def ListMotors() -> List[str]:
    return str(get(f'ListMotors\r\n'), ENCODING).split('\r\n')


def ListPresets() -> List[str]:
    return str(get(f'ListPresets\r\n'), ENCODING).split('\r\n')


def ListTrajectories() -> List[str]:
    return str(get(f'ListTrajectories\r\n'), ENCODING).split('\r\n')


def NumberMotors() -> int:
    return int(get(f'NumberMotors\r\n'))
# TODO: f' needed here?


def MoveMotor(motorname: str, pos: Union[float, int]) -> bool:
    return bool(get(f'MoveMotor({motorname}, {pos})\r\n'))


def StopMotor(motorname: str):
    return get(f'StopMotor({motorname})\r\n')


def HomeMotor(motorname: str):
    return get(f'HomeMotor({motorname})\r\n')


def MoveToPreset(presetname: str) -> bool:
    return bool(get(f'MoveToPreset({presetname})\r\n'))


def MoveToTrajectory(trajname: str) -> bool:
    return bool(get(f'MoveToTrajectory({trajname})\r\n'))


def SetBreakpoints(motorname: str, first_bp: float, bp_step: float, num_points: int):
    return get(f'SetBreakpoints({motorname}, {first_bp}, {bp_step}, {num_points})\r\n')


# def SetBreakpointRegions(motorname: str, first_bp: float, num_points: int):
#     return get(f'SetBreakpoints({motorname}, {first_bp}, {num_points})\r\n')
# TODO: Set multiple breakpoints in get call.


def DisableBreakpoints(motorname: str) -> bool:
    return bool(get(f'DisableBreakpoints({motorname})\r\n'))


def GetMotorVelocity(motorname: str) -> float:
    return float(get(f'GetMotorVelocity({motorname})\r\n'))


def GetOrigMotorVelocity(motorname: str) -> float:
    return float(get(f'GetOrigMotorVelocity({motorname})\r\n'))


def SetMotorVelocity(motorname: str, vel: float) -> float:
    return float(get(f'GetMotorVelocity({motorname}, {vel})\r\n'))


# def MoveAllMotors(motorname1, posn1, motorname2, pos2):
#     return get(f'MoveAllMotors({motorname1}, {posn1}, {motorname2}, {posn2})\r\n')
# TODO: Set multiple motornames/positions in get call.
"""
AI/DIO Controls
"""
def GetFreerun(ainame) -> float:
    return float(get(f'GetFreerun({ainame})\r\n'))


def ListAIs() -> List[str]:
    return str(get(f'ListAIs\r\n'), ENCODING).split('\r\n')


def ListDIOs() -> List[str]:
    return str(get(f'ListDIOs\r\n'), ENCODING).split('\r\n')


def StartAcquire(time: float, counts: int):
    return bool(get(f'StartAcquire({time},{counts}\r\n'))