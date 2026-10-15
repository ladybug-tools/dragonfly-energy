"""Test cli translate module."""
import os
from click.testing import CliRunner

from dragonfly_energy.cli.translate import model_to_osm_cli, model_to_idf_cli, \
    model_to_gbxml_cli, model_to_trace_gbxml_cli, model_to_sdd_cli, \
    model_from_idf_cli, model_from_gbxml_cli


def test_model_to_osm():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_osm = './tests/json/in.osm'
    result = runner.invoke(model_to_osm_cli, [input_df_model, '--osm-file', output_osm])
    assert result.exit_code == 0
    assert os.path.isfile(output_osm)

    os.remove(output_osm)


def test_model_to_idf():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_idf = './tests/json/in.idf'
    result = runner.invoke(model_to_idf_cli, [input_df_model, '-f', output_idf])
    assert result.exit_code == 0
    assert os.path.isfile(output_idf)

    output_dfjson = './tests/json/test_output.dfjson'
    result = runner.invoke(model_from_idf_cli, [output_idf, '--output-file', output_dfjson])
    assert result.exit_code == 0
    assert os.path.isfile(output_dfjson)

    os.remove(output_idf)
    os.remove(output_dfjson)


def test_model_to_gbxml():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_gbxml = './tests/json/in.xml'
    in_args = [input_df_model, '--complete-geometry',
               '--reset-geometry-ids', '--reset-resource-ids',
               '--program-name', 'Ladybug Tools', '--program-version', '1.9',
               '--gbxml-schema-version', '5.00', '-f', output_gbxml]
    result = runner.invoke(model_to_gbxml_cli, in_args)
    assert result.exit_code == 0
    assert os.path.isfile(output_gbxml)

    output_dfjson = './tests/json/test_output.dfjson'
    result = runner.invoke(model_from_gbxml_cli, [output_gbxml, '--output-file', output_dfjson])
    assert result.exit_code == 0
    assert os.path.isfile(output_dfjson)

    os.remove(output_gbxml)
    os.remove(output_dfjson)


def test_model_to_trace_gbxml():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_gbxml = './tests/json/in_trace.xml'
    in_args = [input_df_model, '--program-name', 'Ladybug Tools',
               '--program-version', '1.9', '-f', output_gbxml]
    result = runner.invoke(model_to_trace_gbxml_cli, in_args)
    assert result.exit_code == 0

    assert os.path.isfile(output_gbxml)
    os.remove(output_gbxml)


def test_model_to_trace_gbxml_non_utf8():
    runner = CliRunner()
    input_df_model = './tests/json/model_non_utf_8.dfjson'

    output_gbxml = './tests/json/in_trace_non_utf_8.xml'
    result = runner.invoke(model_to_trace_gbxml_cli, [input_df_model, '-f', output_gbxml])
    assert result.exit_code == 0

    assert os.path.isfile(output_gbxml)
    os.remove(output_gbxml)


def test_model_to_sdd():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_sdd = './tests/json/sdd.xml'
    result = runner.invoke(model_to_sdd_cli, [input_df_model, '-f', output_sdd])
    assert result.exit_code == 0

    assert os.path.isfile(output_sdd)
    os.remove(output_sdd)
