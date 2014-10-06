print 'Loading modules'
import matplotlib
matplotlib.use('agg')
from matplotlib.pyplot import * # Grab MATLAB plotting functions

import warnings
warnings.simplefilter('ignore', np.ComplexWarning)

from utils.interval import Interval
from numpy import array, linspace
from operator import add
from datetime import datetime
from math import pi

import cvxopt as cvx
import cvxpy

from models import tank2 as tank
import models.halvgaard
from controllers.thermostat import thermostat
import controllers.mpc
import prediction.ambient
import prediction.load
from prediction.load import spike, Lpm, minutes
import prediction.collector
import simulation.nonlinear as simulation

startTime = datetime(2014, 9, 9, 00, 00, 00)

ambient = prediction.ambient.make(start = startTime)
insolation = lambda *args: 0

# Let's go with a 4-person household. Using information from YVW, we'll make up
# some schedules. Significant events: weekend showers are more spread out. One
# adult stays home on Wednesday. Evening showers on a couple of days.
# http://www.yvw.com.au/Home/Inyourhome/Understandingyourwateruse/index.htm
loadProfile = [
    # Monday
    [
        # Morning showers
        spike(7,   minutes(8),  Lpm(5)),
        spike(7.5, minutes(9),  Lpm(6)),
        spike(7.9, minutes(7),  Lpm(4)),
        spike(8.1, minutes(10), Lpm(5)),
        # Dishwasher
        spike(22.5, minutes(70), Lpm(0.3)),
    ],
    # Tuesday
    [
        # Morning showers
        spike(7.5, minutes(7), Lpm(4)),
        spike(7.2, minutes(8), Lpm(4)),
        spike(7.9, minutes(6), Lpm(5)),
        spike(8.5, minutes(6), Lpm(6)),
    ],
    # Wednesday
    [
        # Morning showers
        spike(6.8, minutes(8), Lpm(5)),
        spike(7.1, minutes(5), Lpm(4)),
        spike(7.8, minutes(9), Lpm(6)),
        spike(8.2, minutes(6), Lpm(5)),
        # Dishwasher
        spike(22.4, minutes(70), Lpm(0.3)),
    ],
    # Thursday
    [
        # Morning showers
        spike(6.5, minutes(8),  Lpm(4)),
        spike(7,   minutes(8),  Lpm(5)),
        spike(7.2, minutes(10), Lpm(6)),
        spike(7.6, minutes(8),  Lpm(7)),
        # Dishwasher
        spike(22.5, minutes(70), Lpm(0.3)),
    ],
    # Friday
    [
        # Morning showers
        spike(7,   minutes(8), Lpm(6)),
        spike(7.5, minutes(7), Lpm(5)),
        spike(7.9, minutes(5), Lpm(5)),
        spike(8.1, minutes(9), Lpm(7)),
    ],
    # Saturday
    [
        # Morning showers
        spike(8.2,   minutes(16), Lpm(6)),
        spike(9.1, minutes(7),  Lpm(5)),
        spike(9.5, minutes(11), Lpm(5)),
        spike(10.5, minutes(12), Lpm(7)),
        # Dishwasher
        spike(21.7, minutes(70), Lpm(0.3)),
    ],
    # Sunday
    [
        # 'Morning' showers
        spike(8.6,  minutes(8),  Lpm(6)),
        spike(9.8,  minutes(13), Lpm(5)),
        spike(10.5, minutes(19),  Lpm(5)),
        spike(13.2, minutes(14), Lpm(7)),
        # Dishwasher
        spike(21, minutes(70), Lpm(0.3)),
    ]
]

load = prediction.load.make(
    start = startTime,
    mainsTemp = ambient,
    profile = loadProfile + loadProfile # Two weeks, yeah
)

N = 20
NC = 10
NX = 10
r = 0.4
h = 1.3
P = 2000
auxOutlet = 0
tankModel = tank.model(
    h = h, r = r, NT = N,
    NC = NC, NX = NX,
    vC = 1, vX = 0.1,
    P = P,
    auxOutlet = auxOutlet,
    getAmbient = ambient,
    getLoad = load,
    getInsolation = insolation,
)

H = 12
C = 2400
UA = 0.5 * (2 * pi * r * h + 2 * pi * r * r)
"""
Q = cvx.matrix(kron(eye(H), diag([0]*(N-1) + [1] + [0]*N)))
predictive = mpc.controller(
    period = 3600,
    law = mpc.linear(
        horizon = H,
        system = halvgaard.model(C, UA),
        objective = lambda X, y: cvxpy.norm(y),
        constraints = lambda X, y, u: [],
        disturbances = lambda t, x: array([0])
    )
)
"""

controller = thermostat(
    measure = 0,
    on  = array([1]),
    off = array([0]),
    setpoint = 55,
    deadband = 5
)

dt = 30
tf = 60 * 60 * 24 * 14 - dt
x0 = array([24] * (N+NC+NX)).T
s = simulation.Run(
    xdot = tankModel,
    u = controller,
    x0 = x0,
    dt = dt,
    tf = tf
)

print 'Beginning simulation'

(us_, xs_) = s.result()

def viewHours(hourFrom, hourTo, size=(15, 20), dpi=80, fname = 'sim.png'):
    plotFrom = int(hourFrom * 60 * 60 / dt)
    plotTo = int(hourTo * 60 * 60 / dt)

    us = us_[:, plotFrom:plotTo]
    xs = xs_[:, plotFrom:plotTo]
    ts = linspace(plotFrom*dt, plotTo*dt, num = len(xs[0,:]))
    th = map(lambda t: t / (60.0*60), ts)

    figure(figsize=size, dpi=dpi)

    a1 = subplot(411)
    ylabel('Tank temperatures')
    hs = [plot(th, xs[i,:])[0] for i in range(N)]
    ls = [str(i) for i in range(N)]
    axis(map(add, [0, 0, -1, 1], axis()))

    a2 = subplot(412, sharex=a1)
    ylabel('Control effort')
    for i in range(len(us[:,0])):
        step(th, us[i,:])
    axis(map(add, [0, 0, -0.002, 0.01], axis()))

    a3 = subplot(413, sharex=a1)
    ylabel('Load flow')
    step(th, map(lambda t: float(load(t*60*60)[0]), th[f:t]))
    axis(map(add, [0, 0, -0.01, 0.01], axis()))

    """
    a3 = subplot(413, sharex=a1)
    ylabel('Collector temperatures')
    hs = [plot(th, xs[i,:])[0] for i in range(N, N+NC)]
    axis(map(add, [0, 0, -1, 1], axis()))
    """

    a4 = subplot(414, sharex=a1)
    ylabel('Auxiliary temperatures')
    hs = [plot(th, xs[i,:])[0] for i in range(N+NC, N+NC+NX)]
    axis(map(add, [0, 0, -1, 1], axis()))

    """
    a4 = subplot(414, sharex=a1)
    ylabel('Collector temperature')
    step(th, map(lambda t: float(collector(t*60*60)[1]), th[f:t]))
    axis(map(add, [0, 0, -1, 1], axis()))
    """

    xlabel('Simulation time (h)')

    savefig(fname)

print 'Completed successfully'
