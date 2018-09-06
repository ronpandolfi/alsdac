#!/usr/bin/env python3
from caproto.server import (pvproperty, PVGroup, SubGroup,
                            ioc_arg_parser, run, records)

import alsdac
import numpy as np

class LVGroup(PVGroup):
    @property
    def devicename(self)->str:
        return self.prefix.split(':')[-1].split('.')[0]


class Instrument(LVGroup):
    trigger = pvproperty(value=[0], dtype=bool)
    read = pvproperty(value=[0], dtype=float)

    # Non-standard PVs
    exposure_time = pvproperty(value=[1], dtype=float)
    exposure_counts = pvproperty(value=[1], dtype=int)

    @trigger.putter
    async def trigger(self, instance, value):
        alsdac.StartInstrumentAcquire(self.devicename, self.exposure_time)

    @read.getter
    async def read(self, instance):
        return alsdac.GetInstrumentAcquired2D(self.devicename)


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
    MOVN = pvproperty(value=[0], dtype=float)
    DMOV = pvproperty(value=[0], dtype=float)
    HLS = pvproperty(value=[0], dtype=float)
    LLS = pvproperty(value=[0], dtype=float)
    TDIR = pvproperty(value=[0], dtype=float)
    STOP = pvproperty(value=[0], dtype=float)
    HOMF = pvproperty(value=[0], dtype=float)
    HOMR = pvproperty(value=[0], dtype=float)
    EGU = pvproperty(value=[0], dtype=float)
    VAL = pvproperty(value=[0], dtype=float)
    RBV = pvproperty(value=[0], dtype=float)

    @VAL.putter
    async def VAL(self, instance, value):
        alsdac.MoveMotor(self.devicename, value)

    # TODO: LABVIEW TCP interface has no command to get the setpoint; request this addition; fill in getter

    # # TODO: And the readback getter
    # @VAL.getter
    # async def VAL(obj, instance):
    #     # NOTE: this is effectively a no-operation method
    #     # that is, with or without this method definition, self.readback.value
    #     # will be returned automatically
    #     return obj._value

    @RBV.getter
    async def RBV(self, instance):
        return alsdac.GetMotorPos(self.devicename)


class Beamline(PVGroup):
    @SubGroup(prefix='instruments:')
    class Detectors(PVGroup):
        names = alsdac.ListInstruments()
        for name in names:
            locals()[name] = SubGroup(Instrument, prefix=name + ':')

    @SubGroup(prefix='ais:')
    class AnalogInputs(PVGroup):
        names = alsdac.ListAIs()
        for name in names:
            locals()[name] = SubGroup(AnalogInput, prefix=name + '.')

    @SubGroup(prefix='dios:')
    class DigitalInputOutputs(PVGroup):
        names = alsdac.ListDIOs()
        for name in names:
            locals()[name] = SubGroup(DigitalInputOutput, prefix=name + '.')

    @SubGroup(prefix='motors:')
    class Motors(PVGroup):
        names = alsdac.ListMotors()
        for name in names:
            locals()[name] = SubGroup(Motor, prefix=name + '.')


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
    # a = ophyd.EpicsSignal('beamline:motors:fake.RBV','beamline:m1:VAL')
    # b = ophyd.EpicsMotor('beamline:motors:fake', name='fake')
    # c = ophyd.
