#!/usr/bin/python

# Taken from: http://yoestuveaqui.es/blog/communications-between-python-and-stellarium-stellarium-telescope-protocol/

import math
import re
import logging
from time import strftime, localtime
from string import replace

# \brief Functions library for format conversions.
#
#  Contains the necessary functions to calculate most commons format conversions used by the communications
#  with the device and Stellarium.

## From radians to hours, with until six decimals of precision (float)
# (rads * 180)/(15 * pi)
#
# \param rads Radians in float format
# \return Float that represents the number of hours equivalent to the received radians
def rad_2_hour(rads):
    h = round( (rads * 180)/(15 * math.pi), 6)
    if h > 24.0:
        h = h - 24.0
    if h < 0.0:
        h = 24.0 + h
    return h

## Tranforms from degrees in string format to radians
# d = D:M:S => D+(M/60)+(S/60^2) degrees => D.d
#
# \param d Degrees in string format ("D:M:S")
# \return Radians in float format
def degStr_2_rad(d):
    exp1 = re.compile('^-?[0-9]{,3}:[0-9]{,3}:[0-9]{,3}$')

    if(not exp1.match(d)):
        logging.debug("Error parameter: %s" % d)
        return None
    elif(exp1.match(d)):
        d_dic = d.split(':')
        d_deg = float(d_dic[0])
        d_min = float(d_dic[1])
        d_sec = float(d_dic[2])

        if(d_deg < 0):
            d_min = 0 - d_min;
            d_sec = 0 - d_sec;

        d_ndeg = (d_deg+(d_min/60)+(d_sec/(60**2)))

    return round((d_ndeg * math.pi) / 180, 6)

## Transforms degrees from float to string format.
#
# \param deg Degrees in float format
# \return Degrees in string format ("D:M:S:")
def deg_2_degStr(deg):

    neg = False
    if deg < 0.0:
        neg = True
        deg = 0.0 - deg

    ndeg = math.floor(float(deg))
    nmins = (deg - ndeg) * 60
    mins = math.floor(nmins)
    secs = round( (nmins - mins) * 60 )

    if mins == 60:
        ndeg += 1
        mins = 0
    if secs == 60:
        mins += 1
        secs = 0

    if neg:
        ndeg = 0.0 - ndeg

    return "%d:%d:%d" % (ndeg, mins, secs)

## From hours in string format to radians
# h =  H:M:S => H+(M/60)+(S/60^2) hours
# (hours * 15 * pi)/180
#
# \param h Hours in string format ("H:M:SS")
# \return Radians in float format
def hourStr_2_rad(h):
    exp = re.compile('^[0-9]{,3}:[0-9]{,3}:[0-9]{,3}$')
    if(not exp.match(h)):
        logging.debug("Error parametro: %s" % h)
        return None

    h_dic = h.split(':')

    h_h = float(h_dic[0])
    h_m = float(h_dic[1])
    h_s = float(h_dic[2])

    nh = (h_h+(h_m/60)+(h_s/(60**2)))

    return round((nh * 15 * math.pi) / 180, 6)

## Transforms hours from float to string format
#
# \param hours Hours in float format
# \return Hours in string format ("H:M:SS")
def hour_2_hourStr(hours):
    (h, m, s) = hour_min_sec(hours)
    return '%d:%d:%00.1f' % (h, m, s)

## From hours in float format, to a list with number of hours, minutes and seconds
#
# \param hours Hours in float format
# \return List with (hours, minutes, seconds)
def hour_min_sec(hours):
    h = math.floor(hours)

    hours_m = (hours - h)*60.0
    m = math.floor(hours_m)

    s = (hours_m - m)*60.0

    #Evitando los .60..
    if s >= 59.99:
        s = 0
        m += 1
    if m >= 60:
        m = 60-m
        h += 1

    return (h, m, s)

## From degrees in float format, to a list with number of degrees, minutes and seconds
#
# \param degs Degrees in float format
# \return List with (degrees, minutes, seconds)
def grad_min_sec(degs):
    #Evitando operaciones con valores negativos..
    to_neg = False
    if degs < 0:
        degs = math.fabs(degs)
        to_neg = True

    d = math.floor(degs)

    degs_m = (degs - d)*60.0
    m = math.floor(degs_m)

    s = (degs_m - m)*60.0

    #Evitando el .60..
    if s >= 59.99:
        s = 0
        m += 1
    if m >= 60.0:
        m = 60.0-m
        d += 1

    if to_neg:
        d = -d;

    return (d, m, s)

## Transforms the values obtained from "Stellarium Telescope Protocol", to a list with each value in string format
# ("H:M:SS", "D:M:S", "H:M:S")
#
# \param ra Right ascension
# \param dec Declination
# \param mtime Timestamp in microseconds
# \return List with (Right ascension, declination, time) => ("H:M:SS", "D:M:S", "H:M:S")
def eCoords2str(ra, dec, mtime):
    ra_h = ra*12.0/2147483648
    dec_d = dec*90.0/1073741824
    time_s = math.floor(mtime / 1000000)

    return ('%d:%d:%00.0f' % hour_min_sec(ra_h), '%d:%d:%00.0f' % grad_min_sec(dec_d), strftime("%H:%M:%S", localtime(time_s)))

## Transforms coordinates from radians to the "Stellarium Telescope Protocol" format
#
# \param ra Right ascension (float)
# \param dec Declination (float)
# \return List with (Right ascension, Declination) in the "Stellarium Telescope Protocol" format
def rad_2_stellarium_protocol(ra, dec):

    ra_h = rad_2_hour(ra)

    dec_d = (dec * 180) / math.pi

    logging.debug("(hours, degrees): (%f, %f) -> (%s, %s)" % (ra_h, dec_d, hour_2_hourStr(ra_h), deg_2_degStr(dec_d)))

    ra_ret = int(ra_h*(2147483648/12.0))
    dec_ret = int(dec_d*(1073741824/90.0))

    return (ra_ret, dec_ret)
