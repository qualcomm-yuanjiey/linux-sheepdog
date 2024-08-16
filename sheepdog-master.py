import serial, os, sys, logging, time, glob
import paramiko, getpass, TACDev
import subprocess, datetime, threading
import serial.tools.list_ports
import configparser, argparse
import logging.config, fs, platform
from winmagic import magic
from pydevicetree import Devicetree
from pathlib import Path


def exit_with_msg(msg, code=0):
    logging.error(msg)
    exit(code)


def sheepdog_abspath(path, base, style=""):
    """
    Judge if input path is a relative path. If so, convert it into a
    absolute path based on 'base'
    """
    if os.path.isabs(path):
        return path

    path = os.path.join(base, path)
    path = os.path.normpath(path)

    if len(style) != 0 and style != os_type:
        if style == "Linux":
            path = Path(path).as_posix()

    return path


def exec_cmd(cmd, local=True):
    """
    Execute a shell command and return the output
    """
    logging.debug(f"cmd={cmd}\r\nlocal={local}")

    if local:
        ret = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        retcode = ret.returncode
        result = ret.stdout
    else:
        cmd += "\n"

        serial_port.reset_input_buffer()
        serial_port.reset_output_buffer()

        serial_port.write(cmd.encode())
        serial_port.flush()
        time.sleep(0.5)  # wait for command execution
        lines = read_serial().split("\r\n")[1:-1]
        result = "".join(lines)

        serial_port.write("echo $?\n".encode())
        serial_port.flush()
        time.sleep(0.1)
        lines = read_serial().split("\r\n")[1:-1]
        retcode = int("".join(lines))

    if retcode != 0:
        raise Exception(f"Error executing command {cmd}\n{result}", retcode)

    logging.debug("exec_cmd finished")
    return (result, retcode)


def log_init():
    log_file = config.get("LOG", "file", fallback=f".\\linux-sheepdog-master.log")
    log_file = sheepdog_abspath(log_file, workspace)
    log_level = config["LOG"]["level"]

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=[
            logging.FileHandler(filename=log_file, mode="a"),
            logging.StreamHandler(),
        ],
    )


class test_device:
    def __init__(self, support_adb=True):
        device_config = config["DEVICE"]

        self.serial_num = device_config["serial_num"]
        self.com_port = device_config["com_port"]
        self.baudrate = int(device_config["baudrate"])
        self.__support_adb = support_adb

        if not support_adb:
            self.TAC_initialize()

    def __del__(self):
        if not self.__support_adb:
            self.__dev.Close()

    def TAC_initialize(self):
        logging.info(f"TAC version: {TACDev.TACVersion()}")
        logging.info(f"Alpaca version: {TACDev.AlpacaVersion()}")
        logging.info(f"Device count: {TACDev.GetDeviceCount()}")

        dev_index = 0
        dev_count = TACDev.GetDeviceCount()

        if dev_count == 0:
            exit_with_msg("no device attached", 1)

        for count in range(0, dev_count):
            dev = TACDev.GetDevice(count)
            assert dev is not None

            desc = dev.Description()
            serial_port = dev.SerialNumber()
            port_name = dev.PortName()

            logging.info(f"TACDevice{count}:\n{desc}\n{serial_port}:{port_name}")

        if dev_count > 1:
            logging.info(f"More than one device exist, select one.")
            dev_index = int(input("input device num:"))

        self.__dev = TACDev.GetDevice(dev_index)
        assert self.__dev is not None

    def flash(self) -> bool:
        images = config["IMAGE"]["names"].split()

        for image in images:
            name_body = image.split(".")[0]
            cmdline = f"fastboot -s {self.serial_num} flash {name_body} {local_image_path}\\{image}"
            try:
                exec_cmd(cmdline)
                logging.info(cmdline)
            except Exception as e:
                exit_with_msg(str(e.args[0]), e.args[1])

        logging.info("Flash succeed")
        return True

    def to_bootloader(self):
        if not self.__support_adb:
            self.__dev.Open()
            self.__dev.BootToFastBootButton()
        else:
            try:
                exec_cmd(f"adb -s {self.serial_num} reboot bootloader")
            except Exception as e:
                exit_with_msg(str(e.args[0]), e.args[1])

        for count in range(10):
            if len(exec_cmd("fastboot devices -l")[0]) != 0:
                logging.info("boot to bootloader succeed")
                return True
            time.sleep(2)

        exit_with_msg("boot to bootloader failed")

    def reboot(self):
        try:
            exec_cmd(f"fastboot -s {self.serial_num} reboot")
        except Exception as e:
            exit_with_msg(str(e.args[0]), e.args[1])


