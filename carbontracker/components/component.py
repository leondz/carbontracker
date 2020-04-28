import numpy as np

from carbontracker.components.gpu import nvidia
from carbontracker.components.cpu import intel

class GPUError(Exception):
    pass

class CPUError(Exception):
    pass

class ComponentNameError(Exception):
    pass

components = [
    {
        "name": "gpu",
        "error": GPUError("No GPU(s) available."),
        "handlers": [nvidia.NvidiaGPU()]
    },
    {
        "name": "cpu",
        "error": CPUError("No CPU(s) available."),
        "handlers": [intel.IntelCPU()]
    }
]

def component_names():
    return [comp["name"] for comp in components]

def error_by_name(name):
    for comp in components:
        if comp["name"] == name:
            return comp["error"]

def handlers_by_name(name):
    for comp in components:
        if comp["name"] == name:
            return comp["handlers"]

class Component:
    def __init__(self, name):
        self.name = name
        if name not in component_names():
            raise ComponentNameError(f"No component found with name '{self.name}'.")
        self._handler = self._determine_handler()
        self.power_usages = []
        self.cur_epoch = -1 # sentry
    
    @property
    def handler(self):
        if self._handler is None:
            raise error_by_name(self.name)
        return self._handler
    
    def _determine_handler(self):
        handlers = handlers_by_name(self.name)
        for handler in handlers:
            if handler.available():
                return handler
        return None
    
    def devices(self):
        return self.handler.devices()
    
    def available(self):
        return self._handler is not None
    
    def collect_power_usage(self, epoch):
        if epoch < 1:
            return

        if epoch != self.cur_epoch:
            self.cur_epoch = epoch
            self.power_usages.append([])

        self.power_usages[-1].append(self.handler.power_usage())
    
    def energy_usage(self, epoch_times):
        """Returns energy (kWh) used by component per epoch."""
        energy_usages = []
        # We have to compute each epoch in a for loop since numpy cannot
        # handle lists of uneven length.
        for power, time in zip(self.power_usages, epoch_times):
            avg_power_usage = np.mean(power, axis=0)
            energy_usage = np.multiply(avg_power_usage, time).sum()
            # Convert from J to kWh.
            energy_usage /= 3600000
            energy_usages.append(energy_usage)
        return energy_usages

    def init(self):
        self.handler.init()
    
    def shutdown(self):
        self.handler.shutdown()        

def create_components(comp_str):
    comp_str = comp_str.strip().replace(" ", "")
    if comp_str == "all":
        return [Component(name=comp_name) for comp_name in component_names()]
    else:
        return [Component(name=comp_name) for comp_name in comp_str.split(",")]