# MolPrint

A Blender add-on that provides a variety of tools for processing molecular models for 3D printing.
The main feature is the ability to "pin" ball-and-stick models to allow complicated molecular structures
to be printed as independent pieces and assembled post-printing. This eliminates a significant amount of support material for 
fused filament printing and enhances the educational value of models by allowing rotation around specific bonds.

Additional features include:
- Automated group coloring to visualize model splitting.
- Selection schemes for common macromolecules (protein/nucleic acid).
- Separation by atom type (atomic radius) to generate models for multi-color printing.
- Choice of cylindrical or rectangular pins to allow or restrict torsion of final model
- Processing of CPK (space-filling) models for multi-color printing (VERY SLOW)
- Basic tools for automatic model orientation to improve build plate placement.
- Manual "strut" placement
- Manual bond size adjustements

# Workflow
- VRML2 scenes are generated from molecular graphics software (PyMol, Chimera, JMol) are imported through MolPrint.
- Models are cleaned to remove extraneous objects and fix bonds in some cases
- Different groups are assigned by selecting interacting cylinders and spheres. A pin will be created at each location.
- Groups are pinned and joined together
- Models are "floored" to the build plate
- Models are exported as STL files for printing.

Video introduction:
https://youtu.be/0eEAlyHRbp4
