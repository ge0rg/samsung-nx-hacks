#!/bin/bash
#
# "Press" the shutter button for a configurable time
# (useful for Manual/Bulb exposure)

st key push s1
st key push s2
[ "$1" ] && sleep $1
st key release s2
st key release s1
