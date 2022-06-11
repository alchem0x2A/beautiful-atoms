"""
view3d_mt_object_context_menu
"""

import bpy
from bpy.types import Menu


def menu_func(self, context):
    self.layout.menu("VIEW3D_MT_object_context_batoms", icon="MESH_UVSPHERE")


class VIEW3D_MT_object_context_batoms_model_style(Menu):
    bl_idname = "VIEW3D_MT_object_context_batoms_model_style"
    bl_label = "model style"
    # bl_icon = ""

    def draw(self, _context):
        layout = self.layout

        layout.operator_context = 'INVOKE_REGION_WIN'

        op0 = layout.operator("batoms.apply_model_style", text="Space-filling")
        op0.model_style = '0'
        op1 = layout.operator("batoms.apply_model_style", text="Ball-and-stick")
        op1.model_style = '1'
        op2 = layout.operator("batoms.apply_model_style", text="Polyhedral")
        op2.model_style = '2'
        op3 = layout.operator("batoms.apply_model_style", text="Stick")
        op3.model_style = '3'


class VIEW3D_MT_object_context_batoms_radius_style(Menu):
    bl_idname = "VIEW3D_MT_object_context_batoms_radius_style"
    bl_label = "model style"
    # bl_icon = ""

    def draw(self, _context):
        layout = self.layout

        layout.operator_context = 'INVOKE_REGION_WIN'

        op0 = layout.operator("batoms.apply_radius_style", text="Covalent")
        op0.radius_style = '0'
        op1 = layout.operator("batoms.apply_radius_style", text="VDW")
        op1.radius_style = '1'
        op2 = layout.operator("batoms.apply_radius_style", text="Ionic")
        op2.radius_style = '2'


class VIEW3D_MT_object_context_batoms_color_style(Menu):
    bl_idname = "VIEW3D_MT_object_context_batoms_color_style"
    bl_label = "model style"
    # bl_icon = ""

    def draw(self, _context):
        layout = self.layout

        layout.operator_context = 'INVOKE_REGION_WIN'

        op0 = layout.operator("batoms.apply_color_style", text="JMOL")
        op0.color_style = '0'
        op1 = layout.operator("batoms.apply_color_style", text="VESTA")
        op1.color_style = '1'
        op2 = layout.operator("batoms.apply_color_style", text="CPK")
        op2.color_style = '2'
    
class VIEW3D_MT_object_context_batoms(Menu):
    bl_idname = "VIEW3D_MT_object_context_batoms"
    bl_label = "Batoms"
    bl_icon = "batoms_molecule"

    def draw(self, _context):
        layout = self.layout

        layout.operator_context = 'INVOKE_REGION_WIN'
        layout.menu("VIEW3D_MT_object_context_batoms_model_style",
                    text="Model Style", icon='LAYER_ACTIVE')
        layout.menu("VIEW3D_MT_object_context_batoms_color_style",
                    text="Color Style", icon='LAYER_ACTIVE')
        layout.menu("VIEW3D_MT_object_context_batoms_radius_style",
                    text="Radius Style", icon='LAYER_ACTIVE')
        layout.operator("batoms.join", text="Join", icon='LAYER_ACTIVE')
        layout.operator("batoms.separate", text="Separate", icon='LAYER_ACTIVE')
        layout.operator("batoms.delete_selected", text="Delete",
                        icon='FORCE_LENNARDJONES')

        layout.separator()

