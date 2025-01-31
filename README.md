# Render-Manager
Blender addon to manager render layers

This addon will create a new section in the renderder setting that will allow you to create to delete new render layers, change their order, copy and past pass settings.

It also allows you to use the render layer manager, which is like a speadsheet, to turn on and off any render passes.

The create render node button will setup the compositor nodes in order to export the files as needed.

A precomp will be created by addind all the image outputs from the render layer nodes, hence the importance of being able to change their order.
The color passes will be saved in Multilayer EXR 16 bits, per render layer
The data passes and cryptomattes will be in and EXR 32 bits per render layer

There's an option called Fix for Y Up. This will modify the normal and position passes so that they work in compositing software that are working Y up, like Nuke or Resolve/Fusion

The combine color/Glossy/Trans will combine the three color, glossy or trans passes into one pass, making it easier for compositing.

The denoise option will denoise the image, the diffuse, glossy and transparent passes. 
