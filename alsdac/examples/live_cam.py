from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import pyqtgraph as pg
import pyqtgraph.ptime as ptime

# FPS Notes: .012 from Bayreuth


# Connect to camera
import os

os.environ['OPHYD_CONTROL_LAYER'] = 'caproto'
from alsdac.ophyd import Instrument

cam = Instrument('beamline:instruments:ptGreyInstrument', name='cam')

app = QtGui.QApplication([])

pg.setConfigOption('imageAxisOrder', 'row-major')

## Create image item
img = pg.ImageItem(border='w')

## Create window with GraphicsView widget
view = pg.ImageView(imageItem=img)
view.setWindowTitle('Live view of ptGreyInstrument')
view.show()
crosshair = pg.ScatterPlotItem
center = pg.PlotDataItem(x=[0], y=[0], symbol='+')
view.view.addItem(center)

## lock the aspect ratio so pixels are always square
# img.setAspectLocked(True)


## Set initial view bounds
# view.setRange(QtCore.QRectF(0, 0, 600, 600))

updateTime = ptime.time()
fps = 0


def updateData(success=False, **kwargs):
    print(success)
    # if not success: return
    global img, data, i, updateTime, fps, center
    ## Display the data
    data = cam.read()['cam_image']['value']
    img.setImage(data, autoLevels=False)

    now = ptime.time()
    fps2 = 1.0 / (now - updateTime)
    updateTime = now
    fps = fps * 0.9 + fps2 * 0.1

    # Set center
    center.setData(x=[data.shape[0]/2], y=[data.shape[1]/2])

    # Trigger the camera
    cam.trigger()
    cam.trigger_signals[0].put(1, callback=updateData)

    print("%0.3f fps" % fps)


cam.subscribe(updateData, event_type=cam.SUB_ACQ_DONE, run=False)  # Not sure why this doesn't emit on each trigger
cam.trigger()

## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
