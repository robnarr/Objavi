#!/usr/bin/python

MYNAME="bookland"
MYVERSION="1.3"
COPYRIGHT="(C) 1999-2007 J. Milgram"
VERSIONDATE = "Mar 2007"
MAINTAINER = "bookland-bugs@cgpp.com"

#   Copyright (C) 1999-2007 Judah Milgram     
#
#   bookland - generate EAN-13 bar codes, including ISBN and ISMN.
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   Because this program copies a portion of itself into its output
#   file, its output files are also copyright the author and licensed
#   under the GPL.  Relevant provisions of the GPL notwithstanding,
#   the author licenses users to use and redistribute output files
#   generated by this program without restriction.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#     
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#

from bookland.productcode import *
import copy
import sys

class PostscriptError(Exception):
    pass


EPSWARNING = """\
% This is free software and comes with NO WARRANTY WHATSOVER. This file
% contains portions of bookland, a free program licensed under the GNU
% General Public License. The GPL notwithstanding, you may use and
% redistribute this output file without restriction."""

BOOKLANDDICT = """
/W { moduleWidth mul 0 rmoveto } def
/B { dup moduleWidth mul 2 div 0 rmoveto
     dup moduleWidth mul barWidthReduction sub setlinewidth
     0 moduleHeight rlineto 0 moduleHeight neg rmoveto
     currentpoint stroke moveto
     moduleWidth mul 2 div 0 rmoveto } def
/L { dup moduleWidth mul 2 div 0 rmoveto
     dup moduleWidth mul barWidthReduction sub setlinewidth
     0 -5 rmoveto 0 5 rlineto
     0 moduleHeight rlineto 0 moduleHeight neg rmoveto
     currentpoint stroke moveto
     moduleWidth mul 2 div 0 rmoveto } def
% function fitstring:
% usage: width string font fitstring
% scale font to fit string to desired width
% leave string on stack
/fitstring { dup findfont 1 scalefont setfont % w s f
             3 1 roll % f w s
             dup stringwidth pop % f w s sw
             3 2 roll exch div % f s x
             3 2 roll findfont exch
             scalefont setfont } def
% get bounding box of string.
% usage: string stringbb ->  llx lly urx ury
/stringbb {gsave false charpath flattenpath pathbbox grestore} def
% String height and width:
/stringhw {stringbb exch % llx lly ury urx
           4 1 roll      % urx llx lly ury
	   sub neg       % urx llx h
           3 1 roll      % h urx llx
	   sub           % h w
           } def
/dx { [ 0 1 2 0 1 2 0 1 2 ] } def
/dy { [ 0 0 0 1 1 1 2 2 2 ] } def
% Set dx and dy to shift to anchor point:
/dxdy { dup dx exch % anchor dx anchor
        get         % anchor idx
	dy          % anchor idx dy
	3 2 roll    % idx dy anchor
	get         % idx idy
        } def
% Usage: string anchor anchorstring
/anchorstring { dxdy          % string idx idy
                3 2 roll      % idx idy string
		dup           % idx idy string string
		4 1 roll      % string idx idy string
		stringhw      % string idx idy h w
		4 1 roll      % string w idx idy h
		mul -2 div    % string w idx ry
		3 1 roll      % string ry w idx
		mul -2 div    % string ry rx
		exch
		rmoveto show } def"""

