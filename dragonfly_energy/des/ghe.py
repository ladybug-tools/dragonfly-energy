# coding=utf-8
"""Ground Heat Exchanger (GHE) in a district thermal system."""
from .._base import _GeometryBase

from ladybug_geometry.geometry2d.polygon import Polygon2D
from honeybee.typing import valid_string, float_positive, float_in_range, int_in_range
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
    """
    __slots__ = ()

    def __init__(self, identifier, geometry):
        """Initialize GroundHeatExchanger."""
        _GeometryBase.__init__(self, identifier)  # process the identifier
        assert isinstance(geometry, Polygon2D), 'Expected ladybug_geometry ' \
            'Polygon2D for GroundHeatExchanger geometry. Got {}'.format(type(geometry))
        self._geometry = geometry

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
        trans = cls(data['identifier'], geo)
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

    def to_dict(self):
        """GroundHeatExchanger dictionary representation."""
        base = {'type': 'GroundHeatExchanger'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
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

    def __copy__(self):
        new_ghe = GroundHeatExchanger(self.identifier, self.geometry)
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
        undisturbed_temperature: A number for the undisturbed annual average soil
            temperature in degrees Celsius. If autocalculate, this value will
            automatically be replaced with the average EPW temperature before
            simulation. (Default: Autocalculate).
        grout_conductivity: A number for the grout conductivity in W/m-K. (Default: 1.0).
        grout_heat_capacity: A number for the volumetric heat capacity of the grout
            in J/m3-K. (Default: 3,901,000).

    Properties:
        * conductivity
        * heat_capacity
        * undisturbed_temperature
        * grout_conductivity
        * grout_heat_capacity
    """

    __slots__ = ('_conductivity', '_heat_capacity', '_undisturbed_temperature',
                 '_grout_conductivity', '_grout_heat_capacity')

    def __init__(self, conductivity=2.3, heat_capacity=2343500,
                 undisturbed_temperature=autocalculate,
                 grout_conductivity=1.0, grout_heat_capacity=3901000):
        """Initialize SoilParameter."""
        self.conductivity = conductivity
        self.heat_capacity = heat_capacity
        self.undisturbed_temperature = undisturbed_temperature
        self.grout_conductivity = grout_conductivity
        self.grout_heat_capacity = grout_heat_capacity

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
            'undisturbed_temperature': 18,  # float in C or autocalculate
            'grout_conductivity': 1.0,  # float in W/m2-K
            'grout_heat_capacity': 3901000
            }
        """
        cond = data['conductivity'] if 'conductivity' in data else 2.3
        cap = data['heat_capacity'] if 'heat_capacity' in data else 2343500
        u_temp = autocalculate if 'undisturbed_temperature' not in data or \
            data['undisturbed_temperature'] == autocalculate.to_dict() \
            else data['undisturbed_temperature']
        g_cond = data['grout_conductivity'] if 'grout_conductivity' in data else 1.0
        g_cap = data['grout_heat_capacity'] if 'grout_heat_capacity' in data else 3901000
        return cls(cond, cap, u_temp, g_cond, g_cap)

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

    @property
    def grout_conductivity(self):
        """Get or set a number for the grout conductivity in W/m-K."""
        return self._grout_conductivity

    @grout_conductivity.setter
    def grout_conductivity(self, value):
        self._grout_conductivity = float_positive(value, 'grout conductivity')

    @property
    def grout_heat_capacity(self):
        """Get or set a number for the volumetric heat capacity of the grout in J/m3-K.
        """
        return self._grout_heat_capacity

    @grout_heat_capacity.setter
    def grout_heat_capacity(self, value):
        self._grout_heat_capacity = float_positive(value, 'grout heat_capacity')

    def to_dict(self):
        """Get SoilParameter dictionary."""
        base = {'type': 'SoilParameter'}
        base['conductivity'] = self.conductivity
        base['heat_capacity'] = self.heat_capacity
        if self._undisturbed_temperature is not None:
            base['undisturbed_temperature'] = self._undisturbed_temperature
        base['grout_conductivity'] = self.grout_conductivity
        base['grout_heat_capacity'] = self.grout_heat_capacity
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = SoilParameter(self._conductivity, self._heat_capacity)
        new_obj._undisturbed_temperature = self._undisturbed_temperature
        new_obj._grout_conductivity = self._grout_conductivity
        new_obj._grout_heat_capacity = self._grout_heat_capacity
        return new_obj

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent SoilParameter."""
        return 'SoilParameter: [conductivity: {} W/m2-K] ' \
            '[heat capacity: {} J/m3-K]'.format(self._conductivity, self._heat_capacity)


