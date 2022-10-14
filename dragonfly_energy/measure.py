# coding=utf-8
"""Mange OpenStudio measures that can be mapped to different buildings in a model."""
from __future__ import division

import os
import xml.etree.ElementTree as ElementTree
from honeybee_energy.measure import Measure, MeasureArgument


class MapperMeasure(Measure):
    """An OpenStudio measure that can be mapped to different buildings in a model.

    Args:
        folder: Path to the folder in which the measure exists. This folder
            must contain a measure.rb and a measure.xml file. Other files are
            optional.

    Properties:
        * folder
        * metadata_file
        * program_file
        * resources_folder
        * identifier
        * display_name
        * description
        * type
        * arguments
    """
    __slots__ = ()

    def __init__(self, folder):
        """Initialize MapperMeasure."""
        Measure.__init__(self, folder)

    @classmethod
    def from_dict(cls, data, folder='.'):
        """Initialize a MapperMeasure from a dictionary.

        Args:
            data: A dictionary in the format below.
            folder: Path to a destination folder to save the measure files. (Default '.')

        .. code-block:: python

            {
            "type": "MapperMeasure",
            "identifier": string,  # Measure identifier
            "xml_data": string,  # XML file data as string
            "rb_data": string,  # Ruby file data as string
            "resource_data": {},  # Dictionary of strings for any resource ruby files
            "argument_values": [],  # List of values for each of the measure arguments
            }
        """
        assert data['type'] == 'MapperMeasure', \
            'Expected MapperMeasure dictionary. Got {}.'.format(data['type'])
        fp = os.path.join(folder, data['identifier'])
        if not os.path.isdir(fp):
            os.makedirs(fp)

        # write out the contents of the measure
        xml_fp = os.path.join(fp, 'measure.xml')
        cls._decompress_to_file(data['xml_data'], xml_fp)
        rb_fp = os.path.join(fp, 'measure.rb')
        cls._decompress_to_file(data['rb_data'], rb_fp)
        if 'resource_data' in data and data['resource_data'] is not None:
            resource_path = os.path.join(fp, 'resources')
            os.makedirs(resource_path)
            for f_name, res in data['resource_data'].items():
                res_fp = os.path.join(resource_path, f_name)
                cls._decompress_to_file(res, res_fp)

        # create the measure object and assign the arguments
        new_measure = cls(fp)
        for arg, val in zip(new_measure.arguments, data['argument_values']):
            if val is not None:
                arg.value = val
        return new_measure

    def to_dict(self):
        """Convert MapperMeasure to a dictionary."""
        base = Measure.to_dict(self)
        base['type'] = 'MapperMeasure'
        return base

    def to_osw_dict(self, full_path=False):
        """Get a Python dictionary that can be written to an OSW JSON.

        Specifically, this dictionary can be appended to the "steps" key of the
        OpenStudio Workflow (.osw) JSON dictionary in order to include the measure
        in the workflow.

        Note that this method does not perform any checks to validate that the
        Measure has all required values and only arguments with values will be
        included in the dictionary. Validation should be done separately with
        the validate method.

        Args:
            full_path: Boolean to note whether the full path to the measure should
                be written under the 'measure_dir_name' key or just the measure
                base name. (Default: False)
        """
        meas_dir = self.folder if full_path else os.path.basename(self.folder)
        base = {'measure_dir_name': meas_dir, 'arguments': {}}
        for arg in self._arguments:
            if arg.value is not None:
                base['arguments'][arg.identifier] = arg.value \
                    if not isinstance(arg.value, tuple) else arg.value[0]
        return base

    def _parse_metadata_file(self):
        """Parse measure properties from the measure.xml file."""
        # create an element tree object
        tree = ElementTree.parse(self._metadata_file)
        root = tree.getroot()

        # parse the measure properties from the element tree
        self._identifier = root.find('name').text
        self._display_name = root.find('display_name').text
        self._description = root.find('description').text
        self._type = None
        for atr in root.find('attributes'):
            if atr.find('name').text == 'Measure Type':
                self._type = atr.find('value').text

        # parse the measure arguments
        self._arguments = []
        for arg in root.find('arguments'):
            arg_obj = MapperMeasureArgument(arg)
            if arg_obj.model_dependent:
                # TODO: Figure out how to implement model-dependent arguments
                raise NotImplementedError(
                    'Model dependent arguments are not yet supported and measure '
                    'argument is "{}" model dependent.'.format(arg_obj.identifier))
            self._arguments.append(arg_obj)

    def __repr__(self):
        return 'MapperMeasure: {}'.format(self.display_name)


class MapperMeasureArgument(MeasureArgument):
    """Object representing a single mapper measure argument.

    Args:
        xml_element: A Python XML Element object taken from the <arguments> section
            of the measure.xml file.

    Properties:
        * identifier
        * display_name
        * value
        * default_value
        * type
        * type_text
        * required
        * description
        * model_dependent
        * valid_choices
    """
    __slots__ = ()

    def __init__(self, xml_element):
        """Initialize MeasureArgument."""
        MeasureArgument.__init__(self, xml_element)

    @property
    def value(self):
        """Get or set the value or list of values for the argument.

        When using a list, the length of it must match the number of buildings in
        the dragonfly Model and each value corresponds to a building under the
        Model.buildings property.

        If not set, this will be equal to the default_value and, if no default
        value is included for this argument, it will be None.
        """
        if self._value is not None:
            return self._value
        return self._default_value

    @value.setter
    def value(self, val):
        if val is not None:
            e_msg = 'Value for measure argument "' + self.identifier + \
                '" must be a {}. Got {}'
            if not isinstance(val, (list, tuple)):
                val = (val,)
            try:
                val = tuple(self._type(v) for v in val)
            except Exception:
                raise TypeError(e_msg.format(self._type, type(val)))
            if self._valid_choices:
                assert all(v in self._valid_choices for v in val), \
                    'Choice measure argument "{}" ' \
                    'must be one of the following:\n{}\nGot {}'.format(
                        self.identifier, self._valid_choices, val)
        self._value = val if val is None or len(val) != 1 else val[0]
