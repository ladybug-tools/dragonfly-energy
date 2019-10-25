[![Build Status](https://travis-ci.org/ladybug-tools/dragonfly-energy.svg?branch=master)](https://travis-ci.org/ladybug-tools/dragonfly-energy)
[![Coverage Status](https://coveralls.io/repos/github/ladybug-tools/dragonfly-energy/badge.svg?branch=master)](https://coveralls.io/github/ladybug-tools/dragonfly-energy)

[![Python 2.7](https://img.shields.io/badge/python-2.7-green.svg)](https://www.python.org/downloads/release/python-270/) [![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)

# dragonfly-energy

Dragonfly extension for energy simulation.

## Installation
```console
pip install dragonfly-energy
```

## QuickStart
```python
import dragonfly_energy

```

## [API Documentation](http://ladybug-tools.github.io/dragonfly-energy/docs)

## Local Development
1. Clone this repo locally
```console
git clone git@github.com:ladybug-tools/dragonfly-energy

# or

git clone https://github.com/ladybug-tools/dragonfly-energy
```
2. Install dependencies:
```console
cd dragonfly-energy
pip install -r dev-requirements.txt
pip install -r requirements.txt
```

3. Run Tests:
```console
python -m pytest tests/
```

4. Generate Documentation:
```console
sphinx-apidoc -f -e -d 4 -o ./docs ./dragonfly_energy
sphinx-build -b html ./docs ./docs/_build/docs
```
