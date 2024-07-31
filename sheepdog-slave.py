#!/usr/bin/python

import sys, os, datetime, logging, configparser, argparse
import subprocess, multiprocessing
import glob, git, shutil, re


def reset2basecommit():
    try:
        local_repo.git.reset("--hard", base_commit)
        logging.info(f"checkout to {base_commit}")
    except NameError:
        logging.error("local_repo is not exist. But if failed before sync kernel code completes, you can ignore this error")


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
        logging.debug(out)
    else:
        raise Exception(
            f"Error executing command {cmd}\nReturn code: ${ret_code}", ret_code
        )

    return result


def sync_kernel():
    logging.info("sync kernel code begin")

    global compile_path, local_repo, track_branch, local_repo_path, base_commit
    tracking = False
    repo_url = config["REPO"]["url"]
    remote_branch = config["REPO"]["branch"]
    repo_name = config["REPO"]["name"]
    local_repo_path = args.local
    tag = config["REPO"]["tag"]
    remote_exist = False

    if local_repo_path != None:
        local_repo_path = os.path.abspath(local_repo_path)
    else:
        local_repo_path = f"{workspace}/{repo_name}"
    
    try:
        if os.path.exists(local_repo_path):
            local_repo = git.Repo(path=local_repo_path)
        else:
            logging.info(f"{local_repo_path} not exist.\n****Begin clone from {repo_url}****")
            local_repo = git.Repo.clone_from(repo_url, local_repo_path)
    except git.exc.InvalidGitRepositoryError as e:
        logging.error(f"{local_repo_path} is exist but no git repository in it.")
        raise e

    compile_path = local_repo.working_dir
    os.chdir(local_repo.working_dir)

    for remote in local_repo.remotes:
        if remote.url == repo_url:
            remote_exist = True
            break

    # use repo name as remote name
    if not remote_exist:
        remote = local_repo.create_remote(repo_name, repo_url)
    else:
        repo_name = remote.name

    # remove unstaged files which would block checkout
    local_repo.git.reset("--hard")
    
    # find if there's a local branch which is tracking remote repo
    for track_branch in local_repo.branches:
        if (
            track_branch.tracking_branch() != None
            and track_branch.tracking_branch().name == f"{repo_name}/{remote_branch}"
        ):
            tracking = True
            break

    if not tracking:
        track_branch = local_repo.create_head(f"{repo_name}-{remote_branch}")
        track_branch.set_tracking_branch(remote.refs[remote_branch])
    track_branch.checkout()

    local_repo.git.fetch(remote, "--tags")
    remote.pull(rebase=True)
    if len(tag) != 0:
        exec_shell_cmd(f"git checkout {tag}")
    else:
        try:
            tag = local_repo.git.describe(tags=True, abbrev=0)
        except git.exc.GitCommandError as e:
            if "No names found, cannot describe anything" in str(e):
                logging.warning("No tags found in the repository")
                tag = "no tags"
            else:
                logging.error(f"Error : {e}")
                raise e

    # store current commit, will reset to this commit in the end
    base_commit = local_repo.head.commit.hexsha

    os.chdir(workspace)
    logging.info(f"sync kernel code finished, current tag: {tag}")


def sync_mkbootimg():
    logging.info("sync mkbootimg begin")

    global mkbootimg
    mkbootimg_url = (
        "ssh://review-android.quicinc.com:29418/kernel_platform/system/tools/mkbootimg"
    )
    target_branch = "KERNEL.PLATFORM.4.0"
    repo_name = "mkbootimg"

    mkbootimg = os.path.abspath(config.get("TOOLS", "mkbootimg", fallback=None))
    if mkbootimg != None and len(mkbootimg) != 0:
        return

    repo = git.Repo.clone_from(url=mkbootimg_url, to_path=f"{tool_path}/{repo_name}")
    os.chdir(repo.working_dir)
    local_branch = repo.create_head(target_branch)
    local_branch.set_tracking_branch(repo.refs[f"origin/{target_branch}"])
    repo.head.reference = local_branch

    mkbootimg = f"{tool_path}/{repo_name}/mkbootimg.py"

    os.chdir(workspace)
    logging.info("sync mkbootimg finished")


