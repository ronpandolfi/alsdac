import sys
import trio
from typing import Union, Tuple, List
import numpy as np
import re
from operator import itemgetter, mul
from functools import reduce, wraps
import os

# arbitrary, but:
# - must be in between 1024 and 65535
# - can't be in use by some other program on your computer
# - must match what we set in our echo server
PORT = 55000
# How much memory to spend (at most) on each call to recv. Pretty arbitrary,
# but shouldn't be too big or too small.
BUFSIZE = 163840

ENCODING = 'ascii'

# SERVER_ADDRESS = "131.243.81.35"  # Dula's sample stage server
# SERVER_ADDRESS = "131.243.81.43" # Dula's primary BCS server
SERVER_ADDRESS = '131.243.163.42'  # Dula's instrumentation lab server

READ_ONLY = os.environ.get('ALSDAC_READ_ONLY', True)

# SERVER_ADDRESS = None


def set_server_address(host):
    global SERVER_ADDRESS
    SERVER_ADDRESS = host


def set_port(port):
    global PORT
    PORT = port

def stream_size(b):
    m = re.match(b'(?P<_0>\d*) Points by (?P<_1>\d*) channels', b)
    if m:
        map(itemgetter(1), sorted(m.groupdict().items()))
        return map(int,m.groups())
    return None, None


# FIXME: Make sends/receives happen from a threaded hot loop,

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
            print('sent:', data.strip())
            await client_sock.send_all(bytes(data, ENCODING))

        async def receiver(client_sock:trio.SocketStream):
            _data = await client_sock.receive_some(BUFSIZE)

            expcols, exprows = stream_size(_data)

            if exprows and expcols:
                while not _data.endswith(b'\r\n\r\n'):
                    _data += await client_sock.receive_some(BUFSIZE)

            if not data:
                sys.exit()
            nonlocal result
            result = _data
            print('received:', str(_data, ENCODING).strip())

        with trio.socket.socket() as client_sock:
            await client_sock.connect((SERVER_ADDRESS, PORT))
            client_sock = trio.SocketStream(client_sock)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(sender, client_sock, data)

                nursery.start_soon(receiver, client_sock)

        return result

    return trio.run(_get, data)

def write_required(func):
    @wraps(func)
    def execute_if_write_permitted(*args, **kwargs):
        if READ_ONLY:
            raise PermissionError('Write access is disabled by default to prevent mishaps.\n'
                                  'To enable write access set alsdac.READ_ONLY = False')
        else:
            return func(*args, **kwargs)
    return execute_if_write_permitted


"""
Motor Controls.
"""


def AtPreset(presetname: str) -> bool:
    return bool(get(f'AtPreset({presetname})\r\n'))


def AtTrajectory(trajname: str) -> bool:
    return bool(get(f'AtTrajectory({trajname})\r\n'))

@write_required
def DisableMotor(motorname: str) -> bool:
    return bool(get(f'DisableMotor({motorname})\r\n'))

@write_required
def EnableMotor(motorname: str) -> bool:
    return bool(get(f'EnableMotor({motorname})\r\n'))


def GetMotor(motorname: str):
    pos, hex, datetime = get(f'GetMotor({motorname})\r\n').split(b' ', 2)
    pos = float(pos)
    hex = str(hex, ENCODING)
    # datetime = datetime.strptime('Jun 1 2005  1:33PM', '%b %d %Y %I:%M%p') the date is nonsense!
    datetime = str(datetime, ENCODING)
    return pos, hex, datetime
    # TODO: fix datetime nonsense

async def GetMotorPos_async(motorname:str, get) -> float:
    return GetMotorPos(motorname, get=get)


def GetMotorPos(motorname: str, get=get) -> float:
    return float(get(f'GetMotorPos({motorname})\r\n'))


def GetMotorStatus(motorname: str) -> bool:  # returns true if move complete
    return get(f'GetMotorStat({motorname})\r\n').startswith(b'Move finished')


