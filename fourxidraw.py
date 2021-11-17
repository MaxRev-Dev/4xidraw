# 4xidraw.py
# Part of the 4xiDraw driver for Inkscape
#
# Copyright 2017 Windell H. Oskay, Evil Mad Scientist Laboratories
# Copyright 2017 Torsten Martinsen
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Requires Pyserial 2.7.0 or newer. Pyserial 3.0 recommended.


import fourxidraw_compat  # To bridge Python 2/3, Inkscape 0.*/1.*
import fourxidraw_conf  # Some settings can be changed here.
import plot_utils   # https://github.com/evil-mad/plotink  Requires version 0.4
from grbl_motion import GrblMotion
from grbl_serial import GrblSerial
import grbl_serial
import time
import string
import serial
import gettext
from array import *
from math import sqrt
import simplepath
from simpletransform import *
import inkex
import sys
sys.path.append('lib')


try:
    xrange = xrange
    # We have Python 2
except:
    xrange = range
    # We have Python 3

IDENTITY_TRANSFORM = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]


class FourxiDrawClass(inkex.Effect):

    def compat_add_option(self, name, action, type, dest, default, help):
        if fourxidraw_compat.isPython3():
            self.arg_parser.add_argument(name,
                                         action=action, type=fourxidraw_compat.compatGetArgumentTypeFromName(
                                             type),
                                         dest=dest, default=default,
                                         help=help)
        else:
            self.OptionParser.add_option(name,
                                         action=action, type=type,
                                         dest=dest, default=default,
                                         help=help)

    def compat_add_option_store_true(self, name, dest, help):
        if fourxidraw_compat.isPython3():
            self.arg_parser.add_argument(name,
                                         action="store_true",
                                         dest=dest,
                                         help=help)
        else:
            self.OptionParser.add_option(name,
                                         action="store_true",
                                         dest=dest,
                                         help=help)

    def __init__(self):
        inkex.Effect.__init__(self)
        self.start_time = time.time()
        self.doLogDebug = False

        self.compat_add_option("--mode",
                               action="store", type="string",
                               dest="mode", default="plot",
                               help="Mode (or GUI tab) selected")

        self.compat_add_option("--penUpPosition",
                               action="store", type="int",
                               dest="penUpPosition", default=fourxidraw_conf.PenUpPos,
                               help="Position of pen when lifted")

        self.compat_add_option("--penDownPosition",
                               action="store", type="int",
                               dest="penDownPosition", default=fourxidraw_conf.PenDownPos,
                               help="Position of pen for painting")

        self.compat_add_option("--setupType",
                               action="store", type="string",
                               dest="setupType", default="align-mode",
                               help="The setup option selected")

        self.compat_add_option("--applySpeed",
                               action="store", type="inkbool",
                               dest="applySpeed", default=fourxidraw_conf.applySpeed,
                               help="Whether to apply pen speeds")

        self.compat_add_option("--penDownSpeed",
                               action="store", type="int",
                               dest="penDownSpeed", default=fourxidraw_conf.PenDownSpeed,
                               help="Speed (mm/min) while pen is down")

        self.compat_add_option("--penUpSpeed",
                               action="store", type="int",
                               dest="penUpSpeed", default=fourxidraw_conf.PenUpSpeed,
                               help="Rapid speed (mm/min) while pen is up")

        self.compat_add_option("--penLiftRate",
                               action="store", type="int",
                               dest="penLiftRate", default=fourxidraw_conf.penLiftRate,
                               help="Rate of lifting pen ")
        self.compat_add_option("--penLiftDelay",
                               action="store", type="int",
                               dest="penLiftDelay", default=fourxidraw_conf.penLiftDelay,
                               help="Added delay after pen up (ms)")

        self.compat_add_option("--penLowerRate",
                               action="store", type="int",
                               dest="penLowerRate", default=fourxidraw_conf.penLowerRate,
                               help="Rate of lowering pen ")
        self.compat_add_option("--penLowerDelay",
                               action="store", type="int",
                               dest="penLowerDelay", default=fourxidraw_conf.penLowerDelay,
                               help="Added delay after pen down (ms)")

        self.compat_add_option("--autoRotate",
                               action="store", type="inkbool",
                               dest="autoRotate", default=fourxidraw_conf.autoRotate,
                               help="Print in portrait or landscape mode automatically")

        self.compat_add_option("--constSpeed",
                               action="store", type="inkbool",
                               dest="constSpeed", default=fourxidraw_conf.constSpeed,
                               help="Use constant velocity mode when pen is down")

        self.compat_add_option("--reportTime",
                               action="store", type="inkbool",
                               dest="reportTime", default=fourxidraw_conf.reportTime,
                               help="Report time elapsed")

        self.compat_add_option("--logSerial",
                               action="store", type="inkbool",
                               dest="logSerial", default=fourxidraw_conf.logSerial,
                               help="Log serial communication")

        self.compat_add_option("--smoothness",
                               action="store", type="float",
                               dest="smoothness", default=fourxidraw_conf.smoothness,
                               help="Smoothness of curves")

        self.compat_add_option("--cornering",
                               action="store", type="float",
                               dest="cornering", default=fourxidraw_conf.smoothness,
                               help="Cornering speed factor")

        self.compat_add_option("--manualType",
                               action="store", type="string",
                               dest="manualType", default="version-check",
                               help="The active option when Apply was pressed")

        self.compat_add_option("--WalkDistance",
                               action="store", type="float",
                               dest="WalkDistance", default=1,
                               help="Distance for manual walk")

        self.compat_add_option("--grblCommand",
                               action="store", type="string",
                               dest="grblCommand", default="$$",
                               help="GRBL command to execute")

        self.compat_add_option("--resumeType",
                               action="store", type="string",
                               dest="resumeType", default="ResumeNow",
                               help="The active option when Apply was pressed")

        self.compat_add_option("--layerNumber",
                               action="store", type="int",
                               dest="layerNumber", default=fourxidraw_conf.DefaultLayer,
                               help="Selected layer for multilayer plotting")

        self.compat_add_option("--fileOutput",
                               action="store", type="inkbool",
                               dest="fileOutput", default=fourxidraw_conf.fileOutput,
                               help="Output updated contents of SVG on stdout")

        self.boundingBox = False
        self.compat_add_option_store_true("--boundingBox",
                                          dest="boundingBox",
                                          help="Trace bounding box")

        self.bb = {'minX': 1e6, 'minY': 1e6, 'maxX': -1e6, 'maxY': -1e6}

        self.serialPort = None
        # Initial state of pen is neither up nor down, but _unknown_.
        self.bPenIsUp = None
        # Keeps track of pen postion when stepping through plot before resuming
        self.virtualPenIsUp = False
        self.ignoreLimits = False

        fX = None
        fY = None
        self.fCurrX = fourxidraw_conf.StartPosX
        self.fCurrY = fourxidraw_conf.StartPosY
        self.ptFirst = (fourxidraw_conf.StartPosX, fourxidraw_conf.StartPosY)
        self.bStopped = False
        self.fSpeed = 1
        self.resumeMode = False
        self.nodeCount = int(0)   # NOTE: python uses 32-bit ints.
        self.nodeTarget = int(0)
        self.pathcount = int(0)
        self.LayersFoundToPlot = False
        self.LayerOverrideSpeed = False
        self.LayerOverridePenDownHeight = False
        self.LayerPenDownPosition = -1
        self.LayerPenDownSpeed = -1

        self.penUpDistance = 0.0
        self.penDownDistance = 0.0

        # Values read from file:
        self.svgLayer_Old = int(0)
        self.svgNodeCount_Old = int(0)
        self.svgDataRead_Old = False
        self.svgLastPath_Old = int(0)
        self.svgLastPathNC_Old = int(0)
        self.svgLastKnownPosX_Old = float(0.0)
        self.svgLastKnownPosY_Old = float(0.0)
        self.svgPausedPosX_Old = float(0.0)
        self.svgPausedPosY_Old = float(0.0)

        # New values to write to file:
        self.svgLayer = int(0)
        self.svgNodeCount = int(0)
        self.svgDataRead = False
        self.svgLastPath = int(0)
        self.svgLastPathNC = int(0)
        self.svgLastKnownPosX = float(0.0)
        self.svgLastKnownPosY = float(0.0)
        self.svgPausedPosX = float(0.0)
        self.svgPausedPosY = float(0.0)

        self.PrintInLayersMode = False

        self.svgWidth = 0
        self.svgHeight = 0
        self.printPortrait = False

        self.xBoundsMax = fourxidraw_conf.PageWidthIn
        self.xBoundsMin = fourxidraw_conf.StartPosX
        self.yBoundsMax = fourxidraw_conf.PageHeightIn
        self.yBoundsMin = fourxidraw_conf.StartPosY

        self.docTransform = IDENTITY_TRANSFORM

        # must be set to a nonzero value before plotting.
        self.stepsPerInch = 0
        self.PenDownSpeed = fourxidraw_conf.PenDownSpeed * \
            fourxidraw_conf.SpeedScale  # Default speed when pen is down
        # Default speed when pen is down
        self.PenUpSpeed = 0.75 * fourxidraw_conf.SpeedScale

        # So that we only generate a warning once for each
        # unsupported SVG element, we use a dictionary to track
        # which elements have received a warning
        self.warnings = {}
        self.warnOutOfBounds = False

    def logDebug(self, msg):
        if not self.doLogDebug:
            return
        try:
            with open("4xidraw-debug.log", "a") as myfile:
                myfile.write('%s\n' % msg)
        except:
            inkex.errormsg(gettext.gettext("Error logging debug data."))

    def createMotion(self):
        self.motion = GrblMotion(self.serialPort, fourxidraw_conf.DPI_16X,
                                 self.options.penUpPosition, self.options.penDownPosition)

    def effect(self):
        '''Main entry point: check to see which mode/tab is selected, and act accordingly.'''

        self.svg = self.document.getroot()
        self.CheckSVGforWCBData()
        useOldResumeData = True
        skipSerial = False

        self.options.mode = self.options.mode.strip("\"")
        self.options.setupType = self.options.setupType.strip("\"")
        self.options.manualType = self.options.manualType.strip("\"")
        self.options.resumeType = self.options.resumeType.strip("\"")

        if (self.options.mode == "Help"):
            skipSerial = True
        if (self.options.mode == "options"):
            skipSerial = True
        if (self.options.mode == "timing"):
            skipSerial = True
        if (self.options.mode == "manual"):
            if (self.options.manualType == "none"):
                skipSerial = True
            elif (self.options.manualType == "strip-data"):
                skipSerial = True
                for node in self.svg.xpath('//svg:WCB', namespaces=inkex.NSS):
                    self.svg.remove(node)
                for node in self.svg.xpath('//svg:eggbot', namespaces=inkex.NSS):
                    self.svg.remove(node)
                inkex.errormsg(gettext.gettext(
                    "I've removed all 4xiDraw data from this SVG file. Have a great day!"))
                return

        if skipSerial == False:
            self.serialPort = grbl_serial.openPort(self.options.logSerial)
            if self.serialPort is None:
                inkex.errormsg(gettext.gettext(
                    "Failed to connect to 4xiDraw. :("))
                sys.exit
            else:
                self.createMotion()

            if self.options.mode == "plot":
                self.LayersFoundToPlot = False
                useOldResumeData = False
                self.PrintInLayersMode = False
                self.plotCurrentLayer = True
                self.svgNodeCount = 0
                self.svgLastPath = 0
                # indicate (to resume routine) that we are plotting all layers.
                self.svgLayer = 12345
                if self.serialPort is not None:
                    self.plotDocument()
                if self.options.boundingBox:
                    print("Bounding box: %d %d %d %d" % (
                        self.bb['minX'], self.bb['minY'], self.bb['maxX'], self.bb['maxY']))
                    self.options.boundingBox = False
                    self.plotSegment(self.bb['minX'], self.bb['minY'])
                    self.plotSegment(self.bb['minX'], self.bb['maxY'])
                    self.plotSegment(self.bb['maxX'], self.bb['maxY'])
                    self.plotSegment(self.bb['maxX'], self.bb['minY'])
                    self.plotSegment(self.bb['minX'], self.bb['minY'])

            elif self.options.mode == "resume":
                useOldResumeData = False
                self.resumePlotSetup()
                if self.resumeMode:
                    fX = self.svgPausedPosX_Old + fourxidraw_conf.StartPosX
                    fY = self.svgPausedPosY_Old + fourxidraw_conf.StartPosY
                    self.resumeMode = False
                    self.plotSegment(fX, fY)

                    self.resumeMode = True
                    self.nodeCount = 0
                    self.plotDocument()

                elif (self.options.resumeType == "justGoHome"):
                    fX = fourxidraw_conf.StartPosX
                    fY = fourxidraw_conf.StartPosY

                    self.plotSegment(fX, fY)

                    # New values to write to file:
                    self.svgNodeCount = self.svgNodeCount_Old
                    self.svgLastPath = self.svgLastPath_Old
                    self.svgLastPathNC = self.svgLastPathNC_Old
                    self.svgPausedPosX = self.svgPausedPosX_Old
                    self.svgPausedPosY = self.svgPausedPosY_Old
                    self.svgLayer = self.svgLayer_Old
                else:
                    inkex.errormsg(gettext.gettext(
                        "There does not seem to be any in-progress plot to resume."))

            elif self.options.mode == "layers":
                useOldResumeData = False
                self.PrintInLayersMode = True
                self.plotCurrentLayer = False
                self.LayersFoundToPlot = False
                self.svgLastPath = 0
                self.svgNodeCount = 0
                self.svgLayer = self.options.layerNumber
                self.plotDocument()

            elif self.options.mode == "setup":
                self.setupCommand()

            elif self.options.mode == "manual":
                useOldResumeData = False
                self.svgNodeCount = self.svgNodeCount_Old
                self.svgLastPath = self.svgLastPath_Old
                self.svgLastPathNC = self.svgLastPathNC_Old
                self.svgPausedPosX = self.svgPausedPosX_Old
                self.svgPausedPosY = self.svgPausedPosY_Old
                self.svgLayer = self.svgLayer_Old
                self.manualCommand()

        # Do not make any changes to data saved from SVG file.
        if (useOldResumeData):
            self.svgNodeCount = self.svgNodeCount_Old
            self.svgLastPath = self.svgLastPath_Old
            self.svgLastPathNC = self.svgLastPathNC_Old
            self.svgPausedPosX = self.svgPausedPosX_Old
            self.svgPausedPosY = self.svgPausedPosY_Old
            self.svgLayer = self.svgLayer_Old
            self.svgLastKnownPosX = self.svgLastKnownPosX_Old
            self.svgLastKnownPosY = self.svgLastKnownPosY_Old

        self.svgDataRead = False
        self.UpdateSVGWCBData(self.svg)
        # self.motion.doTimedPause(10) # Pause a moment for underway commands to finish...
        if self.serialPort is not None:
            self.serialPort.close()

    def resumePlotSetup(self):
        self.LayerFound = False
        if (self.svgLayer_Old < 101) and (self.svgLayer_Old >= 0):
            self.options.layerNumber = self.svgLayer_Old
            self.PrintInLayersMode = True
            self.plotCurrentLayer = False
            self.LayerFound = True
        elif (self.svgLayer_Old == 12345):  # Plot all layers
            self.PrintInLayersMode = False
            self.plotCurrentLayer = True
            self.LayerFound = True
        if (self.LayerFound):
            if (self.svgNodeCount_Old > 0):
                self.nodeTarget = self.svgNodeCount_Old
                self.svgLayer = self.svgLayer_Old
                if self.options.resumeType == "ResumeNow":
                    self.resumeMode = True
                self.penUp()
                self.EnableMotors()
                self.fSpeed = self.PenDownSpeed

                self.fCurrX = self.svgLastKnownPosX_Old + fourxidraw_conf.StartPosX
                self.fCurrY = self.svgLastKnownPosY_Old + fourxidraw_conf.StartPosY

    def CheckSVGforWCBData(self):
        self.svgDataRead = False
        self.recursiveWCBDataScan(self.svg)
        if self.options.fileOutput:
            if (not self.svgDataRead):  # if there is no WCB data, add some:
                WCBlayer = fourxidraw_compat.compatEtreeSubElement(
                    self.svg, 'WCB')
                WCBlayer.set('layer', str(0))
                # node paused at, if saved in paused state
                WCBlayer.set('node', str(0))
                # Last path number that has been fully painted
                WCBlayer.set('lastpath', str(0))
                # Node count as of finishing last path.
                WCBlayer.set('lastpathnc', str(0))
                # Last known position of carriage
                WCBlayer.set('lastknownposx', str(0))
                WCBlayer.set('lastknownposy', str(0))
                # The position of the carriage when "pause" was pressed.
                WCBlayer.set('pausedposx', str(0))
                WCBlayer.set('pausedposy', str(0))

    def recursiveWCBDataScan(self, aNodeList):
        if (not self.svgDataRead):
            for node in aNodeList:
                if node.tag == 'svg':
                    self.recursiveWCBDataScan(node)
                elif node.tag == inkex.addNS('WCB', 'svg') or node.tag == 'WCB':
                    try:
                        self.svgLayer_Old = int(node.get('layer'))
                        self.svgNodeCount_Old = int(node.get('node'))
                        self.svgLastPath_Old = int(node.get('lastpath'))
                        self.svgLastPathNC_Old = int(node.get('lastpathnc'))
                        self.svgLastKnownPosX_Old = float(
                            node.get('lastknownposx'))
                        self.svgLastKnownPosY_Old = float(
                            node.get('lastknownposy'))
                        self.svgPausedPosX_Old = float(node.get('pausedposx'))
                        self.svgPausedPosY_Old = float(node.get('pausedposy'))
                        self.svgDataRead = True
                    except:
                        pass

    def UpdateSVGWCBData(self, aNodeList):
        if self.options.fileOutput:
            if (not self.svgDataRead):
                for node in aNodeList:
                    if node.tag == 'svg':
                        self.UpdateSVGWCBData(node)
                    elif node.tag == inkex.addNS('WCB', 'svg') or node.tag == 'WCB':
                        node.set('layer', str(self.svgLayer))
                        node.set('node', str(self.svgNodeCount))
                        node.set('lastpath', str(self.svgLastPath))
                        node.set('lastpathnc', str(self.svgLastPathNC))
                        node.set('lastknownposx', str((self.svgLastKnownPosX)))
                        node.set('lastknownposy', str((self.svgLastKnownPosY)))
                        node.set('pausedposx', str((self.svgPausedPosX)))
                        node.set('pausedposy', str((self.svgPausedPosY)))

                        self.svgDataRead = True

    def setupCommand(self):
        """Execute commands from the "setup" mode"""

        self.createMotion()

        if self.options.setupType == "align-mode":
            self.penUp()

        elif self.options.setupType == "toggle-pen":
            self.penUp()
            time.sleep(1)
            self.penDown()

    def manualCommand(self):
        """Execute commands in the "manual" mode/tab"""

        if self.options.manualType == "none":
            return

        self.createMotion()

        if self.serialPort is None:
            return

        if self.options.manualType == "raise-pen":
            self.penUp()

        elif self.options.manualType == "lower-pen":
            self.penDown()

        elif self.options.manualType == "version-check":
            strVersion = self.serialPort.query('$I\r')
            inkex.errormsg(
                'I asked GRBL for its version info, and it replied:\n ' + strVersion)

        elif self.options.manualType == "grbl-command":
            strResponse = self.serialPort.query(
                self.options.grblCommand + '\r')
            inkex.errormsg('GRBL command "' + self.options.grblCommand +
                           '" got this reply:\n ' + strResponse)

        else:  # self.options.manualType is walk motor:
            if self.options.manualType == "walk-y-motor":
                nDeltaX = 0
                nDeltaY = self.options.WalkDistance
            elif self.options.manualType == "walk-x-motor":
                nDeltaY = 0
                nDeltaX = self.options.WalkDistance
            else:
                return

            self.fSpeed = self.PenDownSpeed

            self.EnableMotors()
            self.fCurrX = self.svgLastKnownPosX_Old + fourxidraw_conf.StartPosX
            self.fCurrY = self.svgLastKnownPosY_Old + fourxidraw_conf.StartPosY
            self.ignoreLimits = True
            # Note: Walking motors is STRICTLY RELATIVE TO INITIAL POSITION.
            fX = self.fCurrX + nDeltaX
            fY = self.fCurrY + nDeltaY
            self.plotSegment(fX, fY)

    def plotDocument(self):
        '''Plot the actual SVG document, if so selected in the interface:'''
        # parse the svg data as a series of line segments and send each segment to be plotted

        if self.serialPort is None:
            return

        if (not self.getDocProps()):
            # Cannot handle the document's dimensions!!!
            inkex.errormsg(gettext.gettext(
                'This document does not have valid dimensions.\n' +
                'The document dimensions must be in either ' +
                'millimeters (mm) or inches (in).\n\n' +
                'Consider starting with the "Letter landscape" or ' +
                'the "A4 landscape" template.\n\n' +
                'Document dimensions may also be set in Inkscape,\n' +
                'using File > Document Properties.'))
            return

        # Viewbox handling
        # Also ignores the preserveAspectRatio attribute
        viewbox = self.svg.get('viewBox')
        if viewbox:
            vinfo = viewbox.strip().replace(',', ' ').split(' ')
            Offset0 = -float(vinfo[0])
            Offset1 = -float(vinfo[1])

            if (vinfo[2] != 0) and (vinfo[3] != 0):
                sx = self.svgWidth / float(vinfo[2])
                sy = self.svgHeight / float(vinfo[3])
        else:
            # Handle case of no viewbox provided.
            # This can happen with imported documents in Inkscape.
            sx = 1.0 / float(plot_utils.pxPerInch)
            sy = sx
            Offset0 = 0.0
            Offset1 = 0.0 
        self.docTransform = fourxidraw_compat.compatParseTransform(
            'scale(%.15f,%.15f) translate(%.15f,%.15f)' % (sx, sy, Offset0, Offset1))

        self.penUp()
        self.EnableMotors()
        self.sCurrentLayerName = '(Not Set)'

        try:
            # wrap everything in a try so we can for sure close the serial port
            self.recursivelyTraverseSvg(self.svg)
            self.penUp()   # Always end with pen-up

            # return to home after end of normal plot
            if ((not self.bStopped) and (self.ptFirst)):
                self.xBoundsMin = fourxidraw_conf.StartPosX
                self.yBoundsMin = fourxidraw_conf.StartPosY
                fX = self.ptFirst[0]
                fY = self.ptFirst[1]
                self.nodeCount = self.nodeTarget
                self.plotSegment(fX, fY)

            if (not self.bStopped):
                if (self.options.mode == "plot") or (self.options.mode == "layers") or (self.options.mode == "resume"):
                    self.svgLayer = 0
                    self.svgNodeCount = 0
                    self.svgLastPath = 0
                    self.svgLastPathNC = 0
                    self.svgLastKnownPosX = 0
                    self.svgLastKnownPosY = 0
                    self.svgPausedPosX = 0
                    self.svgPausedPosY = 0
                    # Clear saved position data from the SVG file,
                    # IF we have completed a normal plot from the plot, layer, or resume mode.
            if (self.warnOutOfBounds):
                inkex.errormsg(gettext.gettext(
                    'Warning: 4xiDraw movement was limited by its physical range of motion. If everything looks right, your document may have an error with its units or scaling. Contact technical support for help!'))

            if (self.options.reportTime):
                elapsed_time = time.time() - self.start_time
                m, s = divmod(elapsed_time, 60)
                h, m = divmod(m, 60)
                inkex.errormsg("Elapsed time: %d:%02d:%02d" %
                               (h, m, s) + " (Hours, minutes, seconds)")
                downDist = self.penDownDistance / (self.stepsPerInch * sqrt(2))
                totDist = downDist + self.penUpDistance / \
                    (self.stepsPerInch * sqrt(2))
                inkex.errormsg(
                    "Length of path drawn: %1.3f inches." % downDist)
                inkex.errormsg("Total distance moved: %1.3f inches." % totDist)

        finally:
            # We may have had an exception and lost the serial port...
            pass

    def compose_parent_transforms(self, node, mat):  # Inkscape 1.0+ only
        # This is adapted from Inkscape's simpletransform.py's composeParents()
        # function.  That one can't handle nodes that are detached from a DOM.

        trans = node.get("transform")
        if trans:
            mat = inkex.transforms.Transform(trans) * mat

        if node.getparent() is not None:
            if node.getparent().tag == inkex.addNS("g", "svg"):
                mat = self.compose_parent_transforms(node.getparent(), mat)

        return mat

    def recursivelyTraverseSvg(self, aNodeList,
                               matCurrent=IDENTITY_TRANSFORM,
                               parent_visibility='visible'):
        """
        Recursively traverse the svg file to plot out all of the
        paths.  The function keeps track of the composite transformation
        that should be applied to each path.

        This function handles path, group, line, rect, polyline, polygon,
        circle, ellipse and use (clone) elements.  Notable elements not
        handled include text.  Unhandled elements should be converted to
        paths in Inkscape.
        """
        # if not self.plotCurrentLayer:
        #     return        # saves us a lot of time ...

        for node in aNodeList:
            v = None
            style = node.get("style")
            if style is not None:
                kvs = {k.strip(): v.strip()
                       for k, v in [x.split(":", 1) for x in style.split(";")]}
                if "display" in kvs and kvs["display"] == "none":
                    v = "hidden"
            if v is None:
                v = node.get("visibility", parent_visibility)
            if v == "inherit":
                v = parent_visibility
            if v == "hidden" or v == "collapse":
                continue

            # first apply the current matrix transform to this node's transform
            matNew = self.compose_parent_transforms(node, IDENTITY_TRANSFORM)
            matNew = fourxidraw_compat.compatComposeTransform(self.docTransform, matNew)
            matNew = fourxidraw_compat.compatComposeTransform(
                matCurrent, matNew)

            if node.tag == inkex.addNS('g', 'svg') or node.tag == 'g':

                if (node.get(inkex.addNS('groupmode', 'inkscape')) == 'layer'):
                    self.sCurrentLayerName = node.get(
                        inkex.addNS('label', 'inkscape'))
                    self.DoWePlotLayer(self.sCurrentLayerName)
                    if not self.options.boundingBox:
                        self.penUp()
                self.recursivelyTraverseSvg(node, parent_visibility=v)

            elif node.tag == inkex.addNS('use', 'svg') or node.tag == 'use':

                # A <use> element refers to another SVG element via an xlink:href="#blah"
                # attribute.  We will handle the element by doing an XPath search through
                # the document, looking for the element with the matching id="blah"
                # attribute.  We then recursively process that element after applying
                # any necessary (x,y) translation.
                #
                # Notes:
                #  1. We ignore the height and width attributes as they do not apply to
                #     path-like elements, and
                #  2. Even if the use element has visibility="hidden", SVG still calls
                #     for processing the referenced element.  The referenced element is
                #     hidden only if its visibility is "inherit" or "hidden".
                #  3. We may be able to unlink clones using the code in pathmodifier.py

                refid = node.get(inkex.addNS('href', 'xlink'))
                if refid:
                    # [1:] to ignore leading '#' in reference
                    path = '//*[@id="%s"]' % refid[1:]
                    refnode = node.xpath(path)
                    if refnode:
                        x = float(node.get('x', '0'))
                        y = float(node.get('y', '0'))
                        # Note: the transform has already been applied
                        if (x != 0) or (y != 0):
                            matNew2 = fourxidraw_compat.compatComposeTransform(
                                matNew, fourxidraw_compat.compatParseTransform('translate(%.15f,%.15f)' % (x, y)))
                        else:
                            matNew2 = matNew
                        v = node.get('visibility', v)
                        self.recursivelyTraverseSvg(
                            refnode, matNew2, parent_visibility=v)
                    else:
                        pass
                else:
                    pass
            # Skip subsequent tag checks unless we are plotting this layer.
            elif self.plotCurrentLayer:
                if node.tag == inkex.addNS('path', 'svg'):

                    # if we're in resume mode AND self.pathcount < self.svgLastPath,
                    #    then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svgLastPath,
                    #    then start here, and set self.nodeCount equal to self.svgLastPathNC

                    doWePlotThisPath = False
                    if (self.resumeMode):
                        if (self.pathcount < self.svgLastPath_Old):
                            # This path was *completely plotted* already; skip.
                            self.pathcount += 1
                        elif (self.pathcount == self.svgLastPath_Old):
                            # this path is the first *not completely* plotted path:
                            self.nodeCount = self.svgLastPathNC_Old  # Nodecount after last completed path
                            doWePlotThisPath = True
                    else:
                        doWePlotThisPath = True
                    if (doWePlotThisPath):
                        self.pathcount += 1
                        self.plotPath(node, matNew)

                elif node.tag == inkex.addNS('rect', 'svg') or node.tag == 'rect':

                    # Manually transform
                    #    <rect x="X" y="Y" width="W" height="H"/>
                    # into
                    #    <path d="MX,Y lW,0 l0,H l-W,0 z"/>
                    # I.e., explicitly draw three sides of the rectangle and the
                    # fourth side implicitly

                    # if we're in resume mode AND self.pathcount < self.svgLastPath,
                    #    then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svgLastPath,
                    #    then start here, and set
                    # self.nodeCount equal to self.svgLastPathNC

                    doWePlotThisPath = False
                    if (self.resumeMode):
                        if (self.pathcount < self.svgLastPath_Old):
                            # This path was *completely plotted* already; skip.
                            self.pathcount += 1
                        elif (self.pathcount == self.svgLastPath_Old):
                            # this path is the first *not completely* plotted path:
                            self.nodeCount = self.svgLastPathNC_Old  # Nodecount after last completed path
                            doWePlotThisPath = True
                    else:
                        doWePlotThisPath = True
                    if (doWePlotThisPath):
                        self.pathcount += 1
                        # Create a path with the outline of the rectangle
                        newpath = fourxidraw_compat.compatEtreeElement(
                            inkex.addNS('path', 'svg'))
                        x = float(node.get('x'))
                        y = float(node.get('y'))
                        w = float(node.get('width'))
                        h = float(node.get('height'))
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        a = []
                        fourxidraw_compat.compatAppendCommand(a, 'M ', [x, y])
                        fourxidraw_compat.compatAppendCommand(a, ' l ', [w, 0])
                        fourxidraw_compat.compatAppendCommand(a, ' l ', [0, h])
                        fourxidraw_compat.compatAppendCommand(
                            a, ' l ', [-w, 0])
                        fourxidraw_compat.compatAppendCommand(a, ' Z', [])
                        newpath.set('d', fourxidraw_compat.compatFormatPath(a))
                        self.plotPath(newpath, matNew)

                elif node.tag == inkex.addNS('line', 'svg') or node.tag == 'line':

                    # Convert
                    #
                    #   <line x1="X1" y1="Y1" x2="X2" y2="Y2/>
                    #
                    # to
                    #
                    #   <path d="MX1,Y1 LX2,Y2"/>

                    # if we're in resume mode AND self.pathcount < self.svgLastPath,
                    #    then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svgLastPath,
                    #    then start here, and set
                    # self.nodeCount equal to self.svgLastPathNC

                    doWePlotThisPath = False
                    if (self.resumeMode):
                        if (self.pathcount < self.svgLastPath_Old):
                            # This path was *completely plotted* already; skip.
                            self.pathcount += 1
                        elif (self.pathcount == self.svgLastPath_Old):
                            # this path is the first *not completely* plotted path:
                            self.nodeCount = self.svgLastPathNC_Old  # Nodecount after last completed path
                            doWePlotThisPath = True
                    else:
                        doWePlotThisPath = True
                    if (doWePlotThisPath):
                        self.pathcount += 1
                        # Create a path to contain the line
                        newpath = fourxidraw_compat.compatEtreeElement(
                            inkex.addNS('path', 'svg'))
                        x1 = float(node.get('x1'))
                        y1 = float(node.get('y1'))
                        x2 = float(node.get('x2'))
                        y2 = float(node.get('y2'))
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        a = []
                        fourxidraw_compat.compatAppendCommand(
                            a, 'M ', [x1, y1])
                        fourxidraw_compat.compatAppendCommand(
                            a, ' L ', [x2, y2])
                        newpath.set('d', fourxidraw_compat.compatFormatPath(a))
                        self.plotPath(newpath, matNew)

                elif node.tag == inkex.addNS('polyline', 'svg') or node.tag == 'polyline':

                    # Convert
                    #  <polyline points="x1,y1 x2,y2 x3,y3 [...]"/>
                    # to
                    #   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...]"/>
                    # Note: we ignore polylines with no points

                    pl = node.get('points', '').strip()
                    if pl == '':
                        pass

                    # if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
                    # self.nodeCount equal to self.svgLastPathNC

                    doWePlotThisPath = False
                    if (self.resumeMode):
                        if (self.pathcount < self.svgLastPath_Old):
                            # This path was *completely plotted* already; skip.
                            self.pathcount += 1
                        elif (self.pathcount == self.svgLastPath_Old):
                            # this path is the first *not completely* plotted path:
                            self.nodeCount = self.svgLastPathNC_Old  # Nodecount after last completed path
                            doWePlotThisPath = True
                    else:
                        doWePlotThisPath = True
                    if (doWePlotThisPath):
                        self.pathcount += 1

                        pa = pl.split()
                        if not len(pa):
                            pass
                        d = "M {:.11f}".format(pa[0])
                        for i in range(1, len(pa)):
                            d += " L {:.11f} ".format(pa[i])
                        newpath = fourxidraw_compat.compatEtreeElement(
                            inkex.addNS('path', 'svg'))
                        newpath.set('d', d)
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        self.plotPath(newpath, matNew)

                elif node.tag == inkex.addNS('polygon', 'svg') or node.tag == 'polygon':

                    # Convert
                    #  <polygon points="x1,y1 x2,y2 x3,y3 [...]"/>
                    # to
                    #   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...] Z"/>
                    # Note: we ignore polygons with no points

                    pl = node.get('points', '').strip()
                    if pl == '':
                        pass

                    # if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
                    # self.nodeCount equal to self.svgLastPathNC

                    doWePlotThisPath = False
                    if (self.resumeMode):
                        if (self.pathcount < self.svgLastPath_Old):
                            # This path was *completely plotted* already; skip.
                            self.pathcount += 1
                        elif (self.pathcount == self.svgLastPath_Old):
                            # this path is the first *not completely* plotted path:
                            self.nodeCount = self.svgLastPathNC_Old  # Nodecount after last completed path
                            doWePlotThisPath = True
                    else:
                        doWePlotThisPath = True
                    if (doWePlotThisPath):
                        self.pathcount += 1

                        pa = pl.split()
                        if not len(pa):
                            pass
                        d = "M {:.11f}".format(pa[0])
                        for i in xrange(1, len(pa)):
                            d += " L {:.11f} ".format(pa[i])
                        d += " Z"
                        newpath = fourxidraw_compat.compatEtreeElement(
                            inkex.addNS('path', 'svg'))
                        newpath.set('d', d)
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        self.plotPath(newpath, matNew)

                elif node.tag == inkex.addNS('ellipse', 'svg') or \
                        node.tag == 'ellipse' or \
                        node.tag == inkex.addNS('circle', 'svg') or \
                        node.tag == 'circle':

                    # Convert circles and ellipses to a path with two 180 degree arcs.
                    # In general (an ellipse), we convert
                    #   <ellipse rx="RX" ry="RY" cx="X" cy="Y"/>
                    # to
                    #   <path d="MX1,CY A RX,RY 0 1 0 X2,CY A RX,RY 0 1 0 X1,CY"/>
                    # where
                    #   X1 = CX - RX
                    #   X2 = CX + RX
                    # Note: ellipses or circles with a radius attribute of value 0 are ignored

                    if node.tag == inkex.addNS('ellipse', 'svg') or node.tag == 'ellipse':
                        rx = float(node.get('rx', '0'))
                        ry = float(node.get('ry', '0'))
                    else:
                        rx = float(node.get('r', '0'))
                        ry = rx
                    if rx == 0 or ry == 0:
                        pass

                    # if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
                    # if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
                    # self.nodeCount equal to self.svgLastPathNC

                    doWePlotThisPath = False
                    if (self.resumeMode):
                        if (self.pathcount < self.svgLastPath_Old):
                            # This path was *completely plotted* already; skip.
                            self.pathcount += 1
                        elif (self.pathcount == self.svgLastPath_Old):
                            # this path is the first *not completely* plotted path:
                            self.nodeCount = self.svgLastPathNC_Old  # Nodecount after last completed path
                            doWePlotThisPath = True
                    else:
                        doWePlotThisPath = True
                    if (doWePlotThisPath):
                        self.pathcount += 1

                        cx = float(node.get('cx', '0'))
                        cy = float(node.get('cy', '0'))
                        x1 = cx - rx
                        x2 = cx + rx
                        d = 'M %.15f,%.15f ' % (x1, cy) + \
                            'A %.15f,%.15f ' % (rx, ry) + \
                            '0 1 0 %.15f,%.15f ' % (x2, cy) + \
                            'A %.15f,%.15f ' % (rx, ry) + \
                            '0 1 0 %.15f,%.15f' % (x1, cy)
                        newpath = fourxidraw_compat.compatEtreeElement(
                            inkex.addNS('path', 'svg'))
                        newpath.set('d', d)
                        s = node.get('style')
                        if s:
                            newpath.set('style', s)
                        t = node.get('transform')
                        if t:
                            newpath.set('transform', t)
                        self.plotPath(newpath, matNew)

                elif node.tag == inkex.addNS('metadata', 'svg') or node.tag == 'metadata':
                    pass
                elif node.tag == inkex.addNS('defs', 'svg') or node.tag == 'defs':
                    pass
                elif node.tag == inkex.addNS('namedview', 'sodipodi') or node.tag == 'namedview':
                    pass
                elif node.tag == inkex.addNS('WCB', 'svg') or node.tag == 'WCB':
                    pass
                elif node.tag == inkex.addNS('eggbot', 'svg') or node.tag == 'eggbot':
                    pass
                elif node.tag == inkex.addNS('title', 'svg') or node.tag == 'title':
                    pass
                elif node.tag == inkex.addNS('desc', 'svg') or node.tag == 'desc':
                    pass
                elif (node.tag == inkex.addNS('text', 'svg') or node.tag == 'text' or
                      node.tag == inkex.addNS('flowRoot', 'svg') or node.tag == 'flowRoot'):
                    if (not 'text' in self.warnings) and (self.plotCurrentLayer):
                        inkex.errormsg(gettext.gettext('Note: This file contains some plain text, found in a \nlayer named: "' +
                                                       self.sCurrentLayerName + '" .\n' +
                                                       'Please convert your text into paths before drawing,  \n' +
                                                       'using Path > Object to Path. \n' +
                                                       'You can also create new text by using Hershey Text,\n' +
                                                       'located in the menu at Extensions > Render.'))
                        self.warnings['text'] = 1
                    pass
                elif node.tag == inkex.addNS('image', 'svg') or node.tag == 'image':
                    if (not 'image' in self.warnings) and (self.plotCurrentLayer):
                        inkex.errormsg(gettext.gettext('Warning: in layer "' +
                                                       self.sCurrentLayerName + '" unable to draw bitmap images; ' +
                                                       'Please convert images to line art before drawing. ' +
                                                       ' Consider using the Path > Trace bitmap tool. '))
                        self.warnings['image'] = 1
                    pass
                elif node.tag == inkex.addNS('pattern', 'svg') or node.tag == 'pattern':
                    pass
                elif node.tag == inkex.addNS('radialGradient', 'svg') or node.tag == 'radialGradient':
                    # Similar to pattern
                    pass
                elif node.tag == inkex.addNS('linearGradient', 'svg') or node.tag == 'linearGradient':
                    # Similar in pattern
                    pass
                elif node.tag == inkex.addNS('style', 'svg') or node.tag == 'style':
                    # This is a reference to an external style sheet and not the value
                    # of a style attribute to be inherited by child elements
                    pass
                elif node.tag == inkex.addNS('cursor', 'svg') or node.tag == 'cursor':
                    pass
                elif node.tag == inkex.addNS('color-profile', 'svg') or node.tag == 'color-profile':
                    # Gamma curves, color temp, etc. are not relevant to single color output
                    pass
                elif not fourxidraw_compat.compatIsBasestring(node.tag):
                    # This is likely an XML processing instruction such as an XML
                    # comment.  lxml uses a function reference for such node tags
                    # and as such the node tag is likely not a printable string.
                    # Further, converting it to a printable string likely won't
                    # be very useful.
                    pass
                else:
                    if (not str(node.tag) in self.warnings) and (self.plotCurrentLayer):
                        t = str(node.tag).split('}')
                        inkex.errormsg(gettext.gettext('Warning: in layer "' +
                                                       self.sCurrentLayerName + '" unable to draw <' + str(t[-1]) +
                                                       '> object, please convert it to a path first.'))
                        self.warnings[str(node.tag)] = 1
                    pass

    def DoWePlotLayer(self, strLayerName):
        """
        Parse layer name for layer number and other properties.

        First: scan layer name for first non-numeric character,
        and scan the part before that (if any) into a number
        Then, (if not printing in all-layers mode)
        see if the number matches the layer number that we are printing.

        Secondary function: Parse characters following the layer number (if any) to see if
        there is a "+H" or "+S" escape code, that indicates that overrides the pen-down
        height or speed for the given layer.

        """

        # Look at layer name.  Sample first character, then first two, and
        # so on, until the string ends or the string no longer consists of digit characters only.
        TempNumString = 'x'
        stringPos = 1
        layerNameInt = -1
        layerMatch = False
        # Yes this is ugly. More elegant suggestions welcome. :)
        if sys.version_info < (3,):
            CurrentLayerName = strLayerName.encode(
                'ascii', 'ignore')  # Drop non-ascii characters
        else:
            CurrentLayerName = str(strLayerName)
        CurrentLayerName.lstrip  # remove leading whitespace
        self.plotCurrentLayer = True  # Temporarily assume that we are plotting the layer

        MaxLength = len(CurrentLayerName)
        if MaxLength > 0:
            if CurrentLayerName[0] == '%':
                self.plotCurrentLayer = False  # First character is "%" -- skip this layer
            while stringPos <= MaxLength:
                LayerNameFragment = CurrentLayerName[:stringPos]
                if (LayerNameFragment.isdigit()):
                    # Store longest numeric string so far
                    TempNumString = CurrentLayerName[:stringPos]
                    stringPos = stringPos + 1
                else:
                    break

        # Also true if resuming a print that was of a single layer.
        if (self.PrintInLayersMode):
            if (str.isdigit(TempNumString)):
                layerNameInt = int(float(TempNumString))
                if (self.svgLayer == layerNameInt):
                    layerMatch = True  # Match! The current layer IS named.

            if (layerMatch == False):
                self.plotCurrentLayer = False

        if (self.plotCurrentLayer == True):
            self.LayersFoundToPlot = True

            # End of part 1, current layer to see if we print it.
            # Now, check to see if there is additional information coded here.

            oldPenDown = self.LayerPenDownPosition
            oldSpeed = self.LayerPenDownSpeed

            # set default values before checking for any overrides:
            self.LayerOverridePenDownHeight = False
            self.LayerOverrideSpeed = False
            self.LayerPenDownPosition = -1
            self.LayerPenDownSpeed = -1

            if (stringPos > 0):
                stringPos = stringPos - 1

            if MaxLength > stringPos + 2:
                while stringPos <= MaxLength:
                    EscapeSequence = CurrentLayerName[stringPos:stringPos+2].lower()
                    if (EscapeSequence == "+h") or (EscapeSequence == "+s"):
                        paramStart = stringPos + 2
                        stringPos = stringPos + 3
                        TempNumString = 'x'
                        if MaxLength > 0:
                            while stringPos <= MaxLength:
                                if str.isdigit(CurrentLayerName[paramStart:stringPos]):
                                    # Longest numeric string so far
                                    TempNumString = CurrentLayerName[paramStart:stringPos]
                                    stringPos = stringPos + 1
                                else:
                                    break
                        if (str.isdigit(TempNumString)):
                            parameterInt = int(float(TempNumString))

                            if (EscapeSequence == "+h"):
                                if ((parameterInt >= 0) and (parameterInt <= 100)):
                                    self.LayerOverridePenDownHeight = True
                                    self.LayerPenDownPosition = parameterInt

                            if (EscapeSequence == "+s"):
                                if ((parameterInt > 0) and (parameterInt <= 100)):
                                    self.LayerOverrideSpeed = True
                                    self.LayerPenDownSpeed = parameterInt

                        stringPos = paramStart + len(TempNumString)
                    else:
                        break  # exit loop.

            if (self.LayerPenDownSpeed != oldSpeed):
                # Set speed value variables for this layer.
                self.EnableMotors()

    def plotPath(self, path, matTransform):
        '''
        Plot the path while applying the transformation defined
        by the matrix [matTransform].
        '''
        self.logDebug('plotPath: Enter')
        # turn this path into a cubicsuperpath (list of beziers)...

        d = path.get('d')

        if fourxidraw_compat.compatIsEmptyPath(d):
            self.logDebug('plotPath: Zero length')
            return

        if self.plotCurrentLayer:
            self.logDebug('plotPath: plotCurrentLayer')
            p = fourxidraw_compat.compatParseCubicSuperPath(d)

            # ...and apply the transformation to each point
            p = fourxidraw_compat.compatApplyTransformToPath(matTransform, p)

            # p is now a list of lists of cubic beziers [control pt1, control pt2, endpoint]
            # where the start-point is the last point in the previous segment.
            for sp in p:

                plot_utils.subdivideCubicPath(
                    sp, 0.02 / self.options.smoothness)
                nIndex = 0

                singlePath = []
                if self.plotCurrentLayer:
                    for csp in sp:
                        if self.bStopped:
                            return
                        if (self.printPortrait):
                            fX = float(csp[1][1])  # Flipped X/Y
                            fY = (self.svgWidth) - float(csp[1][0])
                        else:
                            fX = float(csp[1][0])  # Set move destination
                            fY = float(csp[1][1])

                        self.logDebug('plotPath: X %.15f Y %.15f' % (fX, fY))

                        if nIndex == 0:
                            if (plot_utils.distance(fX - self.fCurrX, fY - self.fCurrY) > fourxidraw_conf.MinGap):
                                if not self.options.boundingBox:
                                    self.penUp()
                                self.plotSegment(fX, fY)
                        elif nIndex == 1:
                            if not self.options.boundingBox:
                                self.penDown()
                        nIndex += 1

                        singlePath.append([fX, fY])

                    self.PlanTrajectory(singlePath)

            if (not self.bStopped):  # an "index" for resuming plots quickly-- record last complete path
                self.svgLastPath = self.pathcount  # The number of the last path completed
                # the node count after the last path was completed.
                self.svgLastPathNC = self.nodeCount

    def PlanTrajectory(self, inputPath):
        '''
        Plan the trajectory for a full path, accounting for linear acceleration.
        Inputs: Ordered (x,y) pairs to cover.
        Output: A list of segments to plot, of the form (Xfinal, Yfinal, Vinitial, Vfinal)

        Note: Native motor axes are Motor 1, Motor 2.
          Motor1Steps = xSteps + ySteps
          Motor2Steps = xSteps - ysteps

        Important note: This routine uses *inch* units (inches, inches/second, etc.). 

        '''

        spewTrajectoryDebugData = False

        if spewTrajectoryDebugData:
            self.logDebug('\nPlanTrajectory()\n')

        if self.bStopped:
            return
        if (self.fCurrX is None):
            return

        # check page size limits:
        if (self.ignoreLimits == False):
            for xy in inputPath:
                xy[0], xBounded = plot_utils.checkLimits(
                    xy[0], self.xBoundsMin, self.xBoundsMax)
                xy[1], yBounded = plot_utils.checkLimits(
                    xy[1], self.yBoundsMin, self.yBoundsMax)
                if (xBounded or yBounded):
                    self.warnOutOfBounds = True

        # Handle simple segments (lines) that do not require any complex planning:
        if (len(inputPath) < 3):
            if spewTrajectoryDebugData:
                # This is the "SHORTPATH ESCAPE"
                self.logDebug('Drawing straight line, not a curve.')
            self.plotSegment(xy[0], xy[1])
            return

        # For other trajectories, we need to go deeper.
        TrajLength = len(inputPath)

        if spewTrajectoryDebugData:
            for xy in inputPath:
                self.logDebug('x: %1.3f,  y: %1.3f' % (xy[0], xy[1]))
            self.logDebug('\nTrajLength: '+str(TrajLength) + '\n')

        # Absolute maximum and minimum speeds allowed:

        # Values such as PenUpSpeed are in units of _steps per second_.
        # However, to simplify our kinematic calculations,
        # we now presently switch into inches per second.

        # Maximum travel speed
        if (self.virtualPenIsUp):
            # Units of speedLimit: inches/second
            speedLimit = self.PenUpSpeed/self.stepsPerInch
        else:
            speedLimit = self.PenDownSpeed/self.stepsPerInch

        # float, Segment length (distance) when arriving at the junction
        TrajDists = array('f')
        TrajVectors = []    # Array that will hold normalized unit vectors along each segment

        TrajDists.append(0.0)  # First value, at time t = 0

        for i in xrange(1, TrajLength):
            # Distance per segment:
            tmpDist = plot_utils.distance(inputPath[i][0] - inputPath[i - 1][0],
                                          inputPath[i][1] - inputPath[i - 1][1])
            TrajDists.append(tmpDist)
            # Normalized unit vectors:

            if (tmpDist == 0):
                tmpDist = 1
            tmpX = (inputPath[i][0] - inputPath[i - 1][0]) / tmpDist
            tmpY = (inputPath[i][1] - inputPath[i - 1][1]) / tmpDist
            TrajVectors.append([tmpX, tmpY])

        if spewTrajectoryDebugData:
            for dist in TrajDists:
                self.logDebug('TrajDists: %1.3f' % dist)
            self.logDebug('\n')

        for i in xrange(1, TrajLength):
            self.plotSegment(inputPath[i][0], inputPath[i][1])

    def plotSegment(self, xDest, yDest):
        ''' 
        Control the serial port to command the machine to draw
        a straight line segment.

        Inputs:   Destination (x,y)

        Method: Divide the segment up into smaller segments.
        Send commands out the com port as a set of short line segments (dx, dy)

        Inputs are expected be in units of inches (for distance) 
          or inches per second (for velocity).

        '''

