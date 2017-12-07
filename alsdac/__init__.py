# echo-client-low-level.py

import sys
import trio
from typing import Union, Tuple

# arbitrary, but:
# - must be in between 1024 and 65535
# - can't be in use by some other program on your computer
# - must match what we set in our echo server
PORT = 12345
# How much memory to spend (at most) on each call to recv. Pretty arbitrary,
# but shouldn't be too big or too small.
BUFSIZE = 16384


def get(data):
    async def _get(data):
        result = None

        async def sender(client_sock, data):
            print("sender: started!")
            print("sender: sending {!r}".format(data))
            await client_sock.sendall(bytes(data, 'utf-8'))

        async def receiver(client_sock):
            print("receiver: started!")
            _data = await client_sock.recv(BUFSIZE)
            print("receiver: got data {!r}".format(_data))
            if not data:
                print("receiver: connection closed")
                sys.exit()
            nonlocal result
            result = _data

        print("parent: connecting to 127.0.0.1:{}".format(PORT))
        with trio.socket.socket() as client_sock:
            await client_sock.connect(("127.0.0.1", PORT))
            async with trio.open_nursery() as nursery:
                print("parent: spawning sender...")
                nursery.start_soon(sender, client_sock, data)

                print("parent: spawning receiver...")
                nursery.start_soon(receiver, client_sock)

        return result
    return trio.run(_get, data)


def GetMotorPos(motorname:str) -> float:
    return float(get(f'GetMotorPos({motorname})'))


def MoveMotor(motorname:str, pos:Union[float, int]) -> bool:
    return bool(get(f'MoveMotor({motorname}, {pos})'))

def GetSoftLimits(motorname:str) -> Tuple[float, float]:
    return tuple(map(float,get(f'GetSoftLimits({motorname})').split(b' ')))[:2] # The 2 just makes pylint happy :)

if __name__=='__main__':
    GetMotorPos('test')
    MoveMotor('test', 1)
    GetMotorPos('test')
    MoveMotor('test', 0)