def read_serial():
    output = ""
    data = b""
    while serial_port.in_waiting != 0:
        data += serial_port.read(serial_port.in_waiting)
        time.sleep(0.2)

    output = data.decode()
    logging.debug(output)
    return output


def idle_test() -> bool:
    cmds = [
        "echo 0 > /sys/kernel/tracing/tracing_on",
        'echo "" > /sys/kernel/tracing/trace',
        'echo "power:cpu_idle" > /sys/kernel/tracing/set_event',
        "echo 1 > /sys/kernel/tracing/tracing_on",
        'grep -q "state=0" /sys/kernel/tracing/trace',
    ]
    for cmd in cmds[0:-1]:
        output = exec_cmd(cmd, local=False)
        if output[1] != 0:
            return False

    output = exec_cmd(cmds[-1], local=False)
    if "state=0" in output[0]:
        return True
    else:
        return False


def uart_test() -> bool:
    essential_paths = ["boot", "dev", "bin"]
    cmd = "ls /"
    output = exec_cmd(cmd, local=False)
    for path in essential_paths:
        if path not in output[0]:
            logging.info(f"essential directory {path} not exist")
            return False
    return True


def pinctl_test() -> bool:
    cmd = 'grep -q "Pinctrl maps:" /sys/kernel/debug/pinctrl/pinctrl-maps'
    try:
        output = exec_cmd(cmd, local=False)
    except Exception as e:
        return False

    return True


def smp_test() -> bool:
    cmd = "cat /sys/devices/system/cpu/online"

    cpu_nodes = filter(
        lambda node: node.get_field("device_type") == "cpu",
        dts_tree.get_by_path("/cpus").child_nodes(),
    )
    cpu_num = len(list(cpu_nodes))

    output = exec_cmd(cmd, local=False)
    if f"0-{cpu_num-1}" in output[0]:
        return True
    else:
        return False


def wait_bootup() -> bool:

    for count in range(10):
        try:
            exec_cmd("systemctl is-active systemd-logind", local=False)
            exec_cmd("echo 0 > /proc/sys/kernel/printk", local=False)
            logging.info("device has boot up")
            return True
        except:
            time.sleep(2)

    logging.error("device boot timeout")
    exit(1)


test_cases = [idle_test, uart_test, pinctl_test, smp_test]


def run_test_cases():
    for test_func in test_cases:
        logging.info(test_func.__name__)
        try:
            test_func()
            logging.info("\tpass")
        except:
            logging.info("\tfail")


def open_serial():
    global serial_port

    serial_port = serial.Serial(dev.com_port, baudrate=dev.baudrate)
    serial_port.timeout = 2
    serial_port.write_timeout = 2
    serial_port.inter_byte_timeout = 2
    serial_port.bytesize = serial.EIGHTBITS
    serial_port.stopbits = serial.STOPBITS_ONE
    serial_port.parity = serial.PARITY_NONE
    serial_port.xonxoff = True


def close_serial():
    serial_port.close()


def create_sessions():
    global ssh, sftp

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    addr = config["REMOTE"]["addr"]
    username = config["REMOTE"]["username"]

    try:
        ssh.connect(hostname=addr, username=username)
    except:
        passwd = getpass.getpass()
        ssh.connect(hostname=addr, username=username, password=passwd)

    sftp = ssh.open_sftp()


def parse_config():
    global config, local_image_path, remote_image_path, remote_workspace

    config_file = args.config
    if config_file is None:
        config_file = os.path.dirname(__file__) + "\\template-master.ini"

    config = configparser.ConfigParser()
    config.read(config_file)

    local_image_path = sheepdog_abspath(config["IMAGE"]["local_path"], workspace)

    remote_workspace = config["REMOTE"]["workspace"]
    # attention! It is a unix style path
    remote_image_path = sheepdog_abspath(
        config["IMAGE"]["remote_path"], remote_workspace, style="Linux"
    )


def parse_options():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, help="the full path of config file")
    parser.add_argument("--local-images", action="store_true", help="use local images")
    parser.add_argument("--skip_sync", action="store_true", help="to skip sync and rebase to newest kernel repo")
    args = parser.parse_args()


