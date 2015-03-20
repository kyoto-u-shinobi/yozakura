# (C) 2015  Kyoto University Mechatronics Laboratory
# Released under the GNU General Public License, version 3
"""
Control motors.

Motors expect at least one driver, which can be either a serial port for
microcontroller communication, or software PWM. Up to four motors can be
used at any given time.

"""
import logging
from time import sleep

from RPi import GPIO as gpio

from common.exceptions import NoDriversError, TooManyMotorsError, \
    InvalidArgError
from rpi.bitfields import MotorPacket


class Motor(object):
    """
    A motor class.

    The motor driver used here is the Pololu High-Power Motor Driver 18v15.
    [1]_

    After the motor is initialized and registered, at least one driver must be
    added. The drivers can be either a serial port connected to a
    microcontroller for hardware PWM, or software PWM.

    Up to four motors can be registered.

    Parameters
    ----------
    name : str
        The name of the motor.
    fault_1 : int
        GPIO pin for the motor Fault line, FF1.
    fault_2 : int
        GPIO pin for the motor Fault line, FF2.
    reset : int
        GPIO pin for resetting the motor driver.
    start_input : float, optional
        The input at which the motor starts responding. The output will be
        scaled between that value and one. Can range between 0 and 1.

        For instance, if the motors do not turn until the input is at 20%, an
        input of 10% would be scaled up to 28%, and 50% would be scaled up to
        60%.
    max_speed : float, optional
        The maximum speed to use with the motor. Can range between 0 and 1.

    Raises
    ------
    TooManyMotorsError
        Raised when a motor is added after all four motors have already been
        registered.
    InvalidArgError
        Raised when bad inputs are made.

    Attributes
    ----------
    name : str
        The name of the motor.
    motor_id : int
        The motor ID. It is generated automatically.
    pin_fault_1 : int
        The GPIO pin for the motor Fault line, FF1.
    pin_fault_2 : int
        The GPIO pin for the motor Fault line, FF2.
    pin_reset : int
        GPIO pin for resetting the motor driver.
    has_serial : bool
        Whether a serial port is open, and hardware PWM is available.
    has_pwm : bool
        Whether software PWM is available.
    connection : Serial
        The serial port to be used for communication.
    pin_pwm : int
        The GPIO pin for motor PWM line.
    pin_dir : int
        The GPIO pin for motor DIR line.
    start_input : float
        The input at which the motor starts responding.
    max_speed : float
        The maximum speed at which to run the motor.
    motors : list
        Contains all registered motors.

    References
    ----------
    .. [1] Pololu, High-Power Motor Driver 18v15 datasheet.
           https://www.pololu.com/product/755

    """
    gpio.setmode(gpio.BOARD)
    motors = []
    _count = 0

    def __init__(self, name, fault_1, fault_2, reset, start_input=0, max_speed=1):
        if Motor._count == 4:
            raise TooManyMotorsError
        if not 0 <= start_input <= 1:
            raise InvalidArgError("start_input should be between 0 and 1.")
        if not 0 <= max_speed <= 1:
            raise InvalidArgError("max_speed should be between 0 and 1.")

        self.logger = logging.getLogger(name)
        self.logger.debug("Initializing motor")
        self.motor_id = Motor._count
        self.name = name
        self.pin_fault_1 = fault_1
        self.pin_fault_2 = fault_2
        self.pin_reset = reset
        self.start_input = start_input
        self.max_speed = max_speed
        self.has_serial = False
        self.has_pwm = False

        self.logger.debug("Setting up fault interrupt")
        gpio.setup(fault_1, gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.setup(fault_2, gpio.IN, pull_up_down=gpio.PUD_DOWN)
        gpio.add_event_detect(fault_1, gpio.RISING, callback=self._catch_fault)
        gpio.add_event_detect(fault_2, gpio.RISING, callback=self._catch_fault)
        
        self.logger.debug("Resetting motor driver")
        gpio.setup(reset, gpio.OUT)
        self.reset_driver()

        self.logger.debug("Registering motor")
        Motor.motors.append(self)
        self.logger.info("Motor initialized")
        Motor._count += 1

    def enable_pwm(self, pwm, direction, frequency=28000):
        """
        Allow software PWM to control the motor.

        The motor in this case needs to be attached directly to the rpi. If
        serial is also enabled, serial takes priority and software PWM is not
        used.

        Parameters
        ----------
        pwm : int
            The GPIO pin for the motor driver's PWM line.
        direction : int
            The GPIO pin for the motor driver's DIR line.
        frequency : float, optional
            The frequency of the software PWM.

        """
        self.pin_pwm = pwm
        self.pin_dir = direction

        self.logger.debug("Setting up GPIO pins")
        gpio.setup(self.pin_pwm, gpio.OUT)
        gpio.setup(self.pin_dir, gpio.OUT)

        self.logger.debug("Starting PWM drivers")
        gpio.output(self.pin_dir, gpio.LOW)
        self._pwm = gpio.PWM(self.pin_pwm, frequency)
        self._pwm.start(0)

        self.has_pwm = True

    def enable_serial(self, ser):
        """
        Allow the use of a USB serial connection.

        If it is enabled, speed commands will be sent to an external
        microcontroller, such as an mbed, which will output the PWM signal.

        Parameters
        ----------
        ser : Serial
            Communicates with the external hardware.

        """
        self.connection = ser
        self.has_serial = True

    def _catch_fault(self, channel):
        """Threaded callback for fault detection."""
        if gpio.input(self.pin_fault_1) and gpio.input(self.pin_fault_2):
            self.logger.warning("Fault detected! Undervolt.")
        elif gpio.input(self.pin_fault_1):
            self.logger.warning("Fault detected! Overtemp.")
        elif gpio.input(self.pin_fault_2):
            self.logger.warning("Fault detected! Short circuit. " +
                                "Motor driver has been latched.")

    def _scale_speed(self, speed):
        """
        Get the scaled speed according to input parameters.

        Parameters
        ----------
        speed : float
            A value from -1 to 1 indicating the requested speed.

        Returns
        -------
        float
            The scaled speed.

        """
        # Map [start_input:1] to [0:1]
        if speed > 0:
            speed = (speed * (1 - self.start_input)) + self.start_input
        elif speed < 0:
            speed = (speed * (1 - self.start_input)) - self.start_input

        # Map [0:1] to [0:max_speed]
        speed *= self.max_speed
        speed = round(speed, 4)
        return speed

    def _transmit(self, speed):
        """
        Send a byte through a serial connection.

        When connected to the mbed, motor control information is encoded as a
        single byte, with the first two bits encoding the motor's ID, and the
        next bit encoding the sign. The last five bits encode the absolute
        value of the speed to a number between 0 and 31.

        This allows only the relevant information to be transmitted, and also
        lets the mbed perform asynchronously.

        Parameters
        ----------
        speed : float
            A value from -1 to 1 indicating the requested speed.

        """
        packet = MotorPacket()
        packet.motor_id = self.motor_id
        packet.negative = 1 if speed < 0 else 0
        packet.speed = int(abs(self._scale_speed(speed)) * 31)

        self.connection.write(bytes([packet.as_byte]))

    def _pwm_drive(self, speed):
        """
        Drive the motor using software PWM.

        The PWM signal goes to the motor driver's PWM pin. DIR is set depending
        on the speed requested.

        Parameters
        ----------
        speed : float
            A value from -1 to 1 indicating the requested speed of the motor.
            The speed is changed by changing the PWM duty cycle.
        """
        speed = self._scale_speed(speed)

        gpio.output(self.pin_dir, gpio.LOW if speed < 0 else gpio.HIGH)
        self._pwm.ChangeDutyCycle(abs(speed) * 100)

    def drive(self, speed):
        """
        Drive the motor at a given speed.

        The priority goes to the microcontroller if serial is enabled. Software
        PWM is used if serial is not enabled.

        Parameters
        ----------
        speed : float
            A value from -1 to 1 indicating the requested speed.

        Raises
        ------
        NoDriversError
            Neither serial nor PWM are enabled.
        """
        if self.has_serial:
            self._transmit(speed)
        elif self.has_pwm:
            self._pwm_drive(speed)
        else:
            self.logger.error("Cannot drive motor! No serial or PWM enabled.")
            raise NoDriversError(self)
    
    def reset_driver(self):
        """
        Reset the motor driver.
        
        The motor driver is latched upon a short circuit until the reset flag
        is brought to LOW temporarily.
        
        """
        gpio.output(self.pin_reset, gpio.LOW)
        sleep(0.1)
        gpio.output(self.pin_reset, gpio.HIGH)

    def shutdown(self):
        """Shut down and deregister the motor."""
        self.logger.debug("Shutting down motor")
        self.logger.debug("Stopping motor")
        self.drive(0)

        self.logger.debug("Deregistering motor")
        Motor.motors.remove(self)
        self.logger.info("Motor shut down")

    @classmethod
    def shutdown_all(self):
        """A class method to shut down and deregister all motors."""
        logging.info("Shutting down all motors.")
        for motor in Motor.motors:
            motor.shutdown()
        gpio.cleanup()
        logging.info("All motors shut down")

    def __repr__(self):
        return "{} (ID# {})".format(self.name, self.motor_id)

    def __str__(self):
        return self.name