from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

import pygame
from pygame import BLEND_RGBA_ADD, BLEND_RGBA_MULT

__all__ = ["Light", "LightBox", "Wall"]


class Light:
    """
    Holds the attributes for the light and offers some basic interface instructions.
    """

    def __init__(
        self,
        pos: List[int],
        radius: int,
        light_img: pygame.Surface,
        color: Tuple[int, int, int] = (255, 255, 255),
        alpha: int = 255,
    ):
        self._base_position: List[int] = pos  # screen position
        self.position: List[int] = pos
        self._base_radius: int = radius  # screen size
        self.radius: int = radius
        self._base_light_img: pygame.Surface = pygame.transform.scale(light_img, (radius * 2, radius * 2))
        self._colored_light_img: pygame.Surface = self._base_light_img.copy()
        self.light_img: pygame.Surface = self._base_light_img.copy()
        self.alpha: int = alpha
        self.color: Tuple[int, int, int] = color
        self.timer: int = 1  # timer for wave/pule of light
        self.flicker_timer: int = 1  # timer for jumping flicker
        self.variance = 0  # how much variance from radius due to flicker
        self.variance_size = int(self._base_radius / 30)

        self._calculate_light_img()

    def update(self):
        base_radius = self._base_radius
        variance_size = self.variance_size

        # increment wave timer
        self.timer += 1
        self.set_size(int((1 + math.sin(self.timer / 10)) + (base_radius + self.variance)))

        # decrement flicker timer
        self.flicker_timer -= 1

        # update for flickering effect
        if self.flicker_timer < 0:
            # scale size
            self.variance = random.randint(-variance_size, variance_size)
            radius = base_radius + self.variance
            self.set_size(radius)

            # alpha variance
            alpha_variance = int(self.variance)
            self.set_alpha(max(0, min(255, self.alpha + alpha_variance)))

            # set new timer
            self.flicker_timer = random.randint(30, 60)

    def _calculate_light_img(self):
        """
        Alter the original light image by all of the attributes given, e.g. alpha, color, etc.
        """
        self._colored_light_img = mult_color(set_mask_alpha(self._base_light_img, self.alpha), self.color)
        self.light_img = self._colored_light_img.copy()

    def set_alpha(self, alpha: int):
        """
        Set the alpha value of the light. Refreshes the mask and size.
        """
        self.alpha = alpha
        self._colored_light_img = set_mask_alpha(self._base_light_img, self.alpha)
        self.set_size(self.radius)

    def set_color(self, color: Tuple[int, int, int], override_alpha: bool = False):
        """
        Set the color of the light. Refreshes the size. If `override_alpha` is set to `True`, the alpha setting is
        ignored when recalculating the light. This is better for performance.
        """
        self.color = color
        if override_alpha:
            self._colored_light_img = mult_color(self._base_light_img, self.color)
        else:
            self._calculate_light_img()
        self.set_size(self.radius)

    def set_size(self, radius: int):
        """
        Set the size of the light and rescale the image to match.
        """
        self.radius = radius
        self.light_img = pygame.transform.scale(self._colored_light_img, (radius * 2, radius * 2))


