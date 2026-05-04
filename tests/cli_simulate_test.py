"""Test cli simulate module."""
from click.testing import CliRunner
import os
from ladybug.futil import nukedir

from dragonfly_energy.cli.simulate import model_cli


def test_simulate_model():
    runner = CliRunner()
    input_df_model = './tests/json/model_complete_simple.dfjson'
    input_epw = './tests/epw/chicago.epw'

    output_folder = './tests/simulation'
    in_args = [input_df_model, input_epw, '--folder', output_folder]
    result = runner.invoke(model_cli, in_args)
    assert result.exit_code == 0

    output_sql = os.path.join(output_folder, 'OfficeBuilding', 'run', 'eplusout.sql')
    assert os.path.isfile(output_sql)
    nukedir(output_folder)
