# bpyhullsim

blender based buoyancy simulator written in python

Designed for use with: [bpyhullgen](https://edzop.github.io/bpyhullgen/)

For further information please refer to [bpyhullgen Github Wiki](https://github.com/edzop/bpyhullgen/wiki)


## User Interface
bpyhullgen has a sidebar panel tab user interface. It may not be visible if an object is not selected. 

![](images/gui.png)

## Measure
### SelectedFaces
Measures the selected faces of the current object. The number of selected faces and total surface area of selected faces for current object will be displayed in the status bar.
### AllFaces
Measures all the faces of the current object. The total number of faces and total surface area of all faces will be displayed in the status bar. 
### MeasureVolume
The volume for the currently selected object will be displayed in the status bar. Only the first object is calculated if multiple selections exist. 
### Calc CG
Calculates the center of mass for multiple objects. A new empty named "CG" will be created in the scene and placed where the center of gravity exists. Multiple object selections are allowed. 

## Hydrostatics

A basic simulation loop can be used to calculate waterline and other hydrostatic parameters for a defined hull. 

### Submerge
The submerge simulation is used to calculate the waterline and balance in water for a specific weight. The weight is defined by the HullWeight GUI textbox and expressed in KG.

A text object with the displacement weight is generated automatically and updated when frames change. The weight data is cached after the simulation so when you render an animation you can see the displacement value for each step of the simulation. 

The displacement data cache is stored in memory and is not saved with the blender file - If you close and reload the blender file and notice you don't see the text updating between frames you may need to rerun the simulation.

The text changing between frames uses a frame_change_handler callback function. 

Simple cube derived mesh submerged to 2000kg and finding it's equilibrium based on center of buoyancy
![bpyhullsim sink](images/sink_cube.gif)

More complex mesh 500kg more rotation is needed to reach equilibrium due to asymmetrical shape
![bpyhullsim sink](images/sink_duck.gif)

Asymmetrical catamaran shaped hull - note the rotation due to uneven floatation on each side.
![bpyhullsim sink](images/sink_cat.gif)

Submerge to 4000kg displacement
![bpyhullsim sink](images/sink.gif)

Submerge with weight on front of vessel (affects center of gravity)
![bpyhullsim sink](images/sink_weight.gif)



### RollTest
The rollover test simulation is used to calculate the righting moment for the hull when tipped over to a specific angle. The rollover test will roll the hull from 0-180 degrees and record the displacement and righting moment (roll arm about X axis) for each angle. 

The roll test uses one degree increments and for each increment several simulation substeps may occur until the hull is submerged to an equilibrium (stabilized state).

The simulation data will be written to hydro.csv file. And a gnuplot file is provided to easily map this data with the command:

```
gnuplot -p plot_rollover.gnuplot
```

Select any mesh object and click the RollTest button. 

Animation keyframes are created for each degree of rotation so you can see how the displacement shifts for each angle. 


#### Sphere rollover test righting moment
The sphere should have the same righting moment at any angle... This animation demonstrates the results when tested with bpyhullsim:

![bpyhullsim rollover](images/rolltest_sphere.gif)
![bpyhullsim rollover](images/rolltest_sphere.png)


#### Cube rollover test righting moment
![bpyhullsim rollover](images/rolltest_cube.gif)
![bpyhullsim rollover](images/rolltest_cube.png)

#### Cat rollover test righting moment
![bpyhullsim rollover](images/rolltest_cat.gif)
![bpyhullsim rollover](images/rolltest_cat.png)

The expected result is curve changing directions about 90 degrees... I need to analyse this test case a bit more to see what's happening.


### HullWeight

not documented yet