def env_init():
    global workspace, os_type
    workspace = os.getcwd()

    if "Linux" in platform.platform():
        os_type = "Linux"
    elif "Windows" in platform.platform():
        os_type = "Windows"


def initialize():
    env_init()
    parse_options()
    parse_config()
    log_init()
    logging.info("initialize finished")


def build():
    remote_config = config["REMOTE"]

    slave_script = sheepdog_abspath(
        remote_config["slave_script"], remote_workspace, style="Linux"
    )
    slave_config = sheepdog_abspath(
        remote_config["slave_config"], remote_workspace, style="Linux"
    )
    local_repo = sheepdog_abspath(
        remote_config["local_repo"], remote_workspace, style="Linux"
    )

    # attention! They're unix style paths.
    slave_script = Path(slave_script).as_posix()
    slave_config = Path(slave_config).as_posix()
    local_repo = Path(local_repo).as_posix()

    cmdline = slave_script
    if len(slave_config) != 0:
        cmdline = cmdline + " --config " + slave_config
    if len(local_repo) != 0:
        cmdline = cmdline + " --local " + local_repo
    if args.skip_sync:
        cmdline = cmdline + " --skip_sync"  

    cmdline = f"cd {remote_workspace} && {cmdline}"
    logging.info(f"will exe: {cmdline}")
    

    stdin, stdout, stderr = ssh.exec_command(command=cmdline)
    stdout.channel.recv_exit_status()


def close_sessions():
    if "sftp" in globals():
        sftp.close()
    if "ssh" in globals():
        ssh.close()


def cleanup():
    close_serial()
    close_sessions()


def trans_images():
    images = config["IMAGE"]["names"].split()

    for image in images:
        remote_file = f"{remote_image_path}/{image}"
        local_file = f"{local_image_path}\\{image}"
        sftp.get(remotepath=remote_file, localpath=local_file)


def flash_images():
    global dev

    dev = test_device(support_adb=False)
    dev.to_bootloader()
    dev.flash()
    dev.reboot()


def read_test():
    serial_port = serial.Serial("COM10", baudrate=115200)
    while True:
        serial_str = serial_port.readline().decode()
        print(serial_str)


def extract_efibin(image_path):
    logging.info("Extract dts from efibin")

    vfat_fs = fs.open_fs(f"fat://{Path(image_path).as_posix()}")
    dest_path = "/DTB"  # vfat default uppercase

    for dtb_file in vfat_fs.listdir(dest_path):
        dtb_data = vfat_fs.readbytes(f"{dest_path}/{dtb_file}")
        with open(f"{workspace}\\{dtb_file}", "xb") as f:
            f.write(dtb_data)


def extract_bootimg(image_path):
    logging.info("Extract dts from boot image")

    try:
        exec_cmd(f"extract-dtb {image_path} -o {workspace}\\")
    except Exception as e:
        exit_with_msg(str(e.args[0]), e.args[1])


def parse_dts():
    """extract dtb and translate it to dts to get device parameters"""
    global dts_tree
    dts_pattern = f"{workspace}\\*.dts"
    dtb_pattern = f"{workspace}\\*.dtb"
    images = config["IMAGE"]["names"].split()

    dts_files = glob.glob(dts_pattern)
    for file in dts_files:
        os.remove(file)

    dtb_files = glob.glob(dtb_pattern)
    for file in dtb_files:
        os.remove(file)

    for image in images:
        image_path = f"{workspace}\\{image}"
        magic_obj = magic.Magic()
        if "FAT" in magic_obj.from_file(image_path):
            extract_efibin(image_path)
        else:
            extract_bootimg(image_path)

    for dtb_file in glob.glob(dtb_pattern):
        try:
            exec_cmd(f"pydtc.exe unpack {dtb_file}")
        except Exception as e:
            exit_with_msg(str(e.args[0]), e.args[1])

    for dts_file in glob.glob(dts_pattern):
        dts_tree = Devicetree.parseFile(dts_file)


def main():
    initialize()

    if not args.local_images:
        create_sessions()
        build()
        trans_images()

    parse_dts()
    flash_images()
    open_serial()
    wait_bootup()
    run_test_cases()
    cleanup()


if __name__ == "__main__":
    try:
        main()
        logging.info("master success!\n\n")
    except:
        logging.info("master fail!\n\n")
        print(
            "Please refer to https://github.qualcomm.com/yijiyang/linux-sheepdog/blob/main/README.md for instructions"
        )
        raise
