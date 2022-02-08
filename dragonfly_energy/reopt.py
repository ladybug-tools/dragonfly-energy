# coding=utf-8
"""Complete set of REopt Simulation Settings."""
from __future__ import division

import os
import json
import math

from ladybug_geometry.geometry2d.pointvector import Point2D, Vector2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from honeybee.typing import float_positive, float_in_range, int_positive, \
    valid_ep_string, valid_string
from dragonfly.projection import polygon_to_lon_lat, meters_to_long_lat_factors, \
    origin_long_lat_from_location


class REoptParameter(object):
    """Complete set of REopt Simulation Settings.

    Args:
        financial_parameter: A FinancialParameter object to describe the parameters
            of the financial analysis. If None, a set of defaults will be
            generated. (Default: None).
        wind_parameter: A WindParameter object to set the cost and max amount of
            wind to include in the analysis. If None, no wind will be included
            in the analysis. (Default: None).
        pv_parameter: A PVParameter object to set the cost and max amount of
            photovoltaic to include in the analysis. If None, no PV will be included
            in the analysis. (Default: None).
        storage_parameter: A StorageParameter object to set the cost and max amount of
            electricity storage to include in the analysis. If None, no storage
            will be included in the analysis. (Default: None).
        generator_parameter: A GeneratorParameter object to set the cost and max amount
            of generators to include in the analysis. If None, no generators
            will be included in the analysis. (Default: None).

    Properties:
        * financial_parameter
        * wind_parameter
        * pv_parameter
        * storage_parameter
        * generator_parameter
    """
    def __init__(self, financial_parameter=None, wind_parameter=None, pv_parameter=None,
                 storage_parameter=None, generator_parameter=None):
        """Initialize SimulationParameter."""
        self.financial_parameter = financial_parameter
        self.wind_parameter = wind_parameter
        self.pv_parameter = pv_parameter
        self.storage_parameter = storage_parameter
        self.generator_parameter = generator_parameter

    @property
    def financial_parameter(self):
        """Get or set a FinancialParameter object for financial settings."""
        return self._financial_parameter

    @financial_parameter.setter
    def financial_parameter(self, value):
        if value is not None:
            assert isinstance(value, FinancialParameter), 'Expected ' \
                'FinancialParameter. Got {}.'.format(type(value))
            self._financial_parameter = value
        else:
            self._financial_parameter = FinancialParameter()

    @property
    def wind_parameter(self):
        """Get or set a WindParameter object for wind settings."""
        return self._wind_parameter

    @wind_parameter.setter
    def wind_parameter(self, value):
        if value is not None:
            assert isinstance(value, WindParameter), 'Expected ' \
                'WindParameter. Got {}.'.format(type(value))
            self._wind_parameter = value
        else:
            self._wind_parameter = WindParameter()

    @property
    def pv_parameter(self):
        """Get or set a PVParameter object for photovoltaic settings."""
        return self._pv_parameter

    @pv_parameter.setter
    def pv_parameter(self, value):
        if value is not None:
            assert isinstance(value, PVParameter), 'Expected ' \
                'PVParameter. Got {}.'.format(type(value))
            self._pv_parameter = value
        else:
            self._pv_parameter = PVParameter()

    @property
    def storage_parameter(self):
        """Get or set a StorageParameter object for electricity storage settings."""
        return self._storage_parameter

    @storage_parameter.setter
    def storage_parameter(self, value):
        if value is not None:
            assert isinstance(value, StorageParameter), 'Expected ' \
                'StorageParameter. Got {}.'.format(type(value))
            self._storage_parameter = value
        else:
            self._storage_parameter = StorageParameter()

    @property
    def generator_parameter(self):
        """Get or set a GeneratorParameter object for electricity storage settings."""
        return self._generator_parameter

    @generator_parameter.setter
    def generator_parameter(self, value):
        if value is not None:
            assert isinstance(value, GeneratorParameter), 'Expected ' \
                'GeneratorParameter. Got {}.'.format(type(value))
            self._generator_parameter = value
        else:
            self._generator_parameter = GeneratorParameter()

    def to_assumptions_dict(self, base_file, urdb_label):
        """Get REoptParameter as a dictionary representation in the REopt Lite schema.

        Full documentation of the REopt Lite schema can be found at.
        https://developer.nrel.gov/docs/energy-optimization/reopt-v1/

        Args:
            base_file: A JSON file in the REopt Lite schema containing a base set
                of assumptions that will be modified based on the properties of
                this object.
            urdb_label: Text string for the Utility Rate Database (URDB) label
                for the particular electrical utility rate for the
                optimization. The label is the last term of the URL of a
                utility rate detail page (eg. the label for the rate at
                https://openei.org/apps/IURDB/rate/view/5b0d83af5457a3f276733305
                is 5b0d83af5457a3f276733305).
        """
        # load up the base dictionary
        assert os.path.isfile(base_file), \
            'No base JSON file found at {}.'.format(base_file)
        with open(base_file, 'r') as base_f:
            base_dict = json.load(base_f)
        # apply this object's properties
        site_dict = base_dict['Scenario']['Site']
        site_dict['ElectricTariff']['urdb_label'] = urdb_label
        self.financial_parameter.apply_to_dict(site_dict['Financial'])
        self.wind_parameter.apply_to_dict(site_dict['Wind'])
        self.pv_parameter.apply_to_dict(site_dict['PV'])
        self.storage_parameter.apply_to_dict(site_dict['Storage'])
        self.generator_parameter.apply_to_dict(site_dict['Generator'])
        return base_dict

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return REoptParameter(
            self.financial_parameter.duplicate(), self.wind_parameter.duplicate(),
            self.pv_parameter.duplicate(), self.storage_parameter.duplicate(),
            self.generator_parameter.duplicate())

    def __repr__(self):
        return 'REoptParameter:'


