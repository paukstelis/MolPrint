# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

# Generic helper functions, to be used by any modules.

# Large portions borrowed from 3D Printing Tools AddOn
#TODO: Are all of these used?
import bpy
import bmesh
import math
import mathutils
import itertools
import random
import time
import copy
import addon_utils
from mathutils.bvhtree import BVHTree
from mathutils import Matrix,Vector
from collections import Counter
from decimal import *

def loadpins():
   filepath = bpy.context.scene.molprint_lists.directory+"/test.blend"
   with bpy.data.libraries.load(filepath) as (data_from, data_to):
      data_to.objects = data_from.objects

   for obj in data_to.objects:
      bpy.context.scene.objects.link(obj)
        
def bb_size(obj):

   x = obj.dimensions.x
   y = obj.dimensions.y
   z = obj.dimensions.z
   bbox_v = x*y*z
   return bbox_v
   
def makestrut(obj1,obj2):
    interactionlist = bpy.context.scene.molprint_lists.interactionlist
    strut_radius = bpy.context.scene.molprint.strut_radius
    dx = obj2.location.x - obj1.location.x
    dy = obj2.location.y - obj1.location.y
    dz = obj2.location.z - obj1.location.z
    
    dist = get_distance(obj1,obj2)
    bpy.ops.mesh.primitive_cylinder_add(
      vertices = bpy.context.scene.molprint.prim_detail,
      radius = strut_radius, 
      depth = dist,
      location = (dx/2 + obj1.location.x, dy/2 + obj1.location.y, dz/2 + obj1.location.z)   
    )
    phi = math.atan2(dy, dx) 
    theta = math.acos(dz/dist) 
    bpy.context.object.rotation_euler[1] = theta 
    bpy.context.object.rotation_euler[2] = phi
    strut = bpy.context.scene.objects.active
    strut["ptype"] = "Cylinder"
    strut["radius"] = strut_radius
    strut["hbond"] = True
    strut["pinlist"] = ["None"]
    strut["cutcube"] = ['None']
    strut["cone"] = ['None']
    strut["conelist"] = ['None']
    #Go ahead and update interaction list now
    if len(interactionlist) > 2:
        interactionlist.append((obj1,strut))
        interactionlist.append((obj2,strut))
 
def scalebonds(scale_val):
    for obj in bpy.context.scene.objects:
        if obj["ptype"] == 'Cylinder' and obj["hbond"] == 0:
            #scale the object
            obj.scale = (scale_val,1,scale_val)
            #reset the radius value
            obj["radius"] = obj["radius"]*scale_val 

def cylinder_between(pair):
  x2 = pair[1].location.x
  y2 = pair[1].location.y
  z2 = pair[1].location.z
  x1 = pair[0].location.x
  y1 = pair[0].location.y
  z1 = pair[0].location.z  
  dx = x2 - x1
  dy = y2 - y1
  dz = z2 - z1    
  ptb = bpy.context.scene.molprint.pintobond
  dist = get_distance(pair[0],pair[1])
  hbond = pair[1]["hbond"]
  phi = math.atan2(dy, dx) 
  theta = math.acos(dz/dist)
  split = bpy.context.scene.molprint.splitpins
  if not hbond:
    #If we are doing split pins 
    #First make a cone
    if split:
        r1 = pair[1]["radius"]*ptb*0.9
        r2 = pair[1]["radius"]*ptb*1.20
        #Consider doing two cones where cone2 would provide a slight bevel
        bpy.ops.mesh.primitive_cone_add(vertices=bpy.context.scene.molprint.pin_sides,
            radius1=r1,
            radius2=r2, 
            depth=pair[0]["radius"], 
            location=pair[0].location
        )
        cone1 = bpy.context.scene.objects.active
        bpy.context.object.rotation_euler[1] = theta 
        bpy.context.object.rotation_euler[2] = phi
        #Cutcube for later differencing, eventually add as user adjustable variable
        bpy.ops.mesh.primitive_cube_add(radius=r1*0.75, location=pair[0].location)
        cutcube = bpy.context.scene.objects.active
        bpy.context.active_object.dimensions = pair[0]["radius"]*1.75, r1*0.55, pair[0]["radius"]*1.45
        bpy.context.object.rotation_euler[1] = theta 
        bpy.context.object.rotation_euler[2] = phi
  
    r = pair[1]["radius"]*ptb
    bpy.ops.mesh.primitive_cylinder_add(
        vertices = bpy.context.scene.molprint.pin_sides,
        radius = r, 
        depth = dist,
        location = (dx/2 + x1, dy/2 + y1, dz/2 + z1)
    )
    pin = bpy.context.scene.objects.active
    bpy.context.object.rotation_euler[1] = theta 
    bpy.context.object.rotation_euler[2] = phi
    
    if split:
        bool_carve(pin,cone1,'UNION',modapp=True)
        clean_object()
        pin["cutcube"] = [cutcube.name]
        pin["cone"] = [cone1.name]
  else:
    r = pair[1]["radius"]*bpy.context.scene.molprint.h_pintobond
    bpy.ops.mesh.primitive_cylinder_add(
      vertices = bpy.context.scene.molprint.h_pin_sides,
      radius = r, 
      depth = dist,
      location = (dx/2 + x1, dy/2 + y1, dz/2 + z1)   
    )
    
    pin = bpy.context.scene.objects.active
    bpy.context.object.rotation_euler[1] = theta 
    bpy.context.object.rotation_euler[2] = phi
    pin["cutcube"] = ['None']
    pin["cone"] = ['None']
      
