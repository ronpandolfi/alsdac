#!/usr/bin/env python3
from caproto.server import (pvproperty, PVGroup, SubGroup,
                            ioc_arg_parser, run)
import numpy as np
import functools
import alsdac


class AnalogInput(PVGroup):
    value = pvproperty(value=[0],
                     dtype=float,
                     read_only=True)

    @value.getter
    async def value(self, instance):
        # name = instance.pvspec.attr
        return alsdac.GetFreerun('Beam Current')


def Motor(name):
    class Motor(PVGroup):
        VAL = pvproperty(value=[0],
                         dtype=float,
                         )
        RBV = pvproperty(value=[0],
                         dtype=float,
                         )
        @VAL.putter
        async def VAL(self, instance, value):
            print(f'Setting {instance} to {value}')
            # alsdac.MoveMotor(name, value)

            # TODO: LABVIEW TCP interface has no command to get the setpoint; request this addition; fill in getter

        # # And the readback getter:
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
    @SubGroup(prefix='motors')
    class Motors(PVGroup):
        names = alsdac.ListMotors()
        motors={}
        for name in names:
            motors[name] = SubGroup(Motor(name), prefix=name)

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
    # a = ophyd.EpicsSignal('beamline:m1:RBV','beamline:m1:VAL')