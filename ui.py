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

# bpy.ops.script.reload()



import bpy


from .bpyutils import measure_helper as measure_helper
from .hullsim import sim_helper as sim_helper

from bpy.props import (StringProperty,
					BoolProperty,
					IntProperty,
					FloatProperty,
					FloatVectorProperty,
					EnumProperty,
					PointerProperty,
					)

from bpy.types import (Panel,
					Operator,
					PropertyGroup,
					)

# ------------------------------------------------------------------------
#    store properties in the active scene
# ------------------------------------------------------------------------

class hullsim_Properties (PropertyGroup):


	cleanup_options=[ 
				('auto', 'Auto', ""),
				('front', 'Front', ""),
				('left', "Left", ""),
				('up', "Up", ""),
				('down', "Down", "")
			   ]

	cleanup_choice: EnumProperty(
		items=cleanup_options,
		description="Cleanup....",
		name="cleanup",
		default="auto"
	)

	hull_weight : FloatProperty(
		name = "HullWeight",
		description = "Gross Weight of Hull (KG)",
		default = 250,
		min = 0.01,
		max = 50000.0
		)

	scale_to_distance : FloatProperty(
		name = "ScaleTo",
		description = "Scale all objects so distance between 2 vertices is exactly this number",
		default = 1,
		min = 0.01,
		max = 50000.0
		)

	output_csv : BoolProperty(
		name="Output CSV",
		description="Output hydro.csv file containing simulation data",
		default = True
    )

	simulate_depth : BoolProperty(
		name="Sim Depth",
		description="Simulate Depth (sinking)",
		default = True
    )

	simulate_pitch : BoolProperty(
		name="Sim Pitch",
		description="Simulate Pitch (Y Axis)",
		default = True
    )

	simulate_roll : BoolProperty(
		name="Sim Roll",
		description="Simulate Roll (X Axis)",
		default = True
    )






# ------------------------------------------------------------------------
#    Measure Area All
# ------------------------------------------------------------------------

class MeasureAreaSelectedOperator (bpy.types.Operator):
	"""Measure the area of all faces in selected object"""
	bl_idname = "wm.measure_area_all"
	bl_label = "AllFaces"

	def execute(self, context):

		obj = bpy.context.active_object
		face_data=measure_helper.measure_selected_faces_area(obj,True)

		self.report({'INFO'}, "faces %d: area %f"%(face_data[0],face_data[1]))

		return {'FINISHED'}

# ------------------------------------------------------------------------
#    Measure Area Selected
# ------------------------------------------------------------------------

class MeasureAreaAllOperator (bpy.types.Operator):
	"""Measure the area of selected faces in selected object"""
	bl_idname = "wm.measure_area_selected"
	bl_label = "SelectedFaces"

	def execute(self, context):

		obj = bpy.context.active_object
		face_data=measure_helper.measure_selected_faces_area(obj,False)

		self.report({'INFO'}, "faces %d: area %f"%(face_data[0],face_data[1]))

		return {'FINISHED'}


class MeasureVolumeOperator (bpy.types.Operator):
	"""Measure the volume of selected object"""
	bl_idname = "wm.measure_volume"
	bl_label = "MeasureVolume"

	def execute(self, context):

		total_volume=0
		total_weight=0

		for obj in bpy.context.selected_objects:
			if obj.type=="MESH":
				volume=measure_helper.measure_object_volume(obj)
				total_volume+=volume
				aluminum_weight=volume*measure_helper.aluminum_weight
				total_weight+=aluminum_weight

		self.report({'INFO'}, "Volume: %f m3 (aluminum: %f kg)"%(total_volume,total_weight))

		return {'FINISHED'}


class CalculateCGOperator (bpy.types.Operator):
	"""Calculate CG of selected objects"""
	bl_idname = "wm.calculate_cg"
	bl_label = "Calc CG"

	def execute(self, context):

		influence_object_list=[]

		for obj in bpy.context.selected_objects:
			if obj.type=="MESH":
				influence_object_list.append(obj)
		
		measure_helper.calculate_cg(influence_object_list)


		return {'FINISHED'}


class RollTestOperator (bpy.types.Operator):
	"""RollTest - Calculate righting moment"""
	bl_idname = "wm.rolltest"
	bl_label = "RollTest"

	def execute(self, context):

		mytool = context.scene.hullsim_Props

		hull_object=bpy.context.active_object

		csv_file=None

		if mytool.output_csv==True:
			csv_file="hydro.csv"

		
		force_roll_max=180
			
		sim_helper.submerge_boat(hull_object,
			mytool.hull_weight,mytool.simulate_depth,
			mytool.simulate_pitch,
			False,
			force_roll_max,
			csv_file)

		return {'FINISHED'}


class SubmergeOperator (bpy.types.Operator):
	"""Float boat according to CG"""
	bl_idname = "wm.submerge"
	bl_label = "Submerge"

	def execute(self, context):

		#bpy.ops.object.bpysim_operator('INVOKE_DEFAULT')

		#return {'FINISHED'}

		mytool = context.scene.hullsim_Props

		print("Weight:", mytool.hull_weight)

		hull_object=bpy.context.active_object

		csv_file=None

		if mytool.output_csv==True:
			csv_file="bpyhullgen_hydro.csv"
		
		sim_helper.submerge_boat(hull_object,
			mytool.hull_weight,mytool.simulate_depth,
			mytool.simulate_pitch,
			mytool.simulate_roll,
			0,
			csv_file)

		return {'FINISHED'}

# ------------------------------------------------------------------------
#    my tool in objectmode
# ------------------------------------------------------------------------

class OBJECT_PT_bpyhullsim_panel (Panel):

	bl_label = "bpyHullSim"
	bl_space_type = "VIEW_3D"   
	bl_region_type = "UI"
	bl_category = "bpyHullSim"


	@classmethod
	def poll(self,context):
		return context.object is not None

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		mytool = scene.hullsim_Props

		row = layout.row()
		row.label(text="Measure:")
		rowsub = layout.row(align=True)
		rowsub.operator( "wm.measure_area_selected")
		rowsub.operator( "wm.measure_area_all")
		rowsub = layout.row(align=True)
		rowsub.operator( "wm.measure_volume")
		rowsub.operator( "wm.calculate_cg")
		
		
		
		row = layout.row()
		row.label(text="Hydrostatics:")
		rowsub = layout.row(align=True)
		layout.prop( mytool, "hull_weight")
		layout.prop( mytool, "output_csv")
		layout.prop( mytool, "simulate_roll")
		layout.prop( mytool, "simulate_pitch")
		layout.prop( mytool, "simulate_depth")
		rowsub.operator( "wm.submerge")
		rowsub.operator( "wm.rolltest")
