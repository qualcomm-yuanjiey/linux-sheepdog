# linux-sheepdog
* The principle and how-to can be found on [this](https://confluence.qualcomm.com/confluence/display/LK/Linux+Kernel+Test+Tool) confluence page.
* This tool was designed to verify upstream kernels on different physical platforms.
* It can implement syncing, making patches, compiling, flashing and verification automatically.
* Two parts of this tool can be used either unified or separately.


# Terms
* slave: refer to the environment where code can be synced and compiled. Usually a server or a gv. It also referred to as 'compilation environment'.
* master/host: refer to the environment where the target test device connected to. 
![over.img](./doc/img/overview.png)

# Preparation
## Environment
* A slave with enough disk space.
* Ensure **network connectivity** between master and slave.

## Install Python modules
  ```bash
    python -m pip install <module name>
  ```
  Modules for compilation environment:
  ```bash
    GitPython
  ``` 
  Modules for the host:
  ```bash
    pyserial, paramiko, pydevicetree, python-magic-win64, pyfatfs, extract-dtb, fs, pydtc
  ``` 
* You may get error messages when installing pydtc:
'error: Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools": https://visualstudio.microsoft.com/visual-cpp-build-tools/ '
* Follow the instructions to install necessary development components on your host


## Install TACDev
* TACDev is a Python module provided by **alpaca** and it should be installed manually on master side.
* Python greater than 3.8 should be installed on both sides.
* Install the Alpaca software suite from the QPM.
* Navigate to the path 'C:\ProgramData\Qualcomm\Alpaca\Python\XPlatform'(should have the `setup.py` to install TACDev) and execute the setup.bat(need to be configured according to your own work environment)

example setup.bat
```bat
DEL /F /Q /S TACDev.egg-info > NUL
RMDIR /Q /S TACDev.egg-info

DEL /F /Q /S build > NUL
RMDIR /Q /S build

DEL /F /Q /S dist > NUL
RMDIR /Q /S dist

; need to change to your python.exe path
C:\Users\yanzl\AppData\Local\Microsoft\WindowsApps\python3.9.exe -m pip uninstall -y tacdev
 
DEL /F /Q /S EPMDev.egg-info > NUL
RMDIR /Q /S EPMDev.egg-info

DEL /F /Q /S build > NUL
RMDIR /Q /S build

DEL /F /Q /S dist > NUL
RMDIR /Q /S dist

; need to change to your python.exe path
C:\Users\yanzl\AppData\Local\Microsoft\WindowsApps\python3.9.exe -m pip uninstall -y epmdev

; need to change to your python.exe path
C:\Users\yanzl\AppData\Local\Microsoft\WindowsApps\python3.9.exe setup.py install

```

* Ensure join 'oe.filer.ro' group to ensure your access to esdk.

## Install apt applications

* diffstat

```bash
sudo apt install diffstat
```

# Download
* Clone this tool from GitHub to you compiling environment.
```bash
git clone https://github.qualcomm.com/yijiyang/linux-sheepdog
```
* This tool consists of two parts. Files for master side including sheepdog-master.py and template-master.ini. While files for the slave side including sheepdog-slave.py and template-slave.ini.

![files](./doc/img/download-files.png)
* Tracking origin/main is recommended.

![recommend](./doc/img/download-branch_recommend.png)

# Deployment
* Files of two parts should be deployed manually. Both copying files or sharing directories is okay. There's no restrictions on where files should be placed.
* Ensure files for master side can be accessed from master. The same goes for slave.
* It is recommended to place files to local path for faster execution.

# Configuration
* Revise config files according to requirements.
* Relative paths are based on user's working directory.
* Be aware of the **different path formats** in Windows and Linux.

![configs-overview](./doc/img/configs-overview.png)


## The master side
For example, in the `template-master.ini`:
### REMOTE
* **addr**: the IP address or  hostname of your compilation environment.
* **username**: the username for login into the compilation environment.
* **slave_script** & slave_config: the name of sheepdog-slave.py and template-slave.ini in your compilation environment.
* **local_repo**: the path of an existing local repo (usually upstream kernel) in compilation environment if it has been downloaded before. Using this option would save much time on syncing code. 

  ⚠️**But unstaged changes in that repo will be discarded!**
  If path not exist, will clone repo(slave.ini set the url) to this path.
* **remote_path**: a path of the slave side where artifacts (the images) of sheepdog-slave stored.
### IMAGE
![config-image](./doc/img/config-image.png)

* **local_path**: the path of the host to which these artifacts (the images) are going to be copied.
* **workspace**: the path where you want the remote command to be executed in compilation environment.
* **names**: images' names. If there're more than one image, each name can be separated with space.
### DEVICE
* **com_port**: get it from device manager.
![com_port](./doc/img/device-comport.png)
* **serial_num**: get it from either adb or fastboot
  ```bash
    adb devices -l
    fastboot devices -l
  ```
![serial_num1](./doc/img/device-adb_serial_num.png)
![serial_num2](./doc/img/device-flash_serial_num.png)

## The slave side
### REPO
example is [here](#set-the-target-repo)
* **url**: the URL of the target repository going to be test
* **branch**: the remote branch
* **linux-next**: the tracking remote
* **tag**: the commit want to checkout. If empty, sheepdog will find the nearest tag to checkout.

✏️ If `branch` isn't be tracked by local branch, sheepdog will create a branch `{linux-next}-{branch}` to track.

### DEVICE
* **arch**: the kernel arch. It's same with `ARCH` option when compiling kernel using 'make'.

* **name**: the name of the dtb file used
* **vendor**: the directory where the target dtb file exists. Will be used like `arch/arm64/boot/dts/{vendor}/`
* **cmdline**: the kernel command line for this test
* **ramdisk_url**: the url of ramdisk 

### TOOLS
* **toolchain_prefix**: the prefix of cross compiling tools. It's same with `CROSS_COMPILE` option when compiling kernel using 'make'.
* **mkbootimg**: the path of tool 'mkbootimg'.
### KERNEL_OPTION
* **kernel**: Kconfig options that should be compiled into kernel during this test.
* **module**: Kconfig options that should be compiled as module during this test.
* **close**: Kconfig options that shouldn't be compiled during this test.
* **make_efi_bin**: If this option is True, sheepdog will make efi.bin; otherwise, will not.
### PATCH

If you want to check your patches correction and apply them to build, you can use this configuration. 

* **patch_dir**: The absolute path where patches exist. If you don't need apply patch, just keep this option empty. If you have multiple directories, you can just split these directories by spaces. Sheepdog will apply patches one directory at a time in sequence, so you need to ensure the correct order of the directories yourself.

📝This option support absolute path and relative path based on the sheepdog directory.

⚠️sheepdog will reset repository to the commit before the patch was applied in the end, so you will find nothing happened in repository after execute sheepdog-slaver.py. But don't be astonished, you can find patch infomation in log file.

More information and example is [here](#make-and-test-patch).

# Integrated Execution
* It would trigger sheepdog-slave.py to sync and compile.
* Syncing code usually time consuming. If there's an existing repo in compilation environment * cloned before, just filled out 'local_repo' in REMOTE section of the config file.
* The process starts at the host with the following command:
  ```bash
    <path>\sheepdog-master.py [--config <config file>]
  ```
* --config: specify config file's path of the master side. If this option not provided, it would search under the same path of the script.
* --local-images: skip syncing and compilation of slave side. Verify existing images in 'local_path' of 'IMAGE' section directly.
* username and password are required after execution if no-password of ssh hasn't been configured.


# Split Execution
* The two parts can be executed separately if you only want to sync & compile upstream or you want to verify existing meta.
* The script of the host part can be used alone by adding an '--local-images' option.
  ```bash
    <path>\sheepdog-master.py [--config <config file>] [--local-images]
  ```
* It will find images from 'local_path' in 'IMAGE' section of the config file.
* The slave script can be used separately as follows:
  ```bash
    <path>/sheepdog-slave.py [--config <config file>] [--local <local repo path>]
  ```
* --config: specify config file's path of the master side. If this option not provided, it would search under the same path of the script.

* --local: same meaning as 'local_repo' in 'REMOTE' section of template-master.ini which represents the path of an existing local repo (usually upstream kernel) in compilation environment if it has been downloaded before
⚠️ If path not exist, will clone repo(slave.ini set the url) to this path.



# Example

## set the target repo
If want to work on the linux kernel remote branch `linux-next/master`
```ini
# slave.ini
[REPO]
url = https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git
branch = master
name = linux-next
tag =
```
Because `tag` is empty, sheepdog will checkout to the nearest tag.


## make and test patch

1. example git work tree:

To simulate a real situation, use the `main` branch as the tracking remote branch, and the `work` branch as the actual working branch.
* main is tracking remote `linux-sheepdogtest`
* work is developers develop branch

⚠️ **sheepdog firstly find the tracking branch `main` and then checkout to it. After that all commands will execute with the `HEAD` in this `main` commit. Especially will apply patches to `main` one by one to test patches correction.**

![worktree](./doc/img/patch-worktree.png)
![remoteshow](./doc/img/patch-remoteshow.png)


2. example check process

```
# ini file
[REPO]
url = git@github.qualcomm.com:yanzl/sheepdog-patchtest.git
# tracking branch
branch = main
# tracking remote
name = sheepdog-patchtest
tag =

...

[PATCH]
; If you want to use absolute path
patch_dir = /local/mnt/workspace/test/sheepdog-patchtest/patches/
; patch_dir = /local/mnt/workspace/test/sheepdog-patchtest/patches

; If patch directory in {sheepdog_dir}/patches/, this option also can be
; patch_dir = ./patches/
; patch_dir = ./patches
; patch_dir = patches/
; patch_dir = patches
```
There are two patches from `main` to `work` to display the process. If you have more than one patch, you should ensure the dependency order of the patches by sorting the names of the patches in **ascending order** yourself.

![patches](./doc/img/patch-patches.png)

Such as we have patches from `work` to `main`(`{patch_dir}/0001-work1.patch` and `{patch_dir}/0002-work2.patch`).

After run sheepdog-slave.py, `{patch_dir}/0001-work1.patch` and `{patch_dir}/0002-work2.patch` will run like below commands
```bash
git am {patch_dir}/0001-work1.patch
git am {patch_dir}/0002-work2.patch
```

