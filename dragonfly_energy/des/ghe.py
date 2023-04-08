# coding=utf-8
"""Ground Heat Exchanger (GHE) in a district thermal system."""
from .._base import _GeometryBase

from ladybug_geometry.geometry2d.polygon import Polygon2D
from honeybee.typing import float_positive, float_in_range
from honeybee.altnumber import autocalculate
from dragonfly.projection import polygon_to_lon_lat


class GroundHeatExchanger(_GeometryBase):
    """Represents a Ground Heat Exchanger in a district thermal system.

    Args:
        identifier: Text string for a unique heat exchanger ID. Must contain only
            characters that are acceptable in OpenDSS. This will be used to
            identify the object across the exported geoJSON and OpenDSS files.
        geometry: A Polygon2D representing the geometry of the heat exchanger.

    Properties:
        * identifier
        * display_name
        * geometry
        * soil_parameters
        * pipe_parameters
        * borehole_parameters
    """
    __slots__ = ('_soil_parameters', '_pipe_parameters', '_borehole_parameters')

    def __init__(self, identifier, geometry, soil_parameters=None,
                 pipe_parameters=None, borehole_parameters=None):
        """Initialize GroundHeatExchanger."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, Polygon2D), 'Expected ladybug_geometry ' \
            'Polygon2D for GroundHeatExchanger geometry. Got {}'.format(type(geometry))
        self._geometry = geometry
        self.soil_parameters = soil_parameters
        self.pipe_parameters = pipe_parameters
        self.borehole_parameters = borehole_parameters

    @classmethod
    def from_dict(cls, data):
        """Initialize a GroundHeatExchanger from a dictionary.

        Args:
            data: A dictionary representation of an GroundHeatExchanger object.
        """
        # check the type of dictionary
        assert data['type'] == 'GroundHeatExchanger', 'Expected GroundHeatExchanger ' \
            'dictionary. Got {}.'.format(data['type'])
        geo = Polygon2D.from_dict(data['geometry'])
        soil = SoilParameter.from_dict(data['soil_parameters']) \
            if 'soil_parameters' in data else None
        pipe = PipeParameter.from_dict(data['pipe_parameters']) \
            if 'pipe_parameters' in data else None
        bore = BoreholeParameter.from_dict(data['borehole_parameters']) \
            if 'borehole_parameters' in data else None
        trans = cls(data['identifier'], geo, soil, pipe, bore)
        if 'display_name' in data and data['display_name'] is not None:
            trans.display_name = data['display_name']
        return trans

    @classmethod
    def from_geojson_dict(
            cls, data, origin_lon_lat, conversion_factors):
        """Get a GroundHeatExchanger from a dictionary as it appears in a GeoJSON.

        Args:
            data: A GeoJSON dictionary representation of an GroundHeatExchanger feature.
            origin_lon_lat: An array of two numbers in degrees. The first value
                represents the longitude of the scene origin in degrees (between -180
                and +180). The second value represents latitude of the scene origin
                in degrees (between -90 and +90). Note that the "scene origin" is the
                (0, 0) coordinate in the 2D space of the input polygon.
            conversion_factors: A tuple with two values used to translate between
                meters and longitude, latitude.
        """
        geo = cls._geojson_coordinates_to_polygon2d(
            data['geometry']['coordinates'], origin_lon_lat, conversion_factors)
        return cls(data['properties']['id'], geo)

    @property
    def geometry(self):
        """Get a Polygon2D representing the ground heat exchanger."""
        return self._geometry

    @property
    def soil_parameters(self):
        """Get or set a SoilParameters object for the heat exchanger field."""
        return self._soil_parameters

    @soil_parameters.setter
    def soil_parameters(self, value):
        if value is None:
            value = SoilParameter()
        assert isinstance(value, SoilParameter), \
            'Expected SoilParameter object' \
            ' for GroundHeatExchanger. Got {}.'.format(type(value))
        self._soil_parameters = value

    @property
    def pipe_parameters(self):
        """Get or set a PipeParameter object for the heat exchanger field."""
        return self._pipe_parameters

    @pipe_parameters.setter
    def pipe_parameters(self, value):
        if value is None:
            value = PipeParameter()
        assert isinstance(value, PipeParameter), \
            'Expected PipeParameter object' \
            ' for GroundHeatExchanger. Got {}.'.format(type(value))
        self._pipe_parameters = value

    @property
    def borehole_parameters(self):
        """Get or set a BoreholeParameter object for the heat exchanger field."""
        return self._borehole_parameters

    @borehole_parameters.setter
    def borehole_parameters(self, value):
        if value is None:
            value = BoreholeParameter()
        assert isinstance(value, BoreholeParameter), \
            'Expected BoreholeParameter object' \
            ' for GroundHeatExchanger. Got {}.'.format(type(value))
        self._borehole_parameters = value

    def to_dict(self):
        """GroundHeatExchanger dictionary representation."""
        base = {'type': 'GroundHeatExchanger'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
        base['soil_parameters'] = self.soil_parameters.to_dict()
        base['pipe_parameters'] = self.pipe_parameters.to_dict()
        base['borehole_parameters'] = self.borehole_parameters.to_dict()
        if self._display_name is not None:
            base['display_name'] = self.display_name
        return base

    def to_geojson_dict(self, origin_lon_lat, conversion_factors):
        """Get GroundHeatExchanger dictionary as it appears in an URBANopt geoJSON.

        Args:
            origin_lon_lat: An array of two numbers in degrees. The first value
                represents the longitude of the scene origin in degrees (between -180
                and +180). The second value represents latitude of the scene origin
                in degrees (between -90 and +90). Note that the "scene origin" is the
                (0, 0) coordinate in the 2D space of the input polygon.
            conversion_factors: A tuple with two values used to translate between
                meters and longitude, latitude.
        """
        pts = [(pt.x, pt.y) for pt in self.geometry.vertices]
        coords = [polygon_to_lon_lat(pts, origin_lon_lat, conversion_factors)]
        coords[0].append(coords[0][0])
        return {
            'type': 'Feature',
            'properties': {
                'id': self.identifier,
                'geometryType': 'Rectangle',
                'name': self.display_name,
                'type': 'District System',
                'footprint_area': round(self.geometry.area, 1),
                'footprint_perimeter': round(self.geometry.perimeter, 1),
                'floor_area': round(self.geometry.area, 1),
                'district_system_type': 'Ground Heat Exchanger',
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': coords
            }
        }

    def to_des_param_dict(self):
        """Get the GroundHeatExchanger as it appears in a System Parameter dictionary."""
        u_temp = self.soil_parameters.undisturbed_temperature \
            if self.soil_parameters._undisturbed_temperature is not None \
            else 'Autocalculate'
        return {
            'ghe_parameters': {
                'connectors': {  # not currently used
                    'pipe_diameter': 12,
                    'pipe_insulation_rvalue': 5,
                    'pipe_location': 'Tunnel'
                },
                'soil': {
                    'conductivity': self.soil_parameters.conductivity,
                    'rho_cp': self.soil_parameters.heat_capacity,
                    'undisturbed_temp': u_temp
                },
                'pipe': {
                    'inner_diameter': self.pipe_parameters.inner_diameter,
                    'outer_diameter': self.pipe_parameters.outer_diameter,
                    'shank_spacing': self.pipe_parameters.shank_spacing,
                    'roughness': self.pipe_parameters.roughness,
                    'conductivity': self.pipe_parameters.conductivity,
                    'rho_cp': self.pipe_parameters.heat_capacity
                },
                'borehole': {
                    'length': self.borehole_parameters.length,
                    'buried_depth': self.borehole_parameters.buried_depth,
                    'diameter': self.borehole_parameters.diameter
                }
            }
        }

    def __copy__(self):
        new_ghe = GroundHeatExchanger(
            self.identifier, self.geometry, self.soil_parameters.duplicate(),
            self.pipe_parameters.duplicate(), self.borehole_parameters.duplicate())
        new_ghe._display_name = self._display_name
        return new_ghe

    def __repr__(self):
        return 'GroundHeatExchanger: {}'.format(self.display_name)


class SoilParameter(object):
    """Represents the soil properties within a ground heat exchanger field.

    Args:
        conductivity: A number for the soil conductivity in W/m-K. (Default: 2.3).
        heat_capacity: A number for the volumetric heat capacity of the soil
            in J/m3-K. (Default: 2,343,500).
        undisturbed_temperature: A number the undisturbed annual average soil
            temperature in degrees Celsius. If autocalculate, this value will
            automatically be replaced with the average EPW temperature before
            simulation. (Default: Autocalculate).

    Properties:
        * conductivity
        * heat_capacity
        * undisturbed_temperature
    """

    __slots__ = ('_conductivity', '_heat_capacity', '_undisturbed_temperature')

    def __init__(self, conductivity=2.3, heat_capacity=2343500,
                 undisturbed_temperature=autocalculate):
        """Initialize SoilParameter."""
        self.conductivity = conductivity
        self.heat_capacity = heat_capacity
        self.undisturbed_temperature = undisturbed_temperature

    @classmethod
    def from_dict(cls, data):
        """Create a SoilParameter object from a dictionary

        Args:
            data: A dictionary representation of an SoilParameter object
                in the format below.

        .. code-block:: python

            {
            'type': 'SoilParameter',
            'conductivity': 1.8,  # float in W/m2-K
            'heat_capacity': 2100000,  # float in J/m3-K
            'undisturbed_temperature': 18  # float in C or autocalculate
            }
        """
        cond = data['conductivity'] if 'conductivity' in data else 2.3
        cap = data['heat_capacity'] if 'heat_capacity' in data else 2343500
        u_temp = autocalculate if 'undisturbed_temperature' not in data or \
            data['undisturbed_temperature'] == autocalculate.to_dict() \
            else data['undisturbed_temperature']
        return cls(cond, cap, u_temp)

    @property
    def conductivity(self):
        """Get or set a number for the soil conductivity in W/m-K."""
        return self._conductivity

    @conductivity.setter
    def conductivity(self, value):
        self._conductivity = float_positive(value, 'soil conductivity')

    @property
    def heat_capacity(self):
        """Get or set a number for the volumetric heat capacity of the soil in J/m3-K."""
        return self._heat_capacity

    @heat_capacity.setter
    def heat_capacity(self, value):
        self._heat_capacity = float_positive(value, 'soil heat_capacity')

    @property
    def undisturbed_temperature(self):
        """Get or set an integer (or Autocalculate) for the vegetation end month."""
        return self._undisturbed_temperature if self._undisturbed_temperature \
            is not None else autocalculate

    @undisturbed_temperature.setter
    def undisturbed_temperature(self, value):
        if value == autocalculate:
            self._undisturbed_temperature = None
        else:
            self._undisturbed_temperature = \
                float_in_range(value, -273, 200, 'undisturbed_temperature')

    def to_dict(self):
        """Get SoilParameter dictionary."""
        base = {'type': 'SoilParameter'}
        base['conductivity'] = self.conductivity
        base['heat_capacity'] = self.heat_capacity
        if self._undisturbed_temperature is not None:
            base['undisturbed_temperature'] = self._undisturbed_temperature
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = SoilParameter(self._conductivity, self._heat_capacity)
        new_obj._undisturbed_temperature = self._undisturbed_temperature
        return new_obj

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent SoilParameter."""
        return 'SoilParameter: [conductivity: {} W/m2-K] ' \
            '[heat capacity: {} J/m3-K]'.format(self._conductivity, self._heat_capacity)