def bmesh_copy_from_object(obj, transform=True, triangulate=True, apply_modifiers=False):

    assert(obj.type == 'MESH')

    if apply_modifiers and obj.modifiers:
        me = obj.to_mesh(bpy.context.scene, True, 'PREVIEW', calc_tessface=False)
        bm = bmesh.new()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    else:
        me = obj.data
        if obj.mode == 'EDIT':
            bm_orig = bmesh.from_edit_mesh(me)
            bm = bm_orig.copy()
        else:
            bm = bmesh.new()
            bm.from_mesh(me)

    # Remove custom data layers to save memory
    for elem in (bm.faces, bm.edges, bm.verts, bm.loops):
        for layers_name in dir(elem.layers):
            if not layers_name.startswith("_"):
                layers = getattr(elem.layers, layers_name)
                for layer_name, layer in layers.items():
                    layers.remove(layer)

    if transform:
        bm.transform(obj.matrix_world)

    if triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces)

    return bm

def bmesh_check_intersect_objects(obj, obj2, selectface=False):

    assert(obj != obj2)
    # Triangulate in most cases, not if using CPK matching
    tris = True
    if selectface:
        tris = False
    bm = bmesh_copy_from_object(obj, transform=True, triangulate=tris)
    bm2 = bmesh_copy_from_object(obj2, transform=True, triangulate=tris)
    intersect = False
    BMT1 = BVHTree.FromBMesh(bm)
    BMT2 = BVHTree.FromBMesh(bm2)   
    overlap_pairs = BMT1.overlap(BMT2)

    if len(overlap_pairs) > 0:
       intersect = True
       
    if selectface:
        #deselect everything for both objects
        bpy.context.scene.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.context.scene.objects.active = obj2
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        for each in overlap_pairs:
            obj.data.polygons[each[0]].select = True
            obj.update_from_editmode()
            obj2.data.polygons[each[1]].select = True
            obj2.update_from_editmode()
            
    bm.free()
    bm2.free()
            
    return intersect

def clean_object():
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles()
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_interior_faces()
    bpy.ops.mesh.delete(type='FACE')
    bpy.ops.mesh.dissolve_limited()
    bpy.ops.object.mode_set(mode='OBJECT')

def get_distance(obj1, obj2):
    return  (obj1.location - obj2.location).length

#This is needed for older pymol vrml versions which added lots of extra primitive spheres
def isinside(obj1,obj2):
    #This is messy, but works reasonably well
    if bb_size(obj1) > bb_size(obj2):
        big = obj1
        small = obj2
    else:
        big = obj2
        small = obj1
    #Easier way to do this with Vectors? Had to do it this way because very small objects
    #could be inside very large objects, so location centers may not be close in some cases
    x1 = big.location.x
    x2 = small.location.x
    y1 = big.location.y
    y2 = small.location.y
    z1 = big.location.z
    z2 = small.location.z
       
    inside = True
    
    xdistance = math.sqrt((x1 - x2)**2)
    ydistance = math.sqrt((y1 - y2)**2)
    zdistance = math.sqrt((z1 - z2)**2)
    
    #This makes sure that the bounding box is fully inside
    #Might be an easier way to do?
    if xdistance+((small.dimensions.x)/2) > (big.dimensions.x)/2:
        inside = False
    if ydistance+((small.dimensions.y)/2) > (big.dimensions.y)/2:
        inside = False
    if zdistance+((small.dimensions.z)/2) > (big.dimensions.z)/2:
        inside = False
    if inside:
        return small
    else:
        return None
       