def GetSoftLimits(motorname: str) -> Tuple[float, float]:
    return tuple(map(float, get(f'GetSoftLimits({motorname})\r\n').split(b' ')))[:2]  # The 2 just makes pylint happy :)


def GetFlyingPositions(motorname: str) -> str:
    return np.frombuffer(get(f'GetFlyingPositions({motorname})\r\n').strip(), dtype=np.single)
    # TODO: confirm


def ListMotors() -> List[str]:
    return str(get('ListMotors\r\n'), ENCODING).strip().split('\r\n')


def ListPresets() -> List[str]:
    return str(get('ListPresets\r\n'), ENCODING).strip().split('\r\n')


def ListTrajectories() -> List[str]:
    return str(get('ListTrajectories\r\n'), ENCODING).strip().split('\r\n')


def NumberMotors() -> int:
    return int(get('NumberMotors\r\n'))

@write_required
def MoveMotor(motorname: str, pos: Union[float, int]) -> bool:
    return bool(get(f'MoveMotor({motorname}, {pos})\r\n'))

@write_required
def StopMotor(motorname: str):
    return get(f'StopMotor({motorname})\r\n') == b'Motor Stopped\r\n'

@write_required
def HomeMotor(motorname: str):
    return get(f'HomeMotor({motorname})\r\n') == b'OK!0 \r\n'

@write_required
def MoveToPreset(presetname: str) -> bool:
    return bool(get(f'MoveToPreset({presetname})\r\n'))

@write_required
def MoveToTrajectory(trajname: str) -> bool:
    return bool(get(f'MoveToTrajectory({trajname})\r\n'))

@write_required
def SetBreakpoints(motorname: str, first_bp: float, bp_step: float, num_points: int):
    return get(f'SetBreakpoints({motorname}, {first_bp}, {bp_step}, {num_points})\r\n')


# def SetBreakpointRegions(motorname: str, first_bp: float, num_points: int):
#     return get(f'SetBreakpoints({motorname}, {first_bp}, {num_points})\r\n')
# TODO: Set multiple breakpoints in get call.

@write_required
def DisableBreakpoints(motorname: str) -> bool:
    return bool(get(f'DisableBreakpoints({motorname})\r\n'))


def GetMotorVelocity(motorname: str) -> float:
    return float(get(f'GetMotorVelocity({motorname})\r\n'))


def GetOrigMotorVelocity(motorname: str) -> float:
    return float(get(f'GetOrigMotorVelocity({motorname})\r\n'))

@write_required
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
    return str(get('ListAIs\r\n'), ENCODING).strip().split('\r\n')


def ListDIOs() -> List[str]:
    return str(get('ListDIOs\r\n'), ENCODING).strip().split('\r\n')

@write_required
def StartAcquire(time: float, counts: int):
    return bool(get(f'StartAcquire({time},{counts}\r\n'))


"""
Instruments
"""


def GetInstrumentStatus(instrumentname) -> List[str]:
    return str(get(f'GetInstrumentStatus({instrumentname})\r\n'), ENCODING).strip().split('\r\n')


def ListInstruments() -> List[str]:
    return str(get('ListInstruments\r\n'), ENCODING).strip().split('\r\n')

@write_required
def StartInstrumentAcquire(instrumentname, time):
    return str(get(f'StartInstrumentAcquire({instrumentname}, {time})\r\n'))


def GetInstrumentAcquired1D(instrumentname):
    return str(get(f'GetInstrumentAcquired1D({instrumentname})\r\n'))


def GetInstrumentAcquired2D(instrumentname):
    b=get(f'GetInstrumentAcquired2D({instrumentname})\r\n')
    expcols, exprows = stream_size(b)
    s=str(b, ENCODING)
    arr = np.fromstring(s.split('\r\n',maxsplit=1)[1].replace('\r\n','\t'), count=expcols*exprows, sep='\t', dtype=int)
    return arr.reshape((exprows, expcols))


def GetInstrumentAcquired3D(instrumentname):
    return str(get(f'GetInstrumentAcquired3D({instrumentname})\r\n'))
