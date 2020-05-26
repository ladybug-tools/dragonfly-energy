"""dragonfly_energy configurations.

Import this into every module where access configurations are needed.

Usage:

.. code-block:: python

    from dragonfly_energy.config import folders
    print(folders.mapper_path)
    folders.mapper_path = "C:/Urbanopt_test/Honeybee.rb"
"""
import honeybee_energy.config as hb_energy_config

import os
import json


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
        * config_file
        * mute
    """

    def __init__(self, config_file=None, mute=True):
        self.mute = bool(mute)  # set the mute value
        self.config_file  = config_file  # load paths from the config JSON file

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
        self._mapper_path = path  #set the mapper_path
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
        self._urbanopt_gemfile_path = path  #set the urbanopt_gemfile_path
        if path and not self.mute:
            print("Path to URBANopt Gemfile is set to: %s" % path)

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
            "urbanopt_gemfile_path": r''
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

        # set paths for mapper_path and urbanopt_gemfile_path
        self.mapper_path = default_path["mapper_path"]
        self.urbanopt_gemfile_path = default_path["urbanopt_gemfile_path"]

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


"""Object possesing all key folders within the configuration."""
folders = Folders(mute=True)
