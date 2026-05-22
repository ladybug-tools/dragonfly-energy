"""dragonfly energy translation commands."""
import click
import sys
import os
import subprocess
import logging

from ladybug.futil import nukedir, download_file, unzip_file
from ladybug.config import folders as lb_folders
from honeybee.config import folders
from dragonfly_energy.config import folders as df_folders

UO_GMT_VERSION_STR = '.'.join(str(i) for i in df_folders.UO_GMT_VERSION)
UO_TN_VERSION_STR = '.'.join(str(i) for i in df_folders.UO_TN_VERSION)
MBL_VERSION_STR = '.'.join(str(d) for d in df_folders.MBL_VERSION)

_logger = logging.getLogger(__name__)


@click.group(help='Commands for installing dependencies related to urban simulation.')
def install():
    pass


@install.command('all-des')
def all_des_cli():
    """Install all dependencies needed for DES simulation in their default locations.

    This includes the GeoJSON Modelica Translator (GMT), the Thermal Network (TN)
    package, and the Modelica Buildings Library (MBL).
    """
    try:
        all_des()
    except Exception as e:
        _logger.exception(
            'Failed to install the Modelica Buildings Library (MBL).\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def all_des():
    """Install all dependencies needed for DES simulation in their default locations.

    This includes the GeoJSON Modelica Translator (GMT), the Thermal Network (TN)
    package, and the Modelica Buildings Library (MBL).
    """
    # set global values
    ext = '.exe' if os.name == 'nt' else ''
    executor_path = os.path.join(
        lb_folders.ladybug_tools_folder, 'grasshopper',
        'ladybug_grasshopper_dotnet', 'Ladybug.Executor.exe')

    # install the geojson-modelica-translator
    print('Checking for the installation of the geojson-modelica-translator.')
    uo_gmt = '{}/uo_des{}'.format(folders.python_scripts_path, ext)
    uo_gmt_pack = '{}/geojson_modelica_translator-{}.dist-info'.format(
        folders.python_package_path, UO_GMT_VERSION_STR)
    if not os.path.isfile(uo_gmt) or not os.path.isdir(uo_gmt_pack):
        install_cmd = 'pip install geojson-modelica-translator=={}'.format(UO_GMT_VERSION_STR)
        if os.name == 'nt' and os.path.isfile(executor_path) and \
                'Program Files' in executor_path:
            pip_cmd = [
                executor_path, folders.python_exe_path, '-m {}'.format(install_cmd)
            ]
        else:
            pip_cmd = '"{py_exe}" -m {uo_cmd}'.format(
                py_exe=folders.python_exe_path, uo_cmd=install_cmd)
        shell = True if os.name == 'nt' else False
        process = subprocess.Popen(
            pip_cmd, stderr=subprocess.PIPE, shell=shell
        )
        stderr = process.communicate()
        if stderr == '':
            msg = 'Version {} of the geojson-modelica-translator was successfully installed.'
            print(msg.format(UO_GMT_VERSION_STR))
        else:
            print(stderr)
    else:
        msg = 'Version {} of the geojson-modelica-translator is already installed.'
        print(msg.format(UO_GMT_VERSION_STR))

    # install the ThermalNetwork package
    print('Checking for the installation of the thermalnetwork.')
    uo_tn = '{}/thermalnetwork{}'.format(folders.python_scripts_path, ext)
    uo_tn_pack = '{}/ThermalNetwork-{}.dist-info'.format(
        folders.python_package_path, UO_TN_VERSION_STR)
    if not os.path.isfile(uo_tn) or not os.path.isdir(uo_tn_pack):
        install_cmd = 'pip install thermalnetwork=={}'.format(UO_TN_VERSION_STR)
        if os.name == 'nt' and os.path.isfile(executor_path) and \
                'Program Files' in executor_path:
            pip_cmd = [
                executor_path, folders.python_exe_path, '-m {}'.format(install_cmd)
            ]
        else:
            pip_cmd = '"{py_exe}" -m {uo_cmd}'.format(
                py_exe=folders.python_exe_path, uo_cmd=install_cmd)
        shell = True if os.name == 'nt' else False
        process = subprocess.Popen(
            pip_cmd, stderr=subprocess.PIPE, shell=shell)
        stderr = process.communicate()
        if stderr == '':
            msg = 'Version {} of thermalnetwork was successfully installed.'
            print(msg.format(UO_TN_VERSION_STR))
        else:
            print(stderr)
    else:
        msg = 'Version {} of thermalnetwork is already installed.'
        print(msg.format(UO_TN_VERSION_STR))

    # install the Modelica Buildings Library
    print('Checking for the installation of the Modelica Buildings Library.')
    mbl()


@install.command('mbl')
@click.option(
    '--version', '-v', help='Text string for the version of the MBL to install.',
    type=str, default=MBL_VERSION_STR, show_default=True
)
@click.option(
    '--install-directory', '-d', default=None, help='The path to a directory where the '
    'Modelica Buildings Library (MBL) will be installed. By default, it will be saved '
    'into the resources of the installation folder.',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True)
)
def mbl_cli(version, install_directory):
    """Install the Modelica Buildings Library (MBL)."""
    try:
        mbl(version, install_directory)
    except Exception as e:
        _logger.exception(
            'Failed to install the Modelica Buildings Library (MBL).\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def mbl(version=MBL_VERSION_STR, install_directory=None):
    """Install the Modelica Buildings Library (MBL).

    Args:
        version: Text string for the version of the MBL to install.
        install_directory: The path to a directory where the Modelica Buildings
            Library (MBL) will be installed. By default, it will be saved into
            the resources of the installation folder.
    """
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
            print('Removing older Modelica Buildings Library installation.')
            nukedir(final_dir, True)

    # download the MBL to the installation folder
    if not already_installed:
        mbl_url = 'https://github.com/lbl-srg/modelica-buildings/releases/' \
            'download/v{}/Buildings-v{}.zip'.format(version, version)
        mbl_zip_file = os.path.join(install_directory, 'mbl.zip')
        print('Downloading Modelica Buildings Library from:\n{}\n'
              'This may take a few minutes...'.format(mbl_url))
        download_file(mbl_url, mbl_zip_file)
        print('Unzipping Modelica Buildings Library to:\n{}\n'
              'This may take a few minutes...'.format(final_dir))
        unzip_file(mbl_zip_file, install_directory, True)
        default_f = os.path.join(install_directory, 'Buildings {}'.format(version))
        os.rename(default_f, final_dir)
        with open(version_file, 'w') as vf:
            vf.write(version)
        os.remove(mbl_zip_file)
        msg = 'Modelica Buildings Library version {} successfully installed!'
        print(msg.format(MBL_VERSION_STR))
    else:
        msg = 'Modelica Buildings Library version {} is already installed.'
        print(msg.format(MBL_VERSION_STR))
