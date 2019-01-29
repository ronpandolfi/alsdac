#!/usr/bin/env python3
from caproto.server import (pvproperty, PVGroup, SubGroup,
                            ioc_arg_parser, run, records)
from caproto._dbr import ChannelType

import alsdac
import time
import numpy as np
import trio
from alsdac import _sansio
import socket
from caproto.trio.server import Context, run
import caproto as ca
import logging


class LVGroup(PVGroup):

    @property
    def devicename(self) -> str:
        return self.prefix.split(':')[-1].split('.')[0]


class DynamicLVGroup(LVGroup):
    device_list_message_cls = None
    device_cls = None
    devices = pvproperty(value=[], dtype=ChannelType.STRING, max_length=1000)

    async def update(self):
        device_names = (await self.parent.get(self.device_list_message_cls())).data
        newpvs = {}
        for name in device_names:
            device = self.device_cls(name, parent=self)
            newpvs.update({f'{self.prefix}{name}.{key}': value for key, value in device.attr_pvdb.items()
                           if f'{self.prefix}{name}.{key}' not in self.pvdb})
        self.pvdb.update(newpvs)
        return newpvs

    @devices.getter
    async def devices(self, instance):
        await self.update()
        return list(self.pvdb.keys())


class Instrument(LVGroup):
    trigger = pvproperty(value=[0], dtype=bool)
    read = pvproperty(value=[0], dtype=float)
    scalarread = pvproperty(value=[0], dtype=float)

    # Non-standard PVs
    exposure_time = pvproperty(value=[1], dtype=float)
    exposure_counts = pvproperty(value=[1], dtype=int)
    size_x = pvproperty(value=[0], dtype=int)
    size_y = pvproperty(value=[0], dtype=int)

    last_capture = None

    @trigger.putter
    async def trigger(self, instance, value):
        await self.parent.parent.get(_sansio.StartInstrumentAcquireRequest(self.devicename, self.exposure_time))
        self.last_capture = None

    @read.getter
    async def read(self, instance):
        if self.last_capture is not None:
            return self.last_capture.flatten()
        self.last_capture = alsdac.GetInstrumentAcquired2D(self.devicename)
        await self.size_x.write(self.last_capture.shape[0])
        await self.size_y.write(self.last_capture.shape[1])
        return self.last_capture.flatten()

    @scalarread.getter
    async def scalarread(self, instance):
        if self.last_capture is not None:
            return self.reduce_to_scalar(self.last_capture)
        self.last_capture = alsdac.GetInstrumentAcquired2D(self.devicename)
        await self.size_x.write(self.last_capture.shape[0])
        await self.size_y.write(self.last_capture.shape[1])
        scalar = self.reduce_to_scalar(self.last_capture)
        return scalar

    @staticmethod
    def reduce_to_scalar(image):
        shape = image.shape
        return image[shape[0] // 2 - 2:shape[0] // 2 + 2, shape[1] // 2 - 2:shape[1] // 2 + 2].sum()


class AnalogInput(LVGroup):  # AIFields
    value = pvproperty(value=[0], dtype=float, read_only=True)

    @value.getter
    async def value(self, instance):
        return alsdac.GetFreerun(self.devicename)


class DigitalInputOutput(AnalogInput):  # DigitalFields
    pass


class Motor(LVGroup):  # MotorFields
    # FIXME: most of these don't actually do anything
    OFF = pvproperty(value=[0], dtype=float)
    DIR = pvproperty(value=[0], dtype=float)
    FOFF = pvproperty(value=[0], dtype=float)
    SET = pvproperty(value=[0], dtype=float)
    VELO = pvproperty(value=[0], dtype=float)
    ACCL = pvproperty(value=[0], dtype=float)
    MOVN = pvproperty(value=[False], dtype=bool)
    DMOV = pvproperty(value=[0], dtype=float)
    HLS = pvproperty(value=[0], dtype=float)
    LLS = pvproperty(value=[0], dtype=float)
    TDIR = pvproperty(value=[0], dtype=float)
    STOP = pvproperty(value=[0], dtype=float)
    HOMF = pvproperty(value=[0], dtype=float)
    HOMR = pvproperty(value=[0], dtype=float)
    EGU = pvproperty(value='units', dtype=str)
    VAL = pvproperty(dtype=float, precision=3)
    PREC = pvproperty(value=[3], dtype=int)
    RBV = pvproperty(dtype=float, precision=3)

    @VAL.putter
    async def VAL(self, instance, value):
        await self.MOVN.write([True])
        # alsdac.MoveMotor(self.devicename, value[0])
        await self.parent.parent.get(_sansio.MoveMotorRequest(self.devicename, value))

    # TODO: LABVIEW TCP interface has no command to get the setpoint; request this addition; fill in getter

    # # TODO: And the readback getter
    # @VAL.getter
    # async def VAL(obj, instance):
    #     # NOTE: this is effectively a no-operation method
    #     # that is, with or without this method definition, self.readback.value
    #     # will be returned automatically
    #     return obj._value

    @VAL.startup
    async def VAL(self, instance, async_lib):
        'Periodically check if at setpoint'
        while True:
            if self.MOVN.value[0]:
                while True:
                    _, rbv = await self.RBV.read(ChannelType.FLOAT)
                    if abs(instance.value[0] - rbv[0]) < 0.0001:  # Threshold
                        await self.MOVN.write([False])
                        break

                    await async_lib.library.sleep(.1)
            await async_lib.library.sleep(.1)

    @RBV.getter
    async def RBV(self, instance):
        return await self.parent.parent.get(_sansio.GetMotorPosResponse(self.devicename))


async def sender(client_sock, lvs: _sansio.LVS, data):
    # print("sender: started!")
    # print("sender: sending {!r}".format(data))
    # print('sent:', data)
    await client_sock.send_all(lvs.send(data))


async def receiver(client_sock: trio.SocketStream, lvs: _sansio.LVS):
    _data = []
    _data.append(await client_sock.receive_some(alsdac.BUFSIZE))

    expcols, exprows, _ = alsdac.stream_size(_data[0])

    if exprows and expcols:
        while not _data[-1].endswith(b'\r\n\r\n'):
            _data.append(await client_sock.receive_some(alsdac.BUFSIZE))

    # print('received:', str(b''.join(_data), alsdac.ENCODING).strip())
    return lvs.recv(_data)


# TODO: run update periodically

class DeferDict(dict):
    def __init__(self, *args, **kwargs):
        super(DeferDict, self).__init__(*args, **kwargs)
        self.defer_to = []
        self.filter = ''

    def __missing__(self, key):
        if self.filter in key:
            for group in self.defer_to:
                if group.prefix in key:
                    return group.pvdb[key]


class Beamline(PVGroup):
    def __init__(self, *args, **kwargs):
        super(Beamline, self).__init__(*args, **kwargs)
        self._lock = trio.Lock()
        self._socket = None
        self._socket_stream = None
        self.lvs = _sansio.LVS(_sansio.Role.CLIENT)

        # Make pvdb defer to subgroups
        self.pvdb = DeferDict()
        self.pvdb.filter = self.prefix
        self.pvdb.defer_to = [self.Motors, self.Detectors, self.AnalogInputs, self.DigitalInputOutputs]

    async def update(self):
        for group in self.Detectors, self.AnalogInputs, self.DigitalInputOutputs, self.Motors:
            await group.update()  # Ignore introspection warning

    async def startup_socket(self):
        if not self._socket:
            self._socket = trio.socket.socket()
            await self._socket.connect((alsdac.SERVER_ADDRESS, alsdac.PORT))
            self._socket_stream = trio.SocketStream(self._socket)

            self._socket_stream.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self._socket_stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            self._socket_stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
            self._socket_stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 10)
            self._socket_stream.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    async def get(self, cmd):
        async with self._lock:
            await self.startup_socket()
            await sender(self._socket_stream, self.lvs, cmd)
            result = await receiver(self._socket_stream, self.lvs)
            return result

    @SubGroup(prefix='instruments:')
    class Detectors(DynamicLVGroup):
        device_list_message_cls = _sansio.ListInstrumentsRequest
        device_cls = Instrument

    @SubGroup(prefix='ais:')
    class AnalogInputs(DynamicLVGroup):
        device_list_message_cls = _sansio.ListAIsRequest
        device_cls = AnalogInput

    @SubGroup(prefix='dios:')
    class DigitalInputOutputs(DynamicLVGroup):
        device_list_message_cls = _sansio.ListDIOsRequest
        device_cls = DigitalInputOutput

    @SubGroup(prefix='motors:')
    class Motors(DynamicLVGroup):
        device_list_message_cls = _sansio.ListMotorsRequest
        device_cls = Motor


