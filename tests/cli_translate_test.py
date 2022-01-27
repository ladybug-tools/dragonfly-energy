"""Test cli translate module."""
from click.testing import CliRunner
from ladybug.futil import nukedir
from dragonfly_energy.cli.translate import model_to_osm, model_to_idf, model_to_gbxml

import os


def test_model_to_osm():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_df_folder = './tests/json/osm'
    output_df_model = os.path.join(output_df_folder, 'run', 'in.osm')
    result = runner.invoke(model_to_osm, [input_df_model, '-f', output_df_folder])
    assert result.exit_code == 0

    assert os.path.isfile(output_df_model)
    nukedir(output_df_folder)


def test_model_to_idf():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_df_folder = './tests/json/'
    output_df_model = os.path.join(output_df_folder, 'OfficeBuilding.idf')
    result = runner.invoke(model_to_idf, [input_df_model, '-f', output_df_model])
    assert result.exit_code == 0

    assert os.path.isfile(output_df_model)
    os.remove(output_df_model)


def test_model_to_gbxml():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_df_folder = './tests/json/gbxml'
    output_df_model = os.path.join(output_df_folder, 'in.gbxml')
    result = runner.invoke(model_to_gbxml, [input_df_model, '-f', output_df_model])
    assert result.exit_code == 0

    assert os.path.isfile(output_df_model)
    nukedir(output_df_folder)
