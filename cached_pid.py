import time
from simple_pid import PID as SIMPLE_PID



class PID:
    def __init__(self,
        Kp=1.0, Ki=0.0, Kd=0.0,
        setpoint=0, dt=1.0,
        output_limits=(None, None), auto_mode=True,
        proportional_on_measurement=False, error_map=None
    ):
        self._pid = SIMPLE_PID(
            Kp, Ki, Kd,
            setpoint, None,
            output_limits, auto_mode,
            proportional_on_measurement, error_map
        )
        self.__dt = dt
        self.__last_input = None
        self.__last_output = None
        self.__last_calculation  = None

    def __call__(self, input_):
        if (self.__last_input is not None
                and self.__last_output is not None
                and self.__last_calculation is not None
                and self.__last_input == input_
                and time.time_ns() < self.__last_calculation + 187500000
        ):
            return self.__last_output

        self.__last_input = input_
        self.__last_output = self._pid(input_, self.__dt)
        self.__last_calculation = time.time_ns()
        return self.__last_output