class FinancialParameter(object):
    """Complete set of Financial settings for REopt.

    Args:
        analysis_years: An integer for the number of years over which cost will
            be optimized. (Default: 25).
        escalation_rate: A number between 0 and 1 for the escalation rate over
            the analysis. (Default: 0.023).
        tax_rate: A number between 0 and 1 for the rate at which the owner/host
            of the system is taxed. (Default: 0.26).
        discount_rate: A number between 0 and 1 for the discount rate for the
            owner/host of the system. (Default: 0.083).

    Properties:
        * analysis_years
        * escalation_rate
        * tax_rate
        * discount_rate
    """
    def __init__(self, analysis_years=25, escalation_rate=0.023,
                 tax_rate=0.26, discount_rate=0.083):
        """Initialize FinancialParameter."""
        self.analysis_years = analysis_years
        self.escalation_rate = escalation_rate
        self.tax_rate = tax_rate
        self.discount_rate = discount_rate

    @property
    def analysis_years(self):
        """Get or set a integer for the number of years to run the analysis."""
        return self._analysis_years

    @analysis_years.setter
    def analysis_years(self, value):
        self._analysis_years = int_positive(
            value, input_name='financial parameter analysis years')

    @property
    def escalation_rate(self):
        """Get or set a fractional number for the escalation rate."""
        return self._escalation_rate

    @escalation_rate.setter
    def escalation_rate(self, value):
        self._escalation_rate = float_in_range(
            value, 0, 1, input_name='financial parameter escalation rate')

    @property
    def tax_rate(self):
        """Get or set a fractional number for the tax rate."""
        return self._tax_rate

    @tax_rate.setter
    def tax_rate(self, value):
        self._tax_rate = float_in_range(
            value, 0, 1, input_name='financial parameter tax rate')

    @property
    def discount_rate(self):
        """Get or set a fractional number for the discount rate."""
        return self._discount_rate

    @discount_rate.setter
    def discount_rate(self, value):
        self._discount_rate = float_in_range(
            value, 0, 1, input_name='financial parameter discount rate')

    def apply_to_dict(self, base_dict):
        """Apply this object's properties to a 'Financial' object of REopt schema."""
        base_dict['analysis_years'] = self.analysis_years
        base_dict['escalation_pct'] = self.escalation_rate
        base_dict['offtaker_tax_pct'] = self.tax_rate
        base_dict['offtaker_discount_pct'] = self.discount_rate

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return FinancialParameter(
            self.analysis_years, self.escalation_rate, self.tax_rate, self.discount_rate)

    def __repr__(self):
        return 'REopt FinancialParameter:'


class _SourceParameter(object):
    """Base class for all REopt energy sources.

    Args:
        max_kw: A number for the maximum installed kilowatts of the energy
            source. (Default: 0).
        dollars_per_kw: A number for the installation cost of the energy source in
            US dollars. (Default: 500).

    Properties:
        * max_kw
        * dollars_per_kw
    """
    def __init__(self, max_kw=0, dollars_per_kw=500):
        self.max_kw = max_kw
        self.dollars_per_kw = dollars_per_kw

    @property
    def max_kw(self):
        """Get or set a number for the maximum installed kilowatts."""
        return self._max_kw

    @max_kw.setter
    def max_kw(self, value):
        self._max_kw = float_positive(value, input_name='reopt max kw')

    @property
    def dollars_per_kw(self):
        """Get or set a number for the installation cost in US dollars."""
        return self._dollars_per_kw

    @dollars_per_kw.setter
    def dollars_per_kw(self, value):
        self._dollars_per_kw = float_positive(value, input_name='reopt dollars per kw')

    def apply_to_dict(self, base_dict):
        """Apply this object's properties to an object of REopt schema."""
        base_dict['max_kw'] = self.max_kw
        base_dict['installed_cost_us_dollars_per_kw'] = self.dollars_per_kw

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return self.__class__(self.max_kw, self.dollars_per_kw)


