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
from mathutils import Matrix
from math import radians
from bpy.app.handlers import persistent


def update_db_rot(self, context):
    doubles = [value for value in bpy.context.selected_objects]
    double_rot = bpy.context.scene.molprint.double_rot

    for each in doubles:
        rot = Matrix.Rotation(radians(double_rot), 4, 'Y')
        each.matrix_world *= rot


class MolPrintSettings(PropertyGroup):
    prim_detail = IntProperty(
        name="Number of subdivisions for primitive detail",
        description="Number of circle division for objects. Large numbers slow things down!",
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
        # default=0.465,
        default=0.540,
        precision=3,
        min=0.0, max=4.0,
    )
    carbon_radius = FloatProperty(
        name="C-radius",
        description="Carbon atom radius",
        # default=0.510,
        default=0.600,
        precision=3,
        min=0.0, max=4.0,
    )
    oxygen_radius = FloatProperty(
        name="O-radius",
        description="Oxygen atom radius",
        # default=0.456,
        default=0.534,
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
    splitpins = BoolProperty(
        name="Split Pins",
        description="Split pins with conic heads",
        default=False,
    )
    pip = BoolProperty(
        name="PIP Pins",
        description="Print in place rotatable bonds",
        default=False,
    )
    autocolor = BoolProperty(
        name="Color Groups",
        description="Autocoloring,requires autogrouping",
        default=False,
    )
    pin_sides = IntProperty(
        name="Number of sides for each pin cylinder",
        description="Number of sides the pin will have. 3 = triangle, 4 = square, etc",
        default=16,
        min=3, max=32
    )
    pintobond = FloatProperty(
        name="Pin-to-bond ratio",
        description="The ratio of the pin size the bond it will be joined with.",
        default=0.666,
        precision=3,
        min=0.1, max=1,
    )
    h_pin_sides = IntProperty(
        name="Number of sides for each H-bond pin cylinder",
        description="Number of sides the H-bond pin",
        default=16,
        min=3, max=32
    )
    h_pintobond = FloatProperty(
        name="Pin-to-bond ratio for H-bonds",
        description="The ratio of the pin size to the H-bond",
        default=0.90,
        precision=3,
        min=0.1, max=0.98,
    )
    pinscale = FloatProperty(
        name="Pinscale",
        description="The amount to scale hole sizes over actual pin size",
        default=1.05,
        precision=3,
        min=1.0, max=1.5,
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
    double_scale = FloatProperty(
        name="DB scale",
        description="How much to scale double bonds down",
        default=0.58,
        precision=3,
        min=0, max=1.5,
    )
    double_distance = FloatProperty(
        name="DB separation distance",
        description="Fuse double bonds",
        default=1.6,
        precision=3,
        min=0, max=4,
    )
    double_rot = FloatProperty(
        name="DB rotation",
        description="Rotation around local Y",
        default=0.0,
        precision=1,
        min=-360, max=360.0,
        update=update_db_rot,
    )
    multicolor = BoolProperty(
        name="Multicolor",
        description="Separate atoms and bonds of each group for multicolor printing",
        default=False,
    )
    pip = BoolProperty(
        name="Print-in-place",
        description="Flag as print-in-place rotable bonds",
        default=False,
    )
    pin_decrease = FloatProperty(
        name="Pin decrease",
        description="Amount to decrease pin length to avoid overlaps. Note, may leave extra pieces inside atoms!",
        default=0,
        precision=2,
        min=0, max=4,
    )

## Addons Preferences Update Panel
def update_panel(self, context):
    try:
        bpy.utils.unregister_class(ui.MolPrintToolBarObject)
        # bpy.utils.unregister_class(ui.MolPrintToolBarMesh)
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
    pingroups = []
    interactionlist = []
    splitlist = {"conelist": [], "cutcube": []}
    internames = {"name": 'intername', "pairs": []}
    pinlist = {"pinlist": []}
    grouplist = []
    selectedlist = []
    floorlist = []

def reset_lists():
    bpy.types.Scene.molprint_lists = MolPrintLists()

# Where is the best place to put this? Really not sure.
@persistent
def updategroups(scene):
    # Ignore this callback if conditions not met
    if bpy.context.scene.molprint.interact and bpy.context.scene.molprint.autogroup:
        if bpy.context.scene.molprint_lists.selectedlist != bpy.context.selected_objects:
            bpy.context.scene.molprint_lists.selectedlist = bpy.context.selected_objects
            bpy.ops.mesh.molprint_updategroups()
    return


@persistent
def populatelists(scene):
    if bpy.context.scene.molprint.cleaned:
        import json
        try:
            text_obj = bpy.data.texts['interactions.json']
            text_str = text_obj.as_string()
            bpy.context.scene.molprint_lists.internames = json.loads(text_str)
        except:
            print("No previous interactions found")
            #delete any previously defined interactions
            reset_lists()

        try:
            text_obj = bpy.data.texts['pingroup.json']
            text_str = text_obj.as_string()
            bpy.context.scene.molprint_lists.pingroups = json.loads(text_str)
        except:
            print("No previous pin groups found")
            reset_lists()

        bpy.ops.mesh.molprint_updategroups()


@persistent
def savelists(scene):
    import json
    #delete any old text data blocks first, or we end up with multiple lists.
    #for each in bpy.data.texts:
    #    print(each)
    try:
        bpy.data.texts.remove(bpy.data.texts["interactions.json"])
        bpy.data.texts.remove(bpy.data.texts["pingroup.json"])
    except:
        print("No previous text to clear")
    i = json.dumps(bpy.context.scene.molprint_lists.internames, sort_keys=True, indent=2)
    text_block = bpy.data.texts.new('interactions.json')
    text_block.from_string(i)
    p = json.dumps(bpy.context.scene.molprint_lists.pingroups, sort_keys=True, indent=2)
    text_block = bpy.data.texts.new('pingroup.json')
    text_block.from_string(p)


classes = (
    ui.MolPrintToolBar1,
    ui.MolPrintToolBar2,
    ui.MolPrintToolBar3,
    ui.MolPrintToolBar4,
    ui.MolPrintToolBar5,
    ui.MolPrintFloorObject,
    ui.MolPrintFloorMesh,
    ui.MolPrintToolBar7,
    operators.ImportX3DE,
    operators.MolPrintClean,
    operators.MolPrintGetInteractions,
    operators.MolPrintObjInteract,
    operators.MolPrintAddStrut,
    operators.MolPrintScaleBonds,
    operators.MolPrintUpdateGroups,
    operators.MolPrintSelectHbonds,
    operators.MolPrintSelectPhosphate,
    operators.MolPrintSelectAmide,
    operators.MolPrintSelectGlyco,
    operators.MolPrintPinJoin,
    operators.MolPrintFloorAll,
    operators.MolPrintFloorSelected,
    operators.MolPrintApplyFloor,
    operators.MolPrintExportAll,
    operators.MolPrintFloorMulti,
    operators.MolPrintCPKSplit,
    operators.MolPrintSetPinGroup,
    operators.MolPrintMakeDouble,
    operators.MolPrintPIP,
    MolPrintSettings,
    printerpreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.molprint = PointerProperty(type=MolPrintSettings)
    bpy.types.Scene.molprint_lists = MolPrintLists()
    bpy.app.handlers.scene_update_post.append(updategroups)
    bpy.app.handlers.load_post.append(populatelists)
    bpy.app.handlers.save_pre.append(savelists)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.molprint
    del bpy.types.Scene.molprint_lists
    bpy.app.handlers.scene_update_post.remove(updategroups)
    bpy.app.handlers.load_post.append(populatelists)
    bpy.app.handlers.save_pre.append(savelists)
