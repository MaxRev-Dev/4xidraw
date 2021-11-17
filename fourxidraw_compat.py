# fourxidraw_compat.py
#
# Part of the 4xiDraw driver for Inkscape
# 
# This offers functions to bridge non-compatible changes between pre- and post-1.0 versions of Inkscape.
# 
# See https://wiki.inkscape.org/wiki/index.php/Updating_your_Extension_for_1.0
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

import builtins
import sys

def isPython3():
    return sys.version_info[0] == 3

# Import what's necessary to support the code paths that we're using
if isPython3():
    # new
    import inkex
    from inkex.paths import *
    from inkex.transforms import *
    from inkex import bezier
    from lxml import etree
else:
    # old
    import cspsubdiv
    from bezmisc import *
    from simpletransform import *

# Convert from typenames to types
def compatGetArgumentTypeFromName(type_name):
    try:
        # Cater for non-built-in type as per
        # https://wiki.inkscape.org/wiki/index.php/Updating_your_Extension_for_1.0#Collecting_the_options_of_the_extension
        if type_name == 'inkbool':
            return inkex.Boolean
            
        return getattr(builtins, type_name)
    except AttributeError:
        return None

def compatIsBasestring(obj):

    if isPython3():
        return isinstance(obj, str)
    else:
        return isinstance(obj, basestring)

def compatPxPerInch():

    if isPython3():
        # Inkscape 1.x follows the SVG specification of 96 px per inch
        return 96.0
    else:
        # 90 px per inch, as of Inkscape 0.91
        return 90.0

# DeprecationWarning: inkex.etree was removed, use "from lxml import etree"
def compatEtreeElement(elem):

    if isPython3():
        return etree.Element(elem)
    else:
        return inkex.etree.Element(elem)

# DeprecationWarning: inkex.etree was removed, use "from lxml import etree"
def compatEtreeSubElement(a, b):

    if isPython3():
        return etree.SubElement(a, b)
    else:
        return inkex.etree.SubElement(a, b)

# Behaviour change: 0.9.x accepts (requires?) spaces between commands and other elements, 1.x rejects them
# This may be a consequence of simplepath.FormatPath(a) being deprecated/replaced by str(Path(a)) and differences in the relevant code
def compatAppendCommand(a, command, data):

    if isPython3():
        # Remove any leading or trailing spaces in the command - it should be a single letter
        a.append([command.strip(), data])
    else:
        # Keep any leading or trailing spaces - perhaps they are necessary for 0.9.x
        a.append([command, data])

# DeprecationWarning: simplepath.formatPath -> str(element.path) or str(Path(array))
def compatFormatPath(a):
 
    if isPython3():
        return str(Path(a))
    else:
        return simplepath.formatPath(a)


# DeprecationWarning: inkex.bezier.beziersplitatt -> Split bezier at given time
def compatBezierSplitAtT(b, t):

    if isPython3():
        return bezier.beziersplitatt( b, t )
    else:
        return beziersplitatt( b, t )        
        
# DeprecationWarning: inkex.bezier.maxdist -> Get maximum distance within bezier curve
def compatCspSubDivMaxDist(b):

    if isPython3():
        return bezier.maxdist( b )
    else:
        return cspsubdiv.maxdist( b )
        
# DeprecationWarning: simpletransform.parseTransform -> Transform(str).matrix
def compatParseTransform(stringRepresentation):

    if isPython3():
        return Transform(stringRepresentation).matrix
    else:
        return simpletransform.parseTransform(stringRepresentation)

# DeprecationWarning: simpletransform.composeTransform -> Transform(M1) * Transform(M2)
def compatComposeTransform(a, b):

    if isPython3():
        return Transform(a) * Transform(b)
    else:
        return composeTransform(a, b)
        
# DeprecationWarning: simplepath.parsePath -> element.path.to_arrays()
def compatIsEmptyPath(stringRepresentation):

    if isPython3():
        return len(Path(stringRepresentation).to_arrays()) == 0
    else:
        return len(simplepath.parsePath(stringRepresentation)) == 0
        
# DeprecationWarning: cubicsuperpath.parsePath -> None
def compatParseCubicSuperPath(stringRepresentation):

    if isPython3():
        return CubicSuperPath(Path(stringRepresentation))
    else:
        return cubicsuperpath.parsePath(stringRepresentation)

# This one looks like changed behaviour with no deprecation warning!
# 
# From the code, it looks like Inkscape 0.9.x transformed the path in place. That isn't how
# Inkscape 1.x works - its "applyTransformToPath" does NOT modify p.
# 
# If the path isn't modified, documents with a size expressed in mm instead of inches
# (e.g. examples/AxiDraw_First.svg, which has height="210mm", width="297mm") will not plot correctly -
# the transform will not affect the path and as a result we'll get a path in mm being interpreted as
# being in inches - the practical effect being to lock everything to the maximum coordinates.
# By contrast, files such as examples/basic demos/HappyBirthday.svg have their height and witdth in
# inches, and so get through OK.
def compatApplyTransformToPath(matTransform, p):
    
    if isPython3():
        return inkex.paths.CubicSuperPath(Path(p).transform(Transform(matTransform)))
    else:
        applyTransformToPath(matTransform, p)
        return p
