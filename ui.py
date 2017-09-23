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

# Interface for this addon.

import bmesh
from bpy.types import Panel
class MolPrintToolBar:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "MolPrint"
    
class MolPrintToolBar1(MolPrintToolBar,Panel):
    bl_category = "MolPrint"
    bl_label = "Import/Cleanup"
    bl_context = "objectmode"
        
    def draw(self, context):
        layout = self.layout

        scene = context.scene
        molprint = scene.molprint
        obj = context.object

        # TODO, presets

        row = layout.row()
        rowsub = layout.row(align=True)
        rowsub.operator("import_scene.x3d_extra", text="Import VRML")
        rowsub = layout.row(align=True)
        rowsub.label("Primitive divisions")
        rowsub.prop(molprint, "prim_detail", text="")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_clean", text="Clean Scene")
        #rowsub = layout.row(align=True)
        #rowsub.operator("mesh.molprint_clean", text="Clean Scene")

class MolPrintToolBar2(MolPrintToolBar,Panel):
    bl_category = "MolPrint"
    bl_label = "Interactions"
    bl_context = "objectmode"
        
    def draw(self, context):
        layout = self.layout

        scene = context.scene
        molprint = scene.molprint
        obj = context.object

        # TODO, presets                
        row = layout.row()
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_interactions", text="Build/Update Interaction List")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_addstrut", text="Add Strut")
        rowsub.prop(molprint, "strut_radius", text="")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_scalebonds", text="Scale Bonds")
        rowsub.prop(molprint, "bond_scale", text="")

class MolPrintToolBar3(MolPrintToolBar,Panel):
    bl_category = "MolPrint"
    bl_label = "Atom/Bond Preferences"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        layout = self.layout

        scene = context.scene
        molprint = scene.molprint
        obj = context.object
        
        rowsub = layout.row(align=True)
        rowsub.label("H-bond radius")
        rowsub.prop(molprint, "max_hbond", text="")        
        rowsub = layout.row(align=True)
        rowsub.label("Carbon radius")
        rowsub.prop(molprint, "carbon_radius", text="")
        rowsub = layout.row(align=True)
        rowsub.label("Nitrogen radius")
        rowsub.prop(molprint, "nitrogen_radius", text="")
        rowsub = layout.row(align=True)
        rowsub.label("Oxygen radius")
        rowsub.prop(molprint, "oxygen_radius", text="")
        rowsub = layout.row(align=True)
        rowsub.label("Phos. radius")
        rowsub.prop(molprint, "phosphorous_radius", text="")
        rowsub = layout.row(align=True)
        rowsub.label("Proton radius")
        rowsub.prop(molprint, "proton_radius", text="")
        rowsub = layout.row(align=True)
        rowsub.label("Sulfur radius")
        rowsub.prop(molprint, "sulfur_radius", text="")

class MolPrintToolBar4(MolPrintToolBar,Panel):
    bl_category = "MolPrint"
    bl_label = "Grouping"
    bl_context = "objectmode"
        
    def draw(self, context):
        layout = self.layout

        scene = context.scene
        molprint = scene.molprint
        obj = context.object
        
        row = layout.row()
        rowsub = layout.row(align=True)
        rowsub.prop(molprint,"autogroup")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_selecthbonds", text="Select H-bonds")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_selectamide", text="Select C-alpha")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_selectphosphate", text="Select Phosphate")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_selectglyco", text="Select Glycosidic")
        rowsub = layout.row(align=True)
        
class MolPrintToolBar5(MolPrintToolBar,Panel):
    bl_category = "MolPrint"
    bl_label = "Pinning/Joining"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        molprint = scene.molprint
        obj = context.object
        
        row = layout.row()
        #rowsub = layout.row(align=True)
        rowsub = layout.row(align=True)
        rowsub.label("Pin sides")
        rowsub.prop(molprint, "pin_sides", text="")
        rowsub = layout.row(align=True)
        rowsub.label("Pin:bond diameter")
        rowsub.prop(molprint, "pintobond", text="")
        rowsub = layout.row(align=True)
        rowsub.label("H-bond pin sides")
        rowsub.prop(molprint, "h_pin_sides", text="")
        rowsub = layout.row(align=True)
        rowsub.label("H-bond pin:bond")
        rowsub.prop(molprint, "h_pintobond", text="")
        rowsub = layout.row(align=True)
        rowsub.label("Hole size increase")
        rowsub.prop(molprint, "pinscale", text="")
        rowsub = layout.row(align=True)
        rowsub.prop(molprint,"splitpins")
        rowsub = layout.row(align=True)
        rowsub.prop(molprint,"multicolor")
        rowsub = layout.row(align=True)
   
        rowsub.operator("mesh.molprint_pinjoin", text="Pin and Join")

class MolPrintToolBar6(MolPrintToolBar,Panel):
    bl_category = "MolPrint"
    bl_label = "Floor and Export"
    #bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        molprint = scene.molprint
        obj = context.object
        
        row = layout.row()
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_floorall", text="Floor All")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_floorselected", text="Selective Floor")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_applyfloor", text="Apply Floor")
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_exportall", text="Export All")

# So we can have a panel in both object mode and editmode
class MolPrintFloorObject(MolPrintToolBar6):

    bl_context = "objectmode"

class MolPrintFloorMesh(MolPrintToolBar6):

    bl_context = "mesh_edit"

class MolPrintToolBar7(MolPrintToolBar,Panel):
    bl_category = "MolPrint"
    bl_label = "CPK Tools"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        molprint = scene.molprint
        obj = context.object        
        row = layout.row()
        rowsub = layout.row(align=True)
        rowsub.operator("mesh.molprint_cpksplit", text="CPK by atom")



