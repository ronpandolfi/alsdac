import enum
import numpy as np
import re
from operator import itemgetter


class _SimpleReprEnum(enum.Enum):
    def __repr__(self):
        return self.name


class Role(_SimpleReprEnum):
    CLIENT = enum.auto()
    SERVER = enum.auto()


class Direction(_SimpleReprEnum):
    RESPONSE = enum.auto()
    REQUEST = enum.auto()


Commands = {}
Commands[Role.CLIENT] = {}
Commands[Role.SERVER] = {}
_commands = set()

ENCODING = 'ascii'


class _MetaDirectionalMessage(type):
    # see what you've done, @tacaswell and @danielballan?
    def __new__(metacls, name, bases, dct):
        if name.endswith('Request'):
            direction = Direction.REQUEST
            command_dict = Commands[Role.CLIENT]
        else:
            direction = Direction.RESPONSE
            command_dict = Commands[Role.SERVER]

        dct['DIRECTION'] = direction
        new_class = super().__new__(metacls, name, bases, dct)

        if new_class.FNC is not None:
            command_dict[new_class.FNC] = new_class

        if not name.startswith('_'):
            _commands.add(new_class)
        return new_class


class Message(metaclass=_MetaDirectionalMessage):
    __slots__ = ('str_payload')
    WRITE_REQUIRED = False
    FNC = None

    def __init__(self, str_payload):
        self.str_payload = str_payload

    @classmethod
    def from_wire(cls, payload_buffers):
        return cls.from_components(
            str(b''.join(payload_buffers), ENCODING).strip())

    @classmethod
    def from_components(cls, str_payload):
        # Bwahahahaha
        instance = cls.__new__(cls)
        instance.str_payload = str_payload
        return instance

    def __bytes__(self):
        return bytes(self.str_payload, ENCODING)

    def __repr__(self):
        return f'{self.__class__.__name__}: {self.str_payload!r}'

class _TwoParamRequestBase(Message):
    __slots__ = ()
    FNC=''

    def __init__(self, target, value):
        super().__init__(f'{self.FNC}({target}, {value})\r\n')


class _OneParamRequestBase(Message):
    __slots__ = ()
    FNC = ''

    def __init__(self, target):
        super().__init__(f'{self.FNC}({target})\r\n')


class _ZeroParamRequestBase(Message):
    __slots__ = ()
    FNC = ''

    def __init__(self):
        super().__init__(f'{self.FNC}()\r\n')

class AtPresetRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'AtPreset'


class AtPresetResponse(Message):
    __slots__ = ()
    FNC = 'AtPreset'

    @property
    def data(self):
        return bool(self.str_payload)


class AtTrajectoryRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'AtTrajectory'


class AtTrajectoryResponse(Message):
    __slots__ = ()
    FNC = 'AtTrajectory'

    @property
    def data(self):
        return bool(self.str_payload)


class DisableBreakpointsRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'DisableBreakpoints'


class DisableBreakpointsResponse(Message):
    __slots__ = ()
    FNC = 'DisableBreakpoints'

    @property
    def data(self):
        return bool(self.str_payload)


class DisableMotorRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'DisableMotor'


class DisableMotorResponse(Message):
    __slots__ = ()
    FNC = 'DisableMotor'

    @property
    def data(self):
        return bool(self.str_payload)


class EnableMotorRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'EnableMotor'


class EnableMotorResponse(Message):
    __slots__ = ()
    FNC = 'EnableMotor'

    @property
    def data(self):
        return bool(self.str_payload)


class GetFlyingPositionsRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetFlyingPositions'


class GetFlyingPositionsResponse(Message):
    __slots__ = ()
    FNC = 'GetFlyingPositions'

    @property
    def data(self):
        # TODO check
        np.fromstring(self.str_payload, dtype=np.single)


class ListResponse(Message):
    @property
    def data(self):
        names = str(self.str_payload, ENCODING).strip().split('\r\n')
        if names == ['']: names = []
        return names

class ListMotorsRequest(_ZeroParamRequestBase):
    __slots__ = ()
    FNC = 'ListMotors'


class ListMotorsResponse(ListResponse):
    __slots__ = ()
    FNC = 'ListMotors'

class ListInstrumentsRequest(_ZeroParamRequestBase):
    __slots__ = ()
    FNC = 'ListInstruments'


class ListInstrumentsResponse(ListResponse):
    __slots__ = ()
    FNC = 'ListInstruments'


class ListAIsRequest(_ZeroParamRequestBase):
    __slots__ = ()
    FNC = 'ListAIs'


class ListAIsResponse(ListResponse):
    __slots__ = ()
    FNC = 'ListAIs'


class ListDIOsRequest(_ZeroParamRequestBase):
    __slots__ = ()
    FNC = 'ListDIOs'


class ListDIOsResponse(ListResponse):
    __slots__ = ()
    FNC = 'ListDIOs'


class GetFreerunRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetFreerun'