def updategroups():
    '''Generates a list of connected spheres/cylinders that will be an independent object'''
    #start = time.time()
    #Reset grouplist
    grouplist = []
    bpy.context.scene.molprint_lists.grouplist = []
    interaction_list = bpy.context.scene.molprint_lists.interactionlist
    #Run for each object that is selected in scene
    for each in (bpy.context.selected_objects):
        group = []
        #checks to see if the object is already part of a group
        if each in itertools.chain.from_iterable(grouplist):
            continue
        #determine if our current/next interaction will be cylinder of sphere. Must always alternate in this case, i.e. no sphere-sphere contacts
        if each["ptype"] == 'Sphere':
             i,j = 0,1 
        if each["ptype"] == 'Cylinder':
             i,j = 1,0 
        #This object defines the first member of a new group
        group.append(each)
        #This is a list of all interacters that we need to branch from for defining the group
        nextlist = [value[j] for value in interaction_list if value[i] == each and value[j] not in bpy.context.selected_objects]
        additions = True
        
        while additions:
            additionlist = []
            additions = False
            for nextobj in nextlist:
                group.append(nextobj)
                objinteract = [obj[i] for obj in interaction_list if obj[j] == nextobj]
                #print("Object inteaction list:", objinteract)
                for nexts in objinteract:
                    if nexts in group:
                        continue
                    if nextobj["ptype"] == 'Sphere' and nextobj in bpy.context.selected_objects and nexts in bpy.context.selected_objects:
                        continue
                    if nextobj["ptype"] == 'Cylinder' and nextobj in bpy.context.selected_objects and nexts in bpy.context.selected_objects:
                        continue
                    
                    additionlist.append(nexts)

            nextlist = []
            nextlist = additionlist 
            if len(nextlist) > 0:
                additions = True
            if i == 1:
                i,j = 0,1
            else:
                i,j = 1,0        
        grouplist.append(group)

    bpy.context.scene.molprint_lists.grouplist = grouplist
    #This updates materials - useful for small things, but might slow things down for bigger stuff   
    colors = material_colors(grouplist) 
    #Is creating materials each time a waste of resources? Probably    
    m = 0
    for each in grouplist:
        mat = makeMaterial('mat'+str(m),colors[m])
        for ob in each:    
            ob.data.materials.clear()
            ob.data.materials.append(mat)
        m += 1
      
    #end = time.time()
    #print("Update group seconds:", end-start)

    
def makeMaterial(name, diffuse):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = diffuse
    mat.diffuse_shader = 'LAMBERT' 
    mat.diffuse_intensity = 1.0 
    return mat

def material_colors(thelist):
    color_num = 0
    i = 1.0
    colors = []
    toggle_r = itertools.cycle([0,0.25,0.5,0.75,1])
    toggle_g = itertools.cycle([1.0, 0.66, 0.33, 0])
    toggle_b = itertools.cycle([1.0,0.33,0.25,0.66,0.05,0.75,0])
    while color_num <= len(thelist):
        r = next(toggle_r)
        g = next(toggle_g)
        b = next(toggle_b)
        colors.append((r,g,b))
        color_num+=1
    
    return colors        

def color_by_radius():
    '''Color every object in the model by radius value'''
    unique = radius_sort(bpy.context.scene.objects)
    colors = material_colors(bpy.context.scene.objects)
    
    m = 0
    for each in unique:
        mat = makeMaterial('mat'+str(m),colors[m])
        for ob in each:    
            ob.data.materials.clear()
            ob.data.materials.append(mat)
        m += 1
            
def getinteractions():
    '''Build a complete list of interactions between objects to speed up joining'''
    objlist = itertools.combinations(bpy.context.scene.objects, 2)
    interactionlist = []
    for each in objlist:

        if (each[0]["ptype"] == 'Cylinder') and (each[1]["ptype"] == 'Cylinder'):
            continue
        distance = get_distance(each[0],each[1])
        intersect = False
        if distance < 2:	
            intersect = bmesh_check_intersect_objects(each[0], each[1])
        if intersect:
            if each[0]["ptype"] == 'Sphere':
                interactionlist.append((each[0],each[1]))
           
            if each[0]["ptype"] == 'Cylinder':
                interactionlist.append((each[1],each[0]))     
                
    return interactionlist
    

