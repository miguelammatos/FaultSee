import math

class ExperimentStep():
    # self.time
    # self.operation
    def __init__(self, fault_time):
        self.time = fault_time

    def __str__(self):
        return "Step: Operation: " + self.operation + " Time: " + str(self.time) + " sec"

    def get_id(self):
        return self.id

    def set_id(self, identifier):
        self.id = identifier


class SimpleStep(ExperimentStep):
    def calculate_service_amounts(self, current_replicas):
        # nothing to do
        pass

    # returns the amounts of ids this fault consumes
    @staticmethod
    def consumes_ids():
        return 1


class BeginningStep(SimpleStep):
    operation = "beginning"


class EndStep(SimpleStep):
    operation = "end"


class MarkStep(SimpleStep):
    operation = "mark"


class ServiceChangeStep(ExperimentStep):
    # self.number_replicas
    # self.service_name
    def __init__(self, fault_time, service_name, step_details):
        super().__init__(fault_time)
        self.service_name = service_name
        self.parse_step(step_details)

    def __str__(self):
        return super().__str__() + \
            " service: " + str(self.service_name) + \
            " number_replicas: " + str(self.number_replicas)

    def save_target(self, target_details):
        self.target_details = target_details

    def parse_step(self, details):
        self.save_target(details)


class StartReplicasStep(ServiceChangeStep):
    operation = "start"

    def calculate_service_amounts(self, current_replicas):
        before_amount = current_replicas[self.service_name]
        details = self.target_details
        try:

            amount = details.get('amount', None)
            percentage = details.get('percentage', None)
            if amount is not None:
                self.number_replicas = int(amount)
            elif percentage is not None:
                    percentage = int(percentage)
                    self.number_replicas = int(math.ceil(percentage * before_amount / 100.0))
            else:
                raise ValueError("Could not pre process Start Moment")

            after_amount = self.number_replicas + before_amount
            current_replicas[self.service_name] = after_amount
        except:
            raise ValueError("Could not pre process Start Moment")

    # returns the amounts of ids this fault consumes
    @staticmethod
    def consumes_ids():
        return 1


class StopReplicasStep(ServiceChangeStep):
    # self.signal
    operation = "stop"

    def calculate_service_amounts(self, current_replicas):
        before_amount = current_replicas[self.service_name]
        details = self.target_details
        try:
            amount = details.get('amount', None)
            percentage = details.get('percentage', None)
            specific = details.get('specific', None)
            if amount is not None:
                self.number_replicas = int(amount)
            elif percentage is not None:
                percentage = int(percentage)
                self.number_replicas = int(math.ceil(percentage * before_amount / 100.0))
            elif specific is not None:
                self.number_replicas = len(specific)
            else:
                raise ValueError("Could not pre process Stop Moment")

            if self.number_replicas > before_amount:
                raise ValueError("Stop Moment: Trying to stop more containers than there are alive")
            after_amount = before_amount - self.number_replicas
            current_replicas[self.service_name] = after_amount
        except:
            raise ValueError("Could not pre process Stop Moment")

    # returns the amounts of ids this fault consumes
    def consumes_ids(self):
        return self.number_replicas


class FaultStep(ServiceChangeStep):
    # makes sure all elements are strings
    def list_to_strings(self, list):
        return [str(x) for x in list]

    def parse_step(self, details):
        self.save_target(details.get("target", ""))
        self.parse_details(details)

    def parse_target_details(self, details, before_amount):
        amount = details.get('amount', None)
        percentage = details.get('percentage', None)
        specific = details.get('specific', None)
        if amount is not None:
            self.number_replicas = int(amount)
        elif percentage is not None:
            percentage = int(percentage)
            self.number_replicas = int(math.ceil(percentage * before_amount / 100.0))
        elif specific is not None:
            self.number_replicas = len(specific)
        else:
            raise ValueError("Could not pre process Stop Moment")
        return self.number_replicas