class GetFreerunResponse(Message):
    __slots__ = ()
    FNC = 'GetFreerun'

    @property
    def data(self):
        return float(self.str_payload)

class StartInstrumentAcquireRequest(_TwoParamRequestBase):
    __slots__ = ()
    FNC = 'StartInstrumentAcquire'

class StartInstrumentAcquireResponse(Message):
    __slots__ = ()
    FNC = 'StartInstrumentAcquire'

class GetInstrumentAcquired1DRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetInstrumentAcquired1D'


class GetInstrumentAcquired1DResponse(Message):
    __slots__ = ()
    FNC = 'GetInstrumentAcquired1D'

    @property
    def data(self):
        return self.str_payload


class GetInstrumentAcquired2DRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetInstrumentAcquired2D'


class GetInstrumentAcquired2DResponse(Message):
    __slots__ = ()
    FNC = 'GetInstrumentAcquired2D'

    @property
    def data(self):
        def stream_size(b):
            m = re.match(b'(?P<_0>\d*) Points by (?P<_1>\d*) channels', b)
            if m:
                map(itemgetter(1), sorted(m.groupdict().items()))
                return map(int, m.groups())
            return None, None

        b = self.str_payload
        header, _, img = b.partition('\r\n')
        img.replace('\r\n', '\t')
        expcols, exprows = stream_size(header)
        arr = np.fromstring(img,
                            count=expcols * exprows, sep='\t',
                            dtype=int)
        return arr.reshape((exprows, expcols))


class GetInstrumentAcquired3DRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetInstrumentAcquired3D'


class GetInstrumentAcquired3DResponse(Message):
    __slots__ = ()
    FNC = 'GetInstrumentAcquired3D'

    @property
    def data(self):
        return self.str_payload


class GetInstrumentStatusRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetInstrumentStatus'


class GetInstrumentStatusResponse(Message):
    __slots__ = ()
    FNC = 'GetInstrumentStatus'

    @property
    def data(self):
        return self.str_payload.split('\r\n')


class GetMotorRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetMotor'


class GetMotorResponse(Message):
    __slots__ = ()
    FNC = 'GetMotor'

    @property
    def data(self):
        pos, hexv, datetime = self.str_payload.split(' ', 2)
        pos = float(pos)
        # TODO make datetime actuually return datetime
        return pos, hexv, datetime


class GetMotorPosRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetMotorPos'


class GetMotorPosResponse(Message):
    __slots__ = ()
    FNC = 'GetMotorPos'

    @property
    def data(self):
        return float(self.str_payload)


class GetMotorStatusRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetMotorStatus'


class GetMotorStatusResponse(Message):
    __slots__ = ()
    FNC = 'GetMotorStatus'

    @property
    def data(self):
        return self.str_payload.startswith('Move finished')


class GetMotorVelocityRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetMotorVelocity'


class GetMotorVelocityResponse(Message):
    __slots__ = ()
    FNC = 'GetMotorVelocity'

    @property
    def data(self):
        return self.str_payload


class GetSoftLimitsRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'GetSoftLimits'


class GetSoftLimitsResponse(Message):
    __slots__ = ()
    FNC = 'GetSoftLimits'

    @property
    def data(self):
        return self.str_payload


class HomeMotorRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'HomeMotor'


class HomeMotorResponse(Message):
    __slots__ = ()
    FNC = 'HomeMotor'

    @property
    def data(self):
        return self.str_payload


class MoveToTrajectoryRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'MoveToTrajectory'


class MoveToTrajectoryResponse(Message):
    __slots__ = ()
    FNC = 'MoveToTrajectory'

    @property
    def data(self):
        return self.str_payload


class StopMotorRequest(_OneParamRequestBase):
    __slots__ = ()
    FNC = 'StopMotor'


class StopMotorResponse(Message):
    __slots__ = ()
    FNC = 'StopMotor'

    @property
    def data(self):
        return self.str_payload


class State(_SimpleReprEnum):
    IDLE = enum.auto()
    AWAIT_RESPONSE = enum.auto()


class ProtocolError(Exception):
    ...


class LVS:
    def __init__(self, our_role):
        self.our_role = our_role
        if our_role is Role.CLIENT:
            self.their_role = Role.SERVER
        else:
            self.their_role = Role.CLIENT

        self.state = State.IDLE

        self.active_resp = None

    def send(self, cmd):
        if self.our_role is Role.CLIENT:
            if self.state is not State.IDLE:
                raise ProtocolError(
                    'may not have more than one request in flight')
            self.active_resp = Commands[Role.SERVER][cmd.FNC]

            self.state = State.AWAIT_RESPONSE
            return bytes(cmd)
        else:
            raise Exception

    def recv(self, payload):
        if self.our_role is Role.CLIENT:
            if self.state is not State.AWAIT_RESPONSE:
                raise ProtocolError(
                    'Did not ask for anything')
            ret = self.active_resp.from_wire(payload)
            self.state = State.IDLE
            self.active_resp = None
            return ret
        else:
            raise Exception