class FluidParameter(object):
    """Represents the fluid properties within a ground heat exchanger field.

    Args:
        fluid_type: Text to indicate the type of fluid circulating through the
            ground heat exchanger loop. Choose from the options
            below. (Default: Water).

            * Water
            * EthylAlcohol
            * EthyleneGlycol
            * MethylAlcohol
            * PropyleneGlycol

        concentration: A number between 0 and 60 for the concentration of the
            fluid_type in water in percent. Note that this variable has no effect
            when the fluid_type is Water. (Default: 35).
        temperature: A number for the average design fluid temperature at peak
            conditions in Celsius. (Default: 20).

    Properties:
        * fluid_type
        * concentration
        * temperature
    """

    __slots__ = ('_fluid_type', '_concentration', '_temperature')
    FLUID_TYPES = (
        'Water', 'EthylAlcohol', 'EthyleneGlycol', 'MethylAlcohol', 'PropyleneGlycol')

    def __init__(self, fluid_type='Water', concentration=35, temperature=20):
        """Initialize FluidParameter."""
        self.fluid_type = fluid_type
        self.concentration = concentration
        self.temperature = temperature

    @classmethod
    def from_dict(cls, data):
        """Create a FluidParameter object from a dictionary

        Args:
            data: A dictionary representation of an FluidParameter object
                in the format below.

        .. code-block:: python

            {
            'type': 'FluidParameter',
            'fluid_type': 'PropyleneGlycol',  # text for fluid_type
            'concentration': 33,  # float for percentage concentration
            'temperature': 22  # float in C
            }
        """
        ft = data['fluid_type'] if 'fluid_type' in data else 'Water'
        con = data['concentration'] if 'concentration' in data else 35
        temp = 20 if 'temperature' not in data else data['temperature']
        return cls(ft, con, temp)

    @property
    def fluid_type(self):
        """Get or set text to indicate the type of fluid."""
        return self._fluid_type

    @fluid_type.setter
    def fluid_type(self, value):
        clean_input = valid_string(value).lower()
        for key in self.FLUID_TYPES:
            if key.lower() == clean_input:
                value = key
                break
        else:
            raise ValueError(
                'fluid_type {} is not recognized.\nChoose from the '
                'following:\n{}'.format(value, self.FLUID_TYPES))
        self._fluid_type = value

    @property
    def concentration(self):
        """Get or set a number for the concentration of the fluid_type in water [%]."""
        return self._concentration

    @concentration.setter
    def concentration(self, value):
        self._concentration = float_in_range(value, 0, 60, 'fluid concentration')

    @property
    def temperature(self):
        """Get or set a number for the average design fluid temperature in Celsius."""
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        self._temperature = float_positive(value, 'fluid temperature')

    def to_dict(self):
        """Get FluidParameter dictionary."""
        base = {'type': 'FluidParameter'}
        base['fluid_type'] = self.fluid_type
        base['concentration'] = self.concentration
        base['temperature'] = self.temperature
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return FluidParameter(self._fluid_type, self._concentration, self._temperature)

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent SoilParameter."""
        return 'FluidParameter: [fluid_type: {}] ' \
            '[concentration: {}%]'.format(self._fluid_type, self._concentration)


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
        arrangement: Text for the specified pipe arrangement. Choose from the
            following options. (Default: SingleUTube).

            * SingleUTube
            * DoubleUTubeSeries
            * DoubleUTubeParallel

    Properties:
        * inner_diameter
        * outer_diameter
        * shank_spacing
        * roughness
        * conductivity
        * heat_capacity
        * arrangement
    """
    __slots__ = ('_inner_diameter', '_outer_diameter', '_shank_spacing',
                 '_roughness', '_conductivity', '_heat_capacity', '_arrangement')
    ARRANGEMENT_TYPES = ('SingleUTube', 'DoubleUTubeSeries', 'DoubleUTubeParallel')

    def __init__(
            self, inner_diameter=0.0216, outer_diameter=0.0266, shank_spacing=0.0323,
            roughness=1e-06, conductivity=0.4, heat_capacity=1542000,
            arrangement='SingleUTube'):
        """Initialize PipeParameter."""
        self._inner_diameter = float_positive(inner_diameter, 'pipe inner_diameter')
        self.outer_diameter = outer_diameter
        self.shank_spacing = shank_spacing
        self.roughness = roughness
        self.conductivity = conductivity
        self.heat_capacity = heat_capacity
        self.arrangement = arrangement

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
            'heat_capacity': 1542000,  # float in J/m3-K
            'arrangement': 'SingleUTube'  # text for arrangement type
            }
        """
        in_d = data['inner_diameter'] if 'inner_diameter' in data else 0.0216
        out_d = data['outer_diameter'] if 'outer_diameter' in data else 0.0266
        s_spc = data['shank_spacing'] if 'shank_spacing' in data else 0.0323
        rough = data['roughness'] if 'roughness' in data else 1e-06
        cond = data['conductivity'] if 'conductivity' in data else 2.3
        cap = data['heat_capacity'] if 'heat_capacity' in data else 2343500
        arr = data['arrangement'] if 'arrangement' in data else 'SingleUTube'
        return cls(in_d, out_d, s_spc, rough, cond, cap, arr)

    @property
    def inner_diameter(self):
        """Get or set a number for the inner diameter of the pipe in meters."""
        return self._inner_diameter

    @inner_diameter.setter
    def inner_diameter(self, value):
        self._inner_diameter = float_positive(value, 'pipe inner diameter')
        self._diameter_check()

    @property
    def outer_diameter(self):
        """Get or set a number for the outer diameter of the pipe in meters."""
        return self._outer_diameter

    @outer_diameter.setter
    def outer_diameter(self, value):
        self._outer_diameter = float_positive(value, 'pipe outer diameter')
        self._diameter_check()

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

    @property
    def arrangement(self):
        """Get or set text for the pipe arrangement.

        Choose from the following options:

        * SingleUTube
        * DoubleUTubeSeries
        * DoubleUTubeParallel
        """
        return self._arrangement

    @arrangement.setter
    def arrangement(self, value):
        clean_input = valid_string(value).lower()
        for key in self.ARRANGEMENT_TYPES:
            if key.lower() == clean_input:
                value = key
                break
        else:
            raise ValueError(
                'arrangement {} is not recognized.\nChoose from the '
                'following:\n{}'.format(value, self.ARRANGEMENT_TYPES))
        self._arrangement = value

    def to_dict(self):
        """Get PipeParameter dictionary."""
        base = {'type': 'PipeParameter'}
        base['inner_diameter'] = self.inner_diameter
        base['outer_diameter'] = self.outer_diameter
        base['shank_spacing'] = self.shank_spacing
        base['roughness'] = self.roughness
        base['conductivity'] = self.conductivity
        base['heat_capacity'] = self.heat_capacity
        base['arrangement'] = self.arrangement
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return PipeParameter(
            self.inner_diameter, self.outer_diameter, self.shank_spacing,
            self.roughness, self.conductivity, self.heat_capacity, self.arrangement)

    def _diameter_check(self):
        """Check that outer_diameter is greater than or equal to the inner_diameter."""
        assert self._outer_diameter > self._inner_diameter, \
            'Pipe outer_diameter must be greater than or equal to inner_diameter.'

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
        min_depth: A number for the minimum depth of the heat-exchanging part
            of the boreholes in meters. All boreholes will have a depth of
            at least this value. So this typically represents the depth at which
            borehole-drilling is most economical or the point at which it becomes
            more cost effective to start a new borehole instead of making a given
            borehole deeper. (Default: 60).
        max_depth: A number for the maximum depth of the heat-exchanging part
            of the boreholes in meters. When the system demand cannot be met
            using boreholes with the min_depth, the boreholes will be extended
            until either the loads or met or they reach this depth. So this
            typically represents the depth of bedrock or the point at which
            drilling deeper ceases to be practical. (Default: 135).
        min_spacing: A number for the minimum spacing between boreholes in meters.
            When the system demand cannot be met using boreholes with the max_spacing,
            the borehole spacing will be reduced until either the loads or met
            or they reach this spacing. So this typically represents the spacing
            at which each borehole will interfere with neighboring ones so much
            that it is not worthwhile to decrease the spacing further. (Default: 3).
        max_spacing: A number for the maximum spacing between boreholes in meters.
            All boreholes will have a spacing of at most this value. So this
            typically represents the spacing at which the performance effects of
            one borehole on a neighboring one are negligible. (Default: 25).
        buried_depth: A number for the depth below the ground surface at which
            the top of the heat exchanging part of the borehole sits in
            meters. (Default: 2).
        diameter: A number for the diameter of the borehole in meters. (Default: 0.15).

    Properties:
        * min_depth
        * max_depth
        * min_spacing
        * max_spacing
        * buried_depth
        * diameter
    """
    __slots__ = ('_min_depth', '_max_depth', '_min_spacing', '_max_spacing',
                 '_buried_depth', '_diameter')

    def __init__(self, min_depth=60, max_depth=135, min_spacing=3, max_spacing=25,
                 buried_depth=2, diameter=0.15):
        """Initialize BoreholeParameter."""
        self._min_depth = float_positive(min_depth, 'borehole min_depth')
        self.max_depth = max_depth
        self._min_spacing = float_positive(min_spacing, 'borehole min_spacing')
        self.max_spacing = max_spacing
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
            'min_depth': 30,  # float in meters
            'max_depth': 90,  # float in meters
            'min_spacing': 2.5,  # float in meters
            'max_spacing': 8,  # float in meters
            'buried_depth': 4,  # float in meters
            'diameter': 0.2  # float in meters
            }
        """
        min_depth = data['min_depth'] if 'min_depth' in data else 60
        max_depth = data['max_depth'] if 'max_depth' in data else 135
        min_spacing = data['min_spacing'] if 'min_spacing' in data else 3
        max_spacing = data['max_spacing'] if 'max_spacing' in data else 10
        dth = data['buried_depth'] if 'buried_depth' in data else 2
        dia = data['diameter'] if 'diameter' in data else 0.15
        return cls(min_depth, max_depth, min_spacing, max_spacing, dth, dia)

    @property
    def min_depth(self):
        """Get or set a number for the minimum depth of the borehole in meters."""
        return self._min_depth

    @min_depth.setter
    def min_depth(self, value):
        self._min_depth = float_positive(value, 'borehole min_depth')
        self._depth_check()

    @property
    def max_depth(self):
        """Get or set a number for the maximum depth of the borehole in meters."""
        return self._max_depth

    @max_depth.setter
    def max_depth(self, value):
        self._max_depth = float_positive(value, 'borehole max_depth')
        self._depth_check()

    @property
    def min_spacing(self):
        """Get or set a number for the minimum spacing between boreholes in m.
        """
        return self._min_spacing

    @min_spacing.setter
    def min_spacing(self, value):
        self._min_spacing = float_positive(value, 'borehole min_spacing')
        self._spacing_check()

    @property
    def max_spacing(self):
        """Get or set a number for the maximum spacing between boreholes in m.
        """
        return self._max_spacing

    @max_spacing.setter
    def max_spacing(self, value):
        self._max_spacing = float_positive(value, 'borehole max_spacing')
        self._spacing_check()

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
        base['min_depth'] = self.min_depth
        base['max_depth'] = self.max_depth
        base['min_spacing'] = self.min_spacing
        base['max_spacing'] = self.max_spacing
        base['buried_depth'] = self.buried_depth
        base['diameter'] = self.diameter
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return BoreholeParameter(
            self.min_depth, self.max_depth, self.min_spacing, self.max_spacing,
            self.buried_depth, self.diameter)

    def _depth_check(self):
        """Check that max_depth is greater than or equal to min_depth."""
        assert self._max_depth >= self._min_depth, \
            'Borehole max_depth must be greater than or equal to min_depth.'

    def _spacing_check(self):
        """Check that max_spacing is greater than or equal to min_spacing."""
        assert self._max_spacing >= self._min_spacing, \
            'Borehole max_spacing must be greater than or equal to min_spacing.'

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent BoreholeParameter."""
        return 'BoreholeParameter: [depth: {}m - {}m] [spacing: {}m - {}m]'.format(
            self.min_depth, self.max_depth, self.min_spacing, self.max_spacing)


