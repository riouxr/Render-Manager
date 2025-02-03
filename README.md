# Render-Manager
Blender addon to manager render layers

This addon will create a new section in the renderder setting that will allow you to create to delete new render layers, change their order, copy and past pass settings.

The collection manager pop a spreadsheet that will allow you to turn on/off the collection, holdout or indirect.

The the render layer manager, which is like a speadsheet, to turn on and off any render passes, shader, world ans sampling overrides.

The create render node button will setup the compositor nodes in order to export the files as needed.

A precomp will be created by addind all the image outputs from the render layer nodes, hence the importance of being able to change their order.
The color passes will be saved in Multilayer EXR 16 bits, per render layer
The data passes and cryptomattes will be in and EXR 32 bits per render layer

Note that the image will be named rgba instead of image so that Nuke can read them without the need of a shuffle node.

The sequences will be saved in a folder named after the render later name.

There's an option called Fix for Y Up. This will modify the normal and position passes so that they work in compositing software that are working Y up, like Nuke or Resolve/Fusion

The combine color/Glossy/Trans will combine the three color, glossy or trans passes into one pass, making it easier for compositing.

The denoise option will denoise the image, the diffuse, glossy and transparent passes. 

Special thanks to Tinkerboi and MJ for there awesome support. 
