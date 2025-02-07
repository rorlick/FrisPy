import math
from pprint import pprint

import matplotlib.pyplot as plt
from scipy.optimize import minimize

from frispy import Disc
from frispy import Discs

# model = Discs.wraith
model = Discs.xcal
pprint(Discs.turn_from_cm0(model.coefficients["PTy0"]))
model = Discs.from_flight_numbers({"speed": 12, "glide": 5, "turn": -1})
mph_to_mps = 0.44704
v = 55 * mph_to_mps
# rot = -v / model.diameter
rot = -v / model.diameter
nose_up = -3
hyzer = 0
uphill = 5 - nose_up

disc = Disc(model, {"vx": math.cos(uphill * math.pi / 180) * v, "dgamma": rot, "vz": math.sin(uphill * math.pi / 180) * v, "nose_up": nose_up, "hyzer": hyzer})

result = disc.compute_trajectory(15.0, **{"max_step": .2})
times = result.times
t, x, y, z, anhyzer = result.times, result.x, result.y, result.z, result.phi

plt.plot(x, y)
plt.plot(x, z)
plt.plot(x, [-a * 180 / math.pi for a in anhyzer])

pprint(x[-1] * 3.28084) # feet
plt.show()