class LightBox:
    """
    Handles the processing of Lights.
    The name "LightBox" comes from the idea that the lighting is only rendered within the "box" of the display.

    The dimensions provided upon initialization will usually be the dimensions of your display. The `blit_flags`
    argument determines the blitting flags used in `LightBox.render()`. By default, it uses the adding flags which
    adds light values. However, other flags such as `BLEND_RGBA_MULT` can be used. `BLEND_RGBA_MULT` multiplies the
    destination surface by the lighting surface which results in darkening the areas that aren't lit up instead of
    brightening the areas that are.
    """

    def __init__(self, size: Tuple[int, int], blit_flags: int = BLEND_RGBA_ADD):
        self.vision_box_r: pygame.Rect = pygame.Rect(0, 0, size[0], size[1])
        #  The position of this rect should be `[0, 0]` as the top left of a window's coordinates are also `[0,
        #  0]`. Terrain offset is applied elsewhere. We can adjust the size of this rect to adjust the size of your
        #  visible area using the `pygame.Rect.width` and the `pygame.Rect.height` attributes.

        self.walls: List[Wall] = []

        # dict for storing walls by chunk
        self.chunk_walls: Dict = {}
        # size of chunks (tweak for better performance)
        self.chunk_size: int = 80
        # the amount of extra chunks in each direction the game should process (necessary for large lights outside
        # the light box)
        self.chunk_overshoot: int = 1

        # dict for storing dynamic walls
        self.dynamic_walls: Dict = {}
        # keeps track of the IDs for dynamic walls so they have different IDs
        self.dynamic_wall_id: int = 0

        self.lights: Dict[str, Light] = {}

        # keeps track of IDs for lights so that each new light has a different ID
        # converted to str when added to dict
        self.light_id: int = 0

        self.blit_flags: int = blit_flags

    def add_walls(self, walls: List[Wall]):
        """
        Add walls to the lightbox.
        This is used for manual wall additions, however, typically, walls are loaded using generate_walls.
        """
        self.walls += walls

        # split walls into all the chunks they cross
        # this creates duplicates, but the name keys can be put into a dict to efficiently remove duplicates
        for wall in walls:
            wall_str = point_str(wall.p1) + ";" + point_str(wall.p2) + ";" + str(wall.direction)
            p1_chunk = get_chunk(wall.p1, self.chunk_size)
            p2_chunk = get_chunk(wall.p2, self.chunk_size)
            chunk_list = []
            if p1_chunk != p2_chunk:
                if abs(p1_chunk[0] - p2_chunk[0]) > 0:
                    for i in range(max(p1_chunk[0], p2_chunk[0]) - min(p1_chunk[0], p2_chunk[0]) + 1):
                        chunk_list.append([min(p1_chunk[0], p2_chunk[0]) + i, p1_chunk[1]])
                elif abs(p1_chunk[1] - p2_chunk[1]) > 0:
                    for i in range(max(p1_chunk[1], p2_chunk[1]) - min(p1_chunk[1], p2_chunk[1]) + 1):
                        chunk_list.append([p1_chunk[0], min(p1_chunk[1], p2_chunk[1]) + i])
            else:
                chunk_list = [p1_chunk, p2_chunk]
            for chunk in chunk_list:
                chunk_str = point_str(chunk)
                if chunk_str not in self.chunk_walls:
                    self.chunk_walls[chunk_str] = {}
                self.chunk_walls[chunk_str][wall_str] = wall

    def clear_walls(self):
        """
        Delete all walls.
        """
        self.walls = []
        self.chunk_walls = {}

    def add_dynamic_walls(self, walls: List[Wall]) -> str:
        """
        Add a dynamic wall and return the dynamic wall id.
        This works similarly to add_walls, it just uses a different system in the background that allows
        modification but performs worse.
        """
        self.dynamic_wall_id += 1
        self.dynamic_walls[str(self.dynamic_wall_id)] = walls
        return str(self.dynamic_wall_id)

    def update_dynamic_walls(self, group_id: str, walls: List[Wall]):
        """
        Set a group_id to contain a set of walls. Existing walls can be modified directly for better performance
        since  objects use pointers.

        This is useful for overwriting the walls and takes walls in the same format as add_walls.
        """
        self.dynamic_walls[group_id] = walls

    def delete_dynamic_walls(self, group_id: int):
        """
        Delete a group of walls.
        """
        del self.dynamic_walls[group_id]

    def add_light(self, light: Light) -> str:
        """
        Create a new light with a light object. Returns the light id.
        """
        self.light_id += 1
        self.lights[str(self.light_id)] = light
        return str(self.light_id)

    def get_light(self, light_id: str):
        """
        Get a light object based on ID.
        Often used so that the position can then be modified.
        """
        return self.lights[light_id]

    def delete_light(self, light_id: str):
        """
        Delete a light.
        """
        del self.lights[light_id]

    def _get_max_light_radius(self):
        """
        Get max light radius.
        """
        max_radius = 0
        for light in self.lights:
            max_radius = max(max_radius, self.lights[light].radius)

        return max_radius

    def render(self, target_surf: pygame.Surface, offset: Optional[List[int]] = None):
        """
        The core rendering function that renders the lighting within the lightbox. The offset is used to specify
        the terrain offset (aka camera offset or scroll) of the game relative to the viewed area.

        The `target_surface` is the `pygame.Surface` that will have the lighting rendered onto it. If it is a black
        surface, you get the internal lighting mask. This can be useful for static lighting. However, normally the
        main display surface should be used.
        """
        # avoid mutable default
        if offset is None:
            offset = [0, 0]
        assert isinstance(offset, list)

        # get the max light radius to determine which lights need to be rendered
        # if a light center is farther away from the viewing range than its radius, it's off the screen
        # if the light's modifications don't reach onto the screen, then its shadows won't have an effect,
        # so it's not necessary to process
        max_radius = self._get_max_light_radius()

        # define an updated render_box rect with respect to the terrain offset and the light range to determine which
        # walls needs to be processed
        render_box_r = pygame.Rect(
            -max_radius + offset[0],
            -max_radius + offset[1],
            self.vision_box_r.width + max_radius * 2,
            self.vision_box_r.height + max_radius * 2,
        )

        # get all visible walls by using the chunk indexes
        valid_wall_dict = {}
        for y in range(self.vision_box_r.height // self.chunk_size + self.chunk_overshoot * 2 + 1):
            for x in range(self.vision_box_r.width // self.chunk_size + self.chunk_overshoot * 2 + 1):
                chunk_str = (
                    str(int(x - self.chunk_overshoot // 2 + offset[0] // self.chunk_size))
                    + ";"
                    + str(int(y - self.chunk_overshoot // 2 + offset[1] // self.chunk_size))
                )
                if chunk_str in self.chunk_walls:
                    valid_wall_dict.update(self.chunk_walls[chunk_str])
        valid_walls = list(valid_wall_dict.values())
        for group in self.dynamic_walls:
            valid_walls += self.dynamic_walls[group]

        # adjust for offset to get the "shown position"
        valid_walls = [
            wall.clone_move([-offset[0], -offset[1]]) for wall in valid_walls if wall.rect.colliderect(render_box_r)
        ]

        # redefine the render_box rect with the terrain offset removed since the walls have been moved
        render_box_r = pygame.Rect(
            -max_radius,
            -max_radius,
            self.vision_box_r.width + max_radius * 2,
            self.vision_box_r.height + max_radius * 2,
        )

        # generate a Surface to render the lighting mask onto
        rendered_mask = pygame.Surface(self.vision_box_r.size)

        # iterate through all of the lights
        for light in self.lights.values():
            # apply the terrain offset
            light_pos = [light.position[0] - offset[0], light.position[1] - offset[1]]
            # check for visibility (don't forget that the current rect is adjusted for the radii of the lights)
            if render_box_r.collidepoint(light_pos):
                # apply lighting image
                light_instance_surf = light.light_img.copy()
                light_offset = [light_pos[0] - light.radius, light_pos[1] - light.radius]

                # draw over the light image with the shadows of each wall (the draw_shadow function only draws if
                # applicable, so a polygon isn't drawn every time)
                for wall in valid_walls:
                    wall.draw_shadow(light_instance_surf, light_pos, render_box_r, (0, 0, 0), light_offset)

                # blit lighting mask onto main surface with RGBA_ADD so that the lighting can accumulate
                rendered_mask.blit(light_instance_surf, light_offset, special_flags=BLEND_RGBA_ADD)

                # update the light
                light.update()

        # blit the final lighting mask onto the target surface
        target_surf.blit(rendered_mask, (0, 0), special_flags=self.blit_flags)

        # return the list of visible walls in case they need to be used for anything
        return valid_walls


class Wall:
    """
    Handles shadow casting within a Lightbox.
    """

    def __init__(
        self,
        p1: List[int],
        p2: List[int],
        vertical: int,
        direction: int,
        color: Tuple[int, int, int] = (255, 255, 255),
    ):
        self.p1 = p1
        self.p2 = p2

        # The vertical aspect of the wall that is used to determine direction for shadows (must be `1` or `0`).
        # Vertical refers to the direction of the face, not the direction of the wall, so if it's set to `1`,
        # the face  is up/down and the line that makes up the wall is horizontal.
        self.vertical = vertical

        # The direction of the wall (inward/outward). This must be set to `-1` or `1`. The direction refers to the
        # axis the wall is on based on `Wall.vertical` with `-1` being associated with the negative direction on the
        # associated axis.
        self.direction = direction
        self.color: Tuple[int, int, int] = color

        # generate the rect for light_box collisions
        self.rect: pygame.Rect = self._create_rect()

    def clone_move(self, offset: Tuple[int, int]) -> Wall:
        """
        Create a duplicate Wall with an offset.
        """
        return Wall(
            [self.p1[0] + offset[0], self.p1[1] + offset[1]],
            [self.p2[0] + offset[0], self.p2[1] + offset[1]],
            self.vertical,
            self.direction,
            self.color,
        )

    def _create_rect(self):
        """
        Create a rect using the points in the wall
        """
        r_p1 = [min(self.p1[0], self.p2[0]), min(self.p1[1], self.p2[1])]
        r_p2 = [max(self.p1[0], self.p2[0]), max(self.p1[1], self.p2[1])]
        # +1 in the x_size and y_size because straight walls have a width or height of 0

        return pygame.Rect(r_p1[0], r_p1[1], r_p2[0] - r_p1[0] + 1, r_p2[1] - r_p1[1] + 1)

    def _check_cast(self, source) -> int:
        # will return 1 (or True) if the direction/position of the wall logically allows a shadow to be cast
        if (source[self.vertical] - self.p1[self.vertical]) * self.direction < 0:
            return 1
        else:
            return 0

    @staticmethod
    def _determine_cast_endpoint(source, point, vision_box):
        """
        Determine the point on the vision_box's edge that is collinear to the light and the endpoint of the Wall.
        This must be called for each endpoint of the wall.
        """
        difx = source[0] - point[0]
        dify = source[1] - point[1]
        try:
            slope = dify / difx
        # questionable, but looks alright
        except ZeroDivisionError:
            slope = 999999
        if slope == 0:
            slope = 0.000001

        # since the vision_box's edges are being treated as lines, there are technically 2 collinear points on the
        # vision box's edge
        # one must be a horizontal side and the other must be vertical since the 2 points must be on adjacent sides

        # determine which horizontal and which vertical sides of the vision box are used (top/bottom and left/right)
        cast_hside = 0
        cast_vside = 0
        if difx < 0:
            cast_hside = 1
        if dify < 0:
            cast_vside = 1

        # calculate the collinear points with quick mafs
        if cast_hside:
            hwall_p = [vision_box.right, slope * (vision_box.right - source[0]) + source[1]]
        else:
            hwall_p = [vision_box.left, slope * (vision_box.left - source[0]) + source[1]]
        if cast_vside:
            vwall_p = [(vision_box.bottom - source[1]) / slope + source[0], vision_box.bottom]
        else:
            vwall_p = [(vision_box.top - source[1]) / slope + source[0], vision_box.top]

        # calculate closer point out of the 2 collinear points and return side used
        if (abs(hwall_p[0] - source[0]) + abs(hwall_p[1] - source[1])) < (
            abs(vwall_p[0] - source[0]) + abs(vwall_p[1] - source[1])
        ):
            # horizontal sides use numbers 2 and 3
            return hwall_p, cast_hside + 2
        else:
            # vertical sides use numbers 0 and 1
            return vwall_p, cast_vside

    def _get_intermediate_points(self, p1_side, p2_side, vision_box):
        """
        Get the corner points for the polygon.
        If the casted shadow points for walls are on different vision_box sides, the corners between the points must
        be added.
        """
        # the "sides" refer to the sides of the vision_box that the wall endpoints casted onto
        # 0 = top, 1 = bottom, 2 = left, 3 = right
        sides = [p1_side, p2_side]
        sides.sort()
        # return the appropriate sides based on the 2 sides
        # the first 4 are the cases where the 2 shadow points are on adjacent sides
        if sides == [0, 3]:
            return [vision_box.topright]
        elif sides == [1, 3]:
            return [vision_box.bottomright]
        elif sides == [1, 2]:
            return [vision_box.bottomleft]
        elif sides == [0, 2]:
            return [vision_box.topleft]
        # these 2 are for when the shadow points are on opposite sides (normally happens when the light source is
        # close to the wall)
        # the intermediate points depend on the direction the shadow was cast in this case (they could be on either
        # side without knowing the direction)
        elif sides == [0, 1]:
            if self.direction == -1:
                return [vision_box.topleft, vision_box.bottomleft]
            else:
                return [vision_box.topright, vision_box.bottomright]
        elif sides == [2, 3]:
            if self.direction == -1:
                return [vision_box.topleft, vision_box.topright]
            else:
                return [vision_box.bottomleft, vision_box.bottomright]
        # this happens if the sides are the same, which would mean the shadow doesn't cross sides and has no
        # intermediate points
        else:
            return []

    def draw_shadow(
        self,
        surf: pygame.Surface,
        source: List[int],
        vision_box: pygame.Rect,
        color: Tuple[int, int, int],
        offset: Optional[List[int]] = None,
    ):
        """
        Draw a shadow, as cast by the light source.

        Primarily used internally by the `LightBox` class, but it's available for independent use if you want to do
        something crazy. In this context, `light_source` is point (`[x, y]`), not a `Light` object. The `vision_box`
        is just a `pygame.Rect` that specifies the visible area. The `color` is the color of the shadow. In normal
        use, the shadow is black and used to create a mask, but you can do some weird stuff by changing the color.
        """
        # avoid mutable default
        if offset is None:
            offset = [0, 0]
        assert isinstance(offset, list)

        # check if a shadow needs to be casted
        if self._check_cast(source):

            # calculate the endpoints of the shadow when casted on the edge of the vision_box
            p1_shadow, p1_side = self._determine_cast_endpoint(source, self.p1, vision_box)
            p2_shadow, p2_side = self._determine_cast_endpoint(source, self.p2, vision_box)

            # calculate the intermediate points of the shadow (see the function for a more detailed description)
            intermediate_points = self._get_intermediate_points(p1_side, p2_side, vision_box)

            # arrange the points of the polygon
            points = [self.p1] + [p1_shadow] + intermediate_points + [p2_shadow] + [self.p2]

            # apply offset
            points = [[p[0] - offset[0], p[1] - offset[1]] for p in points]

            # draw the polygon
            pygame.draw.polygon(surf, color, points)

    def render(self, surf: pygame.Surface, offset: Optional[List[int]] = None):
        """
        Render the line that makes up the wall.
        Mostly just useful for debugging.
        """
        # avoid mutable default
        if offset is None:
            offset = [0, 0]
        assert isinstance(offset, list)

        pygame.draw.line(
            surf,
            self.color,
            [self.p1[0] + offset[0], self.p1[1] + offset[1]],
            [self.p2[0] + offset[0], self.p2[1] + offset[1]],
        )


def box(pos: List[int], size: List[int]):
    """
    Generate a box of Walls with all walls facing outwards. The pos is the top left of the box. This list of walls can
    be added to a LightBox using LightBox.add_walls. Useful for custom wall generation.
    """
    walls = []
    walls.append(Wall([pos[0], pos[1]], [pos[0] + size[0], pos[1]], 1, -1))
    walls.append(Wall([pos[0], pos[1]], [pos[0], pos[1] + size[1]], 0, -1))
    walls.append(Wall([pos[0] + size[0], pos[1]], [pos[0] + size[0], pos[1] + size[1]], 0, 1))
    walls.append(Wall([pos[0], pos[1] + size[1]], [pos[0] + size[0], pos[1] + size[1]], 1, 1))
    return walls


def point_str(point) -> str:
    """
    Convert a point to a string
    """
    # some string conversion functions (since looking up strings in a dict is pretty fast performance-wise)
    return str(point[0]) + ";" + str(point[1])


def line_str(line, point) -> str:
    """
    Convert a line to a string
    """
    return point_str(line[point]) + ";" + str(line[2][0]) + ";" + str(line[2][1])


def str_point(string: str):
    """
    Convert string to point
    """
    return [int(v) for v in string.split(";")[:2]]


def set_mask_alpha(surf: pygame.Surface, alpha: int) -> pygame.Surface:
    """
    Set the alpha of the screen mask
    """
    return mult_color(surf, (alpha, alpha, alpha))


def mult_color(surf: pygame.Surface, color: Tuple[int, int, int]) -> pygame.Surface:
    """
    Multiply the color given on the provided surface.
    """
    mult_surf = surf.copy()
    mult_surf.fill(color)
    new_surf = surf.copy()
    new_surf.blit(mult_surf, (0, 0), special_flags=BLEND_RGBA_MULT)
    return new_surf


def get_chunk(point, chunk_size):
    return [point[0] // chunk_size, point[1] // chunk_size]


def generate_walls(light_box: LightBox, map_data: List[List[int]], tile_size: int) -> List[Wall]:
    """
    Adds walls to the designated light box using  a list of "air" (empty) tiles.

    Bordering sides will be joined together to reduce the wall count.  The tile locations in the map_data should be
    the grid positions. The positions are then multiplied by the tile_size to get the pixel positions of the
    tiles along with the coordinates of the sides. The returned data is just a list of Wall objects that were
    added to the given LightBox.
    """
    # looking up a string in a dict is significantly quicker than looking up in a list
    map_dict = {}
    lines = []

    # generate a dict with all of the tiles
    for tile in map_data:
        map_dict[str(tile[0]) + ";" + str(tile[1])] = 1

    # add all the walls by checking air tiles for bordering solid tiles (solid tiles are where there are no tiles in
    # the dict)
    for air_tile in map_data:
        # check all sides for each air tile
        if point_str([air_tile[0] + 1, air_tile[1]]) not in map_dict:
            # generate line in [p1, p2, [vertical, inside/outside]] format
            lines.append(
                [
                    [air_tile[0] * tile_size + tile_size, air_tile[1] * tile_size],
                    [air_tile[0] * tile_size + tile_size, air_tile[1] * tile_size + tile_size],
                    [0, -1],
                ]
            )
        if point_str([air_tile[0] - 1, air_tile[1]]) not in map_dict:
            lines.append(
                [
                    [air_tile[0] * tile_size, air_tile[1] * tile_size],
                    [air_tile[0] * tile_size, air_tile[1] * tile_size + tile_size],
                    [0, 1],
                ]
            )
        if point_str([air_tile[0], air_tile[1] + 1]) not in map_dict:
            lines.append(
                [
                    [air_tile[0] * tile_size, air_tile[1] * tile_size + tile_size],
                    [air_tile[0] * tile_size + tile_size, air_tile[1] * tile_size + tile_size],
                    [1, -1],
                ]
            )
        if point_str([air_tile[0], air_tile[1] - 1]) not in map_dict:
            lines.append(
                [
                    [air_tile[0] * tile_size, air_tile[1] * tile_size],
                    [air_tile[0] * tile_size + tile_size, air_tile[1] * tile_size],
                    [1, 1],
                ]
            )

    # reformat the data into a useful form for the geometry tricks later
    # this adds each endpoint to a dict as a key with the associated endpoint being in the list of associated values
    # (so 1 point can link to 2 bordering points where lines are connected)
    # it keys with respect to the vertical/horizontal aspect and the inward/outward aspect, so all lines that use the
    # same keys are part of a single joined line
    line_dict: Dict[str, List[str]] = {}
    for line in lines:
        for i in range(2):
            if line_str(line, i) in line_dict:
                line_dict[line_str(line, i)].append(line_str(line, 1 - i))
            else:
                line_dict[line_str(line, i)] = [line_str(line, 1 - i)]

    final_walls = []
    # keep track of the processed points so that those keys can be ignored (we add 4 points per line since each point
    # must be a key once and a value once)
    processed_points = []
    for point in line_dict:
        # the length of the items in this dict are the number of connected points
        # so if there's only 1 connected point, that means it's the end of a line
        # we can then follow the line's points to calculate the single line based off the connections
        if point not in processed_points:
            # look for the end of the line and skip all the others (since anything else must be connected to an end
            # due to the respect to direction)
            if len(line_dict[point]) == 1:
                # add this point to the list to ignore
                processed_points.append(point)
                offset = 1
                p1 = str_point(point)
                p2 = str_point(line_dict[point][0])
                # calculate the direction based on the 2 points
                direction = [(p2[0] - p1[0]) // tile_size, (p2[1] - p1[1]) // tile_size]
                # loop through the connected points until the other end is found
                while 1:
                    # generate the string for the next point
                    target_pos = (
                        str(p1[0] + direction[0] * offset * tile_size)
                        + ";"
                        + str(p1[1] + direction[1] * offset * tile_size)
                        + ";"
                        + point.split(";")[2]
                        + ";"
                        + point.split(";")[3]
                    )
                    # when the connected point only links to 1 point, you've found the other end of the line
                    processed_points.append(target_pos)
                    if len(line_dict[target_pos]) == 1:
                        break
                    offset += 1
                # append to the walls list based on the last point found and the starting point
                final_walls.append([p1, str_point(target_pos), int(point.split(";")[2]), int(point.split(";")[3])])

    # correct overshot edges (must be done after grouping for proper results) and generate Wall objects
    for wall in final_walls:
        grid_pos_x = wall[0][0]
        grid_pos_y = wall[0][1]

        # get tile location of wall
        tile_x = int(grid_pos_x // tile_size)
        tile_y = int(grid_pos_y // tile_size)

        # check for relevant bordering tiles to determine if it's okay to shorten the wall
        if not wall[2]:
            if wall[3] == 1:
                if [tile_x, tile_y + 1] in map_data:
                    wall[1][1] -= 1
            else:
                if [tile_x - 1, tile_y + 1] in map_data:
                    wall[1][1] -= 1

            # move right-facing wall inward
            if wall[3] == 1:
                wall[0][0] -= 1
                wall[1][0] -= 1
        else:
            if wall[3] == 1:
                if [tile_x + 1, tile_y] in map_data:
                    wall[1][0] -= 1
            else:
                if [tile_x + 1, tile_y - 1] in map_data:
                    wall[1][0] -= 1

            # move downward-facing wall inward
            if wall[3] == 1:
                wall[0][1] -= 1
                wall[1][1] -= 1

    # generate Wall objects
    _final_walls = [Wall(*wall) for wall in final_walls]

    # apply walls
    light_box.add_walls(_final_walls)

    # return the list just in case it's needed for something
    return _final_walls