class DynamicContext(Context):
    def __init__(self, update, *args, **kwargs):
        super(DynamicContext, self).__init__(*args, **kwargs)
        self._devices_inited = False
        self.update = update

    async def _broadcaster_evaluate(self, addr, commands):
        if not self._devices_inited:
            await self.update()
            self._devices_inited = True
        await super(DynamicContext, self)._broadcaster_evaluate(addr, commands)


async def main(update, pvdb, log_pv_names):
    ctx = DynamicContext(update, pvdb)
    return await ctx.run(log_pv_names=log_pv_names)


if __name__ == '__main__':
    import sys

    if '--address' in sys.argv:
        alsdac.set_server_address(sys.argv['--address'])
    if '--port' in sys.argv:
        alsdac.set_port(sys.argv['--port'])

    ioc_options, run_options = ioc_arg_parser(
        default_prefix='beamline:',
        desc='als test')
    ioc = Beamline(**ioc_options)
    # run(ioc.pvdb, **run_options)
    # logging.getLogger('caproto').setLevel('DEBUG')
    print(run_options)
    trio.run(main, ioc.update, ioc.pvdb, '--list-pvs' in sys.argv)

    # # Afterwards, you can connect to these devices like:
    # import os
    # os.environ['OPHYD_CONTROL_LAYER']='caproto'
    # import ophyd
    # x = ophyd.EpicsMotor('beamline:motors:esp300axis2', name='x')
    # z = ophyd.EpicsMotor('beamline:motors:esp300axis2', name='z')
    # c = ophyd.EpicsSignal('beamline:instruments:ptGreyInstrument.read', name='cam')
