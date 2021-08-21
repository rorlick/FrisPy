from typing import Dict, Union

import numpy as np

from frispy.environment import Environment
from frispy.model import Model
from frispy.trajectory import Trajectory


class EOM:
    """
    ``EOM`` is short for "equations of motion" is used to run the ODE solver
    from `scipy`. It takes in a model for the disc, the trajectory object,
    the environment, and implements the functions for calculating forces
    and torques.
    """

    def __init__(
        self,
        environment: Environment = Environment(),
        model: Model = Model(),
        trajectory: Trajectory = Trajectory(),
    ):
        self._environment = environment
        self._model = model
        self._trajectory = trajectory

    @property
    def environment(self) -> Environment:
        return self._environment

    @property
    def model(self) -> Model:
        return self._model

    @property
    def trajectory(self) -> Trajectory:
        return self._trajectory

    def compute_forces(
        self,
        phi: float,
        theta: float,
        velocity: np.ndarray,
        ang_velocity: np.ndarray,
    ) -> Dict[str, Union[float, np.ndarray, Dict[str, np.ndarray]]]:
        """
        Compute the lift, drag, and gravitational forces on the disc.

        Args:
        TODO
        """
        res = self.trajectory.calculate_intermediate_quantities(
            phi, theta, velocity, ang_velocity
        )
        aoa = res["angle_of_attack"]
        vhat = velocity / np.linalg.norm(velocity)
        force_amplitude = (
            0.5
            * self.environment.air_density
            * (velocity @ velocity)
            * self.model.area
        )
        # Compute the lift and drag forces
        res["F_lift"] = (
            self.model.C_lift(aoa)
            * force_amplitude
            * np.cross(vhat, res["unit_vectors"]["yhat"])
        )
        res["F_drag"] = self.model.C_drag(aoa) * force_amplitude * (-vhat)
        # Compute gravitational force
        res["F_grav"] = (
            self.model.mass
            * self.environment.g
            * self.environment.grav_vector
        )
        res["F_total"] = res["F_lift"] + res["F_drag"] + res["F_grav"]
        res["Acc"] = res["F_total"] / self.model.mass
        return res

    def compute_torques(
        self,
        velocity: np.ndarray,
        ang_velocity: np.ndarray,
        res: Dict[str, Union[float, np.ndarray, Dict[str, np.ndarray]]],
    ) -> Dict[str, Union[float, np.ndarray, Dict[str, np.ndarray]]]:

        aoa = res["angle_of_attack"]
        res["torque_amplitude"] = (
            0.5
            * self.environment.air_density
            * (velocity @ velocity)
            * self.model.diameter
            * self.model.area
        )

        i_xx = self.model.I_xx
        i_zz = self.model.I_zz
        torque = res["torque_amplitude"]
        wx, wy, wz = ang_velocity

        # Handle pitch and roll as precession around Z and not a change to angular velocity.
        #pitch_up = self.model.C_x(wz) * res["torque_amplitude"] * res["unit_vectors"]["yhat"]
        #delta_x = (res["rotation_matrix"] @ pitch_up)
        roll = -self.model.C_y(aoa) * res["torque_amplitude"]
        #delta_y = (res["rotation_matrix"] @ roll)

        # Dampen angular velocity
        dampening = self.model.dampening_factor
        dampening_z = self.model.dampening_z
        acc = np.array([wx * dampening / i_xx, wy * dampening / i_xx, wz * dampening_z / i_zz]) * torque

        # Handle wobble by precession of angular velocity
        delta_moment = self.model.I_zz - self.model.I_xx
        acc += delta_moment / i_xx * wz * np.array([-wy, wx, 0])

        res["precession"] = np.array([roll / (i_zz * wz), 0, 0])
        res["T"] = acc
        return res

    def compute_derivatives(
        self, time: float, coordinates: np.ndarray
    ) -> np.ndarray:
        """
        Right hand side of the ordinary differential equations. This is
        supplied to :meth:`scipy.integrate.solve_ivp`. See `this page
        <https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html#scipy.integrate.solve_ivp>`_
        for more information about its `fun` argument.

        .. todo::

           Implement the disc hitting the ground as a (Callable) scipy
           event object.

        Args:
          time (float): instantanious time of the system
          coordinates (np.ndarray): kinematic variables of the disc

        Returns:
          derivatives of all coordinates
        """
        x, y, z, vx, vy, vz, phi, theta, gamma, dphi, dtheta, dgamma = coordinates
        # If the disk hit the ground, then stop calculations
        if z <= 0:
            return coordinates * 0

        velocity = np.array([vx, vy, vz])
        ang_velocity = np.array([dphi, dtheta, dgamma])
        result = self.compute_forces(phi, theta, velocity, ang_velocity)
        result = self.compute_torques(velocity, ang_velocity, result)
        derivatives = np.array(
            [
                vx,
                vy,
                vz,
                result["Acc"][0],  # x component of acceleration
                result["Acc"][1],  # y component of acceleration
                result["Acc"][2],  # z component of acceleration
                dphi + result["precession"][0],
                dtheta + result["precession"][1],
                dgamma,
                result["T"][0],  # phi component of ang. acc.
                result["T"][1],  # theta component of ang. acc.
                result["T"][2],  # gamma component of ang. acc.
            ]
        )
        return derivatives
