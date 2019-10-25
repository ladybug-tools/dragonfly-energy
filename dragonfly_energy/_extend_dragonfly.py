# coding=utf-8
from dragonfly.properties import BuildingProperties, StoryProperties, Room2DProperties

from .properties.building import BuildingEnergyProperties
from .properties.story import StoryEnergyProperties
from .properties.room2d import Room2DEnergyProperties


# set a hidden energy attribute on each core geometry Property class to None
# define methods to produce energy property instances on each Property instance
BuildingProperties._energy = None
StoryProperties._energy = None
Room2DProperties._energy = None


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


# add energy property methods to the Properties classes
BuildingProperties.energy = property(building_energy_properties)
StoryProperties.energy = property(story_energy_properties)
Room2DProperties.energy = property(room2d_energy_properties)
