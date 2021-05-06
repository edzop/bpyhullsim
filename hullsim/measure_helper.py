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

import bpy

import bmesh
import csv

from ..hullsim import bpy_helper

CG_object_name="CG"

#from math import radians, degrees
#from bpy.props import *
#from bpy.props import FloatProperty, BoolProperty, FloatVectorProperty


#from ..hullsim import bpy_helper
#from ..hullsim import material_helper

# hard coded to 5083 aluminum for now
# expressed as KG per m3
aluminum_weight=2653

material_weight=aluminum_weight



# =======================================================================================
# This bmesh_copy_from_object function was borrowed from the object_print3d_utils addon.
# I found it in the default blender 2.8 installation under the file:
# addons/object_print3d_utils/mesh_helpers.py
# Credit due to whoever the author is. 
# =======================================================================================
def bmesh_copy_from_object(obj, transform=True, triangulate=True, apply_modifiers=False):
	"""
	Returns a transformed, triangulated copy of the mesh
	"""

	assert obj.type == 'MESH'

	if apply_modifiers and obj.modifiers:
		import bpy
		depsgraph = bpy.context.evaluated_depsgraph_get()
		obj_eval = obj.evaluated_get(depsgraph)
		me = obj_eval.to_mesh()
		bm = bmesh.new()
		bm.from_mesh(me)
		obj_eval.to_mesh_clear()
		del bpy
	else:
		me = obj.data
		if obj.mode == 'EDIT':
			bm_orig = bmesh.from_edit_mesh(me)
			bm = bm_orig.copy()
		else:
			bm = bmesh.new()
			bm.from_mesh(me)

	# TODO. remove all customdata layers.
	# would save ram

	if transform:
		bm.transform(obj.matrix_world)

	if triangulate:
		bmesh.ops.triangulate(bm, faces=bm.faces)

	return bm


# returns empty object representing center of gravity location
def calculate_cg(influence_objects):

	title_object=influence_objects[0]
	CG_object_name

	bpy_helper.find_and_remove_object_by_name(CG_object_name)

	bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
	cg_empty = bpy.context.active_object
	cg_empty.name=CG_object_name
	cg_empty.empty_display_type = 'SPHERE'


	# Moment = weight * arm

	total_weight=0
	total_moment=[0,0,0]
	cg_pos=[0,0,0]

	for obj in influence_objects:

		bpy.ops.object.select_all(action='DESELECT')
		bpy_helper.select_object(obj,True)
		#bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')

		object_volume=measure_object_volume(obj)

		face_data=measure_selected_faces_area(obj,True)

		# object surface area in m2
		object_face_area=face_data[1]



		# hdpe 970 KG per m3

		# hard coded 3mm for now
		material_thickness=0.003

		object_weight=material_thickness*material_weight*object_face_area

		total_weight=total_weight+object_weight

		print("Object: %s Weight: %f KG Total weight: %d KG"%(obj.name,object_weight,total_weight))

		# Calculate 3D moment tuple for this influence object
		object_moment=[	object_weight*obj.location.x,
						object_weight*obj.location.y,
						object_weight*obj.location.z ]

		total_moment[0]=total_moment[0]+object_moment[0]
		total_moment[1]=total_moment[1]+object_moment[1]
		total_moment[2]=total_moment[2]+object_moment[2]

		assign_weight(obj,object_weight)



	if total_weight>0:
		# offset center of gravity by moment
		cg_pos[0]=total_moment[0]/total_weight
		cg_pos[1]=total_moment[1]/total_weight
		cg_pos[2]=total_moment[2]/total_weight

		print("Total weight: %d KG CG: %f %f %f"%(total_weight,cg_pos[0],cg_pos[1],cg_pos[2]))

		
		cg_empty.location[0]=cg_pos[0]
		cg_empty.location[1]=cg_pos[1]
		cg_empty.location[2]=cg_pos[2]
	else:
		# prevent divide by zero
		print("Something went wrong... no total weight calculated")

	assign_weight(cg_empty,total_weight)
	
	return cg_empty



def measure_object_volume(obj):

	bm = bmesh_copy_from_object(obj, apply_modifiers=True)
	volume = bm.calc_volume()
	bm.free()

	aluminum_weight=volume*material_weight

	print("Volume: %f (Aluminum: %f)"%(volume,aluminum_weight))

	return volume

def measure_selected_faces_area(obj,SelectAll=False):

	previous_mode=obj.mode

	# Selection not accurate if not in object mode... 
	bpy.ops.object.mode_set(mode='OBJECT')

	selected_face_count=0
	total_area=0

	if SelectAll==True:
		bpy_helper.select_object(obj,True)
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_all(action='SELECT')
		bpy.ops.object.mode_set(mode='OBJECT')

	for f in obj.data.polygons:
		if f.select:
			selected_face_count+=1
			total_area+=f.area

	face_data=[selected_face_count,total_area]

	bpy.ops.object.mode_set(mode=previous_mode)

	return face_data

	
def assign_weight(obj,weight):

	rna_ui = obj.get('_RNA_UI')
	if rna_ui is None:
		rna_ui = obj['_RNA_UI'] = {}

	rna_ui = obj.get('_RNA_UI')

	# property attributes.for UI 
	rna_ui["weight"] = {"description":"Multiplier for Scale",
					"default": 1.0,
					"min":0.0,
					"max":100000.0,
					"soft_min":0.0,
					"soft_max":10000.0,
					"is_overridable_library":False
					}

	obj["weight"]=weight

# Gets the distance between two selected vertices on selected object
# Assumes you are in edit mode and have only 2 vertices selected
def get_distance_between_two_selected_points():

	obj = bpy.context.object
	
	selected_vertices=[]
	
	if obj==None:
		print("No Object Selected")
		return 0
	
	# cycle between edit mode and object mode to ensure selections are propogated
	# from temporary copy
	bpy.ops.object.mode_set(mode='OBJECT')
	bpy.ops.object.mode_set(mode='EDIT')


	for v in bpy.context.active_object.data.vertices:
		if v.select:
			print(str(v.select))
			co_final =  obj.matrix_world @ v.co
			print(co_final)
			selected_vertices.append(co_final)
			
	print(len(selected_vertices))
		
	if len(selected_vertices)>2:
		print("Please select only 2 vertices")
		return 0
	
	distance=(selected_vertices[0]-selected_vertices[1]).length

	return distance
		


