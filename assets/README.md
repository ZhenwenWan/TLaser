# Lasers device geometry

`lasers_geometry.json` is the original 15-part `telecom_laser_geometry.json`
from https://zhenwenwan.github.io/Pages/Projects/Lasers/index.html
(model version `task-1.1`). The part dimensions, materials, roles, colors, and
reference visualization scales are preserved.

The viewer adapts cavity length to the TLaser device configuration, moving the
facet coatings with the cavity ends while retaining coating thickness. Other
dimensions retain the reference values. Reduced-model effective active width
and thickness are not substituted for physical ridge or MQW dimensions.

Axes follow Lasers: x is cavity length, y is lateral width, z is layer height.
The default vertical display scale is 12×. True proportions removes that
display magnification. Layer separation is an inspection displacement only;
hover dimensions remain physical part dimensions.
