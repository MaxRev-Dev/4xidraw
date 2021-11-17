# 4xidraw_conf.py
# Part of the 4xiDraw driver for Inkscape
# Version 1.3.0, dated March 7, 2017.
#
# Copyright 2017 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# https://github.com/bullestock/4xidraw/
#
# "Change numbers here, not there." :)


'''
Primary user-adjustable control parameters:

We encourage you to freely tune these values as needed to match the
 behavior and performance of your 4xiDraw to your application and taste.

If you are operating the 4xiDraw from within Inkscape (either within the
 application from the Extensions menu or from the command line), please
 set your preferences within Inkscape, using the 4xiDraw Control dialog.
 (The values listed here are ignored when called via Inkscape.)

If you are operating the 4xiDraw in "standalone" mode, that is, outside
 of the Inkscape context, then please set your preferences here or via
 command-line arguments. (Preferences set within Inkscape -- via the 
 4xiDraw Control dialog -- are ignored when called via the command line.)
 Best practice is to adjust and test settings from within the Inkscape
 GUI, before 
'''

PenUpPos = 40			# Default pen-up position
PenDownPos = 0			# Default pen-down position

applySpeed = False      # Whether to apply speeds to GRBL for pen up and pen down
PenUpSpeed = 5000       # Speed when pen up (mm/min)
PenDownSpeed = 1000     # Speed when pen down (mm/min)

penLowerDelay = 0		# added delay (ms) for the pen to go down before the next move
penLiftDelay = 0		# added delay (ms) for the pen to go up before the next move

penLiftRate = 150		# Default pen-lift servo speed 
penLowerRate = 150		# Default pen-lift servo speed when lowering


autoRotate = True		# Print in portrait or landscape mode automatically
constSpeed = False		# Use constant velocity mode when pen is down
reportTime = True		# Report time elapsed
logSerial = False		# Log serial communication

smoothness = 10.0		# Curve smoothing (default: 10.0)
cornering = 10.0		# Cornering speed factor (default: 10.0)

DefaultLayer = 1		# Default inkscape layer, when plotting in "layers" mode


'''
Additional user-adjustable control parameters:

These parameters are adjustable only from the command line, and are not
visible from within the Inkscape GUI.
'''

fileOutput = False		# If True: Output updated contents of SVG on stdout. 




'''
Secondary control parameters:

Values below this point have been carefully chosen, and generaly do not need to be 
adjusted in everyday use. That said, proceed with caution, and keep a backup copy.
'''

# Page size values typically do not need to be changed. They primarily affect viewpoint and centering.
# Measured in page pixelssteps.  Default printable area for 4xiDraw is 300 x 218 mm

PageWidthIn = 16.5		# Default page width in inches 	300 mm = about 11.81 inches
PageHeightIn = 11.69	# Default page height in inches 	218 mm = about 8.58 inches


# Machine resolution: Used in converting drawing size to motor steps.
DPI_16X = 100*25.4		# DPI ("dots per inch") @ 16X microstepping.  Standard value: 100 steps per mm.  

SpeedScale = 24950		# Maximum (110%) speed, in steps per second. 

StartPosX = 0.			# parking position, in pixels. Default: 0
StartPosY = 0.			# parking position, in pixels. Default: 0


# Acceleration rates and motion-control time slices:
AccelTime = .2			# Seconds of acceleration to reach full speed WITH PEN DOWN
AccelTimePU = .5		# Seconds of acceleration to reach full speed WITH PEN UP.
AccelTimePUHR = .15		# Seconds of acceleration to reach full speed WITH PEN UP in slower high-res mode.

TimeSlice = 0.025		# Interval, in seconds, of when to update the motors.

# Short-move pen-up distance threshold, below which we use the faster pen-down acceleration rate:
ShortThreshold = 1.0	# Distance Threshold (inches)

# Skip pen-up moves shorter than this distance, when possible:
MinGap = 0.010			# Distance Threshold (inches)