class CPUFault(FaultStep):
    operation = "cpu"

    def parse_details(self, details):
        cpu_details = details.get("cpu", None)
        if cpu_details is None:
            raise ValueError("CPU Fault Type must have cpu section")
        # will take care of the "kill_container" section
        self.duration = cpu_details.get("duration", None)

    def calculate_service_amounts(self, current_replicas):
        self.parse_target_details(self.target_details, current_replicas[self.service_name])

    # returns the amounts of ids this fault consumes
    def consumes_ids(self):
        return self.number_replicas

class KillFault(FaultStep):
    operation = "kill"

    def parse_details(self, details):
        # nothing to parse
        pass

    def calculate_service_amounts(self, current_replicas):
        before_amount = current_replicas[self.service_name]
        self.parse_target_details(self.target_details, before_amount)
        after_amount = before_amount - self.number_replicas
        current_replicas[self.service_name] = after_amount

    # returns the amounts of ids this fault consumes
    def consumes_ids(self):
        return self.number_replicas

class MayKillContainerStep(FaultStep):
    # self.kills_container

    def parse_kills_container(self, details):
        kills_container_string = details.get("kills_container", None)
        if kills_container_string is None:
            raise ValueError("kills_container must be set in custom and signal faults")
        if not isinstance(kills_container_string, str):
            raise ValueError("Could not interpret kills_container as string value: ", kills_container_string)

        upper_str = kills_container_string.upper()
        if upper_str == "YES":
            self.kills_container = True
        elif upper_str == "NO":
            self.kills_container = False
        else:
            raise ValueError("kills_container must be YES or NO")

    def calculate_service_amounts(self, current_replicas):
        before_amount = current_replicas[self.service_name]
        self.parse_target_details(self.target_details, before_amount)
        if self.kills_container:
            after_amount = before_amount - self.number_replicas
            current_replicas[self.service_name] = after_amount
        else:
            # after = before
            pass

DEFAULT_FILE_FOLDER = "/usr/lib/faultsee/"
DEFAULT_EXECUTABLE = "/bin/sh"
DEFAULT_EXECUTABLE_ARGUMENTS = []
DEFAULT_FAULT_SCRIPT_ARGUMENTS = []


class CustomFaultStep(MayKillContainerStep):
    operation = "custom"

    # self.fault_file_name
    # self.fault_file_folder
    # self.executable
    # self.executable_arguments
    # self.fault_script_arguments
    # self.kills_container
    def parse_details(self, details):
        custom_details = details.get("custom", None)
        if custom_details is None:
            raise ValueError("Custom Fault Type must have custom section")
        # will take care of the "kill_container" section
        super().parse_kills_container(custom_details)
        self.fault_file_name = custom_details.get("fault_file_name", None)
        if self.fault_file_name is None:
            raise ValueError("fault_file_name must be set in custom faults")
        self.fault_file_folder = custom_details.get(
            "fault_file_folder", DEFAULT_FILE_FOLDER)
        self.executable = custom_details.get("executable", DEFAULT_EXECUTABLE)
        self.executable_arguments = self.list_to_strings(custom_details.get(
            "executable_arguments", DEFAULT_EXECUTABLE_ARGUMENTS))
        self.fault_script_arguments = self.list_to_strings(custom_details.get(
            "fault_script_arguments", DEFAULT_FAULT_SCRIPT_ARGUMENTS))

    # returns the amounts of ids this fault consumes
    def consumes_ids(self):
        return self.number_replicas

class SignalStep(MayKillContainerStep):
    operation = "signal"

    # self.signal
    # self.kills_container
    def parse_details(self, details):
        # will take care of the "kill_container" section
        signal_details = details.get("signal", None)
        if signal_details is None:
            raise ValueError("Signal Fault Type must have signal section")

        super().parse_kills_container(signal_details)

        self.signal = signal_details.get("signal", None)
        if self.signal is None:
            raise ValueError("Signal Fault must specify which signal to inject")

    # returns the amounts of ids this fault consumes
    def consumes_ids(self):
        return self.number_replicas