def bool_carve(obj1,obj2,booltype,modapp=False):
    mymod = obj1.modifiers.new('simpmod', 'BOOLEAN')
    mymod.operation = booltype
    #mymod.double_threshold = 0.00001
    mymod.solver = 'CARVE'
    mymod.object = obj2
    if modapp:
        bpy.context.scene.objects.active = obj1
        bpy.ops.object.modifier_apply (modifier='simpmod')
    

def bool_bmesh(obj1,obj2,booltype,modapp=False):
    mymod = obj1.modifiers.new('simpmod', 'BOOLEAN')
    mymod.operation = booltype
    #mymod.double_threshold = 0.00001
    mymod.solver = 'BMESH'
    mymod.object = obj2
    if modapp:
        bpy.context.scene.objects.active = obj1
        bpy.ops.object.modifier_apply (modifier='simpmod')

def radius_sort(tosort):
#Create list that contains all objects by radius. Tosort is the list to sort from
    sortlist = [ob for ob in tosort]
    sortlist.sort(key = lambda o: o["radius"])
    unique = []
    for key, group in itertools.groupby(sortlist, lambda item: item["radius"]):
        unique.append(list(group))
    return unique
    
#This is the workhorse of the entire addon. Look for ways to speed up
def joinall():
    '''Join and apply pins to different groups'''
    updategroups()
    cylinders = []
    spheres = []
    pairs = []
    #Turn these off so it isn't constantly trying to update
    bpy.context.scene.molprint.interact = False
    bpy.context.scene.molprint.autogroup = False
    #start = time.time()
    #setup objects and pin pairs
    for ob in bpy.context.selected_objects:
 
        if ob.type == 'MESH' and ob["ptype"] == 'Cylinder':
            cylinders.append(ob)

        if ob.type == 'MESH' and ob["ptype"] == 'Sphere':
            spheres.append(ob)
         
    for cyl in cylinders:
        intersect = False
        for sphere in spheres:
            intersect = bmesh_check_intersect_objects(sphere, cyl)
            if intersect:
                pairs.append((sphere,cyl))
                
    #Sanity check to make sure pairs are in different groups, otherwise things explode
    for pair in pairs:
        p1group = next(((i) for i, group in enumerate(bpy.context.scene.molprint_lists.grouplist) if pair[0] in group), None)
        p2group = next(((i) for i, group in enumerate(bpy.context.scene.molprint_lists.grouplist) if pair[1] in group), None)
        #print(p1group,p2group)
        if p1group == p2group:
            pairs.remove(pair)
            
    #For print-in-place bonds, will need to up-scale sphere and then do carve or parts will be touching               
    for each in pairs:
        bool_bmesh(each[1],each[0],'DIFFERENCE',modapp=True)
            
    pinlist = []
    conelist = []
    oblist = []
    
    for each in pairs:
        #Make pin objects and give them a specific ptype   
        cylinder_between(each)
        #put the sphere and the pin cylinder into a list
        pin = bpy.context.scene.objects.active
        pin["ptype"] = 'pin'
        #Are these lists used for anything? check
        #pinlist.append(pin)
        #conelist.append(pin["cone"])
        each[0]["pinlist"] += [pin.name]
        if bpy.context.scene.molprint.splitpins:
            each[0]["conelist"] += pin["cone"]
            each[1]["cutcube"] += pin["cutcube"]
        #union cylinder and pin if normal mode
        bool_bmesh(each[1],pin,'UNION',modapp=True)
        bpy.ops.object.select_all(action='DESELECT')
    #TODO: Put each group into a thread to speed things up?   
    for group in bpy.context.scene.molprint_lists.grouplist:
        bpy.ops.object.select_all(action='DESELECT')
        pins = []
        cones = []
        cutcubes = []
        if bpy.context.scene.molprint.multicolor:
            cylob = None
            new_obs = []
            multis = radius_sort(group)
            origin_set=True
            origin = None
            for each in multis:
                pins = []
                cones = []
                cutcubes = []
                bpy.ops.object.select_all(action='DESELECT')
                
                for ob in each:
                    obpin = []
                    obcone = []
                    obcut = []
                    obpin[:] = (value for value in ob["pinlist"] if value != 'None')
                    obcone[:] = (value for value in ob["conelist"] if value != 'None')
                    obcut[:] = (value for value in ob["cutcube"] if value != 'None')
                    ob.select = True
                    pins = pins+obpin
                    cones = cones+obcone
                    cutcubes = cutcubes+obcut

                pins = list(set(pins))
                cones = list(set(cones))
                cutcubes = list(set(cutcubes))
                bpy.context.selected_objects[0]["pinlist"] = pins
                bpy.context.selected_objects[0]["conelist"] = cones
                bpy.context.selected_objects[0]["cutcube"] = cutcubes    
                bpy.context.scene.objects.active = bpy.context.selected_objects[0]
                bpy.ops.object.join()
                
                if origin_set:
                    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
                    origin = bpy.context.selected_objects[0].location
                    bpy.context.scene.cursor_location = origin
                    origin_set = False

                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                new_obs.append(bpy.context.selected_objects[0])
            
            cylob = next(value for value in new_obs if value["ptype"] == 'Cylinder')  
            sphereobs = [value for value in new_obs if value["ptype"] == 'Sphere']
            #Difference sphere and cyls
            #print(cylob,sphereobs)
            for sp in sphereobs:
                try:
                    bool_bmesh(cylob,sp,"DIFFERENCE",modapp=True)
                except:
                    continue
            #Cylinder fixing
            newcube = intersect_pin(cylob)
            cylob = newcube
            #Difference pinning
            if bpy.context.scene.molprint.splitpins:
                difference_pin(sp,sp["pinlist"],doscale=False)
                difference_pin(sp,sp["conelist"])
                difference_pin(cylob,cylob["cutcube"],doscale=False,carve=True)
            else:
                for sp in sphereobs:
                    difference_pin(sp,sp["pinlist"])
        
        #combine all pins objects for each group
        else:
            for obj in group:
                #print(obj)
                obpin = []
                obcone = []
                obcut = []
                obpin[:] = (value for value in obj["pinlist"] if value != 'None')
                obcone[:] = (value for value in obj["conelist"] if value != 'None')
                obcut[:] = (value for value in obj["cutcube"] if value != 'None')
                pins = pins+obpin
                cones = cones+obcone
                cutcubes = cutcubes+obcut
                obj.select = True
            #Make all objects of a group active and join    
            bpy.context.scene.objects.active = group[0]
            #Remove duplicates
            pins = list(set(pins))
            cones = list(set(cones))
            cutcubes = list(set(cutcubes))
            group[0]["pinlist"] = pins
            group[0]["conelist"] = cones
            group[0]["cutcube"] = cutcubes
            #print(pins)
            bpy.ops.object.join()
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
            mat = group[0].data.materials[0]
            newcube = intersect_pin(group[0])            
            newcube.data.materials.append(mat)
            #Do these if we are doing split pins
            if bpy.context.scene.molprint.splitpins:
                difference_pin(newcube,newcube["pinlist"],doscale=False,carve=True)
                difference_pin(newcube,newcube["conelist"])
                difference_pin(newcube,newcube["cutcube"],doscale=False,carve=True)
            else:
                difference_pin(newcube,newcube["pinlist"],carve=True)
            clean_object()    
    if bpy.context.scene.molprint.multicolor:
        color_by_radius()
        
