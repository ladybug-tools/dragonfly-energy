"""dragonfly_energy configurations.

Import this into every module where access configurations are needed.

Usage:

.. code-block:: python

    from dragonfly_energy.config import folders
    print(folders.mapper_path)
    folders.mapper_path = "C:/Urbanopt_test/Honeybee.rb"
"""
from ladybug.futil import write_to_file
import honeybee_energy.config as hb_energy_config

import os
import platform
import json
import subprocess


class Folders(object):
    """Dragonfly_energy folders.

    Args:
        config_file: The path to the config.json file from which folders are loaded.
            If None, the config.json module included in this package will be used.
            Default: None.
        mute: If False, the paths to the various folders will be printed as they
            are found. If True, no printing will occur upon initialization of this
            class. Default: True.

    Properties:
        * mapper_path
        * urbanopt_gemfile_path
        * urbanopt_cli_path
        * urbanopt_env_path
        * urbanopt_version
        * urbanopt_version_str
        * reopt_assumptions_path
        * config_file
        * mute
    """
    URBANOPT_VERSION = (0, 9, 0)
    COMPATIBILITY_URL = 'https://github.com/ladybug-tools/lbt-grasshopper/wiki/' \
        '1.4-Compatibility-Matrix'

    def __init__(self, config_file=None, mute=True):
        self.mute = bool(mute)  # set the mute value
        self.config_file = config_file  # load paths from the config JSON file

    @property
    def mapper_path(self):
        """Get or set the path to the Ruby mapper used in URBANopt workflows.

        This is the Ruby file that is used to map URBANopt geoJSON features to
        honeybee model JSONs.
        """
        return self._mapper_path

    @mapper_path.setter
    def mapper_path(self, path):
        if not path:  # check the default installation location
            path = self._find_mapper_path()
        if path:  # check that the mapper file exists in the path
            assert os.path.isfile(path) and path.endswith('.rb'), \
                '{} is not a valid path to a Ruby mapper file.'.format(path)
        self._mapper_path = path  # set the mapper_path
        if path and not self.mute:
            print("Path to Mapper is set to: %s" % path)

    @property
    def urbanopt_gemfile_path(self):
        """Get or set the path to the Gemfile used in URBANopt workflows.

        Setting this can be used to test newer versions of URBANopt with upgraded
        dependencies in the Gemfile.
        """
        return self._urbanopt_gemfile_path

    @urbanopt_gemfile_path.setter
    def urbanopt_gemfile_path(self, path):
        if not path:  # check the default installation location
            path = self._find_urbanopt_gemfile_path()
        if path:  # check that the Gemfile exists at the path
            assert os.path.isfile(path), \
                '{} is not a valid path to an URBANopt Gemfile.'.format(path)
        self._urbanopt_gemfile_path = path  # set the urbanopt_gemfile_path
        if path and not self.mute:
            print("Path to URBANopt Gemfile is set to: %s" % path)

    @property
    def urbanopt_cli_path(self):
        """Get or set the path to the path where URBANopt is installed.

        Setting this can be used to test newer versions of URBANopt.
        """
        return self._urbanopt_cli_path

    @urbanopt_cli_path.setter
    def urbanopt_cli_path(self, path):
        if not path:  # check the default installation location
            path = self._find_urbanopt_cli_path()
        if path:  # check that the installation exists at the path
            assert os.path.isdir(path), \
                '{} is not a valid path to an URBANopt installation.'.format(path)
        self._urbanopt_cli_path = path  # set the urbanopt_cli_path
        self._urbanopt_env_path = None
        self._urbanopt_version = None
        self._urbanopt_version_str = None
        if path and not self.mute:
            print("Path to URBANopt CLI is set to: %s" % path)

    @property
    def urbanopt_env_path(self):
        """Get or set the path to the executable used to set the URBANopt environment.
        """
        return self._urbanopt_env_path

    @urbanopt_env_path.setter
    def urbanopt_env_path(self, path):
        if path:  # check that the file exists at the path
            assert os.path.isfile(path), \
                '{} is not a valid path to an URBANopt env executable.'.format(path)
        self._urbanopt_env_path = path  # set the urbanopt_env_path
        if path and not self.mute:
            print("Path to URBANopt Environment executable is set to: %s" % path)

    @property
    def urbanopt_version(self):
        """Get a tuple for the version of URBANopt (eg. (0, 7, 1)).

        This will be None if the version could not be sensed or if no URBANopt
        installation was found.
        """
        if self._urbanopt_cli_path and self._urbanopt_version_str is None:
            self._urbanopt_version_from_cli()
        return self._urbanopt_version

    @property
    def urbanopt_version_str(self):
        """Get text for the full version of URBANopt (eg. "0.7.1").

        This will be None if the version could not be sensed or if no URBANopt
        installation was found.
        """
        if self._urbanopt_cli_path and self._urbanopt_version_str is None:
            self._urbanopt_version_from_cli()
        return self._urbanopt_version_str

    @property
    def reopt_assumptions_path(self):
        """Get or set the path to the JSON file that contains base REopt assumptions.
        """
        return self._reopt_assumptions_path

    @reopt_assumptions_path.setter
    def reopt_assumptions_path(self, path):
        if not path:  # check the default installation location
            path = self._find_reopt_assumptions_path()
        if path:  # check that the file exists at the path
            assert os.path.isfile(path), \
                '{} is not a valid path to a REopt assumptions JSON.'.format(path)
        self._reopt_assumptions_path = path  # set the reopt_assumptions_path
        if path and not self.mute:
            print("Path to REopt assumptions is set to: %s" % path)

    @property
    def config_file(self):
        """Get or set the path to the config.json file from which folders are loaded.

        Setting this to None will result in using the config.json module included
        in this package.
        """
        return self._config_file

    @config_file.setter
    def config_file(self, cfg):
        if cfg is None:
            cfg = os.path.join(os.path.dirname(__file__), 'config.json')
        self._load_from_file(cfg)
        self._config_file = cfg

    def generate_urbanopt_env_path(self):
        """Run the URBANopt setup-env file to set this object's urbanopt_env_path."""
        # search for the file in its default location
        home_folder = os.getenv('HOME') or os.path.expanduser('~')
        env_file = os.path.join(home_folder, '.env_uo.bat') if os.name == 'nt' else \
            os.path.join(home_folder, '.env_uo.sh')

        if self.urbanopt_cli_path:  # try to generate the env file
            env_setup = os.path.join(self.urbanopt_cli_path, 'setup-env.bat') \
                if os.name == 'nt' else \
                os.path.join(self.urbanopt_cli_path, 'setup-env.sh')
            if os.path.isfile(env_setup):
                if os.name == 'nt':  # run the batch file on Windows
                    os.system(env_setup)
                else:  # run the sell file on Mac or Linux
                    subprocess.check_call(['chmod', 'u+x', env_setup])
                    subprocess.call(env_setup)
            if os.path.isfile(env_file):
                self._urbanopt_env_path = env_file  # the file was successfully generated

    def check_urbanopt_version(self):
        """Check if the installed version of URBANopt is the acceptable one."""
        in_msg = 'Get a compatible version of URBANopt by downloading and installing\n' \
            'the version of URBANopt listed in the Ladybug Tools compatibility ' \
            'matrix\n{}.'.format(self.COMPATIBILITY_URL)
        assert self.urbanopt_cli_path is not None, \
            'No URBANopt installation was found on this machine.\n{}'.format(in_msg)
        uo_version = self.urbanopt_version
        if uo_version is None:
            if self.urbanopt_env_path is not None:
                ext = '.bat' if os.name == 'nt' else '.sh'
                ver_file = os.path.join(
                    os.path.dirname(self.urbanopt_env_path),
                    '.check_uo_version{}'.format(ext))
                process = subprocess.Popen(ver_file, stderr=subprocess.PIPE, shell=True)
                _, stderr = process.communicate()
            else:
                stderr = 'Unable to set up the URBANopt environment.'
            msg = 'An URBANopt installation was found at {}\n' \
                'but the URBANopt executable is not accessible.\n{}'.format(
                    self.urbanopt_cli_path, stderr)
            raise ValueError(msg)
        assert uo_version[0] == self.URBANOPT_VERSION[0] and \
            uo_version[1] == self.URBANOPT_VERSION[1], \
            'The installed URBANopt is version {}.\nMust be version {} to work ' \
            'with dragonfly.\n{}'.format(
                '.'.join(str(v) for v in uo_version),
                '.'.join(str(v) for v in self.URBANOPT_VERSION), in_msg)

    def _load_from_file(self, file_path):
        """Set all of the the properties of this object from a config JSON file.

        Args:
            file_path: Path to a JSON file containing the file paths. A sample of this
                JSON is the config.json file within this package.
        """
        # check the default file path
        assert os.path.isfile(str(file_path)), \
            ValueError('No file found at {}'.format(file_path))

        # set the default paths to be all blank
        default_path = {
            "mapper_path": r'',
            "urbanopt_gemfile_path": r'',
            "urbanopt_cli_path": r'',
            "urbanopt_env_path": r'',
            "reopt_assumptions_path": r''
        }

        with open(file_path, 'r') as cfg:
            try:
                paths = json.load(cfg)
            except Exception as e:
                print('Failed to load paths from {}.\n{}'.format(file_path, e))
            else:
                for key, p in paths.items():
                    if isinstance(key, list) or not key.startswith('__'):
                        try:
                            default_path[key] = p.strip()
                        except AttributeError:
                            default_path[key] = p

        # set paths for the configuration
        self.mapper_path = default_path["mapper_path"]
        self.urbanopt_gemfile_path = default_path["urbanopt_gemfile_path"]
        self.urbanopt_cli_path = default_path["urbanopt_cli_path"]
        self.urbanopt_env_path = default_path["urbanopt_env_path"]
        self.reopt_assumptions_path = default_path["reopt_assumptions_path"]

    def _urbanopt_version_from_cli(self):
        """Set this object's URBANopt version by making a call to URBANopt CLI."""
        if not self.urbanopt_env_path:
            self.generate_urbanopt_env_path()
        assert self.urbanopt_env_path is not None, 'Unable to set up the URBANopt ' \
            'environment. Make sure it is installed correctly.'
        if os.name == 'nt':
            working_drive = self.urbanopt_env_path[:2]
            batch = '{}\ncd {}\ncall {}\nuo --version'.format(
                working_drive, working_drive, self.urbanopt_env_path)
            batch_file = os.path.join(
                os.path.dirname(self.urbanopt_env_path), '.check_uo_version.bat')
            write_to_file(batch_file, batch, True)
            process = subprocess.Popen(batch_file, stdout=subprocess.PIPE, shell=True)
            stdout = process.communicate()
        else:
            shell = '#!/usr/bin/env bash\nsource {}\nuo --version'.format(
                self.urbanopt_env_path)
            shell_file = os.path.join(
                os.path.dirname(self.urbanopt_env_path), '.check_uo_version.sh')
            write_to_file(shell_file, shell, True)
            # make the shell script executable using subprocess.check_call
            subprocess.check_call(['chmod', 'u+x', shell_file])
            # run the shell script
            process = subprocess.Popen(shell_file, stdout=subprocess.PIPE, shell=True)
            stdout = process.communicate()
        base_str = str(stdout[0]).split('--version')[-1]
        base_str = base_str.replace(r"\r", '').replace(r"\n", '').replace(r"'", '')
        base_str = base_str.strip()
        try:
            ver_nums = base_str.split('.')
            self._urbanopt_version = tuple(int(i) for i in ver_nums)
            self._urbanopt_version_str = base_str
        except Exception:
            pass  # failed to parse the version into integers

    @staticmethod
    def _find_mapper_path():
        """Find the mapper that is distributed with the honeybee-openstudio-gem."""
        measure_install = hb_energy_config.folders.honeybee_openstudio_gem_path
        if measure_install:
            mapper_file = os.path.join(measure_install, 'files', 'Honeybee.rb')
            if os.path.isfile(mapper_file):
                return mapper_file
        return None

    @staticmethod
    def _find_urbanopt_gemfile_path():
        """Find the URBANopt Gemfile that's distributed with honeybee-openstudio-gem."""
        measure_install = hb_energy_config.folders.honeybee_openstudio_gem_path
        if measure_install:
            gem_file = os.path.join(measure_install, 'files', 'urbanopt_Gemfile')
            if os.path.isfile(gem_file):
                return gem_file
        return None

    @staticmethod
    def _find_reopt_assumptions_path():
        """Find the REopt assumptions that's distributed with honeybee-openstudio-gem."""
        measure_install = hb_energy_config.folders.honeybee_openstudio_gem_path
        if measure_install:
            reopt_file = os.path.join(measure_install, 'files', 'reopt_assumptions.json')
            if os.path.isfile(reopt_file):
                return reopt_file
        return None

    @staticmethod
    def _find_urbanopt_cli_path():
        """Find the most recent URBANopt CLI in its default location."""
        def getversion(urbanopt_path):
            """Get digits for the version of OpenStudio."""
            try:
                ver = ''.join(s for s in urbanopt_path if (s.isdigit() or s == '.'))
                return sum(int(d) * (10 ** i)
                           for i, d in enumerate(reversed(ver.split('.'))))
            except ValueError:  # folder starting with 'openstudio' and no version
                return 0

        if os.name == 'nt':  # search the C:/ drive on Windows
            uo_folders = ['C:\\{}'.format(f) for f in os.listdir('C:\\')
                          if (f.lower().startswith('urbanopt') and
                              os.path.isdir('C:\\{}'.format(f)))]
        elif platform.system() == 'Darwin':  # search the Applications folder on Mac
            uo_folders = \
                ['/Applications/{}'.format(f) for f in os.listdir('/Applications/')
                 if (f.lower().startswith('urbanopt') and
                     os.path.isdir('/Applications/{}'.format(f)))]
        elif platform.system() == 'Linux':  # search the usr/local folder
            uo_folders = ['/usr/local/{}'.format(f) for f in os.listdir('/usr/local/')
                          if (f.lower().startswith('urbanopt') and
                              os.path.isdir('/usr/local/{}'.format(f)))]
        else:  # unknown operating system
            uo_folders = None

        if not uo_folders:  # No Openstudio installations were found
            return None

        # get the most recent version of OpenStudio that was found
        uo_path = sorted(uo_folders, key=getversion, reverse=True)[0]
        return uo_path


"""Object possesing all key folders within the configuration."""
folders = Folders(mute=True)
