##Copyright 2017 Thomas Paviot (tpaviot@gmail.com)
##
##This file is part of pythonOCC.
##
##pythonOCC is free software: you can redistribute it and/or modify
##it under the terms of the GNU Lesser General Public License as published by
##the Free Software Foundation, either version 3 of the License, or
##(at your option) any later version.
##
##pythonOCC is distributed in the hope that it will be useful,
##but WITHOUT ANY WARRANTY; without even the implied warranty of
##MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##GNU Lesser General Public License for more details.
##
##You should have received a copy of the GNU Lesser General Public License
##along with pythonOCC.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, absolute_import

import sys
import enum
import uuid
import operator

try:
    from functools import reduce
except: pass

try:
    from pythreejs import *
    # this renderer currently targets pythreejs version number 1.0.x
    assert version_info[0] == 1 and version_info[1] == 0
    from IPython.display import display
    import numpy as np
except ImportError:
    print("Error You must install pythreejs/ipywidegets/numpy to run the jupyter notebook renderer")
    sys.exit(0)

from OCC.Bnd import Bnd_Box
from OCC.BRepBndLib import brepbndlib_Add
from OCC.Visualization import Tesselator

# default values

def format_color(r, g, b):
    return '#%02x%02x%02x' % (r, g, b)

default_shape_color = format_color(166, 166, 166)
default_edge_color = format_color(0, 0, 0)


class bounding_box(object):
    """ Representation of the bounding box of the TopoDS_Shape `shape`
    Constructor Parameters
    ----------
    shape : TopoDS_Shape or a subclass such as TopoDS_Face
        the shape to compute the bounding box from
    tol: float
        tolerance of the computed boundingbox
    """

    def __init__(self, shape_or_values, tol=1.e-5):
        if isinstance(shape_or_values, tuple):
            self.values = shape_or_values
        else:
            bbox = Bnd_Box()
            bbox.SetGap(tol)
            brepbndlib_Add(shape_or_values, bbox, True)  # use the shape triangulation
            self.values = bbox.Get()

    def __getattr__(self, k):
        attrs_0 = "x_min", "y_min", "z_min", "x_max", "y_max", "z_max"
        if k in attrs_0:
            return self.values[attrs_0.index(k)]

        idx = "xyz".index(k.split('_')[0])

        attrs_1 = "x_size", "y_size", "z_size"
        if k in attrs_1:
            return self.values[idx + 3] - self.values[idx]

        attrs_2 = "x_center", "y_center", "z_center"
        if k in attrs_2:
            return (self.values[idx] + self.values[idx + 3]) / 2.

        raise AttributeError("bounding_box has no attribute " + k)

    def __add__(self, other):
        a, b = self.values, other.values
        mi = tuple(map(min, a[0:3], b[0:3]))
        ma = tuple(map(max, a[3:6], b[3:6]))
        return bounding_box(mi + ma)


class NORMAL(enum.Enum):
    SERVER_SIDE = 1
    CLIENT_SIDE = 2


