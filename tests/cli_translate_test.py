"""Test cli translate module."""
from click.testing import CliRunner
from dragonfly_energy.cli.translate import model_to_osm_cli, model_to_idf_cli, \
    model_to_gbxml_cli, model_to_trace_gbxml_cli, model_to_sdd_cli

import os


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
    os.remove(output_idf)


def test_model_to_gbxml():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_gbxml = './tests/json/in.xml'
    in_args = [input_df_model, '--complete-geometry', '-f', output_gbxml]
    result = runner.invoke(model_to_gbxml_cli, in_args)
    assert result.exit_code == 0

    assert os.path.isfile(output_gbxml)
    os.remove(output_gbxml)


def test_model_to_trace_gbxml():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'

    output_gbxml = './tests/json/in_trace.xml'
    result = runner.invoke(model_to_trace_gbxml_cli, [input_df_model, '-f', output_gbxml])
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
