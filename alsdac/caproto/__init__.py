#!/usr/bin/env python3
from caproto.server import (pvproperty, PVGroup, SubGroup,
                            ioc_arg_parser, run)

import alsdac

def Instrument(name):
    class Instrument(PVGroup):
        @SubGroup(prefix='cam1.')
        class Camera(PVGroup):
            blah = pvproperty(value=[0], dtype=float)
    return Instrument

def AnalogInput(name):
    class AnalogInput(PVGroup):
        value = pvproperty(value=[0], dtype=float, read_only=True)

        @value.getter
        async def value(self, instance):
            return alsdac.GetFreerun(name)

    return AnalogInput


def Motor(name):
    class Motor(PVGroup):
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
            print(f'Setting {instance} to {value}')
            # alsdac.MoveMotor(name, value)

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
            return alsdac.GetMotorPos(name)
    return Motor

class Beamline(PVGroup):

    @SubGroup(prefix='instruments:')
    class Detectors(PVGroup):
        names = alsdac.ListInstruments()
        for name in names:
            locals()[name] = SubGroup(Instrument(name), prefix=name+':')

    @SubGroup(prefix='ais:')
    class AnalogInputs(PVGroup):
        names = alsdac.ListAIs()
        for name in names:
            locals()[name] = SubGroup(AnalogInput(name), prefix=name+'.')

    @SubGroup(prefix='motors:')
    class Motors(PVGroup):
        names = alsdac.ListMotors()
        for name in names:
            locals()[name] = SubGroup(Motor(name), prefix=name+'.')


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