# astrophotography-tools
A set of tools to help with astrophotography.

## autosolver

autosolver is a python script that will watch a folder for new .jpg files. It
will attempt to use `solve-field` from [astrometry.net](http://astrometry.net/)
to determine the center coordinates of the image, save the output files in the
folder specified on the command line, and then update
[Stellarium](http://www.stellarium.org/) with the current location of your
telescope. It listens for connections from Stellarium's telescope-control
plugin on port 10001. You can then configure your camera to output to the
output folder and see where you are pointing in Stellarium.

autosolver requires a working install of the astrometry.net software. Please
see their docs for info on how to install it.

Example:

`python autosolver.py --watch-folder ./watch/ --output-folder ./output/`

Thanks to [JuanRa](http://yoestuveaqui.es/blog/communications-between-python-and-stellarium-stellarium-telescope-protocol/)
for the functions to transform D:M:S and H:M:S to a format Stellarium will
accept.