def intersect_pin(ob):
    #print(ob)
    #start = time.time()
    pinlist = []
    conelist = []
    cutcubelist = []
    bpy.ops.mesh.primitive_cube_add(location=(ob.location))
    bpy.ops.transform.resize(value=(30, 30, 30))
    cube = bpy.context.selected_objects[0]
    cube["ptype"] = 'newcube'
    pinlist[:] = (value for value in ob["pinlist"] if value != 'None')
    cube["pinlist"] = pinlist
    conelist[:] = (value for value in ob["conelist"] if value != 'None')
    cube["conelist"] = conelist
    cutcubelist[:] = (value for value in ob["cutcube"] if value != 'None')
    cube["cutcube"] = cutcubelist
    
    cube["radius"] = ob["radius"]
    bool_carve(cube,ob,'INTERSECT',modapp=True)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select = True
    bpy.ops.object.delete()       
    #end = time.time()
    #print("Intersect unionization time:",end-start)
    return cube
    
def difference_pin(obj,thelist,doscale=True,carve=False):
    pinscale = bpy.context.scene.molprint.pinscale
    if len(thelist) > 0:
        bpy.ops.object.select_all(action='DESELECT')
        
       
        for pinname in thelist:
            pin = bpy.context.scene.objects[pinname]
            if doscale:
                pin.scale=((pinscale,pinscale,pinscale))
            pin.select = True
                
        firstpin = bpy.context.scene.objects[thelist[0]]
        bpy.context.scene.objects.active = firstpin
        bpy.ops.object.join()
        if carve:           
            bool_carve(obj,firstpin,'DIFFERENCE',modapp=True)
        else:
            bool_bmesh(obj,firstpin,'DIFFERENCE',modapp=True)
        bpy.ops.object.select_all(action='DESELECT')
        firstpin.select=True
        bpy.ops.object.delete()