def sync_code():
    sync_mkbootimg()
    sync_kernel()
    sync_build_tool()
    install_esdk()

def make_ramdisk(kernel_components):
    ramdisk_url = config["DEVICE"]["ramdisk_url"]
    try:
        if not os.access('./clean_ramdisk.gz', os.F_OK):
            exec_shell_cmd(f"wget -O ./clean_ramdisk.gz {ramdisk_url}")
        shutil.copy("clean_ramdisk.gz", kernel_components['ramdisk'])

        modules_install_dir = f'{compile_path}/modules_dir/lib/modules'
        if os.path.exists(modules_install_dir):
            os.chdir(f'{compile_path}/modules_dir')
        else:
            logging.warning(f'{modules_install_dir} not exists')
            logging.warning('skip package modules into ramdisk')
            return
        
        cmd = f"find ./lib/modules | cpio -o -H newc -R +0:+0 | pigz -9 >> {kernel_components['ramdisk']}"
        exec_shell_cmd(cmd)

        shutil.rmtree(modules_install_dir)
        os.chdir(f'{workspace}')
    except Exception as e:
        os.chdir(f'{workspace}')
        exit_with_msg(str(e.args[0]), e.args[1])

def build_boot_image(kernel_components):
    logging.info("build boot image")

    cmd = mkbootimg
    cmd += " --header_version 2"
    cmd += " --kernel " + kernel_components["kernel_image"]
    cmd += " --dtb " + kernel_components["dtb"][0]
    cmd += " --cmdline " + '"' + kernel_components["cmdline"] + '"'
    cmd += " --ramdisk " + kernel_components["ramdisk"]
    cmd += " --base 0x80000000 --pagesize 4096"
    cmd += f" --output {workspace}/boot.img"

    try:
        logging.debug(f"Build boot image command: {cmd}")
        exec_shell_cmd(cmd)
    except Exception as e:
        exit_with_msg(str(e.args[0]), e.args[1])

def am_patch():
    if config["PATCH"]["patch_dir"] == '':
        return
    logging.info("patch apply begin")

    # get patches file
    patch_dirs = config["PATCH"]["patch_dir"].split()
    for patch_dir in patch_dirs:
        if os.path.isabs(f"{patch_dir}"):
            patch_dir = os.path.normpath(f"{patch_dir}")
        else:
            patch_dir = f"{workspace}/{patch_dir}"
            patch_dir = os.path.abspath(patch_dir)
        
        if not os.path.exists(patch_dir):
            logging.error("Wrong patch directory path. Please check patch_dir option in ini file")
            raise FileNotFoundError("Not found patch directory")
        logging.debug(f"patches dir is {patch_dir}")

        patches_pattern = f"{patch_dir}/*.patch"
        patch_files = glob.glob(patches_pattern)
        patch_files = sorted(patch_files)
        
        if len(patch_files) < 1:
            logging.error("Not found the patches. Please check the patch_dir")
            raise FileNotFoundError("Not found the patches.")

        # check patches
        logging.debug(f"patch base commit is {base_commit}")
        for patch_file in patch_files:
            try:
                local_repo.git.am(patch_file)
            except git.exc.GitCommandError as e:
                logging.error(f"Error is {e}\n")
                logging.error(f"Git am operation aborted and changes reverted")
                local_repo.git.am("--abort")
                raise e
            
            logging.debug(f"{patch_file} applies to {track_branch}")
        logging.info(f'patches in {patch_dir} are all applied down')

    logging.info(f"patches apply down")

