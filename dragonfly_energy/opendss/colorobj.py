"""Module for coloring OpenDSS geometry with attributes."""
from ladybug_geometry.geometry2d import Point2D
from ladybug_geometry.geometry3d import Point3D
from honeybee.colorobj import _ColorObject

from .network import ElectricalNetwork


class ColorElectricalNetwork(_ColorObject):
    """Object for visualizing ElectricalNetwork attributes.

    Args:
        network: An ElectricalNetwork object, which will be colored with the attribute.
        attr_name: A text string of an attribute that the input network equipment has.
            This can have '.' that separate the nested attributes from one another.
            For example, 'properties.kva' for the kva rating of transformers.
        legend_parameters: An optional LegendParameter object to change the display
            of the results (Default: None).

    Properties:
        * network
        * attr_name
        * legend_parameters
        * attr_name_end
        * attributes
        * attributes_unique
        * attributes_original
        * geometries
        * graphic_container
        * min_point
        * max_point
    """
    __slots__ = ('_network', '_geometries')

    def __init__(self, network, attr_name, legend_parameters=None):
        """Initialize ColorElectricalNetwork."""
        assert isinstance(network, ElectricalNetwork), 'Expected ElectricalNetwork for' \
            ' ColorElectricalNetwork. Got {}.'.format(type(network))
        self._network = network
        all_obj = (network.substation,) + network.transformers + network.connectors
        self._geometries = tuple(obj.geometry for obj in all_obj)
        self._calculate_min_max(all_obj)

        # assign the legend parameters of this object
        self.legend_parameters = legend_parameters

        # get the attributes of the input equipment
        self._process_attribute_name(attr_name)
        self._process_attributes(all_obj)

    @property
    def network(self):
        """Get the ElectricalNetwork associated with this object."""
        return self._network

    @property
    def geometries(self):
        """A tuple of Polygon2D, Polyline2D and LineSegment2D aligned with attributes.
        """
        return self._geometries

    @property
    def min_point(self):
        """Get a Point3D for the minimum of the box around the objects."""
        return Point3D(self._min_point.x, self._min_point.y, 0)

    @property
    def max_point(self):
        """Get a Point3D for the maximum of the box around the objects."""
        return Point3D(self._max_point.x, self._max_point.y, 0)

    def _calculate_min_max(self, hb_objs):
        """Calculate maximum and minimum Point3D for a set of objects."""
        st_rm_min, st_rm_max = hb_objs[0].geometry.min, hb_objs[0].geometry.max
        min_pt = [st_rm_min.x, st_rm_min.y]
        max_pt = [st_rm_max.x, st_rm_max.y]

        for obj in hb_objs[1:]:
            rm_min, rm_max = obj.geometry.min, obj.geometry.max
            if rm_min.x < min_pt[0]:
                min_pt[0] = rm_min.x
            if rm_min.y < min_pt[1]:
                min_pt[1] = rm_min.y
            if rm_max.x > max_pt[0]:
                max_pt[0] = rm_max.x
            if rm_max.y > max_pt[1]:
                max_pt[1] = rm_max.y

        self._min_point = Point2D(min_pt[0], min_pt[1])
        self._max_point = Point2D(max_pt[0], max_pt[1])

    def __repr__(self):
        """Color ElectricalNetwork representation."""
        return 'Color ElectricalNetwork: {} [{}]'.format(
            self.network.display_name, self.attr_name_end)
