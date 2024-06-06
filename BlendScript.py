import bpy
from bpy_extras.object_utils import world_to_camera_view
import sys
import os
import json
import time
from mathutils import Euler, Matrix, Vector
import numpy

filepath = bpy.data.filepath

root = os.path.dirname(filepath)
if not root in sys.path:
    sys.path.append(root)
    
#This bit is present in both sets of code, and is used to make sure that file references direct to the right place
if not os.path.exists(root+r'\temp'):
    os.makedirs(root+r'\temp')

#These lines are setting up how images will be rendered    
bpy.context.scene.render.engine = 'BLENDER_EEVEE' #Set render engine
bpy.context.scene.eevee.taa_samples = 1 #Set antialiasing samples - smaller is faster, this is fastest
bpy.context.scene.eevee.taa_render_samples = 1 #Set render samples - as above
bpy.context.scene.render.image_settings.file_format='JPEG' #We are rendering images as .jpeg s
bpy.context.scene.render.filepath = root+r'\temp\renimg.jpg' #This is overwritten frequently

#Making sure that every panel which displays the 3D models is displaying in rendered mode, since our 'renders' are basically taking a screenshot of the panel, which is cheaper than rendering how it renders if you press the render image button (F12)
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type ='RENDERED'
   
def render():
    #Just a function to make the rendering command simpler 
    bpy.ops.render.opengl(write_still = True)

#These are fairly badly named, but they are the only object references required by the program    
Planecam = bpy.data.objects['Camera'] #The camera pointing straight at the screen
Perpcam = bpy.data.objects['Camera.001'] #The camera representing our physical head position
Screen = bpy.data.objects['Screen'] #The physical screen used by project_screen()

def switch_camera(cam):
    #We use this to quick switch the observer camera (the one we render with)
    if cam == Planecam:
        #Planecam points directly at the screen so this is the 'true' render, and requires that the screen is visible
        bpy.context.scene.render.filepath = root+r'\temp\renimg.jpg'
        Screen.hide_viewport = False
        Screen.hide_render = False
    else:
        #Perpcam represents our head position, so we want to see through the physical screen and render as temporary images which are distorted later
        bpy.context.scene.render.filepath = root+r'\temp\perimg.jpg'
        Screen.hide_viewport = True
        Screen.hide_render = True
    bpy.data.scenes['Scene'].camera = cam
    
def project_screen(screen = Screen):
    #This function projects the image of the perspective camera onto the physical screen object
    bpy.data.scenes['Scene'].camera = Perpcam
    #The next four lines make sure that the screen is selected
    bpy.ops.object.select_all(action = 'DESELECT')
    bpy.context.view_layer.objects.active = screen
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action= 'SELECT')
    #Set of for, ifs used to find a panel with the screen in it, then switch to edit mode
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    override = {'area': area, 'region': region, 'edit_object': bpy.context.edit_object}
                    #Project from view distorts the UVs of the screen so that they match the shape of the screen in the perspective cameras view
                    #If you don't know about UVs, in short they just map images onto the 3D objects
                    bpy.ops.uv.project_from_view(override , camera_bounds=True, correct_aspect=False, scale_to_bounds=False)
    #Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    #Render what we see from the perspective camera without a screen present
    switch_camera(Perpcam)
    render()
    #Update the internal image which is displayed on the screen
    bpy.data.images["perimg.jpg"].reload()
    #Upoate the 3D scene so that it uses the new images as textures, rather than old ones
    for area in bpy.context.screen.areas:
        if area.type in ['IMAGE_EDITOR', 'VIEW_3D']:
            area.tag_redraw()
    #Switch to the camera looking directly at the screen
    switch_camera(Planecam)
    #This final render is the actual output of this whole system
    render()
    
def get_corner_coords():
    #This function is used to give the image coordinates of the screen corners to the other python program, so we can do a simple warp deform
    scene = bpy.context.scene
    #Next four lines used to get the dimensions of rendered images
    render = scene.render
    res_x = render.resolution_x
    res_y = render.resolution_y
    resperc = render.resolution_percentage/100
    #RefPlane is an untextured version of Screen - it just has a vertex at each corner
    obj = bpy.data.objects['RefPlane']
    camera = Perpcam
    #Now we get a reference to RefPlane's vertices
    verts = (vert.co for vert in obj.data.vertices)
    #Find the image coordinates of these vertices according to the perspective camera
    coords_2d = [world_to_camera_view(scene, camera, coord) for coord in verts]
    i = 0
    dat = {}
    #This next section writes these corner coords to a .json file which the other program uses
    for x, y, distance_to_lens in coords_2d:
        dat.update({str(i):[x*res_x*resperc, y*res_y*resperc]})
        i += 1
    json_object = json.dumps(dat, indent = 4)
    with open(root+r'\temp\corndat.json', 'w') as outfile:
        outfile.write(json_object)
    
def set_cam_pos():
    #Here we open a .json file which tells us the coordinates of the camera, then move the perspective camera to this position
    #Perpcam has a built-in rotation modifier so it always looks at the center of the screen, we don't need to think about rotating it
    with open(root+r'\posfile.json', 'r') as openfile:
        json_object = json.load(openfile)
        if 'pos' in json_object:
            Perpcam.location.xyz = json_object['pos']

def loop_project():
    #Blender version of python doesn't like looping statements, but has an interior timer system requiring a function structured like this
    #This is the looping function which moves the camera and re-renders every 'frame'
    t1 = time.time()
    if not os.path.exists(root+r'\temp\perimg.jpg'):
        if os.path.exists(root+r'\posfile.json'):
            set_cam_pos()
            os.remove(root+r'\posfile.json')
        get_corner_coords()
        render()
    return time.time()-t1

#These are the main programs which are used to do the off-axis rendering for the python program
#The first 5 lines are just used to attempt to prevent errors
Screen.hide_viewport = True
Screen.hide_render = True
switch_camera(Perpcam)
get_corner_coords()
render()
bpy.app.timers.register(loop_project) #This is the main looper which makes the program repeat

#THE LOOP WILL NEVER STOP, IF YOU WANT TO STOP IT GO TO WINDOW -> TOGGLE SYSTEM CONSOLE, THEN CTRL+C

#The following is used to visually represent the off axis distortion
#This was how I originally did the distortion but it was slower than the current method
#Just comment out the main program and uncomment these, then run
#Screen.hide_viewport = False
#Screen.hide_render = False
#project_screen(Screen)