class JupyterRenderer(object):
    def __init__(self, size=(480, 480), compute_normals_mode=NORMAL.SERVER_SIDE):
        """ Creates a jupyter renderer.
        size: a tuple (width, height). Must be a square, or shapes will look like deformed
        compute_normals_mode: optional, set to SERVER_SIDE by default. This flag lets you choose the
                              way normals are computed. If SERVER_SIDE is selected (default value), then normals
                              will be computed by the Tesselator, packed as a python tuple, and send as a json structure
                              to the client. If, on the other hand, CLIENT_SIDE is chose, then the computer only compute vertex
                              indices, and let the normals be computed by the client (the web js machine embedded in the webrowser).
                              In a few words:
                              SERVER_SIDE: higher server load, loading time increased, lower client load. Poor performance client will
                              choose this option (mobile terminals for instance)
                              CLIENT_SIDE: lower server load, loading time decreased, higher client load. Higher performance clients will
                              choose this option (laptops, desktop machines).
        """
        self._background = 'white'
        self._background_opacity = 1
        self._size = size
        self._compute_normals_mode = compute_normals_mode

        # the default camera object
        self._camera = None

        # the collection of displayed shapes, empty by default
        self._shapes = []

        # a collection for Mesh objects
        self._meshes = []

        # a collection for edges
        self._edges = []

        # we save the renderer so that is can be accessed
        self._renderer = None

    def _update_camera(self):
        bb = reduce(operator.add, map(bounding_box, self._shapes))

        self._camera = PerspectiveCamera(position=[0, bb.y_center - 3 * bb.y_size, bb.z_center + 3 * bb.z_center],
                                         lookAt=[bb.x_center, bb.y_center, bb.z_center],
                                         up=[0, 0, 1],
                                         fov=50,
                                         children=[DirectionalLight(color='#ffffff', position=[50, 50, 50], intensity=0.5)])


    def DisplayShape(self,
                     shp,  # the TopoDS_Shape to be displayed
                     shape_color=default_shape_color,  # the default
                     render_edges=False,
                     edge_color=default_edge_color,
                     compute_uv_coords=False,
                     quality=1.0,
                     update=False):
        """ Displays a topods_shape in the renderer instance.
        shp: the TopoDS_Shape to render
        shape_color: the shape color, in html corm, eg '#abe000'
        render_edges: optional, False by default. If True, compute and dislay all
                      edges as a linear interpolation of segments.
        edge_color: optional, black by default. The color used for edge rendering,
                    in html form eg '#ff00ee'
        compute_uv_coords: optional, false by default. If True, compute texture
                           coordinates (required if the shape has to be textured)
        quality: optional, 1.0 by default. If set to something lower than 1.0,
                      mesh will be more precise. If set to something higher than 1.0,
                      mesh will be less precise, i.e. lower numer of triangles.
        update: optional, False by default. If True, render all the shapes.
        """
        # adds the shape to the collection of displayed_shapes
        self._shapes.append(shp)

        # first, compute the tesselation
        tess = Tesselator(shp)
        tess.Compute(uv_coords=compute_uv_coords, compute_edges=render_edges, mesh_quality=quality)

        # get vertices and normals
        vertices_position = tess.GetVerticesPositionAsTuple()

        number_of_triangles = tess.ObjGetTriangleCount()
        number_of_vertices = len(vertices_position)

        # number of vertices should be a multiple of 3
        assert number_of_vertices % 3 == 0
        assert number_of_triangles * 9 == number_of_vertices

        # then we build the vertex and faces collections as numpy ndarrays
        np_vertices = np.array(vertices_position, dtype='float32').reshape(int(number_of_vertices / 3), 3)
        # Note: np_faces is just [0, 1, 2, 3, 4, 5, ...], thus arange is used
        np_faces = np.arange(np_vertices.shape[0], dtype='uint32')

        # set geometry properties
        buffer_geometry_properties = {'position': BufferAttribute(np_vertices),
                                      'index'   : BufferAttribute(np_faces)}
        if self._compute_normals_mode == NORMAL.SERVER_SIDE:
            # get the normal list, converts to a numpy ndarray. This should not raise
            # any issue, since normals have been computed by the server, and are available
            # as a list of floats
            np_normals = np.array(tess.GetNormalsAsTuple(), dtype='float32').reshape(-1, 3)
            # quick check
            assert np_normals.shape == np_vertices.shape
            buffer_geometry_properties['normal'] = BufferAttribute(np_normals)

        # build a BufferGeometry instance
        shape_geometry = BufferGeometry(attributes=buffer_geometry_properties)

        # if the client has to render normals, add the related js instructions
        if self._compute_normals_mode == NORMAL.CLIENT_SIDE:
            shape_geometry.exec_three_obj_method('computeVertexNormals')

        # then a default material
        shp_material = MeshPhongMaterial(color=shape_color,
                                         polygonOffset=True,
                                         polygonOffsetFactor=1,
                                         polygonOffsetUnits=1,
                                         shininess=0.9)

        # create a mesh unique id
        mesh_id = uuid.uuid4().hex

        # finally create the mash
        shape_mesh = Mesh(geometry=shape_geometry,
                          material=shp_material,
                          id=mesh_id)

        # adds this mesh to the list of meshes
        self._meshes.append(shape_mesh)

        # create a link between the mesh and the shape
        # TODO
        # create a camera

        # edge rendering, if set to True
        edge_lines = None
        if render_edges:
            edges = list(map(lambda i_edge: [tess.GetEdgeVertex(i_edge, i_vert) for i_vert in range(tess.ObjEdgeGetVertexCount(i_edge))], range(tess.ObjGetEdgeCount())))
            edges = list(filter(lambda edge: len(edge) == 2, edges))
            np_edge_vertices = np.array(edges, dtype=np.float32).reshape(-1, 3)
            np_edge_indices = np.arange(np_edge_vertices.shape[0], dtype=np.uint32)
            edge_geometry = BufferGeometry(attributes={
                'position': BufferAttribute(np_edge_vertices),
                'index'   : BufferAttribute(np_edge_indices)
            })
            edge_material = LineBasicMaterial(color=edge_color, linewidth=2)
            edge_lines = LineSegments(geometry=edge_geometry, material=edge_material)
            self._edges.append(edge_lines)

        if update:
            self.Display()

    def EraseAll(self):
        self._meshes = []
        self._edges = []
        self._renderer.scene = Scene(children=[])

    def Display(self):
        # start rendering
        #scene_children = [shape_mesh, edge_lines, self._camera, AmbientLight(color='#101010')]
        # build the children list:
        self._update_camera()
        scene_children = []
        for mesh in self._meshes:
            scene_children.append(mesh)
        for edge in self._edges:
            scene_children.append(edge)
        scene_children.append(self._camera)
        scene_children.append(AmbientLight(color='#101010'))
        scene_shp = Scene(children=scene_children)

        self._renderer = Renderer(camera=self._camera,
                                  background=self._background,
                                  background_opacity=self._background_opacity,
                                  scene=scene_shp,
                                  controls=[OrbitControls(controlling=self._camera)],
                                  width=self._size[0],
                                  height=self._size[1],
                                  antialias=True)
        display(self._renderer)


if __name__ == "__main__":
    from OCC.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeTorus
    my_ren = JupyterRenderer()
    box_s = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
    my_ren.DisplayShape(box_s)
