"""Test cli translate module."""
from click.testing import CliRunner
from dragonfly_energy.cli.translate import model_to_idf

import os


def test_model_to_idf():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.json'

    result = runner.invoke(model_to_idf, [input_df_model])
    assert result.exit_code == 0

    output_df_model = './tests/json/OfficeBuilding.idf'
    assert os.path.isfile(output_df_model)
    os.remove(output_df_model)
