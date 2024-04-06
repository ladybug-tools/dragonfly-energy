![Dragonfly](https://www.ladybug.tools/assets/img/dragonfly.png)

[![Build Status](https://github.com/ladybug-tools/dragonfly-energy/workflows/CI/badge.svg)](https://github.com/ladybug-tools/dragonfly-energy/actions)
[![Coverage Status](https://coveralls.io/repos/github/ladybug-tools/dragonfly-energy/badge.svg?branch=master)](https://coveralls.io/github/ladybug-tools/dragonfly-energy)

[![Python 3.10](https://img.shields.io/badge/python-3.10-orange.svg)](https://www.python.org/downloads/release/python-3100/) [![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/) [![Python 2.7](https://img.shields.io/badge/python-2.7-green.svg)](https://www.python.org/downloads/release/python-270/) [![IronPython](https://img.shields.io/badge/ironpython-2.7-red.svg)](https://github.com/IronLanguages/ironpython2/releases/tag/ipy-2.7.8/)

# dragonfly-energy

Dragonfly extension for energy simulation, including integration with the 
[EnergyPlus](https://github.com/NREL/EnergyPlus) simulation engine, the 
[OpenStudio](https://github.com/NREL/OpenStudio) SDK, and the
[URBANopt](https://docs.urbanopt.net/) SDK.

## Installation

`pip install dragonfly-energy`

To check if Dragonfly command line interface is installed correctly
use `dragonfly-energy --help`.

## QuickStart

```python
import dragonfly_energy
```

## [API Documentation](http://ladybug-tools.github.io/dragonfly-energy/docs)

## Usage
Since the building geometry in dragonfly is fundamentally 2D, creating a model of
a building and assigning energy model properties can be done with a few lines of
code. Here is an example:

```python
from dragonfly.model import Model
from dragonfly.building import Building
from dragonfly.story import Story
from dragonfly.room2d import Room2D
from dragonfly.windowparameter import SimpleWindowRatio
from honeybee_energy.lib.programtypes import office_program

# create the Building object
pts_1 = (Point3D(0, 0, 3), Point3D(0, 10, 3), Point3D(10, 10, 3), Point3D(10, 0, 3))
pts_2 = (Point3D(10, 0, 3), Point3D(10, 10, 3), Point3D(20, 10, 3), Point3D(20, 0, 3))
pts_3 = (Point3D(0, 10, 3), Point3D(0, 20, 3), Point3D(10, 20, 3), Point3D(10, 10, 3))
pts_4 = (Point3D(10, 10, 3), Point3D(10, 20, 3), Point3D(20, 20, 3), Point3D(20, 10, 3))
room2d_1 = Room2D('Office1', Face3D(pts_1), 3)
room2d_2 = Room2D('Office2', Face3D(pts_2), 3)
room2d_3 = Room2D('Office3', Face3D(pts_3), 3)
room2d_4 = Room2D('Office4', Face3D(pts_4), 3)
story = Story('OfficeFloor', [room2d_1, room2d_2, room2d_3, room2d_4])
story.solve_room_2d_adjacency(0.01)
story.set_outdoor_window_parameters(SimpleWindowRatio(0.4))
story.multiplier = 4
building = Building('OfficeBuilding', [story])

# assign energy properties
for room in story.room_2ds:
    room.properties.energy.program_type = office_program
    room.properties.energy.add_default_ideal_air()

# create the Model object
model = Model('NewDevelopment', [building])
```

Once a Dragonfly Model has been created, it can be converted to a honeybee Model,
which can then be converted to IDF format like so:

```python
# create the dragonfly Model object
model = Model('NewDevelopment', [building])

# serialize the dragonfly Model to Honeybee Models and convert them to IDF
hb_models = model.to_honeybee('Building', use_multiplier=False, tolerance=0.01)
idfs = [hb_model.to.idf(hb_model) for hb_model in hb_models]
```

The dragonfly model can also be serialized to a geoJSON to be simulated with URBANopt.

```python
from ladybug.location import Location

# create the dragonfly Model object
model = Model('NewDevelopment', [building])

# create a location for the geoJSON and write it to a folder
location = Location('Boston', 'MA', 'USA', 42.366151, -71.019357)
sim_folder = './tests/urbanopt_model'
geojson, hb_model_jsons, hb_models = model.to.urbanopt(model, location, folder=sim_folder)
```

## Local Development

1. Clone this repo locally
```
git clone git@github.com:ladybug-tools/dragonfly-energy

# or

git clone https://github.com/ladybug-tools/dragonfly-energy
```
2. Install dependencies:
```
cd dragonfly-energy
pip install -r dev-requirements.txt
pip install -r requirements.txt
```

3. Run Tests:
```
python -m pytest tests/
```

4. Generate Documentation:
```
sphinx-apidoc -f -e -d 4 -o ./docs ./dragonfly_energy
sphinx-build -b html ./docs ./docs/_build/docs
```
