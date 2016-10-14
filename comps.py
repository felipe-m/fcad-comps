# classes that creates objects 

import FreeCAD;
import Part;
import logging
import os
import Draft;
#import copy;
#import Mesh;

# ---------------------- can be taken away after debugging
# directory this file is
filepath = os.getcwd()
import sys
# to get the components
# In FreeCAD can be added: Preferences->General->Macro->Macro path
sys.path.append(filepath)
# ---------------------- can be taken away after debugging

import kcomp # before, it was called mat_cte
import fcfun

from fcfun import V0, VX, VY, VZ, V0ROT, addBox, addCyl, addCyl_pos, fillet_len
from fcfun import addBolt, addBoltNut_hole, NutHole


logging.basicConfig(level=logging.DEBUG,
                    format='%(%(levelname)s - %(message)s')
#
#        _______       _______________________________  TotH = H
#       |  ___  |                     
#       | /   \ |      __________ HoleH = h
#       | \___/ |  __
#     __|       |__ /| __
#    |_____________|/  __ TotD = L ___________________
#
#     <- TotW  = W->
#
# hole_x: 1 the depth along X axis 
#           Hole facing X
#         0 the depth along Y axis 
#           Hole facing Y
# cx:     1 if you want the coordinates referenced to the x center of the piece
#         it can be done because it is a new shape formed from the union
# cy:     1 if you want the coordinates referenced to the y center of the piece
# upsdown:  NOT YET
#            0: Normal vertical position, referenced to 0
#            1:  z0 is the center of the hexagon (nut)
#              it can be done because it is a new shape formed from the union


