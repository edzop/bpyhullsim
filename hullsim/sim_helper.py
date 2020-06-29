
import bpy


import queue
from math import radians, degrees


from ..hullsim import bpy_helper
from ..hullsim import material_helper
from ..hullsim import measure_helper

bouyancy_text_object=None
bouyancy_text_object_name="bouyancy_text"

import csv


def make_water_volume():

	# Water volume
	water_object_name="water_volume"

	bpy_helper.find_and_remove_object_by_name(water_object_name)

	depth=5
	width=5
	length=15

	bpy.ops.mesh.primitive_cube_add(size=1, 
		enter_editmode=False, 
		location=(0,0,-depth/2))

	water_volume=bpy.context.view_layer.objects.active

	bpy.ops.transform.resize(value=(length,width,depth))

	bpy.ops.object.transform_apply(scale=True,location=False)

	water_volume.name=water_object_name
	water_volume.display_type="WIRE"

	water_material=material_helper.get_material_water()

	material_helper.assign_material(water_volume,water_material)

	# Displacement area
	water_displaced_name="water_displaced"

	bpy_helper.find_and_remove_object_by_name(water_displaced_name)

	displace_depth=depth-0.5
	displace_width=width-0.5
	displace_length=length=length-0.5

	bpy.ops.mesh.primitive_cube_add(size=1, 
		enter_editmode=False, 
		location=(0,0,-displace_depth/2))

	water_displaced_volume=bpy.context.view_layer.objects.active

	bpy.ops.transform.resize(value=(displace_length,displace_width,displace_depth))

	bpy.ops.object.transform_apply(scale=True,location=False)

	water_displaced_volume.name=water_displaced_name
	water_displaced_volume.display_type="WIRE"

	water_displaced_material=material_helper.get_material_water_displaced()

	material_helper.assign_material(water_displaced_volume,water_displaced_material)

	return (water_volume,water_displaced_volume)


def frame_change_handler(scene):
	current_frame=bpy.context.scene.frame_current
	
	weight=0

	if measure_helper.CG_object_name in bpy.data.objects:
		CG_object=bpy.data.objects[measure_helper.CG_object_name]
		if "displacement_data" in CG_object:
			displacement_data=CG_object["displacement_data"]

			if current_frame > 0:
				if current_frame-1 < len(displacement_data):	
					weight=displacement_data[current_frame-1]
				else:
					# if you scroll past last frame - use last weight (heaviest)
					weight=displacement_data[len(displacement_data)-1]

	if bouyancy_text_object_name in bpy.data.objects:
		bouyancy_text_object=bpy.data.objects[bouyancy_text_object_name]

	bouyancy_text_object.data.body="Displacement: %0.02fkg"%(weight)
	
def register_text_update_callback():
	if frame_change_handler not in bpy.app.handlers.render_complete:
		bpy.app.handlers.frame_change_post.append(frame_change_handler)

#def unregister():
#    bpy.app.handlers.frame_change_post.remove(my_handler)


# calculates amount to rotate (around X or Y axis) to solve simulation
# larger arm = more movement (faster rotation)
# arm = weight X moment
def calculate_rotate_step(rotate_arm):

	rotate_step=0.05

	if rotate_arm<0.1:
		rotate_step=0.01
	elif rotate_arm<0.5:
		rotate_step=0.05
	elif rotate_arm<1:
		rotate_step=0.1
	else:
		rotate_step=0.25

	return rotate_step

def calculate_movement_step(move_arm):

	move_step=move_arm

	if move_step<10:
		move_step=0.0001
	elif move_arm<50:
		move_step=0.001
	elif move_arm<100:
		move_step=0.008
	else:
		move_step=0.01

	return move_step
		
#class SimSession:
#    hull_object=None
#    weight=250
#    simulate_depth=True
#    simulate_pitch=True
#    simulate_roll=True
#    force_roll_max=None
#    csv_output_file=None

