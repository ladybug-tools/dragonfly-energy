# coding=utf-8
"""Parameters for customizing the geometry in gbXML files."""
from __future__ import division

from honeybee.typing import valid_string


class GBXMLGeometryFormat(object):
    """Customize the representation of geometry within a gbXML.

    Args:
        merge_method: An optional text string to describe how the rooms are
            merged into gbXML Spaces during the translation. Specifying a
            value here can be an effective way to reduce the number of Spaces
            in the resulting gbXML and, ultimately, yield a faster simulation
            ime in the destination engine with fewer results to manage. Note
            that rooms will only be merged if they form a continuous
            volume. Otherwise, there can be multiple gbXML Spaces per
            zone or story, each with an integer added at the end of their
            identifiers. (Default: None). Choose from the following options.

            * None - No merging will occur
            * Zones - Rooms in the same zone will be merged
            * PlenumZones - Only plenums in the same zone will be merged
            * Stories - Rooms in the same story will be merged
            * PlenumStories - Only plenums in the same story will be merged

        include_shell_geometry: Boolean for whether shell geometry should be included vs.
            just the minimal required non-manifold geometry. (Default: False).
        include_space_boundaries: Boolean for whether space boundaries should be included
             vs. just the minimal required non-manifold geometry. (Default: False).
        exclude_roofs: Boolean to note whether the sloped roof geometries in the
            RoofSpecifications of the model are accounted for in the gbXML (False) or
            all rooms are simply extruded to their floor_to_ceiling_height (True).
            Setting to True is useful when exporting destination software that
            has no means of accounting for sloped roofs (eg. TRACE 3D Plus or
            HAP). (Default: False)
        exclude_shades: Boolean to note whether to include shade geometries in
            the gbXML as Surface elements (False) or whether they are excluded (True).
            Setting this to True is useful when exporting to destination software
            that does not account for shading geometry (eg. TRACE 700) since this
            will ensure that the extra Spaces for Detached Shades and Attached
            Shades are excluded from the gbXML. (Default: False).
        exclude_plenums: Boolean to indicate whether ceiling/floor plenum depths
            generate distinct separated plenum Spaces during the translation (False)
            or they are simply included with the parent room geometry (True).
            Setting this option to True is useful when the destination software
            allows for a more direct means of assigning plenum depths, which does
            not require explicit plenum geometry (eg. TRACE 700). (Default: False).
        opening_simplification: Optional text to note the method by which openings
            (including both windows and doors) are simplified as part of the
            translation to gbXML. (Default: None). Choose from the following options.

            * None - No sub-face simplification will occur
            * Rectangularized - Rect openings left as they are; all others rectangularized
            * MergeAdjWindows - Adjacent windows are merged; doors are left as is
            * MergeAdjWinToRect - Adjacent windows merged and the result rectangularized
            * SingleWindow - All doors removed; windows are merged into one per wall
            * SingleRectWindow - All doors removed; one rectangular window per wall

        triangulate_openings: Boolean to note whether openings (including both
            windows and doors) are triangulated if they have more than 4 sides (True)
            or whether they are left as they are (False). This triangulation is
            necessary when exporting to destination software that does
            not support openings with more than 4 vertices (eg. EnergyPlus/
            OpenStudio). (Default: False).
        triangulate_non_planar: Boolean to note whether any non-planar shade geometry
            in the model should be triangulated. This may be necessary when the
            model may contain non-planar geometry and destination software
            provides no means of correcting it. (Default: False).
        rect_geo_format: Text string to note how the rectangular geometry for
            all Surfaces is written into the gbXML. BoundingRectangle sets the
            width and height of the rectangular geometry using the bounding
            rectangle around the geometry, which results in an overestimated
            area for non-rectangular geo. SimpleArea will set the rectangle width
            always equal to geometry area and the height always equal to one,
            ensuring accurate areas and making it easy to check the geometry
            area in the gbXML. SimpleAreaForNonRectOnly will report the width and
            height of rectangular Face3D correctly but use simpler areas
            for non-rectangular geometry. (Default: BoundingRectangle). Choose
            from the following.

            * BoundingRectangle
            * SimpleArea
            * SimpleAreaForNonRectOnly

        explicit_holes: Boolean to note whether holes in Surfaces should be
            represented explicitly with their own PolyLoop or the hole and boundary
            should be collapsed into a single PolyLoop that winds inwards to
            cut out the holes. (Default: False).
        ignore_multipliers: Boolean to note whether story multipliers are accounted
            for in the gbXML by explicitly converting multipliers to geometry (False)
            or whether they are completely ignored (True). Given that gbXML has
            no support for assigning multipliers to Spaces and is a non-manifold
            geometry schema that relies on all geometry being modeled explicitly,
            this parameter should almost never be set to True. However, if the
            destination software supports a means of assigning the multipliers
            to spaces after importing the gbXML (eg. TRACE 700), it may be useful
            to set this to True. (Default: False).
        ignore_ceiling_adjacencies: Boolean to note whether adjacencies between
            stories are correctly accounted for (False) or they are ignored as
            part of the translation (True). Given that gbXML is fundamentally a
            non-manifold geometry schema, this parameter should almost never
            be set to True. However, if the destination software supports simulating
            each story as a distinct entity, this may be useful. (Default: False).

    Properties:
        * merge_method
        * include_shell_geometry
        * include_space_boundaries
        * exclude_roofs
        * exclude_shades
        * exclude_plenums
        * opening_simplification
        * triangulate_openings
        * triangulate_non_planar
        * rect_geo_format
        * explicit_holes
        * ignore_multipliers
        * ignore_ceiling_adjacencies
    """
    __slots__ = (
        '_merge_method', '_include_shell_geometry', '_include_space_boundaries',
        '_exclude_roofs', '_exclude_shades', '_exclude_plenums',
        '_opening_simplification', '_triangulate_openings',
        '_triangulate_non_planar', '_rect_geo_format', '_explicit_holes',
        '_ignore_multipliers', '_ignore_ceiling_adjacencies'
    )
    MERGE_METHODS = ('None', 'Zones', 'PlenumZones', 'Stories', 'PlenumStories')
    OPENING_SIMPLIFICATIONS = (
        'None', 'Rectangularized',
        'MergeAdjWindows', 'MergeAdjWinToRect'
        'SingleWindow', 'SingleRectWindow'
    )
    RECTANGULAR_FORMATS = (
        'BoundingRectangle', 'SimpleArea', 'SimpleAreaForNonRectOnly'
    )

    def __init__(
        self, merge_method=None, include_shell_geometry=False, include_space_boundaries=False,
        exclude_roofs=False, exclude_shades=False, exclude_plenums=False,
        opening_simplification=None, triangulate_openings=False, triangulate_non_planar=False,
        rect_geo_format='BoundingRectangle', explicit_holes=False,
        ignore_multipliers=False, ignore_ceiling_adjacencies=False
    ):
        """Initialize GBXMLGeometryFormat."""
        self.merge_method = merge_method
        self.include_shell_geometry = include_shell_geometry
        self.include_space_boundaries = include_space_boundaries
        self.exclude_roofs = exclude_roofs
        self.exclude_shades = exclude_shades
        self.exclude_plenums = exclude_plenums
        self.opening_simplification = opening_simplification
        self.triangulate_openings = triangulate_openings
        self.triangulate_non_planar = triangulate_non_planar
        self.rect_geo_format = rect_geo_format
        self.explicit_holes = explicit_holes
        self.ignore_multipliers = ignore_multipliers
        self.ignore_ceiling_adjacencies = ignore_ceiling_adjacencies

    @property
    def merge_method(self):
        """Get or set text for how rooms are merged into gbXML Spaces.

        Choose from the options below:

        * None
        * Zones
        * PlenumZones
        * Stories
        * PlenumStories
        """
        return self._merge_method

    @merge_method.setter
    def merge_method(self, value):
        if value is not None:
            clean_input = valid_string(value).lower()
            for key in self.MERGE_METHODS:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'merge_method {} is not recognized.\nChoose from the '
                    'following:\n{}'.format(value, self.MERGE_METHODS))
        self._merge_method = value

    @property
    def include_shell_geometry(self):
        """Get or set a boolean for whether shell geometry is included."""
        return self._include_shell_geometry

    @include_shell_geometry.setter
    def include_shell_geometry(self, value):
        self._include_shell_geometry = bool(value)

    @property
    def include_space_boundaries(self):
        """Get or set a boolean for whether space boundaries are included."""
        return self._include_space_boundaries

    @include_space_boundaries.setter
    def include_space_boundaries(self, value):
        self._include_space_boundaries = bool(value)

    @property
    def exclude_roofs(self):
        """Get or set a boolean for whether sloped roofs are excluded."""
        return self._exclude_roofs

    @exclude_roofs.setter
    def exclude_roofs(self, value):
        self._exclude_roofs = bool(value)

    @property
    def exclude_shades(self):
        """Get or set a boolean for whether shades are excluded."""
        return self._exclude_shades

    @exclude_shades.setter
    def exclude_shades(self, value):
        self._exclude_shades = bool(value)

    @property
    def exclude_plenums(self):
        """Get or set a boolean for whether plenums are excluded."""
        return self._exclude_plenums

    @exclude_plenums.setter
    def exclude_plenums(self, value):
        self._exclude_plenums = bool(value)

    @property
    def opening_simplification(self):
        """Get or set text for how openings are simplified.

        Choose from the options below:

        * None
        * Rectangularized
        * MergeAdjWindows
        * MergeAdjWinToRect
        * SingleWindow
        * SingleRectWindow
        """
        return self._opening_simplification

    @opening_simplification.setter
    def opening_simplification(self, value):
        if value is not None:
            clean_input = valid_string(value).lower()
            for key in self.OPENING_SIMPLIFICATIONS:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'opening_simplification {} is not recognized.\nChoose from the '
                    'following:\n{}'.format(value, self.OPENING_SIMPLIFICATIONS))
        self._opening_simplification = value

    @property
    def triangulate_openings(self):
        """Get or set a boolean for whether openings with >4 vertices are triangulated."""
        return self._triangulate_openings

    @triangulate_openings.setter
    def triangulate_openings(self, value):
        self._triangulate_openings = bool(value)

    @property
    def triangulate_non_planar(self):
        """Get or set a boolean for whether non planar shades are triangulated."""
        return self._triangulate_non_planar

    @triangulate_non_planar.setter
    def triangulate_non_planar(self, value):
        self._triangulate_non_planar = bool(value)

    @property
    def rect_geo_format(self):
        """Get or set text for how rectangular geometry is formatted.

        Choose from the options below:

        * BoundingRectangle
        * SimpleArea
        * SimpleAreaForNonRectOnly
        """
        return self._rect_geo_format

    @rect_geo_format.setter
    def rect_geo_format(self, value):
        if value is not None:
            clean_input = valid_string(value).lower()
            for key in self.RECTANGULAR_FORMATS:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'rect_geo_format {} is not recognized.\nChoose from the '
                    'following:\n{}'.format(value, self.RECTANGULAR_FORMATS))
        self._rect_geo_format = value

    @property
    def explicit_holes(self):
        """Get or set a boolean for whether holes are represented explicitly."""
        return self._explicit_holes

    @explicit_holes.setter
    def explicit_holes(self, value):
        self._explicit_holes = bool(value)

    @property
    def ignore_multipliers(self):
        """Get or set a boolean for whether story multipliers are ignored."""
        return self._ignore_multipliers

    @ignore_multipliers.setter
    def ignore_multipliers(self, value):
        self._ignore_multipliers = bool(value)

    @property
    def ignore_ceiling_adjacencies(self):
        """Get or set a boolean for whether adjacencies between stories are ignored."""
        return self._ignore_ceiling_adjacencies

    @ignore_ceiling_adjacencies.setter
    def ignore_ceiling_adjacencies(self, value):
        self._ignore_ceiling_adjacencies = bool(value)

    @classmethod
    def from_dict(cls, data):
        """Create a GBXMLGeometryFormat object from a dictionary.

        Args:
            data: A GBXMLGeometryFormat dictionary in following the format below.

        .. code-block:: python

            {
            "type": "GBXMLGeometryFormat",
            "merge_method": "Zones",
            "include_shell_geometry": True,
            "include_space_boundaries": True,
            "exclude_roofs": False,
            "exclude_shades": False,
            "exclude_plenums": False,
            "opening_simplification": "MergeAdjacentWindows",
            "triangulate_openings": False,
            "triangulate_non_planar": False,
            "simple_rect_areas": False,
            "explicit_holes": False,
            "ignore_multipliers": False,
            "ignore_ceiling_adjacencies": False
            }
        """
        # check that it is the correct type
        assert data['type'] == 'GBXMLGeometryFormat', \
            'Expected GBXMLGeometryFormat dictionary. Got {}.'.format(data['type'])
        mm = data['merge_method'] if 'merge_method' in data else None
        sg = data['include_shell_geometry'] if 'include_shell_geometry' in data else False
        sb = data['include_space_boundaries'] if 'include_space_boundaries' in data else False
        er = data['exclude_roofs'] if 'exclude_roofs' in data else False
        es = data['exclude_shades'] if 'exclude_shades' in data else False
        ep = data['exclude_plenums'] if 'exclude_plenums' in data else False
        ops = data['opening_simplification'] if 'opening_simplification' in data else None
        to = data['triangulate_openings'] if 'triangulate_openings' in data else False
        tnp = data['triangulate_non_planar'] if 'triangulate_non_planar' in data else False
        sra = data['simple_rect_areas'] if 'simple_rect_areas' in data else False
        eh = data['explicit_holes'] if 'explicit_holes' in data else False
        im = data['ignore_multipliers'] if 'ignore_multipliers' in data else False
        ica = data['ignore_ceiling_adjacencies'] \
            if 'ignore_ceiling_adjacencies' in data else False

        return cls(mm, sg, sb, er, es, ep, ops, to, tnp, sra, eh, im, ica)

    def to_dict(self):
        """GBXMLGeometryFormat dictionary representation."""
        return {
            'type': 'GBXMLGeometryFormat',
            'merge_method': self.merge_method,
            'include_shell_geometry': self.include_shell_geometry,
            'include_space_boundaries': self.include_space_boundaries,
            'exclude_roofs': self.exclude_roofs,
            'exclude_shades': self.exclude_shades,
            'exclude_plenums': self.exclude_plenums,
            'opening_simplification': self.opening_simplification,
            'triangulate_openings': self.triangulate_openings,
            'triangulate_non_planar': self.triangulate_non_planar,
            'simple_rect_areas': self.simple_rect_areas,
            'explicit_holes': self.explicit_holes,
            'ignore_multipliers': self.ignore_multipliers,
            'ignore_ceiling_adjacencies': self.ignore_ceiling_adjacencies
        }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return GBXMLGeometryFormat(
            self.self.merge_method,
            self.include_shell_geometry,
            self.include_space_boundaries,
            self.exclude_roofs,
            self.exclude_shades,
            self.exclude_plenums,
            self.opening_simplification,
            self.triangulate_openings,
            self.triangulate_non_planar,
            self.simple_rect_areas,
            self.explicit_holes,
            self.ignore_multipliers,
            self.ignore_ceiling_adjacencies
        )

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (
            self.self.merge_method, self.include_shell_geometry, self.include_space_boundaries,
            self.exclude_roofs, self.exclude_shades, self.exclude_plenums,
            self.opening_simplification, self.triangulate_openings,
            self.triangulate_non_planar, self.simple_rect_areas, self.explicit_holes,
            self.ignore_multipliers, self.ignore_ceiling_adjacencies
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, GBXMLGeometryFormat) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        """Represent GBXMLGeometryFormat."""
        return 'GBXMLGeometryFormat:'
