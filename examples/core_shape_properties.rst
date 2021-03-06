core_shape_properties.py
========================

Abstract
^^^^^^^^

No available documentation script.


------

Launch the example
^^^^^^^^^^^^^^^^^^

  $ python core_shape_properties.py

------


Code
^^^^


.. code-block:: python

  ##along with pythonOCC.  If not, see <http://www.gnu.org/licenses/>.
  
  from OCC.BRepPrimAPI import BRepPrimAPI_MakeBox
  from OCC.GProp import GProp_GProps
  from OCC.BRepGProp import brepgprop_VolumeProperties, brepgprop_SurfaceProperties
  
  from core_topology_traverse import Topo
  
  def cube_inertia_properties():
      """ Compute the inertia properties of a shape
      """
      # Create and display cube
      print("Creating a cubic box shape (50*50*50)")
      cube_shape = BRepPrimAPI_MakeBox(50., 50., 50.).Shape()
      # Compute inertia properties
      props = GProp_GProps()
      brepgprop_VolumeProperties(cube_shape, props)
      # Get inertia properties
      mass = props.Mass()
      cog = props.CentreOfMass()
      matrix_of_inertia = props.MatrixOfInertia()
      # Display inertia properties
      print("Cube mass = %s" % mass)
      cog_x, cog_y, cog_z = cog.Coord()
      print("Center of mass: x = %f;y = %f;z = %f;" % (cog_x, cog_y, cog_z))
  
  
  def shape_faces_surface():
      """ Compute the surface of each face of a shape
      """
      # first create the shape
      the_shape = BRepPrimAPI_MakeBox(50., 30., 10.).Shape()
      # then loop over faces
      t = Topo(the_shape)
      props = GProp_GProps()
      shp_idx = 1
      for face in t.faces():
          brepgprop_SurfaceProperties(face, props)
          face_surf = props.Mass()
          print("Surface for face nbr %i : %f" % (shp_idx, face_surf))
          shp_idx += 1
  
  if __name__ == '__main__':
      cube_inertia_properties()
      shape_faces_surface()

Screenshots
^^^^^^^^^^^


No available screenshot.
