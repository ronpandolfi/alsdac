import os
import time

os.environ['OPHYD_CONTROL_LAYER'] = 'caproto'
from ophyd import Device, Component, EpicsSignal, EpicsSignalRO, EpicsMotor, get_cl


class Instrument(Device):
    image = Component(EpicsSignalRO, '.read')
    sig_trigger = Component(EpicsSignal, '.trigger', trigger_value=True)

    size_x = Component(EpicsSignalRO, '.size_x')
    size_y = Component(EpicsSignalRO, '.size_y')

    def read(self):
        # while True:
        #     try:
        d = super(Instrument, self).read()
        shape = self.size_x.get(), self.size_y.get()
        d[f'{self.name}_image']['value'] = d[f'{self.name}_image']['value'].reshape(shape)
        return d

    # except TimeoutError:
    #     print('Waiting for response; connection is slow...')

    def trigger(self):
        # while True:
        #     try:
        return super(Instrument, self).trigger()
    # except TimeoutError:
    #     print('Waiting for response; connection is slow...')

class Motor(EpicsMotor):
    def __init__(self, *args, **kwargs):
        super(Motor, self).__init__(*args, **kwargs)
        self._status_threads = []

    def move(self, *args, **kwargs):
        status = super(Motor, self).move(*args, **kwargs)
        def statusmonitor_thread():
            thisthread = self._status_threads[-1]
            try:
                while True:
                    time.sleep(.01)
                    # check if within threshold
                    if abs(self.user_readback.get(use_monitor=False)-self.user_setpoint.get()) < .0001:
                        success = True
                        break
            except TimeoutError:
                # logger.debug('automonitor(%r, %s) timed out', self.name)
                success = False
            except Exception as ex:
                # logger.debug('automonitor(%r, %s) failed', self.name, exc_info=ex)
                success = False
            finally:
                status._finished(success=success)
                self._status_threads.remove(thisthread)
                del thisthread

        statusthread = get_cl().thread_class(target=statusmonitor_thread)
        self._status_threads.append(statusthread)
        statusthread.daemon = True
        statusthread.start()
        return status

class ScalarInstrument(Device):
    image = Component(EpicsSignalRO, '.scalarread')
    sig_trigger = Component(EpicsSignal, '.trigger', trigger_value=True)



if __name__ == '__main__':
    # Afterwards, you can connect to these devices like:
    import os

    os.environ['OPHYD_CONTROL_LAYER'] = 'caproto'
    from ophyd import Device, Component, EpicsSignal, EpicsSignalRO

    os.environ['OPHYD_CONTROL_LAYER'] = 'caproto'
    import ophyd

    x = Motor('beamline:motors:esp300axis2', name='x')
    z = Motor('beamline:motors:esp300axis2', name='z')
    x.wait_for_connection()
    x.set(.1)
    # c = EpicsSignalRO('beamline:instruments:ptGreyInstrument.read', name='cam')
    # c.wait_for_connection()
    # c.get()

    cam = Instrument('beamline:instruments:ptGreyInstrument', name='cam')
    print(cam.read())
