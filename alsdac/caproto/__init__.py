#!/usr/bin/env python3
from caproto.server import (pvproperty, PVGroup, SubGroup,
                            ioc_arg_parser, run, records)
from caproto._dbr import ChannelType

import alsdac
import numpy as np

class LVGroup(PVGroup):
    @property
    def devicename(self)->str:
        return self.prefix.split(':')[-1].split('.')[0]



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
        alsdac.StartInstrumentAcquire(self.devicename, self.exposure_time)
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
        shape=image.shape
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
    VAL = pvproperty(value=[0], dtype=float, precision=3)
    PREC = pvproperty(value=[3], dtype=int)
    RBV = pvproperty(value=[0], dtype=float, precision=3)

    @VAL.putter
    async def VAL(self, instance, value):
        await self.MOVN.write([True])
        alsdac.MoveMotor(self.devicename, value[0])

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
                    if abs(instance.value[0]-rbv[0]) < 0.0001:  # Threshold
                        await self.MOVN.write([False])
                        break

                    await async_lib.library.sleep(.1)
            await async_lib.library.sleep(.1)

    @RBV.getter
    async def RBV(self, instance):
        return alsdac.GetMotorPos(self.devicename)


class Beamline(PVGroup):
    @SubGroup(prefix='instruments:')
    class Detectors(LVGroup):
        names = alsdac.ListInstruments()
        for name in names:
            locals()[name] = SubGroup(Instrument, prefix=name + '.')

        devices = pvproperty(value=[], dtype=str)

        @devices.getter
        async def devices(self, instance):
            return list(alsdac.ListInstruments())

    @SubGroup(prefix='ais:')
    class AnalogInputs(LVGroup):
        names = alsdac.ListAIs()
        for name in names:
            locals()[name] = SubGroup(AnalogInput, prefix=name + '.')

        devices = pvproperty(value=[], dtype=str)

        @devices.getter
        async def devices(self, instance):
            return list(alsdac.ListAIs())

    @SubGroup(prefix='dios:')
    class DigitalInputOutputs(LVGroup):
        names = alsdac.ListDIOs()
        for name in names:
            locals()[name] = SubGroup(DigitalInputOutput, prefix=name + '.')

        devices = pvproperty(value=[], dtype=str)

        @devices.getter
        async def devices(self, instance):
            return list(alsdac.ListDIOs())


    @SubGroup(prefix='motors:')
    class Motors(LVGroup):
        names = alsdac.ListMotors()
        for name in names:
            locals()[name] = SubGroup(Motor, prefix=name + '.')

        devices = pvproperty(value=[], dtype=str)

        @devices.getter
        async def devices(self, instance):
            return list(alsdac.ListMotors())


if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix='beamline:',
        desc='als test')
    ioc = Beamline(**ioc_options)
    run(ioc.pvdb, **run_options)

    # # Afterwards, you can connect to these devices like:
    # import os
    # os.environ['OPHYD_CONTROL_LAYER']='caproto'
    # import ophyd
    # x = ophyd.EpicsMotor('beamline:motors:esp300axis2', name='x')
    # z = ophyd.EpicsMotor('beamline:motors:esp300axis2', name='z')
    # c = ophyd.EpicsSignal('beamline:instruments:ptGreyInstrument.read', name='cam')