class WindParameter(_SourceParameter):
    """Wind settings for REopt.

    Args:
        max_kw: A number for the maximum installed kilowatts. (Default: 0).
        dollars_per_kw: A number for installation cost in US dollars. (Default: 3013).

    Properties:
        * max_kw
        * dollars_per_kw
    """
    def __init__(self, max_kw=0, dollars_per_kw=3013):
        _SourceParameter.__init__(self, max_kw, dollars_per_kw)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'REopt WindParameter: {} kW'.format(self.max_kw)


class PVParameter(_SourceParameter):
    """Photovoltaic settings for REopt.

    Args:
        max_kw: A number for the maximum installed kilowatts. (Default: 0).
        dollars_per_kw: A number for installation cost in US dollars. (Default: 1600).

    Properties:
        * max_kw
        * dollars_per_kw
        * max_kw_ground
        * dollars_per_kw_ground
    """
    def __init__(self, max_kw=0, dollars_per_kw=1600,
                 max_kw_ground=0, dollars_per_kw_ground=2200):
        _SourceParameter.__init__(self, max_kw, dollars_per_kw)
        self.max_kw_ground = max_kw_ground
        self.dollars_per_kw_ground = dollars_per_kw_ground

    @property
    def max_kw_ground(self):
        """Get or set a number for the maximum installed kilowatts of Ground PV."""
        return self._max_kw_ground

    @max_kw_ground.setter
    def max_kw_ground(self, value):
        self._max_kw_ground = float_positive(value, input_name='reopt max kw')

    @property
    def dollars_per_kw_ground(self):
        """Get or set a number for the installation cost of ground PV in US dollars."""
        return self._dollars_per_kw_ground

    @dollars_per_kw_ground.setter
    def dollars_per_kw_ground(self, value):
        self._dollars_per_kw_ground = \
            float_positive(value, input_name='reopt dollars per kw')

    def apply_to_dict(self, base_dict):
        """Apply this object's properties to an object of REopt schema."""
        if isinstance(base_dict, dict):
            base_dict['max_kw'] = self.max_kw
            base_dict['installed_cost_us_dollars_per_kw'] = self.dollars_per_kw
        else:
            base_dict[0]['max_kw'] = self.max_kw
            base_dict[0]['installed_cost_us_dollars_per_kw'] = self.dollars_per_kw
            base_dict[1]['max_kw'] = self.max_kw_ground
            base_dict[1]['installed_cost_us_dollars_per_kw'] = self.dollars_per_kw_ground

    def __copy__(self):
        return PVParameter(self.max_kw, self.dollars_per_kw,
                           self.max_kw_ground, self.dollars_per_kw_ground)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'REopt PVParameter: {} kW'.format(self.max_kw)


class StorageParameter(_SourceParameter):
    """Electrical storage settings for REopt.

    Args:
        max_kw: A number for the maximum installed kilowatts. (Default: 0).
        dollars_per_kw: A number for installation cost in US dollars. (Default: 840).

    Properties:
        * max_kw
        * dollars_per_kw
    """
    def __init__(self, max_kw=0, dollars_per_kw=840):
        _SourceParameter.__init__(self, max_kw, dollars_per_kw)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'REopt StorageParameter: {} kW'.format(self.max_kw)


class GeneratorParameter(_SourceParameter):
    """Generator settings for REopt.

    Args:
        max_kw: A number for the maximum installed kilowatts. (Default: 0).
        dollars_per_kw: A number for installation cost in US dollars. (Default: 500).

    Properties:
        * max_kw
        * dollars_per_kw
    """
    def __init__(self, max_kw=0, dollars_per_kw=500):
        _SourceParameter.__init__(self, max_kw, dollars_per_kw)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'REopt GeneratorParameter: {} kW'.format(self.max_kw)


