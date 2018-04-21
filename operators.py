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

# All Operator
import time
import bpy
import bmesh
import itertools
from bpy.types import Operator
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty,
)

from . import (
    mesh_helpers,
    import_x3de,
)

from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
    orientation_helper_factory,
    axis_conversion,
    path_reference_mode,
)

IOX3DOrientationHelper = orientation_helper_factory("IOX3DOrientationHelper", axis_forward='Z', axis_up='Y')


# From 3D print tools, do I need?
def clean_float(text):
    # strip trailing zeros: 0.000 -> 0.0
    index = text.rfind(".")
    if index != -1:
        index += 2
        head, tail = text[:index], text[index:]
        tail = tail.rstrip("0")
        text = head + tail
    return text


# ---------
# Mesh Info

class ImportX3DE(Operator, ImportHelper, IOX3DOrientationHelper):
    """Import VRML2 file with extra parameters"""
    bl_idname = "import_scene.x3d_extra"
    bl_label = "Import VRML2"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".x3d"
    filter_glob = StringProperty(default="*.x3d;*.wrl", options={'HIDDEN'})

    def execute(self, context):
        from . import import_x3de

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))
        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix
        keywords["PREF_CIRCLE_DIV"] = bpy.context.scene.molprint.prim_detail
        bpy.context.scene.molprint.cleaned = False
        return import_x3de.load(context, **keywords)


class MolPrintClean(Operator):
    """Clean up Imported VRML objects"""
    bl_idname = "mesh.molprint_clean"
    bl_label = "Clean up import mesh"

    def execute(self, context):
        delete_list = []
        splitcyllist = []
        # Remove all non-mesh objects first so they are out of the way
        for obj in bpy.context.scene.objects:
            obj["conelist"] = ['None']
            obj["cutcube"] = ['None']
            obj["pinlist"] = ['None']
            obj["hbond"] = 0
            obj["pin"] = [{"atom": 'None', "pindiameter": 0.66, "pintype": 1}]

            if obj.type != 'MESH':
                bpy.context.scene.objects.unlink(obj)

        # Make all linked objects single user: Jmol issue
        bpy.ops.object.make_single_user(type='ALL', object=True, obdata=True)
        # Generate a list of pairs of existing objects to do comparisons against
        objlist = itertools.combinations(bpy.context.scene.objects, 2)
        # TODO: Make this whole thing more pythonic
        for (a, b) in objlist:
            distance = mesh_helpers.get_distance(a, b)
            # Sphere check for internal objects, old pymol files require such a high distance check
            if a['ptype'] and b['ptype'] == 'Sphere' and distance < 0.3:
                inside = mesh_helpers.isinside(a, b)
                if inside:
                    delete_list.append(inside)
            # Remove duplicate cylinders that can cause issues
            if a['ptype'] and b['ptype'] == 'Cylinder' and distance < 0.0001:
                delete_list.append(b)
                continue
            # Clyinder check for 'split' cylinder bonds
            if a['ptype'] and b['ptype'] == 'Cylinder' and distance < 2:
                splitcyllist = mesh_helpers.check_split_cyls(a, b, splitcyllist)
                # Delete everything that is in the delete list if it still exists
        # TODO: Make this more pythonic
        for each in delete_list:
            try:
                bpy.ops.object.select_all(action='DESELECT')
                each.select = True
                bpy.ops.object.delete()
            except:
                continue

        # This is causing unexpected issues. Removing for now
        # Join split cylinders if they exist
        # if len(splitcyllist) > 0:
        #    mesh_helpers.merge_split_cyls(splitcyllist)

        bpy.context.scene.molprint.cleaned = True
        # reset any pin groups
        bpy.context.scene.molprint_lists.pingroups = []
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.mesh.molprint_interactions()

        return {'FINISHED'}