class Postscript:
    x0 = 0
    y0 = 0
    bb = 4*[0]
    width = 0
    height = 0
    def __add__(self,other):
        rval = Postscript()
        rval.lines = self.lines + other.lines
        rval.bb[0] = min(self.bb[0]+self.x0,
                         other.bb[0]+other.x0)
        rval.bb[1] = min(self.bb[1]+self.y0,
                         other.bb[1]+other.y0)
        rval.bb[2] = max(self.bb[2]+self.x0,
                         other.bb[2]+other.x0)
        rval.bb[3] = max(self.bb[3]+self.y0,
                         other.bb[3]+other.y0)
        rval.width = rval.bb[2]-rval.bb[0]
        rval.height = rval.bb[3]-rval.bb[1]    
        return rval

    def eps(self,creator="",title="",cmyk=(0,0,0,1),comments="",
            padding=(1,1,1,1), position=None):
        if max(cmyk)>1 or min(cmyk)<0:
            raise PostscriptError("cmyk value out of range")

        bbox = map(int,self.bb)
        # int truncates towards zero.
        for i in range(len(bbox)):
            if bbox[i] > 0:
                bbox[i] += 1 + padding[i]
            elif bbox[i] < 0:
                bbox[i] -= 1 + padding[i]

        if position is None:
            # by default, center it in the middle of a US letter page:
            x0 = int(612/2) - (bbox[2]-bbox[0])/2.
            y0 = int(792/2) - (bbox[3]-bbox[1])/2.
        else:
            width, height, xl, yb = position[1:]
            xr = width + bbox[0] - bbox[2] - xl
            yt = height + bbox[1] - bbox[3] - yb
            print >> sys.stderr, xl, xr, yb, yt
            x0, y0 = {'tl': (xl, yt),
                      'tr': (xr, yt),
                      'bl': (xl, yb),
                      'br': (xr, yb),
                      }[position[0]]
            print >> sys.stderr, x0, y0

        for i in [0,2]:
            bbox[i] += x0
        for i in [1,3]:
            bbox[i] += y0

        lines=[ "%!PS-Adobe-2.0 EPSF-1.2",
                "%%%%Creator: %s" % creator,
                "%%%%Title: %s" % title,
                "%%%%BoundingBox: %d %d %d %d" % \
                       (bbox[0],bbox[1],bbox[2],bbox[3]),
                "%%EndComments",
                comments,
                EPSWARNING,
                BOOKLANDDICT,
                "%s %s translate 0 0 moveto" % (x0,y0),
                "%s %s %s %s setcmykcolor" % cmyk ]
        lines.extend(self.lines)
        lines.extend(["\nstroke","% showpage OK in EPS",
                      "showpage","% Good luck!\n"])
        return "\n".join(lines)

    def __repr__(self):
        return "\n".join(self.lines)


class Bars(Postscript):
    def __init__(self,bits,moduleWidth=(0.0130*72),moduleHeight=1.00*72,
                 barWidthReduction=0,x0=0,y0=0):
        self.x0 = x0
        self.y0 = y0
        llx = 0
        if "L" in bits:
            lly = -5
        else:
            lly = 0
        urx = len(bits)*moduleWidth
        ury = moduleHeight
        self.bb = [llx,lly,urx,ury]
        self.width = urx-llx
        self.height = ury-lly
        self.lines = [ "\n%\n% Product Code Bars\n%",
                       "gsave",
                       "%s %s translate 0 0 moveto" % (x0,y0),
                       "/moduleHeight { %s } def" % moduleHeight,
                       "/moduleWidth { %s } def" % moduleWidth,
                       "/barWidthReduction { %s } def" % barWidthReduction]
        currentVal = None
        n = None
        sep = ""
        line = ""
        dict = {"1":"B", "0":"W", "L":"L"}
        for bit in bits:
            if bit == currentVal:
                n += 1
            else:
                if n:
                    line = line + sep + "%d %s" % (n,dict[currentVal])
                    sep = " "
                currentVal=bit
                n = 1
        line = line + sep + "%d %s" % (n,dict[currentVal])
        self.lines.append(line)
        self.lines.append("grestore")


class setfont(Postscript):
    def __init__(self,font,size=None,fitwidth=None,fitstring=None):
        self.font = font
        self.size=size
        self.fitwidth=fitwidth
        self.fitstring=fitstring
        if size:
            self.lines = [ "/%s findfont %s scalefont setfont" % (font,size) ]
        elif fitwidth and fitstring:
            self.lines = [ "%s (%s) /%s fitstring" % (fitwidth,fitstring,font) ]
        else:
            raise PostscriptError("couldn't set font")

