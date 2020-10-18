"""Test cli translate module."""
from click.testing import CliRunner
from honeybee_energy.config import folders
from dragonfly_energy.cli.translate import model_to_idf

import os


def test_model_to_idf():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.json'

    output_df_folder = './tests/json/'
    output_df_model = os.path.join(output_df_folder, 'OfficeBuilding.idf')
    result = runner.invoke(model_to_idf, [input_df_model, '-f', output_df_folder])
    assert result.exit_code == 0

    assert os.path.isfile(output_df_model)
    os.remove(output_df_model)