class Sk (object):

    """
     SK dimensions:
     dictionary for the dimensions
     mbolt: is mounting bolt. it corresponds to its metric
     tbolt: is the tightening bolt.
    SK12 = { 'd':12.0, 'H':37.5, 'W':42.0, 'L':14.0, 'B':32.0, 'S':5.5,
             'h':23.0, 'A':21.0, 'b': 5.0, 'g':6.0,  'I':20.0,
              'mbolt': 5, 'tbolt': 4} 
    """
    SK12 = kcomp.SK12

    # separation of the upper side (it is not defined). Change it
    # measured for sk12 is 1.2
    up_sep_dist = 1.2

    # tolerances for holes 
    holtol = 1.1

    def __init__(self, size, name, hole_x = 1, cx=0, cy=0):
        self.size = size
        self.name = name
        self.cx = cx
        self.cy = cy

        if size != 12:
            logging.warning("only size 12 supported")
            print ("only size 12 supported")
            
        else:
            doc = FreeCAD.ActiveDocument
            # Total height:
            sk_z = kcomp.SK12['H'];
            self.TotH = sk_z
            # Total width (Y):
            sk_y = kcomp.SK12['W'];
            self.TotW = sk_y
            # Total depth (x):
            sk_x = kcomp.SK12['L'];
            self.TotD = sk_x
            # Base height
            sk_base_z = 6;
            # center width
            sk_center_y = 20;
            # Axis height:
            sk_axis_z = 23;
            self.HoleH = sk_axis_z;
    
            # tightening bolt with added tolerances:
            # Bolt's head radius
            tbolt_head_r = (self.holtol
                            * kcomp.D912_HEAD_D[kcomp.SK12['tbolt']])/2.0
            # Bolt's head lenght
            tbolt_head_l = (self.holtol
                            * kcomp.D912_HEAD_L[kcomp.SK12['tbolt']] )
            # Mounting bolt radius with added tolerance
            mbolt_r = self.holtol * kcomp.SK12['mbolt']/2
    
            # the total dimensions: LxWxH
            # we will cut it
            total_box = addBox(x = sk_x,
                               y = sk_y,
                               z = sk_z,
                               name = "total_box",
                               cx = False, cy=True)

            # what we have to cut from the sides
            side_box_y = (sk_y - kcomp.SK12['I'])/2
            side_box_z = sk_z - kcomp.SK12['g']
    
            side_cut_box_r = addBox (sk_x, side_box_y, side_box_z,
                                     "side_box_r")
            side_cut_pos_r = FreeCAD.Vector(0,
                                            kcomp.SK12['I']/2,
                                            kcomp.SK12['g'])
            side_cut_box_r.Placement.Base = side_cut_pos_r

            side_cut_box_l= addBox (sk_x, side_box_y, side_box_z,
                                     "side_box_l")
            side_cut_pos_l = FreeCAD.Vector(0,-sk_y/2,kcomp.SK12['g'])
            side_cut_box_l.Placement.Base = side_cut_pos_l

            # union 
            side_boxes = doc.addObject("Part::Fuse", "side_boxes")
            side_boxes.Base = side_cut_box_r
            side_boxes.Tool = side_cut_box_l

            # difference 
            sk_shape = doc.addObject("Part::Cut", "sk_shape")
            sk_shape.Base = total_box
            sk_shape.Tool = side_boxes

            # Shaft hole, its height has +2 to make it throughl L all de way
            shaft_hole = addCyl(kcomp.SK12['d']/2,
                                sk_x+2,
                                "shaft_hole")

            """
            First argument defines de position: -1, 0, h
            Second argument rotation: 90 degrees rotation in Y.
            Third argument the center of the rotation, in this case,
                  it is in the cylinder
            axis at the base of the cylinder 
            """
            shaft_hole.Placement = FreeCAD.Placement(
                                         FreeCAD.Vector(-1,0,kcomp.SK12['h']),
                                         FreeCAD.Rotation(VY,90),
                                         V0)

            # the upper sepparation
            up_sep = addBox( sk_x +2,
                             self.up_sep_dist,
                             sk_z-kcomp.SK12['h'] +1,
                             "up_sep")
            up_sep_pos = FreeCAD.Vector(-1,
                                        -self.up_sep_dist/2,
                                         kcomp.SK12['h']+1)
            up_sep.Placement.Base = up_sep_pos

            """
             Tightening bolt shaft hole, its height has +2 to make it
             throughl L all de way
             kcomp.SK12['tbolt'] is the diameter of the bolt: (M..) M4, ...
             tbolt_head_r: is the radius of the tightening bolt's head
             (including tolerance), which its bottom either
             - is at the middle point between
               - A: the total height :sk_z
               - B: the top of the shaft hole: kcomp.SK12['h']+kcomp.SK12['d']/2
               - so the result will be (A + B)/2
             or it is aligned with the top of the 12mm shaft, whose height is: 
                 kcomp.SK12['h']+kcomp.SK12['d']/2
            """
            tbolt_shaft = addCyl(kcomp.SK12['tbolt']/2,kcomp.SK12['I']+2,
                                      "tbolt_shaft")
            tbolt_shaft_pos = FreeCAD.Vector(sk_x/2,
                    kcomp.SK12['I']/2+1,
                    kcomp.SK12['h']+kcomp.SK12['d']/2+tbolt_head_r/self.holtol)
                    #(sk_z + kcomp.SK12['h']+kcomp.SK12['d']/2)/2)
            tbolt_shaft.Placement = FreeCAD.Placement(tbolt_shaft_pos,
                                                 FreeCAD.Rotation(VX,90),
                                                 V0)

            # Head of the thigthening bolt
            tbolt_head = addCyl(tbolt_head_r,tbolt_head_l+1, "tbolt_head")
            tbolt_head_pos = FreeCAD.Vector(sk_x/2,
                   kcomp.SK12['I']/2+1,
                   kcomp.SK12['h']+kcomp.SK12['d']/2+tbolt_head_r/self.holtol)
                   #(sk_z + kcomp.SK12['h']+kcomp.SK12['d']/2)/2)
            tbolt_head.Placement = FreeCAD.Placement(tbolt_head_pos,
                                         FreeCAD.Rotation(VX,90),
                                         V0)


            #Make an union of all these parts

            fuse_shaft_holes = doc.addObject("Part::MultiFuse",
                                             "fuse_shaft_holes")
            fuse_shaft_holes.Shapes = [tbolt_head,
                                       tbolt_shaft,
                                       up_sep, shaft_hole]

            #Cut from the sk_shape

            sk_shape_w_holes = doc.addObject("Part::Cut", "sk_shape_w_holes")
            sk_shape_w_holes.Base = sk_shape
            sk_shape_w_holes.Tool = fuse_shaft_holes

            #Mounting bolts
            mbolt_sh_r = addCyl(mbolt_r,kcomp.SK12['g']+2, "mbolt_sh_r")
            mbolt_sh_l = addCyl(mbolt_r,kcomp.SK12['g']+2, "mbolt_sh_l")

            mbolt_sh_r_pos = FreeCAD.Vector(sk_x/2,
                                            kcomp.SK12['B']/2,
                                            -1)

            mbolt_sh_l_pos = FreeCAD.Vector(sk_x/2,
                                            -kcomp.SK12['B']/2,
                                            -1)

            mbolt_sh_r.Placement.Base = mbolt_sh_r_pos
            mbolt_sh_l.Placement.Base = mbolt_sh_l_pos

            """ Equivalente expresions to the ones above
            mbolt_sh_l.Placement = FreeCAD.Placement(mbolt_sh_l_pos, v0rot, v0)
            mbolt_sh_r.Placement = FreeCAD.Placement(mbolt_sh_r_pos, v0rot, v0)
            """

            mbolts_sh = doc.addObject("Part::Fuse", "mbolts_sh")
            mbolts_sh.Base = mbolt_sh_r
            mbolts_sh.Tool = mbolt_sh_l

            # Instead of moving all the objects from the begining. I do it here
            # so it is easier, and since a new object will be created, it is
            # referenced correctly
            # Now, it is centered on Y, having the width on X, hole facing X
            # on the positive side of X
            if hole_x == 1:
                # this is how it is, no rotation
                rot = FreeCAD.Rotation(VZ,0)
                if cx == 1: #we want centered on X,bring back the half of depth
                    xpos = -self.TotD/2.0
                else:
                    xpos = 0 # how it is
                if cy == 1: # centered on Y, how it is
                    ypos = 0
                else:
                    ypos = self.TotW/2.0 # bring forward the width
            else: # hole facing Y
                rot = FreeCAD.Rotation (VZ,90)
                # After rotating, it is centered on X, 
                if cx == 1: # centered on X, how it is
                    xpos = 0
                else:
                    xpos = self.TotW /2.0
                if cy == 1: # we want centered on Y, bring back
                    ypos = - self.TotD/2.0
                else:
                    ypos = 0
             

            sk_shape_w_holes.Placement.Base = FreeCAD.Vector (xpos, ypos, 0)
            mbolts_sh.Placement.Base = FreeCAD.Vector (xpos, ypos, 0)
            sk_shape_w_holes.Placement.Rotation = rot
            mbolts_sh.Placement.Rotation = rot
 

            sk_final = doc.addObject("Part::Cut", name)
            sk_final.Base = sk_shape_w_holes
            sk_final.Tool = mbolts_sh

            self.CadObj = sk_final

