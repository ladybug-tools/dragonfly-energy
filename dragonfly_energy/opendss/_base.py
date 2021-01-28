# coding: utf-8
"""Base class for all OpenDSS geometry objects."""
from __future__ import division
import math

from ladybug_geometry.geometry2d.pointvector import Point2D, Vector2D
from honeybee.typing import valid_ep_string


class _GeometryBase(object):
    """A base class for all OpenDSS geometry objects.

    Args:
        identifier: Text string for a unique object ID.

    Properties:
        * identifier
        * display_name
        * geometry
    """
    __slots__ = ('_identifier', '_display_name', '_geometry')

    def __init__(self, identifier):
        """Initialize base object."""
        self.identifier = identifier
        self._display_name = None
        self._geometry = None

    @property
    def identifier(self):
        """Get or set the text string for unique object identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, identifier):
        self._identifier = valid_ep_string(identifier, 'identifier')

    @property
    def display_name(self):
        """Get or set a string for the object name without any character restrictions.

        If not set, this will be equal to the identifier.
        """
        if self._display_name is None:
            return self._identifier
        return self._display_name

    @display_name.setter
    def display_name(self, value):
        try:
            self._display_name = str(value)
        except UnicodeEncodeError:  # Python 2 machine lacking the character set
            self._display_name = value  # keep it as unicode

    @property
    def geometry(self):
        """Get a object geometry."""
        return self._geometry

    def move(self, moving_vec):
        """Move this object along a vector.

        Args:
            moving_vec: A ladybug_geometry Vector3D with the direction and distance
                to move the object.
        """
        self._geometry = self._geometry.move(Vector2D(moving_vec.x, moving_vec.y))

    def rotate_xy(self, angle, origin):
        """Rotate this object counterclockwise in the XY plane by a certain angle.

        Args:
            angle: An angle in degrees.
            origin: A ladybug_geometry Point3D for the origin around which the
                object will be rotated.
        """
        self._geometry = self._geometry.rotate(
            math.radians(angle), Point2D(origin.x, origin.y))

    def reflect(self, plane):
        """Reflect this object across a plane.

        Args:
            plane: A ladybug_geometry Plane across which the object will be reflected.
        """
        assert plane.n.z == 0, \
            'Plane normal must be in XY plane to use it on dragonfly object reflect.'
        norm = Vector2D(plane.n.x, plane.n.y)
        origin = Point2D(plane.o.x, plane.o.y)
        self._geometry = self._geometry.reflect(norm, origin)

    def scale(self, factor, origin=None):
        """Scale this object by a factor from an origin point.

        Args:
            factor: A number representing how much the object should be scaled.
            origin: A ladybug_geometry Point3D representing the origin from which
                to scale. If None, it will be scaled from the World origin (0, 0, 0).
        """
        ori = Point2D(origin.x, origin.y) if origin is not None else None
        self._geometry = self._geometry.scale(factor, ori)

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        new_obj = self.__class__(self.identifier)
        new_obj._display_name = self._display_name
        new_obj._geometry = self._geometry
        return new_obj

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'OpenDSS Base Object: %s' % self.display_name