def install_esdk():
    logging.info("Install esdk")

    sdk_path = f"{tool_path}/esdk"
    if os.path.exists(sdk_path):
        logging.info(f"Already installed, remove {sdk_path} to reinstall.")
        return

    esdk_source = "/prj/qct/quic/oe_filer_scratch/ESDK/LE.QCLINUX.1.0"
    if not os.path.exists(esdk_source):
        logging.info(f"esdk source path {esdk_source} not found.")
        exit(1)

    for root, dir, files in os.walk(esdk_source):
        for file in files:
            if ".sh" in file:
                sdk_script = os.path.join(root, file)
                logging.info(f"Found esdk: {sdk_script}")
                break

    cmd = f"{sdk_script} -y -d {sdk_path}"

    logging.info(f"Install esdk to {sdk_path}")
    try:
        logging.debug(f"Install esdk command: {cmd}")
        exec_shell_cmd(cmd)
    except Exception as e:
        exit_with_msg(str(e.args[0]), e.args[1])


def sync_build_tool():
    logging.info("sync build tool begin")

    url = "ssh://git-android-sha-drekar.quicinc.com:29418/kernel/build"
    branch = "qclinux.1.0"
    repo_name = "build"
    remote_name = "origin"
    build_tool_path = f"{tool_path}/{repo_name}"

    if os.path.exists(build_tool_path):
        logging.info(f"Already installed, remove {build_tool_path} to reinstall.")
        return

    repo = git.Repo.clone_from(url=url, to_path=f"{tool_path}/{repo_name}")
    os.chdir(repo.working_dir)
    local_branch = repo.create_head(branch)
    local_branch.set_tracking_branch(repo.refs[f"{remote_name}/{branch}"])
    local_branch.checkout()
    repo.remotes[remote_name].pull(rebase=True)

    os.chdir(workspace)
    logging.info("sync build tool finished")


def modify_build_script(script):
    """
    'du' path in this script was fixed, we @don't use that, so modify it
    """
    with open(script, "r+") as file:
        data = file.read()
        data = re.sub("prebuilt.*du", "du", data)
        file.seek(0)
        file.write(data)
        file.truncate()


def build_efi_bin(kernel_components):
    esdk_bin_path = tool_path + "/esdk/tmp/sysroots/x86_64/usr/bin"
    esdk_img_path = tool_path + "/esdk/tmp/deploy/images/qcm6490"
    esdk_lib_path = tool_path + "/esdk/tmp/sysroots/x86_64/usr/lib"

    # mcopy = esdk_bin_path + "/mcopy"
    ukify = esdk_bin_path + "/ukify"

    systemd_img = esdk_img_path + "/systemd-bootaa64.efi"
    efi_stub = esdk_img_path + "/linuxaa64.efi.stub"

    efi_bin = workspace + "/efi.bin"
    python_path = esdk_lib_path + "/python3.10/site-packages"
    python_exec = esdk_bin_path + "/python3-native/python3.10"

    efi_dir = workspace + "/efi_dir"
    gen_efi_boot = f"{tool_path}/build/generate_efi_boot.sh"

    logging.info("build efi bin")

    modify_build_script(gen_efi_boot)

    if os.access(efi_bin, os.F_OK):
        os.remove(efi_bin)
    if os.path.exists(efi_dir):
        shutil.rmtree(efi_dir)

    os.makedirs(f"{efi_dir}/dtb")
    os.makedirs(f"{efi_dir}/EFI/BOOT")
    os.makedirs(f"{efi_dir}/EFI/Linux")
    os.makedirs(f"{efi_dir}/loader")

    uki_name = workspace + "/uki.efi"

    for dtb in kernel_components["dtb"]:
        shutil.copy(dtb, f"{efi_dir}/dtb")
    shutil.copy(systemd_img, f"{efi_dir}/EFI/BOOT/bootaa64.efi")
    open(f"{efi_dir}/loader/loader.conf", "w").close()

    os.environ["PYTHONPATH"] = python_path
    os.environ["PATH"] = f"{esdk_bin_path}:" + os.environ["PATH"]
    logging.info(f'PYTHONPATH={os.environ["PYTHONPATH"]}')
    logging.info(f'PATH={os.environ["PATH"]}')

    uki_cmd = f"{python_exec} {ukify} build"
    uki_cmd += " --initrd=" + kernel_components["ramdisk"]
    uki_cmd += " --linux=" + kernel_components["kernel_image"]
    uki_cmd += " --efi-arch=aa64"
    uki_cmd += " --cmdline=" + '"' + kernel_components["cmdline"] + '"'
    uki_cmd += " --stub=" + efi_stub
    uki_cmd += " --output=" + uki_name

    try:
        exec_shell_cmd(uki_cmd)
        logging.info(f"UKI image created at {uki_name}")

        shutil.copy(uki_name, f"{efi_dir}/EFI/Linux")

        exec_shell_cmd(f"{gen_efi_boot} {efi_dir} {efi_bin}")
        logging.info(f"EFI image created at {efi_bin}")
    except Exception as e:
        exit_with_msg(str(e.args[0]), e.args[1])