# --------------------------------------------------------------------
# Creates a Misumi Aluminun Profile 30x30 Series 6 Width 8
# length:   the length of the profile
# axis      'x', 'y' or 'z'
#           'x' will along the x axis
#           'y' will along the y axis
#           'z' will be vertical
# cx:     1 if you want the coordinates referenced to the x center of the piece
#         it can be done because it is a new shape formed from the union
# cy:     1 if you want the coordinates referenced to the y center of the piece
# cz:     1 if you want the coordinates referenced to the z center of the piece

class MisumiAlu30s6w8 (object):

    doc = FreeCAD.ActiveDocument
    # filename of Aluminum profile sketch
    skfilename = "misumi_profile_hfs_serie6_w8_30x30.FCStd"
    ALU_W = 30.0
    ALU_Wh = ALU_W / 2.0  # half of it

    def __init__ (self, length, name, axis = 'x',
                  cx=False, cy=False, cz=False):
        doc = FreeCAD.ActiveDocument
        self.length = length
        self.name = name
        self.axis = axis
        self.cx = cx
        self.cy = cy
        self.cz = cz
        # filepath
        path = os.getcwd()
        #logging.debug(path)
        self.skpath = path + '/../../freecad/comps/'
        doc_sk = FreeCAD.openDocument(self.skpath + self.skfilename)

        list_obj_alumprofile = []
        for obj in doc_sk.Objects:
            """
            if (hasattr(obj,'ViewObject') and obj.ViewObject.isVisible()
                and hasattr(obj,'Shape') and len(obj.Shape.Faces) > 0 ):
               # len(obj.Shape.Faces) > 0 to avoid sketches
                list_obj_alumprofile.append(obj)
            """
            if len(obj.Shape.Faces) == 0:
                orig_alumsk = obj

        FreeCAD.ActiveDocument = doc
        self.Sk = doc.addObject("Sketcher::SketchObject", 'sk_' + name)
        self.Sk.Geometry = orig_alumsk.Geometry
        self.Sk.Constraints = orig_alumsk.Constraints
        self.Sk.ViewObject.Visibility = False

        FreeCAD.closeDocument(doc_sk.Name)
        FreeCAD.ActiveDocument = doc #otherwise, clone will not work

        # The sketch is on plane XY, facing Z
        if axis == 'x':
            self.Dir = (length,0,0)
            # rotation on Y
            rot = FreeCAD.Rotation(VY,90)
            if cx == True:
                xpos = - self.length / 2.0
            else:
                xpos = 0
            if cy == True:
                ypos = 0
            else:
                ypos = self.ALU_Wh  # half of the aluminum profile width
            if cz == True:
                zpos = 0
            else:
                zpos = self.ALU_Wh
        elif axis == 'y':
            self.Dir = (0,length,0)
            # rotation on X
            rot = FreeCAD.Rotation(VX,-90)
            if cx == True:
                xpos = 0
            else:
                xpos = self.ALU_Wh
            if cy == True:
                ypos = - self.length / 2.0
            else:
                ypos = 0
            if cz == True:
                zpos = 0
            else:
                zpos = self.ALU_Wh
        elif axis == 'z':
            self.Dir = (0,0,length)
            # no rotation
            rot = FreeCAD.Rotation(VZ,0)
            if cx == True:
                xpos = 0
            else:
                xpos = self.ALU_Wh
            if cy == True:
                ypos = 0
            else:
                ypos = self.ALU_Wh
            if cz == True:
                zpos = - self.length / 2.0
            else:
                zpos = 0
        else:
            logging.debug ("wrong argument")
              
        self.Sk.Placement.Rotation = rot
        self.Sk.Placement.Base = FreeCAD.Vector(xpos,ypos,zpos)

        alu_extr = doc.addObject("Part::Extrusion", name)
        alu_extr.Base = self.Sk
        alu_extr.Dir = self.Dir
        alu_extr.Solid = True

        self.CadObj = alu_extr