class MolPrintGetInteractions(Operator):
    """Generate Interaction List for Objects"""
    bl_idname = "mesh.molprint_interactions"
    bl_label = "Find Interactions"
    bl_options = {'PRESET', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if bpy.context.scene.molprint.cleaned:
            return True
        else:
            return False

    @staticmethod
    def getinteractions(context):
        interactionlist = []
        # Build a complete list of interactions between objects to speed up joining
        # Uses a 2 unit distance cutoff. This may impact long generated struts?
        objlist = itertools.combinations(bpy.context.scene.objects, 2)
        for each in objlist:
            # Ignore cylinder-cylinder interactions
            if (each[0]["ptype"] == 'Cylinder') and (each[1]["ptype"] == 'Cylinder'):
                continue
            distance = mesh_helpers.get_distance(each[0], each[1])
            intersect = False
            if distance < 2:
                intersect = mesh_helpers.bmesh_check_intersect_objects(each[0], each[1])
            if intersect:
                if each[0]["ptype"] == 'Sphere':
                    interactionlist.append([each[0].name, each[1].name])
                if each[0]["ptype"] == 'Cylinder':
                    interactionlist.append([each[1].name, each[0].name])

        return interactionlist

    def execute(self, context):
        ial = self.getinteractions(context)
        bpy.context.scene.molprint_lists.internames["pairs"] = ial
        bpy.ops.mesh.molprint_objinteract()
        bpy.context.scene.molprint.interact = True
        bpy.context.scene.molprint_lists.selectedlist = bpy.context.selected_objects
        return {'FINISHED'}


class MolPrintObjInteract(Operator):
    """Make a name list into an object list"""
    bl_idname = "mesh.molprint_objinteract"
    bl_label = "Convert name list to object list"

    def execute(self, context):
        interaction_list = []

        for each in bpy.context.scene.molprint_lists.internames["pairs"]:
            pair = []
            for name in each:
                pair.append(bpy.data.objects[name])
            interaction_list.append(pair)
        bpy.context.scene.molprint_lists.interactionlist = interaction_list
        return {'FINISHED'}


class MolPrintAddStrut(Operator):
    """Add a strut between two selected spheres"""
    bl_idname = "mesh.molprint_addstrut"
    bl_label = "MolPrint Add Strut"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        selected = bpy.context.selected_objects
        # number of conditions before allowing strut creation
        if len(selected) == 2 and (
                selected[0]['ptype'] == selected[1]['ptype'] == 'Sphere') and bpy.context.scene.molprint.interact:
            return True
        else:
            return False

    def execute(self, context):
        mesh_helpers.makestrut(bpy.context.selected_objects[0], bpy.context.selected_objects[1])
        return {'FINISHED'}


class MolPrintScaleBonds(Operator):
    """Scale Cylinder dimensions"""
    bl_idname = "mesh.molprint_scalebonds"
    bl_label = "MolPrint Scale Bonds"
    bl_options = {'PRESET', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if bpy.context.scene.molprint.interact:
            return True
        else:
            return False

    def execute(self, context):
        mesh_helpers.scalebonds(bpy.context.scene.molprint.bond_scale)
        return {'FINISHED'}


class MolPrintUpdateGroups(Operator):
    """Update and color groups"""
    bl_idname = "mesh.molprint_updategroups"
    bl_label = "MolPrint Update Groups"

    def execute(self, context):
        mesh_helpers.updategroups()
        return {'FINISHED'}


class MolPrintSelectHbonds(Operator):
    """Select all cylinders that are below H-bond max threshold"""
    bl_idname = "mesh.molprint_selecthbonds"
    bl_label = "MolPrint Select H-bonds"

    @classmethod
    def poll(cls, context):
        if bpy.context.scene.molprint.interact:
            return True
        else:
            return False

    def execute(self, context):
        mesh_helpers.select_hbonds()
        return {'FINISHED'}


class MolPrintPinJoin(Operator):
    """Pin and Join selected groups together"""
    bl_idname = "mesh.molprint_pinjoin"
    bl_label = "MolPrint Pin and Join"
    bl_options = {'PRESET', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if len(bpy.context.scene.molprint_lists.pingroups) > 0:
            return True
        else:
            return False

    def execute(self, context):
        mesh_helpers.joinall()
        bpy.context.scene.molprint.joined = True
        return {'FINISHED'}


class MolPrintSelectPhosphate(Operator):
    """Select all phosphate groups"""
    bl_idname = "mesh.molprint_selectphosphate"
    bl_label = "MolPrint Select Phosphate"

    @classmethod
    def poll(cls, context):
        if bpy.context.scene.molprint.interact:
            return True
        else:
            return False

    def execute(self, context):
        mesh_helpers.select_phosphate(context)
        return {'FINISHED'}


class MolPrintSelectAmide(Operator):
    """Select all C-alpha backbone groups"""
    bl_idname = "mesh.molprint_selectamide"
    bl_label = "MolPrint Select Phosphate"

    @classmethod
    def poll(cls, context):
        if bpy.context.scene.molprint.interact:
            return True
        else:
            return False

    def execute(self, context):
        mesh_helpers.select_amides(context)
        return {'FINISHED'}


class MolPrintSelectGlyco(Operator):
    """Select all glycosidic linkages in nucleic acids"""
    bl_idname = "mesh.molprint_selectglyco"
    bl_label = "MolPrint Select Glycosidic"

    @classmethod
    def poll(cls, context):
        if bpy.context.scene.molprint.interact:
            return True
        else:
            return False

    def execute(self, context):
        mesh_helpers.select_glyco_na(context)
        return {'FINISHED'}


class MolPrintFloorAll(Operator):
    """Find optimal orientation to fit on build plate"""
    bl_idname = "mesh.molprint_floorall"
    bl_label = "MolPrint Floor objects"

    @classmethod
    def poll(cls, context):
        if bpy.context.scene.molprint.multicolor:
            return False
        else:
            return True

    def execute(self, context):
        mesh_helpers.floorall(context)
        return {'FINISHED'}

class MolPrintFloorMulti(Operator):
    """Find optimal orientation to fit on build plate using multiple objects"""
    bl_idname = "mesh.molprint_floormulti"
    bl_label = "MolPrint Floor multiple objects as one"

    def execute(self, context):
        mesh_helpers.floormulti(context)
        return {'FINISHED'}

class MolPrintFloorSelected(Operator):
    """Interactively find optimal orientation to fit on build plate. Select an object, select face(s), apply"""
    bl_idname = "mesh.molprint_floorselected"
    bl_label = "MolPrint Floor objects"

    @classmethod
    def poll(cls, context):
        if len(bpy.context.selected_objects) == 1 and not bpy.context.scene.molprint.floorselect:
            return True
        else:
            return False

    def execute(self, context):
        bpy.context.space_data.viewport_shade = 'WIREFRAME'
        bpy.ops.object.rotation_clear()
        obj = bpy.context.scene.objects.active
        bpy.context.scene.molprint_lists.floorlist.append(obj)
        bpy.ops.object.duplicate()
        hullobj = bpy.context.scene.objects.active
        hullobj.name = 'temphull'
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull(delete_unused=True, use_existing_faces=False)
        # bpy.ops.mesh.dissolve_limited()
        bpy.ops.mesh.select_mode(type="FACE")
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.context.scene.molprint.floorselect = True
        return {'FINISHED'}


class MolPrintApplyFloor(Operator):
    """Interactively find optimal orientation to fit on build plate. Select an object, select a face, apply"""
    bl_idname = "mesh.molprint_applyfloor"
    bl_label = "MolPrint Floor objects"

    @classmethod
    def poll(cls, context):
        try:
            obj = bpy.context.scene.objects.active
        except:
            return False
        if bpy.context.scene.molprint.floorselect and obj.mode == 'EDIT':
            return True
        else:
            return False

    def execute(self, context):
        bpy.context.scene.molprint.floorselect = False
        mesh_helpers.floorselected(context)
        bpy.context.space_data.viewport_shade = 'SOLID'
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = bpy.data.objects['temphull']
        bpy.data.scenes[0].objects.unlink(obj)
        bpy.data.objects.remove(obj)
        bpy.context.scene.molprint_lists.floorlist = []
        return {'FINISHED'}


class MolPrintExportAll(Operator):
    """Export all scene objects as STL"""
    bl_idname = "mesh.molprint_exportall"
    bl_label = "MolPrint export all"

    @classmethod
    def poll(cls, context):
        return True if bpy.context.scene.molprint.cleaned else False

    def execute(self, context):
        mesh_helpers.addon_ensure("object_print3d_utils")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            print(obj)
            obj.select = True
            bpy.context.scene.objects.active = obj
            bpy.ops.mesh.print3d_export()
            bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}


class MolPrintCPKSplit(Operator):
    """Split CPK spheres into objects by radius"""
    bl_idname = "mesh.molprint_cpksplit"
    bl_label = "MolPrint, split CPK object into atom groups"

    @classmethod
    def poll(cls, context):
        return True if bpy.context.scene.molprint.cleaned else False

    def execute(self, context):
        starttime = time.time()
        bpy.context.scene.molprint.interact = False
        bpy.context.scene.molprint.autogroup = False
        objlist = itertools.combinations(bpy.context.scene.objects, 2)
        # Create dummy atoms after putting combinations together
        bpy.ops.mesh.primitive_plane_add(
            radius=0.00002,
            location=(0, 0, 0)
        )
        dummy1 = bpy.context.scene.objects.active
        dummy1["ptype"] = "CPKcyl"
        bpy.ops.mesh.primitive_plane_add(
            radius=0.00002,
            location=(0, 0, 0)
        )
        dummy2 = bpy.context.scene.objects.active
        dummy2["ptype"] = "CPKcyl"
        # Build all the cylinders for boolean operations
        for a, b in objlist:
            if a['radius'] == b['radius']:
                continue
            # now check if pairs intersect
            intersect = mesh_helpers.bmesh_check_intersect_objects(a, b, selectface=True)

            if intersect:
                mesh_helpers.cpkcyl(a, b, dummy1, dummy2)
                # mesh_helpers.cpkcyl(b,a,dummy2,dummy1)
        # Apply all modifiers
        for each in bpy.context.scene.objects:
            if each.modifiers:
                for modifier in each.modifiers:
                    bpy.context.scene.objects.active = each
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
        # Delete all extra objects
        for each in bpy.context.scene.objects:
            if each['ptype'] == "CPKcyl":
                each.select = True
                bpy.ops.object.delete()

        # Create list that contains all atoms by radius.
        unique = mesh_helpers.radius_sort(bpy.context.scene.objects)

        # Join all spheres of the same size into single objects
        for each in unique:
            bpy.ops.object.select_all(action='DESELECT')
            for ob in each:
                ob.select = True
            bpy.context.scene.objects.active = bpy.context.selected_objects[0]
            bpy.ops.object.join()
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
        # Do "intersect" unionization, may not be necessary in all cases, but is in some
        for ob in bpy.context.scene.objects:
            bpy.ops.mesh.primitive_cube_add(location=ob.location)
            bpy.ops.transform.resize(value=(30, 30, 30))
            cube = bpy.context.selected_objects[0]
            cube["ptype"] = "CPKcube"
            cube["radius"] = ob["radius"]
            mat = ob.data.materials[0]
            cube.data.materials.append(mat)
            mesh_helpers.bool_carve(cube, ob, 'INTERSECT', modapp=True)
            bpy.ops.object.select_all(action='DESELECT')
            ob.select = True
            bpy.ops.object.delete()

        print("CPK: ", time.time() - starttime)
        return {'FINISHED'}


class MolPrintSetPinGroup(Operator):
    """Define a group of pins from currently selected objects"""
    bl_idname = "mesh.molprint_setpingroup"
    bl_label = "MolPrint set pin groups"

    @classmethod
    def poll(cls, context):
        return True if bpy.context.scene.molprint.cleaned else False

    def execute(self, context):
        pingroups = bpy.context.scene.molprint_lists.pingroups
        pinset = {}
        pinset["type"] = 0
        if bpy.context.scene.molprint.splitpins:
            pinset["type"] = 1
        if bpy.context.scene.molprint.pip:
            pinset["type"] = 2
        pinset["pairs"] = mesh_helpers.getpairs()
        pinset["diameter"] = bpy.context.scene.molprint.pintobond
        pinset["sides"] = bpy.context.scene.molprint.pin_sides
        pinset["decrease"] = bpy.context.scene.molprint.pin_decrease
        pingroups.append(pinset)
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}

class MolPrintPIP(Operator):
    """Make a PIP bond connection"""
    bl_idname = "mesh.molprint_pip"
    bl_label = "MolPrint make PIP bonds"

    @classmethod
    def poll(cls, context):
        selected = bpy.context.selected_objects
        # number of conditions before allowing
        if len(selected) == 2 and any(x for x in selected if x["ptype"] == "Cylinder") and any(y for y in selected if y["ptype"] == "Sphere"):
            return True
        else:
            return False

    def execute(self,context):
        selected = bpy.context.selected_objects
        #determine which is sphere and which is cyl
        cyl = None
        sphere = None
        if selected[0]["ptype"] == "Cylinder":
            cyl = selected[0]
            sphere = selected[1]
        else:
            cyl = selected[1]
            sphere = selected[0]

        #Create pin, cone, etc.
        mesh_helpers.cylinder_between((sphere,cyl),2,0.6,18)
        pin = bpy.context.scene.objects.active
        #Difference cylinder with sphere
        sphere.scale = ((1.08, 1.08, 1.08))
        mesh_helpers.bool_bmesh(cyl, sphere, 'DIFFERENCE', modapp=True)
        sphere.scale = ((1.0, 1.0, 1.0))
        #Union pin with cylinder
        mesh_helpers.bool_bmesh(cyl, pin, 'UNION', modapp=True)
        #Difference cone with sphere
        cyl.scale = ((1.12, 1.02, 1.12))
        mesh_helpers.bool_carve(sphere, cyl, "DIFFERENCE", modapp=True)
        cyl.scale = ((1.0, 1.0, 1.0))
        #delete pin
        bpy.ops.object.select_all(action='DESELECT')
        pin.select = True
        bpy.ops.object.delete()
        #delete cone
        bpy.ops.object.select_all(action='DESELECT')
        conename = bpy.context.scene.molprint_lists.splitlist["conelist"][0][1]
        cone = bpy.data.objects[conename]
        cone.select = True
        bpy.ops.object.delete()
        #reset conelist
        bpy.context.scene.molprint_lists.splitlist["conelist"] = []

        return {'FINISHED'}

class MolPrintMakeDouble(Operator):
    """Create Double Bonds from selected cylinders"""
    bl_idname = "mesh.molprint_makedouble"
    bl_label = "MolPrint make cylinders double bonds"

    def execute(self, context):
        from mathutils import Euler, Vector, Matrix
        # Turn off any autogrouping first
        auto = bpy.context.scene.molprint.autogroup
        autostate = False
        if auto:
            auto = False
            autostate = True
        doubles = [value for value in bpy.context.selected_objects]
        double_scale = bpy.context.scene.molprint.double_scale
        double_distance = bpy.context.scene.molprint.double_distance
        for each in doubles:
            # make sure they are Cylinders
            if each["ptype"] == "Cylinder":
                trans_local_plus = Vector(((each["radius"] / double_distance), 0.0, 0.0))
                trans_local_minus = Vector((-(each["radius"] / double_distance), 0.0, 0.0))

                trans_world_plus = each.matrix_world.to_3x3() * trans_local_plus
                trans_world_minus = each.matrix_world.to_3x3() * trans_local_minus
                newbond = each.copy()
                newbond.data = each.data.copy()
                bpy.context.scene.objects.link(newbond)

                each.matrix_world.translation += trans_world_plus
                newbond.matrix_world.translation += trans_world_minus
                each.scale = (double_scale, 1, double_scale)
                newbond.scale = (double_scale, 1, double_scale)

                # Unionize. Takes longer than join, but might be safer?
                mesh_helpers.bool_carve(each, newbond, 'UNION', modapp=True)
                bpy.ops.object.select_all(action='DESELECT')
                each.select = True
                bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
                # each.rotation_euler = rot
                each.select = False
                newbond.select = True
                bpy.ops.object.delete()
                each.select = True
        if autostate:
            auto = True

        return {'FINISHED'}
