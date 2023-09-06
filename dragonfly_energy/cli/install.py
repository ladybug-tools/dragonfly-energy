"""dragonfly energy translation commands."""
import click
import sys
import os
import logging

from ladybug.futil import nukedir, download_file, unzip_file
from ladybug.config import folders as lb_folders


_logger = logging.getLogger(__name__)


@click.group(help='Commands for installing dependencies related to urban simulation.')
def install():
    pass


@install.command('mbl')
@click.option(
    '--version', '-v', help='Text string for the version of the MBL to install.',
    type=str, default='9.1.1', show_default=True)
@click.option(
    '--install-directory', '-d', default=None, help='The path to a directory where the '
    'Modelica Buildings Library (MBL) will be installed. By default, it will be saved '
    'into the resources of the installation folder.',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
def install_mbl(version, install_directory):
    """Install the Modelica Buildings Library (MBL)."""
    try:
        # set the default folder if it's not specified
        if install_directory is None:
            install_directory = os.path.join(
                lb_folders.ladybug_tools_folder, 'resources')

        # check whether the MBL is already installed
        final_dir = os.path.join(install_directory, 'mbl')
        version_file = os.path.join(final_dir, 'version.txt')
        already_installed = False
        if os.path.isdir(final_dir) and os.path.isfile(version_file):
            with open(version_file, 'r') as vf:
                install_version = vf.read()
            if install_version == version:
                already_installed = True
            else:
                click.echo('Removing older Modelica Buildings Library installation.')
                nukedir(final_dir, True)

        # download the MBL to the installation folder
        if not already_installed:
            mbl_url = 'https://github.com/lbl-srg/modelica-buildings/releases/' \
                'download/v{}/Buildings-v{}.zip'.format(version, version)
            mbl_zip_file = os.path.join(install_directory, 'mbl.zip')
            click.echo('Downloading Modelica Buildings Library from:\n{}\n'
                       'This may take a few minutes...'.format(mbl_url))
            download_file(mbl_url, mbl_zip_file)
            click.echo('Unzipping Modelica Buildings Library to:\n{}\n'
                       'This may take a few minutes...'.format(final_dir))
            unzip_file(mbl_zip_file, install_directory, True)
            default_f = os.path.join(install_directory, 'Buildings {}'.format(version))
            os.rename(default_f, final_dir)
            with open(version_file, 'w') as vf:
                vf.write(version)
            os.remove(mbl_zip_file)
            click.echo('Modelica Buildings Library successfully installed!')
    except Exception as e:
        _logger.exception(
            'Failed to install the Modelica Buildings Library (MBL).\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)