class Text(Postscript):
    def __init__(self,s,sf,x0=0,y0=0,anchor=0):
        # Anchor points:
        # 6 7 8
        # 3 4 5
        # 0 1 2
        # estimate dimensions of text box
        self.x0 = x0
        self.y0 = y0

        # All this stuff is just to track the BB.
        # The actual anchoring of the string is done in Postscript.
        nominalAspectRatio = 0.65
        if sf.size:
            height = sf.size
            width = len(s) * sf.size * nominalAspectRatio
        elif sf.fitwidth and sf.fitstring:
            width = (sf.fitwidth * len(s))/len(sf.fitstring)
            height = width/len(s)/nominalAspectRatio
        else:
            raise PostscriptError("Text: couldn't set width or height")
        self.bb = [ 0, 0, width, height ]
        ndx = -(3*[0,1,2])[anchor]
        ndy = -(3*[0] + 3*[1] + 3*[2])[anchor]
        dx = ndx*width/2
        dy = ndy*height/2
        self.bb = [ dx, dy, width+dx, height+dy ]

        self.lines = [ "\n%\n% Text string\n%",
                       "gsave %s %s translate 0 0 moveto" % (x0,y0) ]
        self.lines.extend(sf.lines)
        self.lines.extend([ "(%s) %s anchorstring" % (s,anchor),
                            "grestore" ])
        
class EAN13Symbol(Postscript):

    def __init__(self,ean13,font="OCRB",
                 moduleWidth=(0.0130*72),moduleHeight=1.00*72,
                 barWidthReduction=0,x0=0,y0=0):

        # The bars:
        bars = Bars(ean13.bits,
                    moduleWidth=moduleWidth,
                    moduleHeight=moduleHeight,
                    barWidthReduction=barWidthReduction,
                    x0=x0,y0=y0)

        # Define an anchor point on top center of bars,
        # for use by ISBN symbol constructor

        self.isbnAnchor = ((bars.bb[0]+bars.bb[2])/2 + bars.x0,
                           bars.bb[3] + bars.y0)
                    
        # The digits:
        # Set font for digits below bars:
        sf = setfont(font,fitwidth=0.98*40*moduleWidth,
                     fitstring=ean13.leftDigits)
        
        # Left digits
        x0 = 24*moduleWidth
        y0 = -1
        leftDigits = Text(ean13.leftDigits,sf,
                          x0=x0,
                          y0=y0,
                          anchor=7)

        # Right digits
        x0 = 70*moduleWidth
        y0 = -1
        rightDigits = Text(ean13.rightDigits,sf,
                           x0=x0,
                           y0=y0,
                           anchor=7)
        
        # Lone first digit:
        x0=-2
        y0=-1
        d = "%s" % ean13.digits[0]
        firstDigit = Text(d,sf,
                          x0=x0,
                          y0=y0,
                          anchor=8)

        # Bogus, but better than nothing. Let's look up the
        # real quiet zone width someday.
        quietZone = Text(" ",sf,
                         x0=bars.width,
                         y0=0,
                         anchor=0)


        ps = rightDigits + leftDigits + firstDigit + bars + quietZone
        self.lines = ps.lines
        self.bb = ps.bb
        self.width = ps.width
        self.height = ps.height
        