def compile():
    cpu_num = multiprocessing.cpu_count()

    dev_info = config["DEVICE"]
    tools = config["TOOLS"]
    kernel_options = config["KERNEL_OPTION"]

    arch = dev_info["arch"]
    dev_name = dev_info["name"]
    vendor = dev_info["vendor"]

    toolchain_prefix = tools["toolchain_prefix"]

    make_options = (
        f"-j{cpu_num} -C {compile_path} ARCH={arch} CROSS_COMPILE={toolchain_prefix}"
    )

    options_kernel = kernel_options["kernel"].split()
    options_module = kernel_options["module"].split()
    options_close = kernel_options["close"].split()

    defconfig = f"{compile_path}/arch/{arch}/configs/defconfig"
    logging.debug(f"defconfig is {defconfig}")

    kernel_components = {
        "kernel_image": f"{compile_path}/arch/{arch}/boot/Image",
        "dtb": [f"{compile_path}/arch/{arch}/boot/dts/{vendor}/{dev_name}.dtb"],
        "ramdisk": f"{workspace}/ramdisk.gz",
        "cmdline": dev_info["cmdline"],
    }

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
    except Exception as e:
        exit_with_msg(str(e.args[0]), e.args[1])
    
    make_ramdisk(kernel_components)
    build_boot_image(kernel_components)
    if kernel_options["make_efi_bin"] == 'True':
        install_esdk()
        build_efi_bin(kernel_components)


def precheck():
    toolchain_prefix = config["TOOLS"]["toolchain_prefix"]

    try:
        exec_shell_cmd(f"{toolchain_prefix}gcc --version")
    except:
        exit_with_msg(f"compiler {toolchain_prefix}gcc may not exist, please check", 1)


def parse_config():
    global config

    config_file = args.config
    if config_file is None:
        config_file = os.path.dirname(__file__) + "/template-slave.ini"
        logging.info("Using the default config tempelete-slave.ini")

    config_file = os.path.abspath(config_file)
    if not os.path.exists(config_file):
        logging.error(f"Don't get the config file{config_file}")
        raise FileNotFoundError(f"File {config_file} not found")
    config = configparser.ConfigParser()
    config.read(config_file)


def log_init():
    log_file = config.get("LOG", "file", fallback=f"./linux-sheepdog-slave.log")
    log_file = os.path.abspath(log_file)
    log_level = config["LOG"]["level"]

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=[
            logging.FileHandler(filename=log_file, mode="a"),
            logging.StreamHandler(),
        ],
    )


def parse_options():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, help="the full path of config file")
    parser.add_argument("--local", type=str, help="the path to already synced code")
    args = parser.parse_args()


def env_init():
    global workspace, tool_path
    workspace = os.getcwd()
    tool_path = os.path.dirname(os.path.abspath(__file__))


def initialize():
    env_init()
    parse_options()
    parse_config()
    log_init()
    logging.info("initialize finished")


def main():
    initialize()
    precheck()
    sync_code()
    am_patch()
    compile()


if __name__ == "__main__":
    try:
        main()
        reset2basecommit()
        logging.info("slave success!\n\n")
    except:
        reset2basecommit()
        logging.info("slave fail!\n\n")
        print(
            "Please refer to https://github.qualcomm.com/yijiyang/linux-sheepdog/blob/main/README.md for instructions"
        )
        raise
