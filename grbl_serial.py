# grbl_serial.py
# Serial connection utilities for RAMPS

import serial
import time
import sys
import string
import inkex
import gettext
import datetime

import fourxidraw_compat  # To bridge Python 2/3, Inkscape 0.*/1.*


def findPort():
    # Find a GRBL board connected to a USB port.
    try:
        from serial.tools.list_ports import comports
    except ImportError:
        comports = None
        return None
    if comports:
        comPortsList = list(comports())
        for port in comPortsList:
            desc = port[1].lower()
            isUsbSerial = "usb" in desc and "serial" in desc
            isArduino = "arduino" in desc or "acm" in desc
            # I used NetBurner from eltima software to create the virtual com port
            isWifi = "eltima" in desc
            isCDC = "CDC" in desc
            if isUsbSerial or isArduino or isCDC or isWifi:
                return port[0]
    return None


def testPort(comPort):
    '''
    Return a SerialPort object for the first port with a GRBL board.
    YOU are responsible for closing this serial port!
    '''
    if comPort is not None:
        try:
            serialPort = serial.Serial()
            serialPort.baudrate = 115200
            serialPort.timeout = 1.0
            serialPort.rts = False
            serialPort.dtr = True
            serialPort.port = comPort
            serialPort.open()
            time.sleep(2)

            # Opening the serial port may reset the unit, in which case we'll get a Grbl message
            #
            # In my (Python3) setup, opening the port resets GRBL on the Arduino: I get a blank line, then a Grbl version
            # line. If we don't pick this info up here and exit, then sending '\x18' causes a *second* reset - we end up
            # having *two* Grbl version messages sent back! The second Grbl message appears as a response to the first
            # command we sent, which causes an error "Error: Unexpected response from GRBL."
            #
            # I'm making this conditional on Python3 because for all I know earlier versions act differently here. But it's
            # possible that this behaviuor may occur with others. If we make the code unconditional we potentially incur
            # 2 comms timeouts at 1 second each.
            if fourxidraw_compat.isPython3():
                nTryCount = 0
                returnedMessage = ''
                while (len(returnedMessage) == 0) and (nTryCount < 2):
                    returnedMessage = serialPort.readline().decode().rstrip()
                    nTryCount += 1
                if len(returnedMessage) != 0:
                    if returnedMessage.startswith('Grbl'):
                        return serialPort

            # If opening the port hasn't caused a reset, send an explicit reset message
            if fourxidraw_compat.isPython3():
                serialPort.write(b'\x18')
            else:
                serialPort.write('\x18')
            time.sleep(1)

            while True:
                strVersion = serialPort.readline()
                if len(strVersion) == 0:
                    break
                grblTarget = b'Grbl' if fourxidraw_compat.isPython3() else 'Grbl'
                if strVersion and strVersion.startswith(grblTarget):
                    return serialPort
            serialPort.close()
        except serial.SerialException:
            pass
        return None
    else:
        return None

# Return a GrblSerial object


def openPort(doLog):
    foundPort = findPort()
    serialPort = testPort(foundPort)
    if serialPort:
        g = GrblSerial(serialPort, doLog)
        # Set absolute mode
        g.command('G90\r')
        return g
    return None


def escaped(s):
    r = ''
    for c in s:
        if ord(c) < 32:
            r = r + ('<%02X>' % ord(c))
        else:
            r = r + c
    return r


class GrblSerial(object):
    def __init__(self, port, doLog):
        self.port = port
        self.doLog = doLog

    def gcodeLog(self, data):
        try:
            with open("4xidraw-gcode.gcode", "a") as myfile:
                myfile.write(data)
        except:
            inkex.errormsg(gettext.gettext("Error logging serial data."))

    def log(self, type, text):
        ts = datetime.datetime.now()
        try:
            with open("4xidraw-serial.log", "a") as myfile:
                myfile.write('--- %s\n%s\n%s\n' %
                             (ts.isoformat(), type, escaped(text)))
        except:
            inkex.errormsg(gettext.gettext("Error logging serial data."))

    def close(self):
        if self.port is not None:
            try:
                self.port.close()
            except serial.SerialException:
                pass

    def write(self, data):
        if self.doLog:
            self.log('SEND', data) 
        if fourxidraw_compat.isPython3():
            self.port.write(data.encode())
        else:
            self.port.write(data)

    def readline(self):
        data = self.port.readline().decode().rstrip()
        if self.doLog:
            self.log('RECV', data)
        return data

    def query(self, cmd):
        if (self.port is not None) and (cmd is not None):
            response = ''
            try:
                self.write(cmd)
                response = self.readline()
                nRetryCount = 0
                while (len(response) == 0) and (nRetryCount < 100):
                    if self.doLog:
                        self.log('QUERY', 'read %d' % nRetryCount)
                    response = self.readline()
                    nRetryCount += 1

                # swallow 'ok'
                extra = self.readline()
                while (len(extra) > 0 and extra != 'ok'):
                    if self.doLog:
                        self.log('QUERY', 'read extra: ' + extra)
                    response = response + '\r' + extra
                    extra = self.readline()
                if self.doLog:
                    self.log('QUERY', 'response is '+response)
            except serial.SerialException:
                inkex.errormsg(gettext.gettext("Error reading serial data."))
            return response
        else:
            return None

    def command(self, cmd):
        if (self.port is not None) and (cmd is not None):
            try:
                self.write(cmd)
                response = self.readline()
                self.gcodeLog(cmd)
                nRetryCount = 0
                while (len(response) == 0) and (nRetryCount < 30):
                    # get new response to replace null response if necessary
                    response = self.readline()
                    nRetryCount += 1
                if 'ok' in response.strip():
                    return
                else:
                    if (response != ''):
                        inkex.errormsg('Error: Unexpected response from GRBL.')
                        inkex.errormsg('   Command: ' + cmd.strip())
                        inkex.errormsg('   Response: ' + str(response.strip()))
                    else:
                        inkex.errormsg(
                            'GRBL Serial Timeout after command: %s)' % cmd.strip())
                        sys.exit()
            except:
                inkex.errormsg('Failed after command: ' + cmd)
                sys.exit()


if __name__ == "__main__":

    serialPort = openPort(True)

    print('ver: '+serialPort.query('$I\r'))