class Bookland(Postscript):

    # ISBN10, ISBN13, ISMN
    
    def __init__(self,isbn,
                 font="OCRB",
                 moduleWidth=(0.0130*72),
                 moduleHeight=1.00*72,
                 barWidthReduction=0,x0=0,y0=0,
                 upc5=None,
                 quietZone=True,
                 labelScale=9):
        
        # The EAN-13 symbol:
        ean13symbol = EAN13Symbol(isbn.as13(),
                                  font=font,
                                  moduleHeight=moduleHeight,
                                  moduleWidth=moduleWidth,
                                  barWidthReduction=barWidthReduction,
                                  x0=x0,y0=y0)

        # Human-readable label on top of bars:

        barsWidth = len(isbn.bits) * moduleWidth
        x0,y0 = ean13symbol.isbnAnchor
        y0 += 2
        label = "%s" % isbn
        if labelScale > 2:
            topLabelFont = setfont(font,size=labelScale)
        elif labelScale > 0:
            fitwidth = barsWidth * labelScale
            topLabelFont = setfont(font,fitwidth=fitwidth,fitstring=label)
        else:
            raise PostscriptError("bad label scale: %s" % labelScale)

        topLabel = Text(label,topLabelFont,
                        x0=x0,
                        y0=y0,
                        anchor=1)

        if upc5:
            # UPC-5 bits
            upc5ModuleHeight=0.852*moduleHeight
            upc5bars = Bars(upc5.bits,moduleWidth=moduleWidth,
                            moduleHeight=upc5ModuleHeight,x0=98,y0=0)

            # Set font for price code:
            s = upc5.s
            sf = setfont(font,fitwidth=0.75*upc5bars.width,
                         fitstring=s)

            # Price code label
            x0 = upc5bars.x0 + upc5bars.width/2
            y0 = upc5bars.y0 + upc5bars.height + 2
            priceCode = Text(s,sf,
                             x0=x0,
                             y0=y0,
                             anchor=1)
            
            # Quiet zone
            if quietZone:
                s = ">"
            else:
                # bogus! is defined as dimensional length.
                # good enough for now but look this up.
                s = " "
            x0 = upc5bars.x0 + upc5bars.bb[2] + 1
            y0 = upc5bars.y0 + upc5bars.height + 2
            quietZone = Text(s,sf,
                             x0=x0,
                             y0=y0,
                             anchor=0)

        ps = ean13symbol + \
             topLabel

        if upc5:
            ps = ps + \
                 upc5bars + \
                 priceCode
            if quietZone:
                ps = ps + quietZone


        self.bb = ps.bb
        self.width = ps.width
        self.height = ps.height
        self.lines = ps.lines

def rgbtocmyk(rgb):
    r,g,b = rgb
    c,m,y = 1-r, 1-g, 1-b
    k = min(c,m,y)
    if k==1:
        return (0,0,0,1)
    else:
        d = 1-k
        c = (c-k)/d
        m = (m-k)/d
        y = (y-k)/d
        return (c,m,y,k)

def colorValOK(color):
    # color is tuple of cmyk or rgb
    if max(color) > 1 or min(color) < 0:
        return False
    else:
        return True

def doTheRightThing(s,font,price,moduleHeight,
                    barWidthReduction,zone,cmyk,labelScale,padding, position):

    if not colorValOK(cmyk):
        raise ProductCodeError("invalid CMYK = %s" % (cmyk,))

    productCode = makeProductCode(s,forceISBN13=True)
    if price:
        if not productCode.type in [ "ISBN10", "ISBN13" ]:
            raise ProductCodeError("oops, no price code for %s" % \
                                   productCode.type)
        else:
            upc5=UPC5(price)
    else:
        upc5=None

    commandLine = string.join(sys.argv)
    epsComment = "%% Command line: %s" % commandLine
    creator = "%s %s" % (MYNAME,MYVERSION)
    title = str(productCode)
    # suggested file name:
    filename = re.sub("[ -]","",title) + ".eps"

    if productCode.type in [ "ISBN10", "ISBN13", "ISMN" ]:
        b = Bookland(productCode,font=font,upc5=upc5,
                     moduleHeight=moduleHeight,
                     barWidthReduction=barWidthReduction,
                     quietZone=zone,
                     labelScale=labelScale)
    elif productCode.type in [ "EAN13" ]:
        b = EAN13Symbol(productCode,
                        font=font,
                        moduleHeight=moduleHeight,
                        barWidthReduction=barWidthReduction)
    else:
        raise ProductCodeError("what kind of product code is this?")

    epslines = b.eps(comments=epsComment,
                     title=title,
                     creator=creator,
                     cmyk=cmyk,
                     padding=padding,
                     position=position)
    return (epslines,filename)



