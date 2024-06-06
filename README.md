This system works by running a script in blender and another in a different python environment simultaneously - we run BlendScript.py in blender at the same time as Blend_LG.py.

I'm not sure if blender savefiles have persistent internal scripts or if they will need to be re-referenced. If you open LG_renderer_basic.blend and there is no script in the 'scripting' tab, simply navigate to text -> open and open BlendScript.py.
I am fairly certain that image file references will not work on different machines, so if you want to use the project_screen function in blender, you'll need to go to the shading tab, select 'Screen' in the object list and then reassign the image in the image texture material node.

As far as I know, I've removed all the machine-specific file paths I was previously using, but if there is one I missed you can replace the path with root + f'\{path to file within the folder the main files are in}'.

Let me know if you find an error, but otherwise I'm not working on this any more.