# ---------- class LinBearing ----------------------------------------
# Creates a cylinder with a thru-hole object
# it also creates a copy of the cylinder without the hole, but a little
# bit larger, to be used to cut other shapes where this cylinder will be
# This will be useful for linear bearing/bushings container
#     r_ext: external radius,
#     r_int: internal radius,
#     h: height 
#     name 
#     axis: 'x', 'y' or 'z'
#           'x' will along the x axis
#           'y' will along the y axis
#           'z' will be vertical
#     h_disp: displacement on the height. 
#             if 0, the base of the cylinder will be on the plane
#             if -h/2: the plane will be cutting h/2
#     r_tol : What to add to r_ext for the container cylinder
#     h_tol : What to add to h for the container cylinder, half on each side

# base_place: position of the 3 elements: All of them have the same base
#             position.
#             It is (0,0,0) when initialized, it has to be changed using the
#             function base_place

class LinBearing (object):

    def __init__ (self, r_ext, r_int, h, name, axis = 'z', h_disp = 0,
                  r_tol = 0, h_tol = 0):

        self.base_place = (0,0,0)
        self.r_ext  = r_ext
        self.r_int  = r_int
        self.h      = h
        self.name   = name
        self.axis   = axis
        self.h_disp = h_disp
        self.r_tol  = r_tol
        self.h_tol  = h_tol

        bearing = fcfun.addCylHole (r_ext = r_ext,
                              r_int = r_int,
                              h= h,
                              name = name,
                              axis = axis,
                              h_disp = h_disp)
        self.bearing = bearing

        bearing_cont = fcfun.addCyl_pos (r = r_ext + r_tol,
                                         h= h + h_tol,
                                         name = name + "_cont",
                                         axis = axis,
                                         h_disp = h_disp - h_tol/2.0)
        # Hide the container
        self.bearing_cont = bearing_cont
        if bearing_cont.ViewObject != None:
            bearing_cont.ViewObject.Visibility=False


    # Move the bearing and its container
    def BasePlace (self, position = (0,0,0)):
        self.base_place = position
        self.bearing.Placement.Base = FreeCAD.Vector(position)
        self.bearing_cont.Placement.Base = FreeCAD.Vector(position)


