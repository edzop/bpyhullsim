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



bl_info = {
    "name": "bpyhullsim",
    "description": "Hydrostatics simulator for blender",
    "author": "Ed Kraus",
    "version": (0, 0, 2),
    "blender": (2, 82, 0),
    "location": "3D View > Tools",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "https://edzop.github.io/bpyhullsim/",
    "tracker_url": "",
    "category": "Development"
}

# ------------------------------------------------------------------------
# register and unregister
# ------------------------------------------------------------------------

from . import hullsim
from .hullsim import sim_helper

if "bpy" in locals():
    import importlib
    importlib.reload(ui)
else:

    import bpy

    from bpy.props import PointerProperty

    from . import (
            ui
            )


classes = (
    ui.hullsim_Properties,
    ui.CalculateCGOperator,
    ui.OBJECT_PT_bpyhullsim_panel,
    ui.MeasureVolumeOperator,
    ui.MeasureAreaSelectedOperator,
    ui.MeasureAreaAllOperator,
    ui.SubmergeOperator,
    ui.RollTestOperator,
)

from .hullsim import sim_helper as sim_helper

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.hullsim_Props = PointerProperty( type = ui.hullsim_Properties )

    sim_helper.register_text_update_callback()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    sim_helper.unregister_text_update_callback()

    #bpy.utils.unregister_class(bpysim_Operator)


    del bpy.types.Scene.hullsim_Props
