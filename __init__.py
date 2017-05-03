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

bl_info = {
    "name": "Molecular 3D Printing Toolbox",
    "author": "Paul Paukstelis",
    "blender": (2, 78, 0),
    "location": "3D View > Toolbox",
    "description": "Object Tools for 3D printing molecules",
    "category": "Mesh"}


if "bpy" in locals():
    import importlib
    importlib.reload(ui)
    importlib.reload(operators)
else:
    import bpy
    from bpy.props import (
            StringProperty,
            BoolProperty,
            IntProperty,
            FloatProperty,
            FloatVectorProperty,
            EnumProperty,
            PointerProperty,
            )
    from bpy.types import (
            Operator,
            AddonPreferences,
            PropertyGroup,
            )
    from . import (
            ui,
            operators,
            )

import math
from bpy.app.handlers import persistent

class MolPrintSettings(PropertyGroup):

    prim_detail = IntProperty(
            name = "Number of subdivisions for primitive detail",
            description = "Number of circle division for objects. Large numbers slow things down!",
            default=16,
            )

    strut_radius = FloatProperty(
            name="Strut radius",
            description="Radius of added struts",
            default=0.175,
            precision=5,
            min=0.1, max=0.3,
            )
    proton_radius = FloatProperty(
            name="H-radius",
            description="Hydrogen atom radius",
            default=0.360,
            precision=3,
            min=0.0, max=4.0,
            )
    nitrogen_radius = FloatProperty(
            name="N-radius",
            description="Nitrogen atom radius",
            default=0.465,
            precision=3,
            min=0.0, max=4.0,
            )
    carbon_radius = FloatProperty(
            name="C-radius",
            description="Carbon atom radius",
            default=0.510,
            precision=3,
            min=0.0, max=4.0,
            )
    oxygen_radius = FloatProperty(
            name="O-radius",
            description="Oxygen atom radius",
            default=0.456,
            precision=3,
            min=0.0, max=4.0,
            )
    phosphorous_radius = FloatProperty(
            name="N-radius",
            description="Phosphorus atom radius",
            default=0.540,
            precision=3,
            min=0.0, max=4.0,
            )
    sulfur_radius = FloatProperty(
            name="S-radius",
            description="Sulfur atom radius",
            default=0.0001,
            precision=5,
            min=0.0, max=0.2,
            )
    bond_scale = FloatProperty(
            name="Bond scaling",
            description="Bond scale value",
            default=1.0000,
            precision=5,
            min=0.1, max=1.5,
            )
    max_hbond = FloatProperty(
            name="Hbond",
            description="Maximum cylinder radius used to define hydrogen bonds when grouping",
            default=0.250,
            precision=3,
            min=0.1, max=0.5,
            )
    atom_scale = FloatProperty(
            name="Atom Scale",
            description="Nitrogen atom radius",
            default=1.0000,
            precision=5,
            min=0.1, max=1.5,
            )
    autogroup = BoolProperty(
            name="Color Groups",
            description="Autogroup and color on the fly, may be slow with many objects",
            default=True,
            )
    autocolor = BoolProperty(
            name="Color Groups",
            description="Autocoloring,requires autogrouping",
            default=False,
            )
    cubepin = BoolProperty(
            name="Square Pins",
            description="Pin generation with cube/rectangles",
            default=False,
            )
    woodruff = BoolProperty(
            name="Woodruff Pins",
            description="Pin generation with cube/rectangles",
            default=False,
            )
    interact = BoolProperty(
            name="Interaction list generated",
            description="Does interaction list exist",
            default=False,
            )
    joined = BoolProperty(
            name="Objects joined",
            description="Objects joined",
            default=False,
            )
    atomgroups = BoolProperty(
            name="Group Atoms",
            description="Pin/join/difference based on atomic radii for multicolor printing",
            default=False,
            )
    cleaned = BoolProperty(
            name="Model cleaned",
            description="Clean-up has been run",
            default=False,
            )
    floorselect = BoolProperty(
            name="Model cleaned",
            description="Clean-up has been run",
            default=False,
            )
    fuse_double = BoolProperty(
            name="Fuse DBs",
            description="Fuse double bonds",
            default=False,
            )
## Addons Preferences Update Panel
def update_panel(self, context):
    try:
        bpy.utils.unregister_class(ui.MolPrintToolBarObject)
        #bpy.utils.unregister_class(ui.MolPrintToolBarMesh)
    except:
        pass
    ui.MolPrintToolBarObject.bl_category = context.user_preferences.addons[__name__].preferences.category
    bpy.utils.register_class(ui.MolPrintToolBarObject)
    ui.MolPrintToolBarMesh.bl_category = context.user_preferences.addons[__name__].preferences.category
    bpy.utils.register_class(ui.MolPrintToolBarMesh)

class printerpreferences(bpy.types.AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    category = bpy.props.StringProperty(
            name="Tab Category",
            description="Choose a name for the category of the panel",
            default="MolPrint",
            update=update_panel)

    def draw(self, context):

        layout = self.layout
        row = layout.row()
        col = row.column()
        col.label(text="Tab Category:")
        col.prop(self, "category", text="")

class MolPrintLists():
    interactionlist = []
    grouplist = []
    selectedlist = []
    floorlist = []

#Where is the best place to put this? Really not sure.
@persistent
def updategroups(scene):
    #Ignore this callback if conditions not met
    if bpy.context.scene.molprint.interact and bpy.context.scene.molprint.autogroup:     
        if bpy.context.scene.molprint_lists.selectedlist != bpy.context.selected_objects:
            bpy.context.scene.molprint_lists.selectedlist = bpy.context.selected_objects
            #print("Do some group update")
            bpy.ops.mesh.molprint_updategroups()
    return 
    
classes = (

    ui.MolPrintToolBarObject,
    ui.MolPrintToolBarMesh,
    operators.ImportX3DE,
    operators.MolPrintClean,
    operators.MolPrintGetInteractions,
    operators.MolPrintAddStrut,
    operators.MolPrintScaleBonds,
    operators.MolPrintUpdateGroups,
    operators.MolPrintSelectHbonds,
    operators.MolPrintSelectPhosphate,
    operators.MolPrintSelectGlyco,
    operators.MolPrintPinJoin,
    operators.MolPrintFloorAll,
    operators.MolPrintFloorSelected,
    operators.MolPrintApplyFloor,
    operators.MolPrintExportAll,
    operators.MolPrintCPKSplit,
    MolPrintSettings,
    printerpreferences,
    )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.molprint = PointerProperty(type=MolPrintSettings)
    bpy.types.Scene.molprint_lists = MolPrintLists()
    bpy.app.handlers.scene_update_post.append(updategroups)
        
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.molprint
    del bpy.types.Scene.molprint_lists
    bpy.app.handlers.scene_update_post.remove(updategroups)