# ---------- class LinBearingClone ----------------------------------------
# Creates an object that is like LinBearing, but it has clones of it
# instead of original Cylinders
# h_bearing: is a LinBearing object. It has the h to indicate that it is
#            a handler, not a FreeCAD object. To get to the FreeCad object
#            take the attributes: bearing and bearing_cont (container)
# name     : name of the objects, depending on namadd, it will add it
#            to the original or not
# namadd   : 1: add to the original name
#            0: creates a new name

class LinBearingClone (LinBearing):

    def __init__ (self, h_bearing, name, namadd = 1):
        self.base_place = h_bearing.base_place
        self.r_ext      = h_bearing.r_ext
        self.r_int      = h_bearing.r_int
        self.h          = h_bearing.h
        if namadd == 1:
            self.name       = h_bearing.name + "_" + name
        else:
            self.name       = h_bearing.name
        self.axis       = h_bearing.axis
        self.h_disp     = h_bearing.h_disp
        self.r_tol      = h_bearing.r_tol
        self.h_tol      = h_bearing.h_tol

        bearing_clone = Draft.clone(h_bearing.bearing)
        bearing_clone.Label = self.name
        self.bearing = bearing_clone

        bearing_cont_clone = Draft.clone(h_bearing.bearing_cont)
        bearing_cont_clone.Label = self.name + "_cont"
        self.bearing_cont = bearing_cont_clone
        if bearing_cont_clone.ViewObject != None:
            bearing_cont_clone.ViewObject.Visibility=False
    

# ---------- class T8NutHousing ----------------------
# Housing for a T8 Nut of a leadscrew