class GroundMountPV(object):
    """Represents a ground-mounted photovoltaic system in REopt.

    Args:
        identifier: Text string for a unique Photovoltaic ID. Must contain only
            characters that are acceptable in REopt. This will be used to
            identify the object across the exported geoJSON and REopt files.
        geometry: A Polygon2D representing the geometry of the PV field.
        building_identifier: An optional identifier of a dragonfly Building with
            which the photovoltaic system is associated. If None, the PV system
            will be assumed to be a community PV field that isn't associated with
            a particular building meter. (Default: None).

    Properties:
        * identifier
        * display_name
        * geometry
        * building_identifier
    """
    __slots__ = ('_identifier', '_display_name', '_geometry', '_building_identifier')

    def __init__(self, identifier, geometry, building_identifier=None):
        """Initialize GroundMountPV."""
        self.identifier = identifier
        self._display_name = None
        assert isinstance(geometry, Polygon2D), 'Expected ladybug_geometry ' \
            'Polygon2D for GroundMountPV geometry. Got {}'.format(type(geometry))
        self._geometry = geometry
        self.building_identifier = building_identifier

    @classmethod
    def from_dict(cls, data):
        """Initialize an GroundMountPV from a dictionary.

        Args:
            data: A dictionary representation of an GroundMountPV object.
        """
        # check the type of dictionary
        assert data['type'] == 'GroundMountPV', 'Expected GroundMountPV ' \
            'dictionary. Got {}.'.format(data['type'])
        geo = Polygon2D.from_dict(data['geometry'])
        pv_obj = cls(data['identifier'], geo)
        if 'display_name' in data and data['display_name'] is not None:
            pv_obj.display_name = data['display_name']
        if 'building_identifier' in data and data['building_identifier'] is not None:
            pv_obj.building_identifier = data['building_identifier']
        return pv_obj

    @property
    def identifier(self):
        """Get or set the text string for unique object identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, identifier):
        self._identifier = valid_ep_string(identifier, 'identifier')

    @property
    def display_name(self):
        """Get or set a string for the object name without any character restrictions.

        If not set, this will be equal to the identifier.
        """
        if self._display_name is None:
            return self._identifier
        return self._display_name

    @display_name.setter
    def display_name(self, value):
        try:
            self._display_name = str(value)
        except UnicodeEncodeError:  # Python 2 machine lacking the character set
            self._display_name = value  # keep it as unicode

    @property
    def building_identifier(self):
        """Get or set the text string for a Building associated with the PV field."""
        return self._building_identifier

    @building_identifier.setter
    def building_identifier(self, identifier):
        if identifier is not None:
            identifier = valid_string(identifier, 'building identifier')
        self._building_identifier = identifier

    @property
    def geometry(self):
        """Get a Polygon2D representing the photovoltaic field."""
        return self._geometry

    def move(self, moving_vec):
        """Move this object along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the object.
        """
        self._geometry = self._geometry.move(Vector2D(moving_vec.x, moving_vec.y))

    def rotate_xy(self, angle, origin):
        """Rotate this object counterclockwise in the XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self._geometry.rotate(
            math.radians(angle), Point2D(origin.x, origin.y))

    def reflect(self, plane):
        """Reflect this object across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will be reflected.
        """
        assert plane.n.z == 0, \
            'Plane normal must be in XY plane to use it on dragonfly object reflect.'
        norm = Vector2D(plane.n.x, plane.n.y)
        origin = Point2D(plane.o.x, plane.o.y)
        self._geometry = self._geometry.reflect(norm, origin)

    def scale(self, factor, origin=None):
        """Scale this object by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        ori = Point2D(origin.x, origin.y) if origin is not None else None
        self._geometry = self._geometry.scale(factor, ori)

    def to_dict(self):
        """GroundMountPV dictionary representation."""
        base = {'type': 'GroundMountPV'}
        base['identifier'] = self.identifier
        base['geometry'] = self.geometry.to_dict()
        if self._display_name is not None:
            base['display_name'] = self.display_name
        if self._building_identifier is not None:
            base['building_identifier'] = self.building_identifier
        return base

    def to_geojson_dict(self, location, point):
        """Get GroundMountPV dictionary as it appears in an URBANopt geoJSON.

        Args:
            location: A ladybug Location object possessing longitude and latitude data.
            point: A ladybug_geometry Point2D for where the location object exists
                within the space of a scene. The coordinates of this point are
                expected to be in the units of this Model. (Default: (0, 0)).
        """
        # get the conversion factors over to (longitude, latitude)
        origin_lon_lat = origin_long_lat_from_location(location, point)
        convert_facs = meters_to_long_lat_factors(origin_lon_lat)

        # create the GeoJSON dictionary
        pts = [(pt.x, pt.y) for pt in self.geometry.vertices]
        coords = [polygon_to_lon_lat(pts, origin_lon_lat, convert_facs)]
        base = {
            'type': 'Feature',
            'properties': {
                'id': self.identifier,
                'geometryType': 'Rectangle',
                'name': self.display_name,
                'type': 'District System',
                'footprint_area': self.geometry.area,
                'footprint_perimeter': self.geometry.perimeter
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': coords
            }
        }
        if self.building_identifier is None:
            base['properties']['district_system_type'] = 'Community Photovoltaic'
        else:
            base['properties']['district_system_type'] = 'Ground Mount Photovoltaic'
            base['properties']['associated_building_id'] = self.building_identifier
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = GroundMountPV(self.identifier, self.geometry, self.building_identifier)
        new_obj._display_name = self._display_name
        return new_obj

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'GroundMountPV: {}'.format(self.display_name)
