"""Module for coloring OpenDSS geometry with attributes."""
from ladybug_geometry.geometry2d import Point2D
from ladybug_geometry.geometry3d import Point3D
from ladybug.datacollection import HourlyContinuousCollection, \
    HourlyDiscontinuousCollection
from ladybug.graphic import GraphicContainer
from ladybug.legend import LegendParameters
from honeybee.typing import int_in_range
from honeybee.colorobj import _ColorObject

from .network import ElectricalNetwork


class ColorNetwork(_ColorObject):
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
        """Initialize ColorNetwork."""
        assert isinstance(network, ElectricalNetwork), 'Expected ElectricalNetwork for' \
            ' ColorNetwork. Got {}.'.format(type(network))
        self._network = network
        all_obj = (network.substation,) + network.transformers + network.connectors
        self._geometries = tuple(obj.geometry for obj in all_obj)
        self._min_point, self._max_point = _calculate_min_max(all_obj)

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

    def __repr__(self):
        """Color ElectricalNetwork representation."""
        return 'Color Network: {} [{}]'.format(
            self.network.display_name, self.attr_name_end)


class ColorNetworkResults(object):
    """Class for coloring ElectricalNetwork geometry with simulation results.

    Args:
        data_collections: An array of data collections of the same data type,
            which will be used to color the network with simulation results. Data
            collections should all have headers with metadata dictionaries with 'type'
            and 'name' keys. These keys will be used to match the data in the collections
            to the input electrical network.
        network: An ElectricalNetwork object, which will be colored with the attribute.
        legend_parameters: An optional LegendParameter object to change the display
            of the ColorNetworkResults (Default: None).
        attribute: Text to note the attribute of the data collections with which the
            network geometry should be colored. Typical values are max, min, average,
            median, or total. This input can also be an integer (greater than or equal
            to 0) to select a specific step of the data collections for which result
            values will be generated. (Default: "Max" to color with the peak value).

    Properties:
        * data_collections
        * network
        * legend_parameters
        * attribute
        * matched_geometries
        * matched_data
        * matched_values
        * graphic_container
        * title_text
        * data_type_text
        * data_type
        * unit
        * analysis_period
        * min_point
        * max_point
    """
    __slots__ = (
        '_data_collections', '_network', '_legend_parameters', '_attribute',
        '_matched_geometries', '_matched_data', '_matched_values',
        '_base_collection', '_base_type', '_base_unit', '_min_point', '_max_point')

    def __init__(self, data_collections, network,
                 legend_parameters=None, attribute='max'):
        """Initialize ColorNetworkResults."""
        # check the input collections
        accept_cols = (HourlyContinuousCollection, HourlyDiscontinuousCollection)
        try:
            data_collections = list(data_collections)
        except TypeError:
            raise TypeError('Input data_collections must be an array. Got {}.'.format(
                type(data_collections)))
        assert len(data_collections) > 0, \
            'ColorNetworkResults must have at least one data_collection.'
        for i, coll in enumerate(data_collections):
            assert isinstance(coll, accept_cols), 'Expected hourly ' \
                'data collection for ColorNetworkResults. Got {}.'.format(type(coll))
        self._base_collection = data_collections[0]
        self._base_type = self._base_collection.header.data_type
        self._base_unit = self._base_collection.header.unit
        for coll in data_collections[1:]:
            assert coll.header.unit == self._base_unit, \
                'ColorNetworkResults data_collections must all have matching units. ' \
                '{} != {}.'.format(coll.header.unit, self._base_unit)
            assert len(coll.values) == len(self._base_collection.values), \
                'ColorNetworkResults data_collections must be aligned with one another' \
                '.{} != {}'.format(len(coll.values), len(self._base_collection.values))
        self._data_collections = data_collections

        # process the input electrical network
        assert isinstance(network, ElectricalNetwork), 'Expected ElectricalNetwork for' \
            ' ColorNetworkResults. Got {}.'.format(type(network))
        self._network = network
        all_obj = (network.substation,) + network.transformers + network.connectors
        self._min_point, self._max_point = _calculate_min_max(all_obj)
        geo_dict = {obj.identifier.lower(): obj.geometry for obj in all_obj}
        self._matched_geometries, self._matched_data = [], []
        for dat in self._data_collections:
            try:
                self._matched_geometries.append(geo_dict[dat.header.metadata['name']])
                self._matched_data.append(dat)
            except KeyError:  # data could not be matched
                pass

        # assign the other properties of this object
        self.legend_parameters = legend_parameters
        self.attribute = attribute

    @property
    def data_collections(self):
        """Get a tuple of data collections assigned to this object."""
        return tuple(self._data_collections)

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
    def legend_parameters(self):
        """Get or set the legend parameters."""
        return self._legend_parameters

    @legend_parameters.setter
    def legend_parameters(self, value):
        if value is not None:
            assert isinstance(value, LegendParameters), \
                'Expected LegendParameters. Got {}.'.format(type(value))
            self._legend_parameters = value.duplicate()
        else:
            self._legend_parameters = LegendParameters()

    @property
    def attribute(self):
        """Get or set text for the data attribute or an integer a specific data step."""
        return self._attribute

    @attribute.setter
    def attribute(self, value):
        if not hasattr(self._base_collection, value):
            value = int_in_range(
                value, 0, len(self._base_collection) - 1, 'simulation step')
        self._attribute = value

    @property
    def matched_geometries(self):
        """Get a tuple of geometries that were matched with the data collections."""
        return tuple(self._matched_geometries)

    @property
    def matched_data(self):
        """Get a tuple of data collections aligned with the matched_geometries."""
        return tuple(self._matched_data)

    @property
    def matched_values(self):
        """Get an array of numbers that correspond to the matched_geometries.

        These values are derived from the data_collections but they will be
        averaged/totaled or for a specific time step depending on the
        other inputs to this object.
        """
        if isinstance(self.attribute, int):  # specific index from all collections
            return tuple(data[self._attribute] for data in self._matched_data)
        else:  # data collection property
            return tuple(getattr(data, self._attribute)
                         for data in self._matched_data)

    @property
    def graphic_container(self):
        """Get a ladybug GraphicContainer that relates to this object.

        The GraphicContainer possesses almost all things needed to visualize the
        object including the legend, value_colors, lower_title_location,
        upper_title_location, etc.
        """
        return GraphicContainer(
            self.matched_values, self.min_point, self.max_point,
            self.legend_parameters, self.data_type, str(self.unit))

    @property
    def title_text(self):
        """Text string for the title of the object."""
        d_type_text = self.data_type
        if isinstance(self.attribute, int):  # specific index from all collections
            time_text = self.time_interval_text(self.attribute)
        else:  # average or total the data
            time_text = str(self.analysis_period).split('@')[0]
            d_type_text = '{} {}'.format(self.attribute.capitalize(), d_type_text)
        return '{}\n{}'.format('{} ({})'.format(d_type_text, self.unit), time_text)

    @property
    def data_type(self):
        """Text for the data type."""
        return self._base_type

    @property
    def unit(self):
        """The unit of this object's data collections."""
        return self._base_unit

    @property
    def analysis_period(self):
        """The analysis_period of this object's data collections."""
        return self._base_collection.header.analysis_period

    @property
    def min_point(self):
        """Get a Point3D for the minimum of the box around the objects."""
        return Point3D(self._min_point.x, self._min_point.y, 0)

    @property
    def max_point(self):
        """Get a Point3D for the maximum of the box around the objects."""
        return Point3D(self._max_point.x, self._max_point.y, 0)

    def time_interval_text(self, simulation_step):
        """Get text for a specific time simulation_step of the data collections.

        Args:
            simulation_step: An integer for the step of simulation for which
                text should be generated.
        """
        return str(self._base_collection.datetimes[simulation_step])

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """Color Network representation."""
        return 'Color Network results: {} [{} results]'.format(
            self.network.display_name, len(self._data_collections))


def _calculate_min_max(net_objs):
    """Calculate maximum and minimum Point3D for a set of objects."""
    st_rm_min, st_rm_max = net_objs[0].geometry.min, net_objs[0].geometry.max
    min_pt = [st_rm_min.x, st_rm_min.y]
    max_pt = [st_rm_max.x, st_rm_max.y]

    for obj in net_objs[1:]:
        rm_min, rm_max = obj.geometry.min, obj.geometry.max
        if rm_min.x < min_pt[0]:
            min_pt[0] = rm_min.x
        if rm_min.y < min_pt[1]:
            min_pt[1] = rm_min.y
        if rm_max.x > max_pt[0]:
            max_pt[0] = rm_max.x
        if rm_max.y > max_pt[1]:
            max_pt[1] = rm_max.y

    return Point2D(min_pt[0], min_pt[1]), Point2D(max_pt[0], max_pt[1])