def select_hbonds():
    '''Selects cylinders below max_hbond as hydrogen bonds'''
    interaction_list = bpy.context.scene.molprint_lists.interactionlist
    for each in interaction_list:
        #Reset in case radius value has been changed, won't deselect however
        each[1]["hbond"] = 0
        if each[1]["radius"] <= bpy.context.scene.molprint.max_hbond:
            each[0].select = True
            each[1].select = True
            each[1]["hbond"] = 1

#Pure nastiness, but couldn't figure out a nicer way initially.
def select_phosphate(context):
    '''Select Phosphates based on atom radius'''
    interaction_list = bpy.context.scene.molprint_lists.interactionlist
    countdictsphere = Counter(elem[0] for elem in interaction_list)
    
    for k, v in countdictsphere.items():
        #is it a phosphorous?
        if v == 4 and abs(k["radius"] - bpy.context.scene.molprint.phosphorous_radius) < 0.0001:
            k.select = True
            fin = False
            cyls = [value[1] for value in interaction_list if value[0] == k and not value[1]["hbond"]]
            for cyl in cyls:
                if fin:
                    break
                second_sphere = [each[0] for each in interaction_list if each[0] != k and each[1] == cyl]
                for ss in second_sphere:
                    second_cyl = [each[1] for each in interaction_list if ss == each[0] and each[1] not in cyls]
                    
                    for sc in second_cyl:
                        third_sphere = [each[0] for each in interaction_list if sc == each[1] and each[0] != ss]
                        
                        for k1, v1 in countdictsphere.items():
                            if k1 == third_sphere[0] and v1 > 2:
                                cyl.select = True
                                fin = True
                                break
                            
def select_glyco_na(context):
    '''Select glycosidic bond of nucleic acids.'''
    interaction_list = bpy.context.scene.molprint_lists.interactionlist
    countdict = Counter(elem[0] for elem in interaction_list)
    rads = (round(bpy.context.scene.molprint.carbon_radius,3),round(bpy.context.scene.molprint.nitrogen_radius,3),round(bpy.context.scene.molprint.oxygen_radius,3))
    for k, v in countdict.items():
        if v == 3 and k["radius"] == round(bpy.context.scene.molprint.carbon_radius,3):
            #first get all cylinders connected, ignoring H-bonds
            cyls = [value[1] for value in interaction_list if value[0] == k and not value[1]["hbond"]]
            second = [each for each in interaction_list if each[0] != k and each[1] in cyls]
            dist1 = get_distance(second[0][0],second[1][0])
            dist2 = get_distance(second[0][0],second[2][0])
            dist3 = get_distance(second[1][0],second[2][0])
            avgdist = dist1+dist2+dist3/3
            secondrads = (round(second[0][0]["radius"],3),round(second[1][0]["radius"],3),round(second[2][0]["radius"],3))
            #This is problematic. Works well with Pymol files, not as well with Chimera
            if rads == secondrads and avgdist > 5.56 and countdict.get(second[1][0]) > 1:
                k.select = True
                second[1][1].select = True