class PipeParameter(object):
    """Represents the pipe properties within a ground heat exchanger field.

    Args:
        inner_diameter: A number for the diameter of the inner pipe surface in
            meters. (Default: 0.0216).
        outer_diameter: A number for the diameter of the outer pipe surface in
            meters. (Default: 0.0266).
        shank_spacing: A number for the spacing between the U-tube legs, as
            referenced from outer surface of the pipes in meters. (NOT referenced
            from each pipe's respective centerline). (Default: 0.0323).
        roughness: A number for the linear dimension of bumps on the pipe surface
            in meters. (Default: 1e-06)
        conductivity: A number for the conductivity of the pipe material in
            W/m-K. (Default: 0.4).
        heat_capacity: A number for the volumetric heat capacity of the pipe
            material in J/m3-K. (Default: 1,542,000).

    Properties:
        * inner_diameter
        * outer_diameter
        * shank_spacing
        * roughness
        * conductivity
        * heat_capacity
    """

    __slots__ = ('_inner_diameter', '_outer_diameter', '_shank_spacing',
                 '_roughness', '_conductivity', '_heat_capacity')

    def __init__(
            self, inner_diameter=0.0216, outer_diameter=0.0266, shank_spacing=0.0323,
            roughness=1e-06, conductivity=0.4, heat_capacity=1542000):
        """Initialize PipeParameter."""
        self.inner_diameter = inner_diameter
        self.outer_diameter = outer_diameter
        self.shank_spacing = shank_spacing
        self.roughness = roughness
        self.conductivity = conductivity
        self.heat_capacity = heat_capacity

    @classmethod
    def from_dict(cls, data):
        """Create a PipeParameter object from a dictionary

        Args:
            data: A dictionary representation of an PipeParameter object
                in the format below.

        .. code-block:: python

            {
            'type': 'PipeParameter',
            'inner_diameter': 0.0216,  # float for inner diameter in meters
            'outer_diameter': 0.0266  # float for outer diameter in meters
            'shank_spacing': 0.0323,  # float for spacing between outer pipes in meters
            'roughness': 1e-06,  # float for the dimension of the surface bumps
            'conductivity': 0.6,  # float in W/m2-K
            'heat_capacity': 1542000  # float in J/m3-K
            }
        """
        in_d = data['inner_diameter'] if 'inner_diameter' in data else 0.0216
        out_d = data['outer_diameter'] if 'outer_diameter' in data else 0.0266
        s_spc = data['shank_spacing'] if 'shank_spacing' in data else 0.0323
        rough = data['roughness'] if 'roughness' in data else 1e-06
        cond = data['conductivity'] if 'conductivity' in data else 2.3
        cap = data['heat_capacity'] if 'heat_capacity' in data else 2343500
        return cls(in_d, out_d, s_spc, rough, cond, cap)

    @property
    def inner_diameter(self):
        """Get or set a number for the inner diameter of the pipe in meters."""
        return self._inner_diameter

    @inner_diameter.setter
    def inner_diameter(self, value):
        self._inner_diameter = float_positive(value, 'pipe inner diameter')

    @property
    def outer_diameter(self):
        """Get or set a number for the outer diameter of the pipe in meters."""
        return self._outer_diameter

    @outer_diameter.setter
    def outer_diameter(self, value):
        self._outer_diameter = float_positive(value, 'pipe outer diameter')

    @property
    def shank_spacing(self):
        """Get or set a number for the shank spacing between the pipes in meters."""
        return self._shank_spacing

    @shank_spacing.setter
    def shank_spacing(self, value):
        self._shank_spacing = float_positive(value, 'pipe shank spacing')

    @property
    def roughness(self):
        """Get or set a number for the dimension of the pipe surface bumps in meters."""
        return self._roughness

    @roughness.setter
    def roughness(self, value):
        self._roughness = float_positive(value, 'pipe roughness')

    @property
    def conductivity(self):
        """Get or set a number for the conductivity of the pipe material in W/m-K."""
        return self._conductivity

    @conductivity.setter
    def conductivity(self, value):
        self._conductivity = float_positive(value, 'pipe conductivity')

    @property
    def heat_capacity(self):
        """Get or set a number for the volumetric heat capacity of the pipe in J/m3-K."""
        return self._heat_capacity

    @heat_capacity.setter
    def heat_capacity(self, value):
        self._heat_capacity = float_positive(value, 'pipe heat_capacity')

    def to_dict(self):
        """Get PipeParameter dictionary."""
        base = {'type': 'PipeParameter'}
        base['inner_diameter'] = self.inner_diameter
        base['outer_diameter'] = self.outer_diameter
        base['shank_spacing'] = self.shank_spacing
        base['roughness'] = self.roughness
        base['conductivity'] = self.conductivity
        base['heat_capacity'] = self.heat_capacity
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return PipeParameter(
            self.inner_diameter, self.outer_diameter, self.shank_spacing,
            self.roughness, self.conductivity, self.heat_capacity)

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent PipeParameter."""
        return 'PipeParameter: [diameter: {}m - {}m]'.format(
            self.inner_diameter, self.outer_diameter)


class BoreholeParameter(object):
    """Represents the borehole properties within a ground heat exchanger field.

    Args:
        length: A number for the length of the borehole in meters. This is the
            distance from the bottom of the heat exchanging part of the borehole
            to the top. (Default: 96).
        buried_depth: A number for the depth below the ground surface at which
            the top of the heat exchanging part of the borehole sits in
            meters. (Default: 2).
        diameter: A number for the diameter of the borehole in meters. (Default: 0.15).

    Properties:
        * length
        * buried_depth
        * diameter
    """

    __slots__ = ('_length', '_buried_depth', '_diameter')

    def __init__(self, length=96, buried_depth=2, diameter=0.15):
        """Initialize BoreholeParameter."""
        self.length = length
        self.buried_depth = buried_depth
        self.diameter = diameter

    @classmethod
    def from_dict(cls, data):
        """Create a BoreholeParameter object from a dictionary

        Args:
            data: A dictionary representation of an BoreholeParameter object
                in the format below.

        .. code-block:: python

            {
            'type': 'BoreholeParameter',
            'length': 120,  # float in meters
            'buried_depth': 4,  # float in meters
            'diameter': 0.2  # float in meters
            }
        """
        length = data['length'] if 'length' in data else 96
        dth = data['buried_depth'] if 'buried_depth' in data else 2
        dia = data['diameter'] if 'diameter' in data else 0.15
        return cls(length, dth, dia)

    @property
    def length(self):
        """Get or set a number for the length of the borehole in meters."""
        return self._length

    @length.setter
    def length(self, value):
        self._length = float_positive(value, 'borehole length')

    @property
    def buried_depth(self):
        """Get or set a number for the depth of the top of the borehole in meters."""
        return self._buried_depth

    @buried_depth.setter
    def buried_depth(self, value):
        self._buried_depth = float_positive(value, 'borehole buried_depth')

    @property
    def diameter(self):
        """Get or set a number for the diameter of the borehole in meters."""
        return self._diameter

    @diameter.setter
    def diameter(self, value):
        self._diameter = float_positive(value, 'borehole diameter')

    def to_dict(self):
        """Get BoreholeParameter dictionary."""
        base = {'type': 'BoreholeParameter'}
        base['length'] = self.length
        base['buried_depth'] = self.buried_depth
        base['diameter'] = self.diameter
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return BoreholeParameter(self.length, self.buried_depth, self.diameter)

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent BoreholeParameter."""
        return 'BoreholeParameter: [length: {}m] ' \
            '[heat diameter: {}m]'.format(self.length, self.diameter)