if __name__=="__main__":


    import sys
    import getopt
    
    USAGE = """\
Usage: %s [-h|--help] [-V|--version] [-f|--font=fontname] [-q]
          [-s|--height=height scale] [-r --reduction=factor]
          [-o|outfile=filename] [-n|--noquietzone] [-a|--autofile]
          [--cmyk=c,m,y,k] [--rgb=r,g,b] productCode [priceCode]""" % MYNAME

    def printUsage():
        sys.stderr.write(USAGE+"\n")

    def warn():
        sys.stderr.write("This is free software and comes with NO WARRANTY\n")        
    def printVersion():
        sys.stderr.write("%s version %s %s.\n" % (MYNAME,MYVERSION,COPYRIGHT))
        sys.stderr.write("Bugs to %s\n" % MAINTAINER)

    try:
        format = "hVb:f:s:r:o:nxaqp:c"
        extendedFormat = [ "reduction=","outfile=","height=","version",
                           "help","font=","noquietzone","cmyk=","rgb=",
                           "autofile", "labelScale=", "padding=", "position=" ]
        opts,args = getopt.getopt(sys.argv[1:],format,extendedFormat)
    except:
        printUsage()
        sys.exit(1)
        

    # some initial defaults:
    s = "1-56592-197-6" # Mark Lutz, "Programming Python",
                        # O'Reilly, Sebastopol CA, 1996
    priceCode = None
    font="OCRB"
    zone=True
    outfile=None
    outfid=sys.stdout
    checkonly=False
    heightScale=1
    barWidthReduction = 0
    cmyk = (0,0,0,1)
    quiet=False
    labelScale = 9
    padding = (1,1,1,1)
    position = None

    commandLine = " ".join(sys.argv)

    # parse command line:
    for opt,val in opts:
        if opt in ("-V","--version"):
            printVersion()
            sys.exit(0)
        elif opt in ("-h","--help"):
            printVersion()
            warn()
            printUsage()
            sys.exit(0)
        elif opt in ("-f","--font"):
            font=val
        elif opt in ("-n","--noquietzone"):
            zone=False
        elif opt in ("-s","--height"):
            heightScale = float(val)
        elif opt in ("-r","--reduction"):
            barWidthReduction = val
        elif opt in ("-x","--checkonly"):
            checkonly=True
        elif opt in ("-o","--outfile"):
            outfile=val
        elif opt in ("-a","--autofile"):
            outfile="auto"
        elif opt in ("--cmyk",):
            v = val.split(",")
            cmyk = (v[0],v[1],v[2],v[3])
        elif opt in ("--rgb",):
            rgb = map(float,val.split(","))
            cmyk = rgbtocmyk(rgb)
        elif opt in ("-q",):
            quiet = True
        elif opt in ("-b","labelScale"):
            labelScale = float(val)
        elif opt in ("-p","--padding"):
            padding = map(int,val.split(","))
        elif opt in ("-c","--position"):
            corner, width, height, x0, y0 = val.split(",")
            position = (corner, float(width), float(height), float(x0), float(y0))
            print >> sys.stderr, position
        else:
            printUsage()
            sys.exit(1)
    if len(args)==1:
        s=args[0]
    elif len(args)==2:
        s=args[0]
        priceCode=args[1]
    elif len(args)>2:
        printUsage()
        sys.exit(1)

    # Do stuff.

    if not quiet:
        warn()

    if checkonly:
        productCode = makeProductCode(s,forceISBN13=True)
        print "%s understood as %s" % (s,productCode)
        if productCode.type in [ "ISBN10", "ISMN" ]:
            print "13-digit version: %s" % productCode.as13()
        sys.exit(0)

    try:
        epslines,filename = doTheRightThing(s,font,priceCode,heightScale*72,
                                            barWidthReduction,zone,cmyk,
                                            labelScale,
                                            padding,
                                            position
                                            )
    except ProductCodeError,e:
        for msg in e.msgs: print msg
        printUsage()
        sys.exit(1)

    if outfile=="auto":
        outfile = filename
    if outfile:
        try:
            outfid = open(outfile,"w")
        except:
            sys.stderr.write("can't open output file %s\n" % outfile)
            sys.exit(1)

    outfid.write(epslines)
    if outfile and not quiet:
        sys.stderr.write("wrote %s\n" % filename)

    outfid.close()