#Meant for protein selection. Actually selects C-alphas.
def select_amides(context):
    '''Select alpha carbon (even though it say amide)'''
    interaction_list = bpy.context.scene.molprint_lists.interactionlist
    countdict = Counter(elem[0] for elem in interaction_list)
    #print(countdict)
    #TODO: assign element variable to radius so this doesn't have to be hardcoded
    rads = (round(bpy.context.scene.molprint.carbon_radius,3),
            round(bpy.context.scene.molprint.nitrogen_radius,3),
            round(bpy.context.scene.molprint.oxygen_radius,3))
    for k, v in countdict.items():
        if v == 3 and k["radius"] == round(bpy.context.scene.molprint.carbon_radius,3):
            #first get all cylinders connected, ignoring H-bonds
            #print(k)
            cyls = [value[1] for value in interaction_list if value[0] == k and value[1]["radius"] > bpy.context.scene.molprint.max_hbond]
            if len(cyls) != 3:
                continue
            #print(cyls)
            #now get sphere,cylinders that are not the original
            second = [each for each in interaction_list if each[0] != k and each[1] in cyls]
            if len(second) != 3:
                continue
            #print(second)
            secondrads = (round(second[0][0]["radius"],3),round(second[1][0]["radius"],3),round(second[2][0]["radius"],3))
            rads = sorted(rads)
            secondrads = sorted(secondrads)
            #print(rads,secondrads)
            if rads == secondrads:
                #Select nitrogen to get its bond, but it is actually better to select our alpha
                nitrogen = next(value for value in second if round(value[0]["radius"],3) == round(bpy.context.scene.molprint.nitrogen_radius,3))
                alpha = next(value for value in second if round(value[0]["radius"],3) == round(bpy.context.scene.molprint.carbon_radius,3))
                #need to differentiate backbone from Asn/Gln
                if countdict.get(nitrogen[0]) > 1:                 
                    alpha[0].select = True
                    alpha[1].select = True
                    #k.select = True
                    
def floorall(context):
    '''Place largest convex hull face orthogonal to Z'''
    vec2 = (0,0,-1)
    for each in bpy.context.scene.objects:
        bpy.ops.object.select_all(action='DESELECT')
        facenormal = getlargestface(each)
        align_vector(each,facenormal,vec2)
        bpy.context.scene.objects.active = each

def floorselected(context):
    '''Select a surface to make orthogonal to Z. This generates a mean normal from selected faces'''
    obj = bpy.context.scene.objects.active
    assert obj.mode == 'EDIT'
    #Get facenormal for each selected face in our object
    bm1 = bmesh.from_edit_mesh(obj.data)
    #bm1.faces.ensure_lookup_table()
    vec2 = (0,0,-1)
    facelist = []
    for f in bm1.faces:
        if f.select:
            #print(f.normal)
            facelist.append(f.normal)
    totalvec = Vector()
    for each in facelist:
        totalvec = totalvec + each
    finalvec = totalvec/len(facelist)
    align_vector(bpy.context.scene.molprint_lists.floorlist[0],finalvec,vec2)
    
                              
def getlargestface(obj):

    bm1 = bmesh_copy_from_object(obj)
    bmesh.ops.convex_hull(bm1,input=(bm1.verts),use_existing_faces=False)
    bmesh.ops.dissolve_limit(bm1,angle_limit=0.09,verts=bm1.verts,edges=bm1.edges)
    bm1.faces.ensure_lookup_table()
  
    largestface = 0
    largestidx = None
    faceidx = 0 
    for face in bm1.faces:
        facearea = face.calc_area()
        if facearea > largestface:
            largestidx = faceidx
            largestface = facearea
        faceidx += 1
    
    bm1.faces[largestidx].select = True
    facenorm = bm1.faces[largestidx].normal
    return facenorm

def align_vector(obj,vec1,vec2):
    matrix_orig = obj.matrix_world.copy()
    axis_src = matrix_orig.to_3x3() * vec1
    axis_dst = vec2
    #axis_dst = Vector((0, 0, -1))
    matrix_rotate = matrix_orig.to_3x3()
    matrix_rotate = matrix_rotate * axis_src.rotation_difference(axis_dst).to_matrix()
    matrix_translation = Matrix.Translation(matrix_orig.to_translation())
    obj.matrix_world = matrix_translation * matrix_rotate.to_4x4()

def check_split_cyls(obj1,obj2,splitcyllist):
    '''PyMol splits all cylinders. This joins them together'''
    bpy.ops.object.select_all(action='DESELECT') 
    bm1 = bmesh_copy_from_object(obj1, transform=True, triangulate=False)
    bm2 = bmesh_copy_from_object(obj2, transform=True, triangulate=False)
    matched = False
    #Must also check face normals
    for f1 in bm1.faces:
        if matched:
            break
        if len(f1.edges) > 4:
            f1.normal_flip()
            for f2 in bm2.faces:
                if len(f2.edges) > 4:
                    fnorm1 = (f1.normal * obj1.matrix_world).to_tuple(3)
                    fnorm2 = (f2.normal * obj2.matrix_world).to_tuple(3)
                    #convert these to a tuple to allow comparision without rounding issues of vectors
                    #only need one check. For chimera, needed to drop precision down to 3
                    if tol(f1.calc_center_median(),f2.calc_center_median()) and fnorm1[1] == fnorm2[1]:
                        matched = True
                        splitcyllist.append((obj1,obj2))
                        break
    bm1.free()
    bm2.free()
    return splitcyllist