def submerge_boat(hull_object,weight,
			simulate_depth,
			simulate_pitch,
			simulate_roll,
			force_roll_max,
			csv_output_file):


	weightQueueSize=5
	weightQueue = queue.Queue(weightQueueSize)

	bpy.context.scene.frame_set(1)

	register_text_update_callback()

	if bouyancy_text_object_name in bpy.data.objects:
		bouyancy_text_object=bpy.context.scene.objects[bouyancy_text_object_name]
	else:
		bpy.ops.object.text_add(enter_editmode=False, location=(0, 0, hull_object.dimensions[2]+1))
		bouyancy_text_object=bpy.context.view_layer.objects.active
		bouyancy_text_object.name=bouyancy_text_object_name
		bpy.ops.transform.rotate(value=radians(90),orient_axis='X')
		bouyancy_text_object.data.extrude = 0.05
		bouyancy_text_object.data.size=0.6

	csvWriter=None
	csvfile=None

	if csv_output_file!=None:

		csvfile = open(csv_output_file, 'w', newline='')
		csvWriter = csv.writer(csvfile, delimiter=',',
					quotechar='|', quoting=csv.QUOTE_MINIMAL)

		csv_row = []

		csv_row.append("frame")

		csv_row.append("displacement_diff")
		csv_row.append("displaced_weight")
		csv_row.append("Z_step")
		csv_row.append("hullZ")
		
		csv_row.append("rotation_Y")
		csv_row.append("pitch_arm")
		csv_row.append("pitch_step")

		csv_row.append("rotation_X")
		csv_row.append("roll_arm")
		csv_row.append("roll_step")

		csvWriter.writerow(csv_row)

	hull_object.animation_data_clear()

	bpy.context.scene.frame_set(bpy.context.scene.frame_start)

	cg_empty=measure_helper.calculate_cg([hull_object])
	displacement_data=[]

	continueSolving=True

	hull_weight=weight

	simulation_step=0

	force_roll_current=0

	#water_volume_phantom=None

	# start hull off above water - start at the height of the hull
	hull_object.location.z=hull_object.dimensions[2]

	while continueSolving==True:

		# =======================================================
		# Create water volume and booleans for calculating displacement
		# =======================================================

		# It's slower to recreate volume each time but we need to APPLY the bool modifier to calculate the center of mass...
		water_volumes=make_water_volume()

		water_displaced_volume=water_volumes[1]
		water_displaced_volume.show_axis = True

		water_volume=water_volumes[0]

		displacement_modifier_name="water_displaced"
		bool_water_displaced = water_displaced_volume.modifiers.new(type="BOOLEAN", name=displacement_modifier_name)
		bool_water_displaced.object = hull_object
		bool_water_displaced.operation = 'INTERSECT'

		#if water_volume_phantom==None:
			# Create a copy "the phantom object" of the water displaced volume because we need to apply bool modifier each time...
			# Keep a copy that will be used during rendering
		#	bpy_helper.select_object(water_displaced_volume,True)
		#	bpy.ops.object.duplicate_move()
		#	water_displaced_volume_phantom=bpy.context.view_layer.objects.active

		#bpy.ops.object.select_all(action='DESELECT')

		bpy_helper.select_object(water_displaced_volume,True)

		# Calculate center of mass for displaced water
		# I tried to calculate mass without applying boolean modifier and it doesn't used the post bool modifier data so we have to do it the slow way
		# It's much slower to apply modifier each part of the simulation but I can't find any other way to solve this problem. 
		bpy.ops.object.modifier_apply(apply_as='DATA', modifier=displacement_modifier_name)
		bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')

		simulation_step+=1


		# =======================================================
		# Calculate hydro physics status of current state
		# =======================================================

		displaced_volume=measure_helper.measure_object_volume(water_displaced_volume)

		# displaced water 1 cubic meter =1000kg (Aprox - not factoring for temp or saltwater ect..)
		displaced_weight=displaced_volume*1000

		displacement_diff=abs(displaced_weight-hull_weight)
		pitch_arm=water_displaced_volume.location.x-hull_object.location.x
		roll_arm=water_displaced_volume.location.y-hull_object.location.y
		
		abs_pitch_arm=abs(pitch_arm)
		abs_roll_arm=abs(roll_arm)

		# Arm solve threshold for finish solving (pitch and roll)
		arm_solve_threshold=0.005 # Solve rotation within 5mm arm
		weight_solve_threshold=5 # solve bouyancy displacement within 5kg

		# =======================================================
		# Maintain a history (queue) of displacement weights to detect velocity trend... 
		# =======================================================	
		queueSum=0

		for i in range(0,weightQueue.qsize()):
			#print("weight: %f average: %f"%(weightQueue.queue[i][0],weightQueue.queue[i][1]))
			queueSum+=weightQueue.queue[i][0]

		# calculate average displacement for last simulation steps
		# If current displacement is same or similar to queue Average - our velocity is stable
		# If current displacement is less than queue average - we bounced up
		# If current displacement is more than queue average - we are sinking
		queueAverage=queueSum/weightQueueSize

		if weightQueue.full():
			weightQueue.get()

		weightQueue.put([displaced_weight,queueAverage])

		# Cache last roll angle to detect roll movement
		last_roll_y=degrees(hull_object.rotation_euler.y)


		# =======================================================
		# Detect if we should abort or continue simulation
		# =======================================================		


		# Abort if hull deeper than water volume... something went wrong
		if hull_object.location.z>water_volume.dimensions.z:
			print("Aborting... Hull Z: %f > water height: %f"%(hull_object.location.z,water_volume.dimensions.z))
			continueSolving=False

		# Abort if runaway...
		if simulation_step>6000:
			continueSolving=False

		#print("submerge frame: %d HullZ: %0.03f displaced_weight/hull: %0.3f/%0.3f BouyancyZ: %0.03f"%(
		#	simulation_step,
		#	hull_object.location.z,
		#	displaced_weight,
		#	hull_weight,
		#	water_displaced_volume.location.z
		#	))

		if force_roll_max==0:

			# If we aren't doing a forced rollover test - detect if simulation is complete

			if ( (simulate_pitch and abs_pitch_arm<arm_solve_threshold) or simulate_pitch==False) and \
				( (simulate_roll and abs_roll_arm<arm_solve_threshold) or simulate_roll==False) and \
				( (simulate_depth and displacement_diff<weight_solve_threshold) or simulate_depth==False):
				continueSolving=False
		else:

			# Abort forced rollover test when we reach the max rollover angle

			if force_roll_current>=force_roll_max:
					continueSolving=False


		bpy_helper.select_object(hull_object,True)

		# =======================================================
		# Adjust pitch part of simulation
		# =======================================================
		pitch_step=0

		if simulate_pitch==True:
			# Only rotate once object hits the water
			if displaced_weight>0:

				pitch_step=calculate_rotate_step(abs_pitch_arm)

				if pitch_arm>arm_solve_threshold:
					bpy.ops.transform.rotate(value=radians(-pitch_step),orient_axis='Y')
				elif pitch_arm<arm_solve_threshold:
					bpy.ops.transform.rotate(value=radians(pitch_step),orient_axis='Y')

		# =======================================================
		# Adjust roll part of simulation
		# =======================================================
		roll_step=0
		degrees_rolled=0

		if force_roll_max>0:
			# If we are doing a forced rollover test - only roll over one degree if bouyancy displacement has reached equilibrium 

			if ( (simulate_depth and displacement_diff<weight_solve_threshold) or simulate_depth==False):
				degrees_rolled=1
				force_roll_current+=degrees_rolled
				hull_object.rotation_euler.x=radians(force_roll_current)

		elif simulate_roll==True:
			# Only rotate once object hits the water
			if displaced_weight>0:

				roll_step=calculate_rotate_step(abs_roll_arm)

				if roll_arm>arm_solve_threshold:
					bpy.ops.transform.rotate(value=radians(roll_step),orient_axis='X')
				elif pitch_arm<arm_solve_threshold:
					bpy.ops.transform.rotate(value=radians(-roll_step),orient_axis='X')

		# =======================================================
		# Adjust water submersion depth (Z position) part of simulation
		# =======================================================
		z_step=calculate_movement_step(displacement_diff)

		average_threshold=5

		if (queueAverage+average_threshold)<hull_weight:
			hull_object.location.z-=z_step
		elif (queueAverage-average_threshold)>hull_weight:
			hull_object.location.z+=z_step


		# =======================================================
		# Bake simulation steps into keyframes
		# =======================================================

		# To make the resulting output animation smoother we should skip some keyframes frames that are considered subframes in the simulation.
		# Subframes are not rendered but used for the calculation...

		if force_roll_max==0 or (force_roll_max>0 and degrees_rolled>0):

			# If a forced roll test - only log steps when roll degrees change
			# If not force roll test - log all frames of simulation

			current_frame=bpy.context.scene.frame_current
			hull_object.keyframe_insert(data_path="location", frame=current_frame) #, index=0)
			hull_object.keyframe_insert(data_path="rotation_euler", frame=current_frame) #, index=0)
			bpy.context.scene.frame_set(current_frame+1)

			# =======================================================
			# Log results and reporting part of simulation
			# =======================================================

			# Cache weight for frame (used in frame_change_handler function)
			displacement_data.append(displaced_weight)

			if csvWriter!=None:

				# only log once it's reached equilibrium if doing roll test
				#if force_roll_max==0 or (simulate_depth and displacement_diff<weight_solve_threshold):

				print("Log CSV")

				csv_row = []

				csv_row.append(simulation_step) #1

				csv_row.append("%f"%displacement_diff) #2
				csv_row.append("%f"%displaced_weight) #3
				csv_row.append("%f"%z_step) #4

				csv_row.append("%f"%hull_object.location.z) #5

				csv_row.append("%f"%degrees(hull_object.rotation_euler.y))  #6 pitch
				csv_row.append("%f"%pitch_arm) #7
				csv_row.append("%f"%pitch_step) #8

				csv_row.append("%f"%degrees(hull_object.rotation_euler.x)) #9 roll
				csv_row.append("%f"%roll_arm) #10
				csv_row.append("%f"%roll_step) #11

				csvWriter.writerow(csv_row)

		statusText=("step:%d queue(sum:%f average:%f) dispdiff:%f zstep:%f yRot:%f Yarm:%f xRot:%f Xarm:%f forceroll(%f/%f)"%(
						simulation_step,
						queueSum,
						queueAverage,
						displacement_diff,
						z_step,
						degrees(hull_object.rotation_euler.y),
						pitch_arm,
						degrees(hull_object.rotation_euler.x),
						roll_arm,
						force_roll_current,
						force_roll_max
						))

		print(statusText)
		
		bpy.context.workspace.status_text_set(statusText)	

		# Update viewport
		bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
		#bpy.context.view_layer.update()
	

	if csvfile!=None:
		csvfile.close()	

	cg_empty["displacement_data"]=displacement_data

	# mark end of submersion animation
	bpy.context.scene.frame_end=bpy.context.scene.frame_current



class bpysim_Operator(bpy.types.Operator):
    bl_idname = "object.bpysim_operator"
    bl_label = "Simple Modal Operator"

    counter=0

    def __init__(self):
        print("Start")
        self.counter=0

    def __del__(self):
        print("End")

    def execute(self, context):
        context.object.location.x = self.value / 100.0
        print("execute: %d"%self.counter)
        return {'FINISHED'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':  # Apply
            self.value = event.mouse_x
            self.execute(context)
        elif event.type == 'LEFTMOUSE':  # Confirm
            return {'FINISHED'}
        elif event.type in ('RIGHTMOUSE', 'ESC'):  # Cancel
            context.object.location.x = self.init_loc_x
            return {'CANCELLED'}

        self.counter+=1

        print("modal: %d"%self.counter)

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.init_loc_x = context.object.location.x
        self.value = event.mouse_x
        self.execute(context)
        print("invoke")
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


#bpy.utils.register_class(bpysim_Operator)

# test call
#bpy.ops.object.bpysim_operator('INVOKE_DEFAULT')
