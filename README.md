# 4xiDraw

The 4xiDraw Extensions for Inkscape - Software to drive the 4xiDraw drawing machine.

More about 4xiDraw:  https://www.instructables.com/id/4xiDraw/

---------


Install as you would any other Inkscape extension.

**Note:** If you change the physical dimension from the 4xiDraw default, be sure to edit ```fourxidraw_conf.py``` and change the values of ```PageWidthIn``` and ```PageHeightIn``` accordingly.

---------

## Dependencies

The main extension "4xiDraw/4xiDraw Control..." should work directly with Inkscape 1.1, but Inkscape 0.9.x will require some python modules and and Inkscape extensions to be installed, as set out below.

**Hatch fill works now.**

### Python Modules

- [lxml](https://lxml.de/)
- [Pyserial](https://pypi.python.org/pypi/pyserial). (Note that an older version, 2.7, must be used on Windows.)

### Inkscape Extensions

To install a new extension, download and unpack the archive file. Copy the files into the directory listed at Edit > Preferences > System: User extensions. Be sure to copy all files directly to this folder. After a restart of Inkscape, the new extension will be available.

---------

## Issues fixed from bullestock/4xidraw:

- Hatch fill works now!

- There is apparently a rounding error somewhere, so the start and end of a drawing does not always line up.
> Try to move the carret by hand. If you see any deformations on the belt, try to tighten the belt.    Also, bumped up the precision for gcode and svg outputs

- The speed is lower than it should be.
> I changed the following values in config

Max feed rate mm/min - with this values motors are a bit warm
```
$110=8500.000
$111=8500.000
```
Acceleration - i don't recommend setting values higher than 400
```
$120=200.000
$121=200.000
```




### No module named lxml

Try to install the python2 version of the module to resolve this issue. See [this issue](https://github.com/NixOS/nixpkgs/issues/31800) for more detailed information.

### No module named serial

Again, make sure to install the python2 version.


---------

This is based on the fork of AxiDraw inkscape plugin, https://github.com/bullestock/4xidraw
and oroginal AxiDraw inkscape plugin, https://github.com/evil-mad/axidraw