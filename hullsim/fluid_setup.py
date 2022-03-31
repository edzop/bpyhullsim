import bpy



def make_cube(name,size,location):

	bpy.ops.mesh.primitive_cube_add(size=1, 
		enter_editmode=False, 
			location=location)

	new_cube=bpy.context.view_layer.objects.active
	bpy.ops.transform.resize(value=size)
	bpy.ops.object.transform_apply(scale=True,location=False)

	new_cube.name=name

	return new_cube


def setup_fluid():
	print("setup fluid")

	water_width=10
	water_length=10
	water_height=3


	water_domain = make_cube(name="water_domain",
		size=(water_length,water_width,water_height),
		location=(0,0,0))

	water_fluid = make_cube(name="water_fluid",
		size=(water_length,water_width,water_height/2),
		location=(0,0,-water_height/2/2))

	
	water_domain_modifier = water_domain.modifiers.new(type="FLUID", name="fluid_domain")
	water_domain_modifier.fluid_type="DOMAIN"
	water_domain_modifier.domain_settings.domain_type="LIQUID"

	water_fluid_modifier = water_fluid.modifiers.new(type="FLUID", name="fluid_domain")
	water_fluid_modifier.fluid_type="FLOW"
	water_fluid_modifier.flow_settings.flow_type="LIQUID"
