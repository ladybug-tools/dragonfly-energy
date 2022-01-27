"""Test cli translate module."""
from click.testing import CliRunner
from ladybug.futil import nukedir
from dragonfly_energy.cli.simulate import simulate_model

import os


def test_simulate_model():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'
    input_epw = './tests/epw/chicago.epw'

    output_df_folder = './tests/json/simulate'
    output_df_sql = os.path.join(output_df_folder, 'OfficeBuilding', 'run', 'eplusout.sql')
    result = runner.invoke(simulate_model, [input_df_model, input_epw, '-f', output_df_folder])
    assert result.exit_code == 0

    assert os.path.isfile(output_df_sql)
    nukedir(output_df_folder)