class T8NutHousing (object):

    Length = kcomp.T8NH_L
    Width  = kcomp.T8NH_W
    Height = kcomp.T8NH_H

    # separation between the screws that attach to the moving part
    ScrewLenSep  = kcomp.T8NH_ScrLSep
    ScrewWidSep  = kcomp.T8NH_ScrWSep

    # separation between the screws to the en
    ScrewLen2end = (Length - ScrewLenSep)/2
    ScrewWid2end = (Width  - ScrewWidSep)/2

    # Screw dimensions, that attach to the moving part: M4 x 7
    ScrewD = kcomp.T8NH_ScrD
    ScrewR = ScrewD / 2.0
    ScrewL = kcomp.T8NH_ScrL + kcomp.TOL

    # Hole for the nut and the screw
    ShaftD = kcomp.T8N_D_SHAFT_EXT + kcomp.TOL # I don't know the tolerances
    ShaftR = ShaftD / 2.0
    FlangeD = kcomp.T8N_D_FLAN + kcomp.TOL # I don't know the tolerances
    FlangeR = FlangeD / 2.0
    FlangeL = kcomp.T8N_FLAN_L + kcomp.TOL
    FlangeScrewD = kcomp.T8NH_FlanScrD
    FlangeScrewR = FlangeScrewD / 2.0
    FlangeScrewL = kcomp.T8NH_FlanScrL + kcomp.TOL
    # Diameter where the Flange Screws are located
    FlangeScrewPosD = kcomp.T8N_D_SCREW_POS
  
    def __init__ (self, name, nutaxis = 'x', screwface_axis = 'z',
                  cx = 1, cy= 1, cz = 0):
        doc = FreeCAD.ActiveDocument
        #housing_box = addBox (self.Length, self.Width, self.Height,
        #                      name= name + "_box")
        housing_box = fcfun.addBox_cen (self.Length, self.Width, self.Height,
                                  name= name + "_box", 
                                  cx=True, cy=True, cz=True)

        hole_list = []

        leadscr_hole = addCyl_pos (r=self.ShaftR, h= self.Length + 1,
                                   name = "leadscr_hole",
                                   axis = 'x', h_disp = -self.Length/2.0-1)
        #leadscr_hole.Placement.Base = FreeCAD.Vector (0,
                                                      #self.Width/2.0,
                                                      #self.Height/2.0)
        hole_list.append(leadscr_hole)
        nutflange_hole = addCyl_pos (r=self.FlangeR, h= self.FlangeL + 1,
                                   name = "nutflange_hole",
                                   axis = 'x',
                                   h_disp = self.Length/2.0 - self.FlangeL)
        #nutflange_hole.Placement.Base = FreeCAD.Vector (0,
        #                                              self.Width/2.0,
        #                                              self.Height/2.0)
        hole_list.append(nutflange_hole)
        # screws to attach the nut flange to the housing
        # M3 x 10
        screwflange_l = addCyl_pos (r = self.FlangeScrewR,
                                    h = self.FlangeScrewL + 1,
                                    name = "screwflange_l",
                                    axis = 'x',
                                    h_disp =   self.Length/2.0
                                             - self.FlangeL
                                             - self.FlangeScrewL)
        screwflange_l.Placement.Base = FreeCAD.Vector(0,
                                    - self.FlangeScrewPosD / 2.0,
                                   )
        hole_list.append(screwflange_l)
        screwflange_r = addCyl_pos (r = self.FlangeScrewR,
                                    h = self.FlangeScrewL + 1,
                                    name = "screwflange_r",
                                    axis = 'x',
                                    h_disp =   self.Length/2.0
                                             - self.FlangeL
                                             - self.FlangeScrewL)
        screwflange_r.Placement.Base = FreeCAD.Vector (0,
                                   self.FlangeScrewPosD / 2.0,
                                   0)
        hole_list.append(screwflange_r)


        # screws to attach the housing to the moving part
        # M4x7
        screwface_1 = fcfun.addCyl_pos (r = self.ScrewR, h = self.ScrewL + 1,
                                        name="screwface_1",
                                        axis = 'z',
                                        h_disp = -self.Height/2 -1)
        screwface_1.Placement.Base = FreeCAD.Vector (
                                    - self.Length/2.0 + self.ScrewLen2end,
                                    - self.Width/2.0 + self.ScrewWid2end,
                                      0)
        hole_list.append (screwface_1)
        screwface_2 = fcfun.addCyl_pos (r = self.ScrewR, h = self.ScrewL + 1,
                                        name="screwface_2",
                                        axis = 'z',
                                        h_disp = -self.Height/2 -1)
        screwface_2.Placement.Base = FreeCAD.Vector(
                                      self.ScrewLenSep /2.0,
                                    - self.Width/2.0 + self.ScrewWid2end,
                                      0)
        hole_list.append (screwface_2)
        screwface_3 = fcfun.addCyl_pos (r = self.ScrewR, h = self.ScrewL + 1,
                                        name="screwface_3",
                                        axis = 'z',
                                        h_disp = -self.Height/2 -1)
        screwface_3.Placement.Base = FreeCAD.Vector (
                                    - self.Length/2.0 + self.ScrewLen2end,
                                      self.ScrewWidSep /2.0,
                                      0)
        hole_list.append (screwface_3)
        screwface_4 = fcfun.addCyl_pos (r = self.ScrewR, h = self.ScrewL + 1,
                                        name="screwface_4",
                                        axis = 'z',
                                        h_disp = -self.Height/2 -1)
        screwface_4.Placement.Base = FreeCAD.Vector(
                                      self.ScrewLenSep /2.0,
                                      self.ScrewWidSep /2.0,
                                      0)
        hole_list.append (screwface_4)
        nuthouseholes = doc.addObject ("Part::MultiFuse", "nuthouse_holes")
        nuthouseholes.Shapes = hole_list
       
        # rotation calculation
        if nutaxis == 'x':
           yaw = 0
           pitch = 0
           if screwface_axis == 'y':
               roll  = 90
           elif screwface_axis == '-y':
               roll  = -90
           elif screwface_axis == 'z':
               roll  = 180
           elif screwface_axis == '-z':
               roll  = 0
           else:
               print "error 1 in yaw-pitch-roll"
        elif nutaxis == '-x':
           yaw = 180
           pitch = 0
           if screwface_axis == 'y':
               roll  = -90 #negative because of the yaw
           elif screwface_axis == '-y':
               roll  = 90 # positive because of the yaw = 180
           elif screwface_axis == 'z':
               roll = 180
           elif screwface_axis == '-z':
               roll  = 0
           else:
               print "error 2 in yaw-pitch-roll"
        elif nutaxis == 'y':
           yaw = 90
           pitch = 0
           if screwface_axis == 'x':
               roll  = -90
           elif screwface_axis == '-x':
               roll  = 90
           elif screwface_axis == 'z':
               roll  = 180
           elif screwface_axis == '-z':
               roll  = 0
           else:
               print "error 3 in yaw-pitch-roll"
        elif nutaxis == '-y':
           yaw = -90
           pitch = 0
           if screwface_axis == 'x':
               roll  = 90 
           elif screwface_axis == '-x':
               roll  = -90 
           elif screwface_axis == 'z':
               roll  = 180
           elif screwface_axis == '-z':
               roll  = 0
           else:
               print "error 4 in yaw-pitch-roll"
        elif nutaxis == 'z':
           pitch = -90
           yaw = 0
           if screwface_axis == 'x':
               roll  = 0 
           elif screwface_axis == '-x':
               roll  = 180 
           elif screwface_axis == 'y':
               roll  = 90
           elif screwface_axis == '-y':
               roll  = -90
           else:
               print "error 5 in yaw-pitch-roll"
        elif nutaxis == '-z':
           pitch = 90
           yaw = 0
           if screwface_axis == 'x':
               roll  = 180 
           elif screwface_axis == '-x':
               roll  = 0 
           elif screwface_axis == 'y':
               roll  = 90
           elif screwface_axis == '-y':
               roll  = -90
           else:
               print "error 6 in yaw-pitch-roll"
           
        housing_box.Placement.Rotation = FreeCAD.Rotation(yaw,pitch,roll)
        nuthouseholes.Placement.Rotation = FreeCAD.Rotation(yaw,pitch,roll)

        if nutaxis == 'x' or nutaxis == '-x':
            if screwface_axis == '-z' or screwface_axis == 'z':
                if cx == False:
                    housing_box.Placement.Base.x = self.Length / 2.0
                    nuthouseholes.Placement.Base.x = self.Length / 2.0
                if cy == False:
                    housing_box.Placement.Base.y = self.Width / 2.0
                    nuthouseholes.Placement.Base.y  = self.Width / 2.0
                if cz == False:
                    housing_box.Placement.Base.z = self.Height / 2.0
                    nuthouseholes.Placement.Base.z  = self.Height / 2.0
            if screwface_axis == '-y' or screwface_axis == 'y':
                if cx == False:
                    housing_box.Placement.Base.x = self.Length / 2.0
                    nuthouseholes.Placement.Base.x = self.Length / 2.0
                if cy == False:
                    housing_box.Placement.Base.y = self.Height / 2.0
                    nuthouseholes.Placement.Base.y  = self.Height / 2.0
                if cz == False:
                    housing_box.Placement.Base.z = self.Width / 2.0
                    nuthouseholes.Placement.Base.z  = self.Width / 2.0
        elif nutaxis == 'y':
            if screwface_axis == '-x' or screwface_axis == 'x':
                if cx == False:
                    housing_box.Placement.Base.x = self.Height / 2.0
                    nuthouseholes.Placement.Base.x = self.Height / 2.0
                if cy == False:
                    housing_box.Placement.Base.y = self.Length / 2.0
                    nuthouseholes.Placement.Base.y  = self.Length / 2.0
                if cz == False:
                    housing_box.Placement.Base.z = self.Width / 2.0
                    nuthouseholes.Placement.Base.z  = self.Width / 2.0
            if screwface_axis == '-z' or screwface_axis == 'z':
                if cx == False:
                    housing_box.Placement.Base.x = self.Width / 2.0
                    nuthouseholes.Placement.Base.x = self.Width / 2.0
                if cy == False:
                    housing_box.Placement.Base.y = self.Length / 2.0
                    nuthouseholes.Placement.Base.y  = self.Length / 2.0
                if cz == False:
                    housing_box.Placement.Base.z = self.Height / 2.0
                    nuthouseholes.Placement.Base.z  = self.Height / 2.0
        elif nutaxis == 'z':
            if screwface_axis == '-x' or screwface_axis == 'x':
                if cx == False:
                    housing_box.Placement.Base.x = self.Height / 2.0
                    nuthouseholes.Placement.Base.x = self.Height / 2.0
                if cy == False:
                    housing_box.Placement.Base.y = self.Width / 2.0
                    nuthouseholes.Placement.Base.y  = self.Width / 2.0
                if cz == False:
                    housing_box.Placement.Base.z = self.Length / 2.0
                    nuthouseholes.Placement.Base.z  = self.Length / 2.0
            if screwface_axis == '-y' or screwface_axis == 'y':
                if cx == False:
                    housing_box.Placement.Base.x = self.Width / 2.0
                    nuthouseholes.Placement.Base.x = self.Width / 2.0
                if cy == False:
                    housing_box.Placement.Base.y = self.Height / 2.0
                    nuthouseholes.Placement.Base.y  = self.Height / 2.0
                if cz == False:
                    housing_box.Placement.Base.z = self.Length / 2.0
                    nuthouseholes.Placement.Base.z  = self.Length / 2.0
                

               
        

        t8nuthouse = doc.addObject ("Part::Cut", "t8nuthouse")
        t8nuthouse.Base = housing_box
        t8nuthouse.Tool = nuthouseholes

        self.CadObj = t8nuthouse

        doc.recompute()

doc = FreeCAD.newDocument()

T8 = T8NutHousing (name="T8NutHousing", nutaxis='z', screwface_axis ='-x', cx=0, cy = 1, cz=0)

T8moved = T8NutHousing (name="T8NutHousing_desp", nutaxis='x', screwface_axis ='-z', cx=1, cy = 1, cz=1)

T8moved.CadObj.Placement.Base = fcfun.calc_desp_nocen (
                                            Length = T8moved.Length,
                                            Width = T8moved.Width,
                                            Height = T8moved.Height,
                                            vec1 = (0,0,1),
                                            vec2 = (-1,0,0),
                                            cx=0, cy = 1, cz=0)

T8moved.CadObj.Placement.Rotation = fcfun.calc_rotation (
                                            vec1 = (0,0,1),
                                            vec2 = (-1,0,0))
