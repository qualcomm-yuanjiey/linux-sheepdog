#!/usr/bin/python

import sys, os, datetime, logging, configparser, argparse
import subprocess, multiprocessing
import glob, git


def exit_with_msg(msg, code):
    logging.error(msg)
    exit(code)


def exec_shell_cmd(cmd):
    """
    Execute a shell command and return the output
    """
    ret_code = 0

    current_time = datetime.datetime.now()
    print(f"{current_time} {cmd}")

    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    ret_code = result.returncode
    out = result.stdout

    if ret_code == 0:
        logging.info(out)
    else:
        raise Exception(f"Error executing command {cmd}. return ${ret_code}", ret_code)

    return result


def sync_code():
    logging.info("sync_code begin")
    repo_exist = False
    tracking = False
    repo_url = config["REPO"]["url"]
    remote_branch = config["REPO"]["branch"]
    repo_name = config["REPO"]["name"]
    local_repo_path = args.local
    tag = config["REPO"]["tag"]

    if local_repo_path != None:
        repo = git.Repo(local_repo_path)
        os.chdir(local_repo_path)
    else:
        repo = git.Repo.clone_from(repo_url, workspace)
        os.chdir(f"{workspace}/{repo_name}")

    if not any(remote.url == repo_url for remote in repo.remotes):
        remote = repo.create_remote(repo_name, repo_url)
    else:
        remote = repo.remotes[repo_name]

    # find if there's a local branch which is tracking remote repo
    for branch in repo.branches:
        if (
            branch.tracking_branch() != None
            and branch.tracking_branch().name == f"{repo_name}/{remote_branch}"
        ):
            tracking = True
            break

    if not tracking:
        local_branch = repo.create_head(f"{repo_name}-{remote_branch}")
        local_branch.set_tracking_branch(remote.refs[remote_branch])
        repo.head.reference = local_branch
    elif repo.active_branch.name != branch.name:
        repo.head.reference = branch

    exec_shell_cmd(f"git fetch --tags {repo_name}")
    if len(tag) != 0:
        exec_shell_cmd(f"git checkout {tag}")

    logging.info("sync_code finished")


def compile():
    cpu_num = multiprocessing.cpu_count()

    dev_info = config["DEVICE"]
    tools = config["TOOLS"]
    kernel_options = config["KERNEL_OPTION"]

    arch = dev_info["arch"]
    dev_name = dev_info["name"]
    ramdisk_url = dev_info["ramdisk_url"]
    cmdline = dev_info["cmdline"]
    vendor = dev_info["vendor"]

    toolchain_prefix = tools["toolchain_prefix"]
    mkbootimg = tools["mkbootimg"]

    cwd = os.getcwd()
    ramdisk = f"{cwd}/ramdisk.gz"
    make_options = f"-j{cpu_num} ARCH={arch} CROSS_COMPILE={toolchain_prefix}"

    options_kernel = kernel_options["kernel"].split()
    options_module = kernel_options["module"].split()
    options_close = kernel_options["close"].split()

    defconfig = f"{cwd}/arch/{arch}/configs/defconfig"
    image = f"arch/{arch}/boot/Image.gz"
    dtb = f"arch/{arch}/boot/dts/{vendor}/{dev_name}.dtb"
    bootimg = f"{workspace}/boot.img"

    with open(defconfig, "a") as f:
        for option in options_kernel:
            f.write(f"\n{option}=y")
        for option in options_module:
            f.write(f"\n{option}=m")
        for option in options_close:
            f.write(f"\n{option}=n")

    try:
        exec_shell_cmd(f"make {make_options} defconfig")
        exec_shell_cmd(f"make {make_options} Image.gz dtbs modules")
        exec_shell_cmd(
            f"make {make_options} modules_install INSTALL_MOD_PATH=./modules_dir INSTALL_MOD_STRIP=1"
        )
        exec_shell_cmd(f"cat {image} {dtb} > Image.gz+dtb")

        if not os.access(ramdisk, os.F_OK):
            exec_shell_cmd(f"wget -O {ramdisk} {ramdisk_url}")

        exec_shell_cmd(
            f'{mkbootimg} --kernel Image.gz+dtb --cmdline "{cmdline}" --ramdisk {ramdisk} --base 0x80000000 --pagesize 4096 --output {bootimg}'
        )
    except Exception as e:
        exit_with_msg(str(e.args[0]), e.args[1])


def precheck():
    toolchain_exist = False
    toolchain_prefix = config["TOOLS"]["toolchain_prefix"]
    mkbootimg = config["TOOLS"]["mkbootimg"]
    exec_paths = ["/bin", "/sbin", "/usr/local/bin", "/usr/local/sbin"]

    for path in exec_paths:
        if len(glob.glob(f"{path}/{toolchain_prefix}*", recursive=True)) != 0:
            toolchain_exist = True
            break

    if not toolchain_exist:
        exit_with_msg(f"compiler {toolchain_prefix}* not exist", 1)

    if not os.access(mkbootimg, os.X_OK):
        exit_with_msg(f"{mkbootimg} not exist or not executable", 1)


def parse_config():
    global config, workspace

    config_file = args.config
    if config_file is None:
        config_file = os.path.dirname(__file__) + "/template-slave.ini"

    config = configparser.ConfigParser()
    config.read(config_file)

    workspace = config.get(section="WORKSPACE", option="path", fallback=os.getcwd())
    os.chdir(workspace)


def log_init():
    log_file = config.get("LOG", "file", fallback=f"{workspace}/test.log")
    log_level = config["LOG"]["level"]

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=[
            logging.FileHandler(filename=log_file, mode="w"),
            logging.StreamHandler(),
        ],
    )


def parse_options():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, help="the full path of config file")
    parser.add_argument("--local", type=str, help="the path to already synced code")
    args = parser.parse_args()


def initialize():
    parse_options()
    parse_config()
    log_init()
    logging.info("initialize finished")


def main():
    initialize()
    precheck()
    sync_code()
    compile()


if __name__ == "__main__":
    try:
        main()
    except:
        print(
            "Please refer to https://github.qualcomm.com/yijiyang/linux-sheepdog/blob/main/README.md for instructions"
        )
        raise
