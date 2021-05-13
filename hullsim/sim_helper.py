import bpy

import queue
from math import radians, degrees

from ..bpyutils import bpy_helper
from ..bpyutils import material_helper
from ..bpyutils import measure_helper

from bpy.app.handlers import persistent

bouyancy_text_object=None
bouyancy_text_object_name="buoyancy_text"

import csv

@persistent
def frame_change_handler(scene):

	if bouyancy_text_object_name in bpy.data.objects:
		bouyancy_text_object=bpy.data.objects[bouyancy_text_object_name]

		current_frame=bpy.context.scene.frame_current
	
		weight=0

		if measure_helper.CG_object_name in bpy.data.objects:
			CG_object=bpy.data.objects[measure_helper.CG_object_name]
			x_rot=degrees(CG_object.rotation_euler[0])
			if "displacement_data" in CG_object:
				displacement_data=CG_object["displacement_data"]

				if displacement_data!=None:

					if current_frame > 0:
						if current_frame-1 < len(displacement_data):	
							weight=displacement_data[current_frame-1]
						else:
							# if you scroll past last frame - use last weight (heaviest)
							if len(displacement_data)>1:
								weight=displacement_data[len(displacement_data)-1]

		bouyancy_text_object.data.body="Displacement: %0.02fkg\nRoll: %d degrees"%(weight,x_rot)
	
def register_text_update_callback():
	if frame_change_handler not in bpy.app.handlers.frame_change_post:
		bpy.app.handlers.frame_change_post.append(frame_change_handler)

def unregister_text_update_callback():
    bpy.app.handlers.frame_change_post.remove(frame_change_handler)



