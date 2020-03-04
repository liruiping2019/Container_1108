from MonitorClient.plugins.linux import cpu_3,host_alive_3,memory_3,load

def LinuxCpuPlugin():
    return cpu_3.monitor()

def host_alive_check():
    return host_alive_3.monitor()

def LinuxMemoryPlugin():
    return memory_3.monitor()

def LinuxLoadPlugin():
    return load.monitor()