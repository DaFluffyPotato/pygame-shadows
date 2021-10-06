# pygame-shadows
a simple shadow library for Pygame

![](https://media.discordapp.net/attachments/758065135423062027/772293910440443924/gif_12.gif)

# Lighting Documentation
This is the documentation for this Pygame lighting module. Please note that this module requires Pygame 2. Some functions and attributes have been omitted as they are primary used internally. Please see the example script for the example usage. Many of these functions will not be needed in the average use case.

## Classes

### LightBox([size_x : int, size_y : int, blit_flags=BLEND_RGBA_ADD])
This is the main class of this module. It stores all of the lights and walls. At a top level, it represents the viewable area for the light. The dimensions provided upon initialization will usually be the dimensions of your display. The `blit_flags` argument determines the blitting flags used in `LightBox.render()`. By default, it uses the adding flags which adds light values. However, other flags such as `BLEND_RGBA_MULT` can be used. `BLEND_RGBA_MULT` multiplies the destination surface by the lighting surface which results in darkening the areas that aren't lit up instead of brightening the areas that are.
##### LightBox.add_light(light : Light) -> light_id
This function adds a `Light` object (provided as an argument) to the light box and returns a `light_id` that can be used to access the light later.
##### LightBox.get_light(light_id : str) -> Light
This function returns the `Light` object with the associated ID from the list of lights in the light box. The position, radius, and image for the light can be modified and it'll update within the light box since the light box points to that object. If you get a `KeyError`, the ID you searched for doesn't exist.
##### LightBox.del_light(light_id : str) -> Light
This function deletes a `Light` object from the light box based on the ID.
##### LightBox.add_walls(walls : list) -> None
This function adds a list of `Wall` objects to the light box. (To be clear, `walls` in the parameters should look something like `[Wall(), Wall(), Wall()]`.) This function is used for manual wall additions. Typically, terrain is loaded using the `generate_walls()` function.
##### LightBox.add_dynamic_walls(walls : list) -> wall_group_id
This function adds a group of dynamic walls that can be modified or deleted through the ID given. It works similarly to `LightBox.add_walls()`. It just uses a different system in the background that allows modification but performs worse.
##### LightBox.update_dynamic_walls(group_id : str, walls : list) -> None
This function updates the group of walls with the given ID. While this is useful for overwriting the walls and takes walls in the same format as `LightBox.add_walls()`. You can actually modify the existing walls that you originally passed to `LightBox.add_dynamic_walls()` for better performance by just modifying the original `Wall` objects since objects use pointers.
##### LightBox.del_dynamic_walls(group_id : str) -> None
This function deletes a group of walls based on the ID given.
##### LightBox.clear_walls() -> None
This function deletes all of the `Wall` objects associated with the light box.
##### LightBox.render(target_surface : pygame.Surface, offset=[0, 0]) -> visible_walls
This function is the primary lighting rendering function. The `target_surface` is the `pygame.Surface` that will have the lighting rendered onto it. If you render onto a black surface, you get the internal lighting mask. This technique can be useful for static lighting. However, normally you'll be rendering your lighting onto your main display surface. The `offset` is used to specify the terrain offset (aka camera offset or scroll) of the game relative to the viewed area.
##### LightBox.vision_box_r : pygame.Rect
This is the `pygame.Rect()` that represents the light box. The position of this rect should be `[0, 0]` as the top left of a window's coordinates are also `[0, 0]`. Terrain offset is applied elsewhere. You can adjust the size of this rect to adjust the size of your visible area using the `pygame.Rect.width` and the `pygame.Rect.height` attributes.
##### LightBox.walls : list
This is the list of walls contained within the light box. When used on a simple level, this attribute probably shouldn't be touched. Use `LightBox.add_walls()` and `LightBox.clear_walls()` instead. This is just a list of instances of the `Wall` class.
##### LightBox.lights : dict
This is a dictionary containing all of the `Light` objects. Since lights can be moved, it's setup to be accessed with light IDs (the keys of the dictionary). This attribute likely won't need to be touched. Use `LightBox.add_light()`, `LightBox.del_light()`, and `LightBox.get_light()` instead.

### Wall(p1 : list, p2 : list, vertical : int, direction : int, color=(255, 255, 255))
The class for the walls that cast shadows. The shadow calculation is done in this class. Refer to the associated attributes for more info on the parameters (these will be set upon initialization based on the parameters). Most of the time, `Wall` objects will be generated by the `generate_walls()` function. Please note that a few functions aren't listed here as they likely aren't useful on their own. More info is in the source code if you *really* want to look.
##### Wall.draw_shadow(target_surf : pygame.Surface, light_source : list, vision_box : pygame.Rect, color : tuple) -> None
The function for drawing the shadow for the wall onto the `target_surf` (a `pygame.Surface`). This function is primarily used internally by the `LightBox` class, but it's available for independent use if you want to do something crazy. In this context, `light_source` is point (`[x, y]`), not a `Light` object. The `vision_box` is just a `pygame.Rect` that specifies the visible area. The `color` is the color of the shadow. In normal use, the shadow is black and used to create a mask, but you can do some weird stuff by changing the color.
##### Wall.render(target_surf : pygame.Surface, offset=[0, 0]) -> None
A function for rendering the line that makes up the `Wall` onto the `target_surf` (`pygame.Surface`) with the specified `offset`. This module is primarily for rendering lighting though, so wall rendering is mostly just a debug tool.
##### Wall.p1 : list
The first endpoint of the wall. Stored in an `[x, y]` format.
##### Wall.p2 : list
The second endpoint of the wall.
##### Wall.vertical : int
The vertical aspect of the wall that is used to determine direction for shadows (must be `1` or `0`). Vertical refers to the direction of the face, not the direction of the wall, so if it's set to `1`, the face is up/down and the line that makes up the wall is horizontal.
##### Wall.direction : int
The direction of the wall (inward/outward). This must be set to `-1` or `1`. The direction refers to the axis the wall is on based on `Wall.vertical` with `-1` being associated with the negative direction on the associated axis.
##### Wall.color : tuple
A tuple in the form of `(red, green, blue)` with colors from in the range of `0-255`. This color is just used for rendering the wall if you choose to do so, but in most cases, the wall is invisible and is just used to calculate shadows.

### Light([x_pos : int, y_pos : int], radius : int, light_image : pygame.Surface)
The base object for lights for use in the `LightBox`. You will need to create some of these for use with the `LightBox.add_light()` function. See the associated attributes for more info on what the parameters are used for. The position list goes into `Light.position`. Please note that the `LightBox.get_light()` function returns `Light` objects so that you can manipulate existing lights using the attributes of the object.
##### Light.set_alpha(alpha : int) -> None
Sets the alpha of the `Light`. This is used to make a light dim.
##### Light.set_color((red : int, green : int, blue : int), override_alpha=False) -> None
Sets the color of the `Light`. If `override_alpha` is set to `True`, the alpha setting is ignored when recalculating the light. This is better for performance.
##### Light.set_size(radius : int) -> None
Set the radius of the `Light`. Please note that this must be an integer.
##### Light.position : list
The position of the light which is stored as `[x_pos, y_pos]`. You can modify this attribute to move the `Light`.
##### Light.radius : int
The radius of the light. If you modify this value, the `Light.light_img` will need to be updated to the appropriate size as well.
##### Light.light_img : pygame.Surface
The image associated with the light. It's resized to the appropriate scale upon initialization of the `Light`, but must be updated any time the `Light.radius` is changed.

## Standalone Functions

### generate_walls(light_box : LightBox, map_data : list, tile_size : int) -> walls_generated
This is the function for adding walls to the terrain based on a tile map (bordering sides will be joined to reduce the wall count). The `light_box` parameter is the `LightBox` object that the generated walls will automatically be added to. The `map_data` list is a list of air tiles. The list contains a bunch of tiles which are represented as lists in the form of `[x, y]`, so the `map_data` could look like `[[0, 0], [1, 0], [0, 2], [3, 9]]`. The tile locations should be the grid positions. The positions are then multiplied by the `tile_size` to get the pixel positions of the tiles along with the coordinates of the sides. The returned data is just a list of `Wall` objects that were added to the given `LightBox`.

### box([x_pos : int, y_pos: int], [size_x : int, size_y : int]) -> walls_generated
This is a function for generating a list of `Wall` objects in the shape of a box with all walls facing outwards. The `x_pos` and `y_pos` are the top left of the box. This list of walls can be added to a `LightBox` using `LightBox.add_walls()`.

# Credits

Original Lighting Module - DaFluffyPotato

Code Cleanup and PEP-ification - [@Snayff](https://github.com/Snayff)
