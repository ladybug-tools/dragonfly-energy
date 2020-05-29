# coding=utf-8
from dragonfly.properties import ModelProperties, BuildingProperties, StoryProperties, \
    Room2DProperties, ContextShadeProperties
import dragonfly.writer.model as model_writer

from .properties.model import ModelEnergyProperties
from .properties.building import BuildingEnergyProperties
from .properties.story import StoryEnergyProperties
from .properties.room2d import Room2DEnergyProperties
from .properties.context import ContextShadeEnergyProperties
from .writer import model_to_urbanopt


# set a hidden energy attribute on each core geometry Property class to None
# define methods to produce energy property instances on each Property instance
ModelProperties._energy = None
BuildingProperties._energy = None
StoryProperties._energy = None
Room2DProperties._energy = None
ContextShadeProperties._energy = None


def model_energy_properties(self):
    if self._energy is None:
        self._energy = ModelEnergyProperties(self.host)
    return self._energy


def building_energy_properties(self):
    if self._energy is None:
        self._energy = BuildingEnergyProperties(self.host)
    return self._energy


def story_energy_properties(self):
    if self._energy is None:
        self._energy = StoryEnergyProperties(self.host)
    return self._energy


def room2d_energy_properties(self):
    if self._energy is None:
        self._energy = Room2DEnergyProperties(self.host)
    return self._energy


def context_energy_properties(self):
    if self._energy is None:
        self._energy = ContextShadeEnergyProperties(self.host)
    return self._energy


# add energy property methods to the Properties classes
ModelProperties.energy = property(model_energy_properties)
BuildingProperties.energy = property(building_energy_properties)
StoryProperties.energy = property(story_energy_properties)
Room2DProperties.energy = property(room2d_energy_properties)
ContextShadeProperties.energy = property(context_energy_properties)


# add model writer to urbanopt
model_writer.urbanopt = model_to_urbanopt
