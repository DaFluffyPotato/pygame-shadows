#!/usr/bin/python3.4
# Setup Python ----------------------------------------------- #
import pygame, sys, math

import lighting

# Setup pygame/window ---------------------------------------- #
mainClock = pygame.time.Clock()
from pygame.locals import *
pygame.init()
pygame.display.set_caption('lighting example')
screen = pygame.display.set_mode((500, 500), 0, 32)

# load a map from a text file into the appropraite format for the lighting system
def load_map(map_id):
    f = open(map_id + '.txt', 'r')
    dat = f.read()
    f.close()
    tile_list = []
    y = 0
    for row in dat.split('\n'):
        x = 0
        for col in row:
            if col == '0':
                tile_list.append([x, y])
            x += 1
        y += 1
    return tile_list

# load the light image
light_img = pygame.image.load('light.png').convert()

# define the light box
light_box = lighting.LightBox(screen.get_size())

# create the lights (mouse_lights will contain a list of the light IDs)
# just setting a dummy position of [0, 0]. this will be moved later
mouse_lights = [light_box.add_light(lighting.Light([0, 0], 80, light_img, (100, 50, 255), 255)) for i in range(9)]
# light positions relative to the mouse
mouse_light_offsets = [[(i % 3 - 1) * 30, (i // 3 - 1) * 30] for i in range(9)]

map_data = load_map('map')
lighting.generate_walls(light_box, map_data, 25)
print(len(light_box.walls))

moving_box_id = light_box.add_dynamic_walls(lighting.box([1200, 100], [20, 20]))

light_color = [100, 50, 255]

offset = [0, 0]
up = False
down = False
right = False
left = False

timer = 0

# Loop ------------------------------------------------------- #
while True:
    
    # Background --------------------------------------------- #
    screen.fill((0, 0, 0))

    # Misc Processing ---------------------------------------- #

    timer += 1

    if right:
        offset[0] += 2
    if left:
        offset[0] -= 2
    if up:
        offset[1] -= 2
    if down:
        offset[1] += 2

    light_box.update_dynamic_walls(moving_box_id, lighting.box([1200 + math.sin(timer / 100) * 50, 100 + math.sin(timer / 72) * 100], [(1 + math.sin(timer / 60)) * 50, (1 + math.sin(timer / 65)) * 50]))

    # calculate new light color
    light_color = [100 + math.sin(timer / 10) * 100, 50 + math.sin(timer / 25) * 50, 200 + math.sin(timer / 15) * 55]
    # set alpha to 10%
    light_color = [v * 0.2 for v in light_color]

    # Update Lights ------------------------------------------ #
    mouse_light_offsets = [[(i % 3 - 1) * math.sin(timer / 40) * 60, (i // 3 - 1) * math.sin(timer / 40) * 60] for i in range(9)]
    mx, my = pygame.mouse.get_pos()
    for i, light in enumerate(mouse_lights):
        # True argument overrides light alpha for faster updates
        light_box.get_light(light).set_color(light_color, True)
        
        light_box.get_light(light).position = [offset[0] + mx + mouse_light_offsets[i][0], offset[1] + my + mouse_light_offsets[i][1]]
        light_box.get_light(light).set_size(int((1 + math.sin(timer / 15)) * 40 + 50))

    # Render ------------------------------------------------- #
    # lighting
    visible_walls = light_box.render(screen, offset)

    # wall lines
    for wall in visible_walls:
        wall.render(screen)

    # dots for light
    for m in mouse_light_offsets:
        pygame.draw.circle(screen, (255, 0, 0), (mx + m[0], my + m[1]), 3)
    
    # Buttons ------------------------------------------------ #
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == K_d:
                right = True
            if event.key == K_a:
                left = True
            if event.key == K_s:
                down = True
            if event.key == K_w:
                up = True
            if event.key == K_e:
                print('fps', int(mainClock.get_fps()))
            if event.key == K_q:
                print('visible walls:', len(visible_walls))
        if event.type == KEYUP:
            if event.key == K_d:
                right = False
            if event.key == K_a:
                left = False
            if event.key == K_s:
                down = False
            if event.key == K_w:
                up = False
                
    # Update ------------------------------------------------- #
    pygame.display.update()
    mainClock.tick(60)
    
