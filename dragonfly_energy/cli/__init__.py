"""dragonfly-energy commands which will be added to dragonfly command line interface."""

try:
    import click
except ImportError:
    raise ImportError(
        'click is not installed. Try `pip install . [cli]` command.'
    )

from dragonfly.cli import main
from .simulate import simulate
from .translate import translate

# command group for all energy extension commands.
@click.group(help='dragonfly energy commands.')
def energy():
    pass


# add sub-commands to energy
energy.add_command(simulate)
energy.add_command(translate)

# add energy sub-commands to dragonfly CLI
main.add_command(energy)