def merge_split_cyls(splitcyllist):
    #looked into doing this with bmesh, but wasn't as straightforward :(
    #print(splitcyllist)
    for a,b in splitcyllist:
        #Some models can have odd organization that leads to failures. Try to fix with a quick check:
        try:
            a.data.materials.clear()
            b.data.materials.clear()
        except:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.scene.objects.active = a
        a.select = True
        b.select = True
        bpy.ops.object.join()
        #Remove interior faces, limited dissolve
        bpy.context.scene.objects.active = a
        a.select
        clean_object()
        
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS') 
        bpy.ops.object.select_all(action='DESELECT')
        
#Tolerance. Not sure why it needs its own method, but OK.  
def tol(v1, v2):
    return (v1 - v2).length < 0.01

#Used for CPK tools
def AlignX(v1,v2):
    dvec=v2-v1
    rotation_quat = dvec.to_track_quat('Z', 'X')
    return rotation_quat

def median_intersect(ob):
    '''Returns the median point of all selected verts'''
    bpy.context.scene.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    ob.update_from_editmode()
    me = ob.data
    verts_sel = [v.co for v in me.vertices if v.select]
    pivot = sum(verts_sel, Vector()) / len(verts_sel)
    return ob.matrix_world * pivot

#Making cylinder objects and doing boolean operations is super slow
#Is there a sane way to do this just with intersecting verts and
#filling the face(s) afterward?

def cpkcyl(obj1,obj2, dummy1, dummy2):
    '''Carve up CPK spheres for multicolor printing'''
    spot1 = median_intersect(obj1)
    dummy1.location = spot1
    #Here is the vector for positioning second point
    dx,dy,dz = obj2.location.x - obj1.location.x, obj2.location.y - obj1.location.y, obj2.location.z - obj1.location.z   
    dist = (obj2.location - obj1.location).length
    diam = obj1.dimensions.x
    scale = diam/dist
    dummy2.location = (dx*scale+obj1.location.x, dy*scale+obj1.location.y, dz*scale+obj1.location.z)
    dx,dy,dz = dummy2.location.x - dummy1.location.x, dummy2.location.y - dummy1.location.y, dummy2.location.z - dummy1.location.z
    align = AlignX(obj1.location,obj2.location)
    make_cpkcyl(dx,dy,dz,dummy1,dummy2,diam,obj1,align)
    
    #Repeat for second cyl, this way the interface position is exact for both cyls
    dx,dy,dz = obj1.location.x - obj2.location.x, obj1.location.y - obj2.location.y, obj1.location.z - obj2.location.z
    dist = (obj1.location - obj2.location).length
    diam = obj2.dimensions.x
    scale = diam/dist
    dummy2.location = (dx*scale+obj2.location.x, dy*scale+obj2.location.y, dz*scale+obj2.location.z)
    dx,dy,dz = dummy2.location.x - dummy1.location.x, dummy2.location.y - dummy1.location.y, dummy2.location.z - dummy1.location.z
    align = AlignX(obj2.location,obj1.location)
    make_cpkcyl(dx,dy,dz,dummy1,dummy2,diam,obj2,align)
    
def make_cpkcyl(dx,dy,dz,dummy1,dummy2,diam,obj,align):

    bpy.ops.mesh.primitive_cylinder_add(
        vertices = 8,
        radius = 2,
        depth = (dummy2.location - dummy1.location).length,
        location = (dx/2 + dummy1.location.x, dy/2 + dummy1.location.y, dz/2 + dummy1.location.z)
    )
   
    cylinder=bpy.context.scene.objects.active
    cylinder["ptype"] = "CPKcyl"
    cylinder.rotation_mode='QUATERNION'
    #Set rotation
    cylinder.rotation_quaternion=align
    #Now do difference bool
    
    mymodifier = obj.modifiers.new('cpkmod', 'BOOLEAN')
    mymodifier.operation = 'DIFFERENCE'
    mymodifier.solver = 'CARVE'
    mymodifier.object = cylinder

def addon_ensure(addon_id):
        # Enable the addon, dont change preferences.
        #So we can used 3d printing tools exports and not write our own!
        default_state, loaded_state = addon_utils.check(addon_id)
        if not loaded_state:
            addon_utils.enable(addon_id, default_set=False)     