class SimSession:

	hull_object=None
	weight=250
	simulate_depth=True
	simulate_pitch=True
	simulate_roll=True

	# If doing a forced rollover - it will iterate roll degrees between 1 and force_roll_max
	force_roll_max=None

	csv_output_filename=None

	displacement_diff=0
	cg_empty=None

	x_arm=0
	y_arm=0

	

	def __init__(self,hull_object,weight,
			simulate_depth,
			simulate_pitch,
			simulate_roll,
			force_roll_max,
			csv_output_filename):

		self.weight=weight

		self.hull_object=hull_object
		self.simulate_depth=simulate_depth
		self.simulate_pitch=simulate_pitch
		self.simulate_roll=simulate_roll
		self.force_roll_max=force_roll_max

		self.csv_output_filename=csv_output_filename

	water_volume=None
	water_displaced_volume=None
	simulation_longest_dimension=0

	def make_water_volume(self):

		# Water volume
		water_object_name="water_volume"

		bpy_helper.find_and_remove_object_by_name(water_object_name)


		# calculation dimensions needed for water volume

		simulation_longest_dimension=self.hull_object.dimensions.y

		if self.hull_object.dimensions.x>simulation_longest_dimension:
			simulation_longest_dimension=self.hull_object.dimensions.x

		if self.hull_object.dimensions.z>simulation_longest_dimension:
			simulation_longest_dimension=self.hull_object.dimensions.z
		
		# oversize it a bit so we have a margin
		simulation_longest_dimension=simulation_longest_dimension*2

		# make it a cube bigger than longest side so object can be rotated 
		# in any direction and still fit in the simulation volume cube
		simulation_depth=simulation_longest_dimension
		simulation_width=simulation_longest_dimension
		simulation_length=simulation_longest_dimension

		bpy.ops.mesh.primitive_cube_add(size=1, 
			enter_editmode=False, 
			location=(0,0,-simulation_longest_dimension/2))

		self.water_volume=bpy.context.view_layer.objects.active

		bpy.ops.transform.resize(value=(simulation_length,simulation_width,simulation_depth))

		bpy.ops.object.transform_apply(scale=True,location=False)

		self.water_volume.name=water_object_name
		self.water_volume.display_type="WIRE"

		water_material=material_helper.make_subsurf_material("water",(0,0,0.8,0))

		material_helper.assign_material(self.water_volume,water_material)

		# Displacement area
		water_displaced_name="water_displaced"

		bpy_helper.find_and_remove_object_by_name(water_displaced_name)

		#displace_depth=depth-0.5
		#displace_width=width-0.5
		#displace_length=length=length-0.5

		bpy.ops.mesh.primitive_cube_add(size=1, 
			enter_editmode=False, 
			location=(0,0,-simulation_longest_dimension/2))

		self.water_displaced_volume=bpy.context.view_layer.objects.active

		bpy.ops.transform.resize(value=(simulation_longest_dimension,simulation_longest_dimension,simulation_longest_dimension))

		bpy.ops.object.transform_apply(scale=True,location=False)

		self.water_displaced_volume.name=water_displaced_name
		self.water_displaced_volume.display_type="WIRE"

		water_displaced_material=material_helper.make_subsurf_material("water",(1,0,0.8,0))

		material_helper.assign_material(self.water_displaced_volume,water_displaced_material)

		self.water_displaced_volume.show_axis = True

		displacement_modifier_name="water_displaced"
		bool_water_displaced = self.water_displaced_volume.modifiers.new(type="BOOLEAN", name=displacement_modifier_name)
		bool_water_displaced.object = self.hull_object
		bool_water_displaced.operation = 'INTERSECT'



	csvWriter=None
	csvfile=None

	def init_csv_file(self):

		if self.csv_output_filename!=None:

			self.csvfile = open(self.csv_output_filename, 'w', newline='')
			self.csvWriter = csv.writer(self.csvfile, delimiter=',',
						quotechar='|', quoting=csv.QUOTE_MINIMAL)


			# Write header data to CSV file
			csv_row = []

			csv_row.append("step")
			csv_row.append("frame")

			csv_row.append("displacement_diff")
			csv_row.append("self.displaced_weight")
			csv_row.append("Z_step")
			csv_row.append("hullZ")
			
			csv_row.append("rotation_Y")
			csv_row.append("y_arm")
			csv_row.append("y_step")

			csv_row.append("rotation_X")
			csv_row.append("x_arm")
			csv_row.append("x_step")

			self.csvWriter.writerow(csv_row)

	def write_csv_status(self,x_step,y_step,z_step):
		if self.csvWriter!=None:

			# only log once it's reached equilibrium if doing roll test
			#if self.force_roll_max==0 or (self.simulate_depth and displacement_diff<weight_solve_threshold):

			csv_row = []

			csv_row.append(self.simulation_step) #1
			csv_row.append(bpy.context.scene.frame_current) #2

			csv_row.append("%0.01f"%self.displacement_diff) #3
			csv_row.append("%0.01f"%self.displaced_weight) #4
			csv_row.append("%0.04f"%z_step) #5

			csv_row.append("%0.04f"%self.cg_empty.location.z) #6

			csv_row.append("%0.02f"%degrees(self.cg_empty.rotation_euler.y))  #7 pitch
			csv_row.append("%0.04f"%self.y_arm) #8
			csv_row.append("%0.04f"%y_step) #9

			csv_row.append("%0.02f"%degrees(self.cg_empty.rotation_euler.x)) #10 roll
			csv_row.append("%0.04f"%self.x_arm) #11
			csv_row.append("%0.04f"%x_step) #12

			self.csvWriter.writerow(csv_row)


	def report_status(self,x_step,y_step,z_step):

		statusText=("s:%004d f: %004d | Xr:%0.03f Xa:%0.04f Xs:%0.04f | Yr:%0.03f Ya:%0.04f  Ys: %0.04f | Zp: %0.04f Zd:%0.3f Zs:%0.04f"%(

						self.simulation_step,
						bpy.context.scene.frame_current,

						self.rotationX,
						self.x_arm,
						x_step,

						self.rotationY,
						self.y_arm,
						y_step,


						self.cg_empty.location.z,
						self.displacement_diff,
						z_step,
						
						))

		print(statusText)
		

	simulation_step=0
	displacement_data=None

	status_message="-"


	def create_bouyancy_text(self):

		register_text_update_callback()

		if bouyancy_text_object_name in bpy.data.objects:
			bouyancy_text_object=bpy.context.scene.objects[bouyancy_text_object_name]
		else:
			bpy.ops.object.text_add(enter_editmode=False, location=(0, 0, self.hull_object.dimensions[2]+1))
			bouyancy_text_object=bpy.context.view_layer.objects.active
			bouyancy_text_object.name=bouyancy_text_object_name
			bpy.ops.transform.rotate(value=radians(-90),orient_axis='X')
			bouyancy_text_object.data.extrude = 0.05
			bouyancy_text_object.data.size=0.6

		self.displacement_data=[]


	# queue used for calculating velocity of falling object
	weightQueue=None

	def run_simulation(self,limitsteps):

		if self.hull_object.type!="MESH":
			self.status_message="Must select mesh object"
			print(self.status_message)
			return

		simulation_timer=bpy_helper.ElapsedTimer()

		self.init_csv_file()

		self.create_bouyancy_text()

		self.weightQueue = queue.Queue(maxsize=5) # length of queue

		bpy.context.scene.frame_set(1)

		self.hull_object.animation_data_clear()

		# goto first frame
		bpy.context.scene.frame_set(bpy.context.scene.frame_start)

		# First see if we have existing CG set
		self.cg_empty=bpy.data.objects.get(measure_helper.CG_object_name)

		# if no CG already set - calculate CG
		if self.cg_empty==None:
			self.cg_empty=measure_helper.calculate_cg([self.hull_object])
		else:
			# delete all keyframes so it doesn't interfere with our simulation
			self.cg_empty.animation_data_clear()

		if self.cg_empty==None:
			self.status_message="No object selected"
			print(self.status_message)
			return
	
		# parent it in case it was assigned to different object
		bpy_helper.parent_objects_keep_transform(self.cg_empty,self.hull_object)

		#continueSolving=True

		self.simulation_step=0

		#force_roll_current=0

		#water_volume_phantom=None

		# Bring to center X any Y location
		self.cg_empty.location.x=0
		self.cg_empty.location.y=0

		# start hull off above water - start at the height of the hull
		self.cg_empty.location.z=self.hull_object.dimensions[2]

		# =======================================================
		# Create water volume and booleans for calculating displacement
		# =======================================================
		self.make_water_volume()

		self.rotationY=0
		self.rotationX=0

		continue_simulation=True

		x_step=0
		y_step=0
		z_step=0

		while continue_simulation:
			
			self.calculate_physics()

			# =======================================================
			# Log results and reporting part of simulation
			# =======================================================

			self.report_status(x_step,y_step,z_step)

			#if ( (self.force_roll_max==0 and self.displaced_weight>0) or 
			#		self.force_roll_max>0):
			#	self.write_csv_status(x_step,y_step,z_step)

			if self.simulation_step==0 and self.force_roll_max==0:

				#if self.force_roll_max==0:
				self.bake_keyframes()
				self.write_csv_status(x_step,y_step,z_step)
			else:

				# To make the resulting output animation smoother we should skip some keyframes frames that are considered subframes in the simulation.
				# Subframes are not rendered but used for the calculation...
				# If a forced roll test - only log steps when roll degrees change
				# If not force roll test - only log when height changes
				if (self.force_roll_max==0 and z_step>0) or \
					(self.force_roll_max>0 and abs(x_step)>0):
					self.bake_keyframes()
					self.write_csv_status(x_step,y_step,z_step)

			if self.check_simulation_finished(limitsteps)==True:
				continue_simulation=False
			else:

				# ==================================
				# Process some changes
				# ==================================

				y_step=self.process_pitch()

				x_step=self.process_roll()

				z_step=self.process_submersion()
				
				self.simulation_step+=1


		# finalize simulation and cleanup

		if self.csvfile!=None:
			self.csvfile.close()	

		self.cg_empty["displacement_data"]=self.displacement_data

		# mark end of submersion animation
		bpy.context.scene.frame_end=bpy.context.scene.frame_current

		simulation_timer.get_elapsed_string()

		# Select hull object so we can repeat operation if needed
		bpy_helper.select_object(self.hull_object)


	def calculate_physics(self):

		# =======================================================
		# Calculate hydro physics status of current state
		# =======================================================

		displaced_volume=measure_helper.measure_object_volume(self.water_displaced_volume)

		# displaced water 1 cubic meter =1000kg (Aprox - not factoring for temp or saltwater ect..)
		self.displaced_weight=displaced_volume*1000

		self.displacement_diff=abs(self.displaced_weight-self.weight)

		#cg_world_location=self.cg_empty.matrix_world.to_translation()
		cg_world_location=self.cg_empty.location

		displaced_water_cg=measure_helper.cg_mesh(self.water_displaced_volume)

		#x_arm=water_displaced_volume.location.y-cg_world_location[0]	# X
		#y_arm=water_displaced_volume.location.x-cg_world_location[1]	# Y

		if self.displaced_weight>0:
			# this is a bit hard to get your head around - flipped from what you think it should be...
			# - Pitch rotates around the Y axis and the arm for Pitch is measured on the X axis
			# - Roll rotates around the X axis and the arm for Pitch is measured on the Y axis
			self.x_arm=displaced_water_cg.x-cg_world_location[1]	# X
			self.y_arm=displaced_water_cg.y-cg_world_location[0]	# Y

			print("cg: (%0.4f %0.4f) displaced(%0.4f,%0.4f)"%(
				cg_world_location[0],
				cg_world_location[1],
				displaced_water_cg.x,
				displaced_water_cg.y,))
		else:
			# if we haven't displaced any water - assume everything is balanced
			self.x_arm=0
			self.y_arm=0
		
	
		if self.weightQueue.full():
			self.weightQueue.get()

		self.weightQueue.put(self.displaced_weight)

		# Cache last roll angle to detect roll movement
		#last_roll_y=degrees(self.hull_object.rotation_euler.y)

	def update_status_message(self,message):
		self.status_message=message
		print(self.status_message)
		bpy.context.workspace.status_text_set(text=message)


	def check_simulation_finished(self,limitsteps):

		# =======================================================
		# Detect if we should abort or continue simulation
		# =======================================================		

		# Abort if hull deeper than water volume... something went wrong
		if self.cg_empty.location.z>self.water_volume.dimensions.z:
			self.update_status_message("Aborting -too deep Hull Z: %f > water height: %f"%(self.cg_empty.location.z,self.water_volume.dimensions.z))
			return True

		# Abort if runaway...
		if self.simulation_step>limitsteps:
			self.update_status_message("Aborting - suspected runaway simulation (%d steps)"%limitsteps)
			return True

		# =======================================================
		# Detect when it's time to abort the simulation
		# =======================================================
		if self.force_roll_max==0:

			# If we aren't doing a forced rollover test - detect if simulation is complete

			if ( (self.simulate_pitch and abs(self.x_arm)<self.arm_solve_threshold) or self.simulate_pitch==False) and \
				( (self.simulate_roll and abs(self.y_arm)<self.arm_solve_threshold) or self.simulate_roll==False) and \
				( (self.simulate_depth and self.displacement_diff<self.weight_solve_threshold) or self.simulate_depth==False):				
				self.update_status_message("Finished - all parameters stabilized")
				return True
		else:
			# we are doing a forced rollover - 
			# Abort forced rollover test when we reach the max rollover angle
			if abs(self.rotationX)>=self.force_roll_max:
					self.update_status_message("Finished - rolltest reached max roll target")
					return True

		return False

	# Arm solve threshold for finish solving (pitch and roll)
	arm_solve_threshold=0.005 # Solve rotation within 5mm arm
	weight_solve_threshold=5 # solve bouyancy displacement within 5kg

	# calculates amount to rotate (around X or Y axis) to solve simulation
	# larger arm = more movement (faster rotation)
	# arm = weight X moment
	def calculate_rotate_step(self,rotate_arm):

		rotate_step=0

		abs_rotate_arm=abs(rotate_arm)

		if abs_rotate_arm>self.arm_solve_threshold*10:
			rotate_step=0.1
		elif abs_rotate_arm>self.arm_solve_threshold*5:
			rotate_step=0.05
		elif abs_rotate_arm>self.arm_solve_threshold:
			rotate_step=0.01


		#if abs_rotate_arm<0.1:
		#	rotate_step=0.01
		#elif abs_rotate_arm<0.5:
		#	rotate_step=0.05
		#elif abs_rotate_arm<1:
		#	rotate_step=0.1
		#else:
		#	rotate_step=0.25



		if rotate_arm>0:
			rotate_step=-rotate_step

		print("rotate step: %f"%rotate_step)

		return rotate_step

	def process_pitch(self):

		#bpy_helper.select_object(self.hull_object,True)

		# =======================================================
		# Process pitch part Y of simulation
		# =======================================================
		y_step=0

		if self.simulate_pitch==True:
			# Only rotate once object hits the water
			if self.displaced_weight>0:

				# Only pitch if arm is greater than threshold
				if abs(self.x_arm)>self.arm_solve_threshold:

					y_step=self.calculate_rotate_step(self.x_arm)

					if y_step!=0:

						self.rotationY+=y_step

						#self.hull_object.rotation_euler.y=radians(self.rotationY)
						self.cg_empty.rotation_euler.y=radians(self.rotationY)

		return y_step

	def process_roll(self):

		# =======================================================
		# Process roll around the X axis part of simulation
		# =======================================================
		x_step=0

		if self.force_roll_max>0:
			# If we are doing a forced rollover test - only roll over one degree if bouyancy displacement has reached equilibrium 
			if ( (self.simulate_depth and self.displacement_diff<self.weight_solve_threshold) or self.simulate_depth==False):
				# only roll over if pitch is stable
				if abs(self.x_arm)<self.arm_solve_threshold:
					x_step=-1
					
		else:
			# we are NOT doing a forced rollover test

			# Only rotate once object hits the water
			if self.displaced_weight>0:

				# only roll if greater than threshold
				if abs(self.y_arm)>self.arm_solve_threshold:
					x_step=self.calculate_rotate_step(self.y_arm)

		if x_step!=0:
			if self.simulate_roll==True:
				self.rotationX-=x_step
				
				#self.hull_object.rotation_euler.x=radians(self.rotationX)
				self.cg_empty.rotation_euler.x=radians(self.rotationX)

		return x_step


	def process_submersion(self):

		# =======================================================
		# Adjust water submersion depth (Z position) part of simulation
		# =======================================================
		z_step=0

		# don't mess with submersion unless pitch or roll stabalized or we haven't touched water yet
		#if (y_step==0 and x_step==0) or self.displaced_weight<0:

		# calculates amount to move up or down in Z axis to solve simulation
		move_arm=abs(self.displacement_diff)

		if move_arm<10:
			z_step=0.0001
		elif move_arm<50:
			z_step=0.001
		elif move_arm<100:
			z_step=0.008
		else:
			z_step=0.01

		average_threshold=5

		# =======================================================
		# Maintain a history (queue) of displacement weights to detect velocity trend... 
		# =======================================================	
		queueSum=0
		queueAverage=0

		for i in range(0,self.weightQueue.qsize()):
			#print("weight: %f average: %f"%(self.weightQueue.queue[i],queueAverage))
			queueSum+=self.weightQueue.queue[i]
			queueAverage=queueSum/(i+1)


		# calculate average displacement for last simulation steps
		# If current displacement is same or similar to queue Average - our velocity is stable
		# If current displacement is less than queue average - we bounced up
		# If current displacement is more than queue average - we are sinking
		if self.weightQueue.qsize()>0:
			queueAverage=queueSum/self.weightQueue.qsize()

		#print("Average: %f limits(%f %f)"%(queueAverage,queueAverage-average_threshold,queueAverage+average_threshold))

		if (queueAverage+average_threshold)<self.weight:
			#self.hull_object.location.z-=z_step
			self.cg_empty.location.z-=z_step
			#print("lower")
		elif (queueAverage-average_threshold)>self.weight:
			#self.hull_object.location.z+=z_step
			self.cg_empty.location.z+=z_step
			#print("higher")
		else:
			z_step=0

		return z_step

	def bake_keyframes(self):

		# =======================================================
		# Bake simulation steps into keyframes
		# =======================================================

		current_frame=bpy.context.scene.frame_current
		
		self.cg_empty.keyframe_insert(data_path="location", frame=current_frame) #, index=0)
		self.cg_empty.keyframe_insert(data_path="rotation_euler", frame=current_frame) #, index=0)
		bpy.context.scene.frame_set(current_frame+1)
		current_frame=bpy.context.scene.frame_current

		# Cache weight for frame (used in frame_change_handler function)
		self.displacement_data.append(self.displaced_weight)

		# Update viewport - whenever we make a keyframe
		#bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
		#bpy.context.view_layer.update()