class GHEDesignParameter(object):
    """Represents criteria used to design a ground heat exchanger.

    Args:
        flow_rate: A number for the volumetric design flow rate through the
            ground heat exchanger in L/s. The value specified will be either for
            the entire system system or per-borehole flow rate depending on
            the flow_type set. (Default: 0.2 L/s).
        flow_type: Text to indicate whether the design volumetric flow rate set on
            a per-borehole or system basis. Choose from the following
            options. (Default: Borehole).

            * Borehole
            * System

        max_eft: A number for the maximum heat pump entering fluid temperature
            in Celsius. (Default: 35C).
        min_eft: A number for the minimum heat pump entering fluid temperature
            in Celsius. (Default: 5C).
        month_count: An integer for the number of months over which the simulation
            will be run in order to ensure stable ground temperature
            conditions. (Default: 240).

    Properties:
        * flow_rate
        * flow_type
        * max_eft
        * min_eft
        * month_count
    """
    __slots__ = ('_flow_rate', '_flow_type', '_max_eft', '_min_eft', '_month_count')
    FLOW_TYPES = ('Borehole', 'System')

    def __init__(self, flow_rate=0.2, flow_type='Borehole', max_eft=35, min_eft=5,
                 month_count=240):
        """Initialize BoreholeParameter."""
        self.flow_rate = flow_rate
        self.flow_type = flow_type
        self._min_eft = float_positive(min_eft, 'GHE min entering fluid temperature')
        self.max_eft = max_eft
        self.month_count = month_count

    @classmethod
    def from_dict(cls, data):
        """Create a GHEDesignParameter object from a dictionary

        Args:
            data: A dictionary representation of an GHEDesignParameter object
                in the format below.

        .. code-block:: python

            {
            'type': 'GHEDesignParameter',
            'flow_rate': 30,  # float in L/s
            'flow_type': 'Borehole',  # text for the type of object flow_rate references
            'max_eft': 35,  # float for max entering fluid temperature in C
            'min_eft': 5,  # float for min entering fluid temperature in C
            'month_count': 240  # int for the number of months to run the simulation
            }
        """
        flow_rate = data['flow_rate'] if 'flow_rate' in data else 0.2
        flow_type = data['flow_type'] if 'flow_type' in data else 'Borehole'
        max_eft = data['max_eft'] if 'max_eft' in data else 35
        min_eft = data['min_eft'] if 'min_eft' in data else 5
        month_count = data['month_count'] if 'month_count' in data else 240
        return cls(flow_rate, flow_type, max_eft, min_eft, month_count)

    @property
    def flow_rate(self):
        """Get or set a number the volumetric design flow rate in L/s."""
        return self._flow_rate

    @flow_rate.setter
    def flow_rate(self, value):
        self._flow_rate = float_positive(value, 'ground heat exchanger flow_rate')

    @property
    def flow_type(self):
        """Get or set text for the type of object flow_rate references.

        Choose from the following options:

        * Borehole
        * System
        """
        return self._flow_type

    @flow_type.setter
    def flow_type(self, value):
        clean_input = valid_string(value).lower()
        for key in self.FLOW_TYPES:
            if key.lower() == clean_input:
                value = key
                break
        else:
            raise ValueError(
                'Flow type {} is not recognized.\nChoose from the '
                'following:\n{}'.format(value, self.FLOW_TYPES))
        self._flow_type = value

    @property
    def min_eft(self):
        """Get or set a number for the minimum entering fluid temperature in Celsius."""
        return self._min_eft

    @min_eft.setter
    def min_eft(self, value):
        self._min_eft = float_positive(value, 'GHE min entering fluid temperature')
        self._eft_check()

    @property
    def max_eft(self):
        """Get or set a number for the maximum entering fluid temperature in Celsius."""
        return self._max_eft

    @max_eft.setter
    def max_eft(self, value):
        self._max_eft = float_positive(value, 'GHE max entering fluid temperature')
        self._eft_check()

    @property
    def month_count(self):
        """Get or set a number for the maximum entering fluid temperature in Celsius."""
        return self._month_count

    @month_count.setter
    def month_count(self, value):
        self._month_count = int_in_range(value, 12, input_name='GHE month count')

    def to_dict(self):
        """Get GHEDesignParameter dictionary."""
        base = {'type': 'GHEDesignParameter'}
        base['flow_rate'] = self.flow_rate
        base['flow_type'] = self.flow_type
        base['min_eft'] = self.min_eft
        base['max_eft'] = self.max_eft
        base['month_count'] = self.month_count
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return GHEDesignParameter(
            self.flow_rate, self.flow_type, self.min_eft, self.max_eft, self.month_count)

    def _eft_check(self):
        """Check that max_eft is greater than or equal to min_eft."""
        assert self._max_eft >= self._min_eft, \
            'GHE max_eft must be greater than or equal to min_eft.'

    def ToString(self):
        """Overwrite .NET ToString method."""
        return self.__repr__()

    def __repr__(self):
        """Represent GHEDesignParameter."""
        return 'GHEDesignParameter: [flow: {}L/s] [eft: {}C - {}C]'.format(
            self.flow_rate, self.min_eft, self.max_eft)
