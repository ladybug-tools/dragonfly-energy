# coding=utf-8
from dragonfly_energy.measure import MapperMeasure, MapperMeasureArgument

from ladybug.futil import nukedir

import os


def test_mapper_measure_init():
    """Test the initialization of MapperMeasure and basic properties."""
    measure_path = './tests/measure/edit_fraction_radiant_of_lighting_and_equipment'
    measure = MapperMeasure(measure_path)
    str(measure)  # test the string representation

    # test the file paths
    assert measure.folder == os.path.abspath(measure_path)
    assert measure.metadata_file.endswith('measure.xml')
    assert measure.program_file.endswith('measure.rb')
    assert measure.resources_folder is None

    # test the measure attributes
    assert measure.type == 'ModelMeasure'
    assert measure.identifier == 'edit_fraction_radiant_of_lighting_and_equipment'
    assert measure.display_name == 'Edit Fraction Radiant of Lighting and Equipment'
    assert measure.description == "This measure replaces the 'Fraction Radiant' of " \
        "all lights and equipment in the model with values that you specify. " \
        "This is useful for thermal comfort studies where the percentage of heat " \
        "transferred to the air is important."

    # test the measure arguments
    assert len(measure.arguments) == 2
    str(measure.arguments[0])  # test the string representation
    assert measure.arguments[0].identifier == 'lightsFractRad'
    assert measure.arguments[0].display_name == 'Lights Fraction Radiant'
    assert measure.arguments[0].type == float
    assert measure.arguments[0].type_text == 'Double'
    assert not measure.arguments[0].required
    assert measure.arguments[0].description is None
    assert not measure.arguments[0].model_dependent
    assert measure.arguments[0].valid_choices is None

    # test the default values for the arguments
    assert measure.arguments[0].value == measure.arguments[0].default_value == 0
    assert measure.arguments[1].value == measure.arguments[1].default_value == 0
    assert measure.validate()

    # test the setting of measure arguments and make sure they get to the OSW
    measure.arguments[0].value = 0.25
    measure.arguments[1].value = 0.25
    osw_dict = measure.to_osw_dict()
    for arg in osw_dict['arguments'].values():
        assert arg == 0.25

    # test the setting of array measure arguments and make sure they are not in the OSW
    measure.arguments[0].value = [0.25, 0.5, 0.75]
    measure.arguments[1].value = [0.25, 0.5, 0.75]
    osw_dict = measure.to_osw_dict()
    for arg in osw_dict['arguments'].values():
        assert arg == 0.25


def test_mapper_measure_to_from_dict():
    """Test the serialization of MapperMeasure to and from a dictionary."""
    measure_path = './tests/measure/edit_fraction_radiant_of_lighting_and_equipment'
    measure = MapperMeasure(measure_path)
    measure.arguments[0].value = [0.25, 0.5, 0.75]
    measure_dict = measure.to_dict()

    new_measure_path = './tests/simulation/measure_test'
    new_measure = MapperMeasure.from_dict(measure_dict, new_measure_path)
    assert os.path.isdir(measure.folder)
    assert os.path.isfile(measure.metadata_file)
    assert os.path.isfile(measure.program_file)
    assert measure_dict == new_measure.to_dict()

    nukedir(new_measure_path, True)
