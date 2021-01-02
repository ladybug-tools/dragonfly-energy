# coding=utf-8
"""Complete set of REopt Simulation Settings."""
from __future__ import division

import os
import json

from honeybee.typing import float_positive, float_in_range, int_positive


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
    """
    def __init__(self, max_kw=0, dollars_per_kw=1600):
        _SourceParameter.__init__(self, max_kw, dollars_per_kw)

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
