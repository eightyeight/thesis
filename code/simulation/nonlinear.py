from scipy.integrate import ode
from numpy import hstack, array

class Run(object):
    def __init__(self, xdot, x0, dt, tf, u = None, report = None):
        self.model = xdot
        self.x0 = x0
        self.tf = tf
        self.dt = dt
        self.u = u
        self.report = report

    def result(self):
        t0 = 0
        sim = ode(self.model) \
                .set_integrator('dop853',
                    #method = 'bdf',
                    #with_jacobian = False,
                    nsteps = 2000,
                    max_step = self.dt,
                ).set_initial_value(self.x0, t0)
        results = []
        inputs = []
        while sim.successful() and sim.t < self.tf:
            u = self.u(sim.t, sim.y) if self.u else array([0])
            sim.set_f_params(u)
            sim.integrate(sim.t + self.dt)
            results.append(sim.y)
            inputs.append(u)
            if self.report:
                self.report(sim.t, sim.y, u)
        return (array(inputs).T, array(results).T)
