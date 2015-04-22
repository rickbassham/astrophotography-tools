# astrophotography-tools
A set of tools to help with astrophotography.

## autosolver

autosolver is a python script that will watch a folder for new .jpg files. It
will attempt to use solve-field from astrometry.net to determine the center
coordinates of the image, save the output files in the folder specified on the
command line, and then update Stellarium with the current location of your
telescope.