#   spewSegmentDebugData = False
        spewSegmentDebugData = True

        if spewSegmentDebugData:
            self.logDebug('\nPlotSegment(x = %1.2f, y = %1.2f) ' %
                          (xDest, yDest))
            if self.resumeMode:
                self.logDebug('resumeMode is active')

        if self.bStopped:
            self.logDebug('Stopped')
            return
        if (self.fCurrX is None):
            self.logDebug('No current position')
            return

        # check page size limits:
        if (self.ignoreLimits == False):
            xDest, xBounded = plot_utils.checkLimits(
                xDest, self.xBoundsMin, self.xBoundsMax)
            yDest, yBounded = plot_utils.checkLimits(
                yDest, self.yBoundsMin, self.yBoundsMax)
            if (xBounded or yBounded):
                self.warnOutOfBounds = True

        self.logDebug('doAbsoluteMove(%.15f, %.15f)' % (xDest, yDest))
        if self.options.boundingBox:
            self.bb['minX'] = min(self.bb['minX'], xDest)
            self.bb['minY'] = min(self.bb['minY'], yDest)
            self.bb['maxX'] = max(self.bb['maxX'], xDest)
            self.bb['maxY'] = max(self.bb['maxY'], yDest)
        else:
            self.motion.doAbsoluteMove(xDest, yDest)

    def EnableMotors(self):
        ''' 
        Enable motors, set native motor resolution, and set speed scales.

        The "pen down" speed scale is adjusted with the following factors 
        that make the controls more intuitive: 
        * Reduce speed by factor of 2 when using 8X microstepping
        * Reduce speed by factor of 2 when disabling acceleration

        These factors prevent unexpected dramatic changes in speed when turning
        those two options on and off. 

        '''

        if (self.LayerOverrideSpeed):
            LocalPenDownSpeed = self.LayerPenDownSpeed
        else:
            LocalPenDownSpeed = self.options.penDownSpeed

        self.stepsPerInch = float(fourxidraw_conf.DPI_16X)
        self.PenDownSpeed = LocalPenDownSpeed * fourxidraw_conf.SpeedScale / 110.0
        self.PenUpSpeed = self.options.penUpSpeed * fourxidraw_conf.SpeedScale / 110.0
        if (self.options.constSpeed):
            self.PenDownSpeed = self.PenDownSpeed / 3

        TestArray = array('i')  # signed integer
        if (TestArray.itemsize < 4):
            inkex.errormsg(
                'Internal array data length error. Please contact technical support.')
            # This is being run on a system that has a shorter length for a signed integer
            # than we are expecting. If anyone ever comes across such a system, we need to know!

    def penUp(self):
        # Virtual pen keeps track of state for resuming plotting.
        self.virtualPenIsUp = True
        # skip if pen is already up, or if we're resuming.
        if (not self.resumeMode) and (not self.bPenIsUp):
            if (self.LayerOverridePenDownHeight):
                penDownPos = self.LayerPenDownPosition
            else:
                penDownPos = self.options.penDownPosition
            vDistance = float(self.options.penUpPosition - penDownPos)
            vTime = int((1000.0 * vDistance) / self.options.penLiftRate)
            if (vTime < 0):  # Handle case that penDownPosition is above penUpPosition
                vTime = -vTime
            vTime += self.options.penLiftDelay
            if (vTime < 0):  # Do not allow negative delay times
                vTime = 0
            self.motion.sendPenUp(
                vTime, self.options.penUpSpeed if self.options.applySpeed else None)
            if (vTime > 50):
                if self.options.mode != "manual":
                    # pause before issuing next command
                    time.sleep(float(vTime - 10)/1000.0)
            self.bPenIsUp = True

    def penDown(self):
        # Virtual pen keeps track of state for resuming plotting.
        self.virtualPenIsUp = False
        if (self.bPenIsUp != False):  # skip if pen is already down
            if ((not self.resumeMode) and (not self.bStopped)):  # skip if resuming or stopped
                if (self.LayerOverridePenDownHeight):
                    penDownPos = self.LayerPenDownPosition
                else:
                    penDownPos = self.options.penDownPosition
                vDistance = float(self.options.penUpPosition - penDownPos)
                vTime = int((1000.0 * vDistance) / self.options.penLowerRate)
                if (vTime < 0):  # Handle case that penDownPosition is above penUpPosition
                    vTime = -vTime
                vTime += self.options.penLowerDelay
                if (vTime < 0):  # Do not allow negative delay times
                    vTime = 0
                self.motion.sendPenDown(
                    vTime, self.options.penDownSpeed if self.options.applySpeed else None)
                if (vTime > 50):
                    if self.options.mode != "manual":
                        # pause before issuing next command
                        time.sleep(float(vTime - 10)/1000.0)
                self.bPenIsUp = False

    def getDocProps(self):
        '''
        Get the document's height and width attributes from the <svg> tag.
        Use a default value in case the property is not present or is
        expressed in units of percentages.
        '''
        self.svgHeight = plot_utils.getLengthInches(self, 'height')
        self.svgWidth = plot_utils.getLengthInches(self, 'width')
        if (self.options.autoRotate) and (self.svgHeight > self.svgWidth):
            self.printPortrait = True
        if (self.svgHeight == None) or (self.svgWidth == None):
            return False
        else:
            return True


e = FourxiDrawClass()
if fourxidraw_compat.isPython3():
    e.run()
else:
    e.affect()
