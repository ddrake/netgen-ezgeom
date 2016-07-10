""" Module ezgeom
    This module provides a simplified interface to netgen for simple geometric
    regions such as rectangles and discs.
    In particular, for rectangles, it tries to eliminate duplicate points
    and remove overlapping line segments

    Sample Usage:
        from ezgeom import *
        ezg = EzGeom()
        ezg.add_rect((-2.0,-0.35),(2.0,2.0),10,1,[2,0,0,0])
        ezg.add_circle((0,0),0.25,1,0,1)
        ezg.add_rect((-2.0,-2.0),(2.0,-0.35),10,2,[0,0,1,0])
        ezg.add_rect((-0.5,-0.6),(0.5,-0.5),2,0,2)
        ezg.make_geometry()
        mesh = ezg.make_mesh()
 """

from ngsolve import *
from netgen.geom2d import SplineGeometry

class EzGeom:
    """ EzGeom -- a class designed to simplify the generation of netgen meshes containing
    multiple simple objects (i.e. rectangles and circles).
    """
    def __init__(self):
        self.rectangles = []
        self.circles = []
        self.geom = SplineGeometry()

    def add_rect(self, blpt, trpt, bnd, din, dout):
        """ Add a rectangle to the geometry
        This method can be used to add rectangluar domains which may be adjacent to other domains
        in this case, the outer domain parameter "dout" should be a list of four elements.
        Its first element should corresponds to the outer domain below its bottom edge.
        The remaining elemnts should correspond to the other sides proceeding
        counter-clockwise.  
        If the rectangle represents a punch which doesn't touch another boundary, 
        "dout" can be just a number
        """
        self.rectangles.append(rectangle(blpt, trpt, bnd, din, dout))
        return self

    def add_circle(self, cenpt, r, bnd, din, dout):
        """ Add a circle to the geometry
        This makes it easy to add circular punches to domains.  The boundary is not checked for
        overlaps with any other regions
        """
        self.circles.append(circle(cenpt, r, bnd, din, dout))
        return self

    def make_geometry(self):
        """ Construct the netgen geometry based on the shapes added
        Duplicated points and lines are removed from rectangles
        """
        for i in range(len(self.rectangles)):
            self.rectangles[i].make_geometry(self.rectangles[:i], self.geom)
        for circ in self.circles:
            circ.make_geometry(self.geom)
    
    def make_mesh(self):
        """ Call netgen to generate the mesh
        """
        return Mesh(self.geom.GenerateMesh())

class rectangle:
    def __init__(self, blpt, trpt, bnd, din, dout):
        blX, blY = blpt
        trX, trY = trpt
        self.pts = [blpt, (trX,blY), trpt, (blX,trY)]
        self.segs = [(self.pts[i],self.pts[(i+1)%4]) for i in range(len(self.pts))]
        self.nums = []
        self.bnd = bnd
        self.din = din
        self.dout = dout
    
    def __str__(self):
        return str(self.pts)
    
    # Add this to the netgen geometry
    def make_geometry(self, others, geom):
        self.add_points(others, geom)
        self.add_segs(others, geom)

    # for each of our points, check each rectangle that has already been added to
    # the geometry to see if it contains our point.
    # if it has, get a reference to that rectangle and stop checking.
    # If we find a matching point, add its number to our list, otherwise append the point.
    def add_points(self, others, geom):
        for i in range(len(self.pts)):
            pt = self.pts[i]
            match = False
            for rect in others:
                if rect.has_pt(pt):
                    match = True
                    break
            if match:
                self.nums.append(rect.get_num(pt))
            else:
                self.nums.append(geom.AppendPoint(*pt))

    # Add the segments, ensuring that no duplicate lines are added to the geometry
    def add_segs(self, others, geom):
        for i in range(len(self.segs)):
            seg = self.segs[i]
            match = False
            for rect in others:
                if rect.has_seg(seg):
                    match = True
                    break
            if not match:
                p1, p2 = seg
                num1 = self.nums[self.pts.index(p1)]
                num2 = self.nums[self.pts.index(p2)]
                dout = self.dout[i] if type(self.dout) == list else self.dout
                geom.Append(["line",num1, num2], bc=self.bnd, leftdomain=self.din, rightdomain=dout)
                print("appended line: ", num1, num2, self.bnd, self.din, dout)

    # Get the netgen point number for a point in this rectangle
    def get_num(self, pt):
        idx = self.pts.index(pt)
        return self.nums[idx]

    # Check whether we contain the given point
    def has_pt(self, pt):
        return pt in self.pts

    # Check whether we contain the given segment
    # Currently we are only checking for an existing segment 
    # with exactly the same points but in the reverse order.
    def has_seg(self, seg):
        for (p1,p2) in self.segs:
            if (p2,p1) == seg:
                return True
        return False


# Currently we are not doing any checks for duplicated points or spline curves
class circle:
    def __init__(self, cenpt, r, bnd, din, dout):
        cenX, cenY = cenpt
        self.pts = [(cenX+r, cenY), (cenX+r, cenY+r), (cenX, cenY+r), (cenX-r, cenY+r),
                    (cenX-r, cenY), (cenX-r, cenY-r), (cenX, cenY-r), (cenX+r, cenY-r) ]
        self.nums = []
        self.bnd = bnd
        self.din = din
        self.dout = dout

    # Add this to the netgen geometry
    def make_geometry(self, geom):
        self.nums = [geom.AppendPoint(*p) for p in self.pts]
        for i in range(4):
            geom.Append(["spline3", self.nums[2*i], self.nums[2*i+1], self.nums[(2*i+2) % 8]], 
                    bc=self.bnd, leftdomain=self.din, rightdomain=self.dout)

