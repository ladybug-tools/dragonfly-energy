"""dragonfly-energy commands which will be added to dragonfly command line interface."""
import click

from dragonfly.cli import main
from .simulate import simulate
from .translate import translate

# command group for all energy extension commands.
@click.group(help='dragonfly energy commands.')
def energy():
    pass


# add sub-commands for energy
energy.add_command(simulate)
energy.add_command(translate)

# add energy sub-commands to dragonfly CLI
main.add_command(energy)
