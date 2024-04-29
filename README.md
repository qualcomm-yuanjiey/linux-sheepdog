# linux-sheepdog
* The principle and how-to can be found on [this](https://confluence.qualcomm.com/confluence/display/LK/Linux+Kernel+Test+Tool) confluence page.
* This tool was designed to verify upstream kernels on different physical platforms.
* It can implement syncing, compiling, flashing and verification automatically.
* Two parts of this tool can be used either unified or seperately.

# Preparation
* A compilation environment with enough space.
* Ensure **network connectivity** between the compilation environment with the host of test device (will be abbreviated as 'the host').
* **Install necessary Python modules** for each environment using the following command:
  ```bash
    python -m pip install <module name>
  ```
  Modules for compilation environment:
  ```bash
    GitPython
  ``` 
  Modules for the host:
  ```bash
    pyserial, TACDev, paramiko, pydevicetree, python-magic, pyfatfs, extract-dtb
  ``` 

## Steps for installing TACDev
* Python 3 should be installed in the host with a version greater or equal to 3.8.0.
* Install the Alpaca software suite from the QPM.
* Navigate to the path 'C:\ProgramData\Qualcomm\Alpaca\Python\XPlatform' and execute the setup.bat


# Download
* Clone this tool from GitHub to you compiling environment.
  ```bash
    git clone https://github.qualcomm.com/yijiyang/linux-sheepdog
  ```
* Files in this tool basically consists of two parts: the slave side and the master side. Files of master side including sheepdog-master.py and template-master.ini work on the host (usually windows OS). While files of the slave side including sheepdog-slave.py and template-slave.ini work on the compilation environment (usually Linux OS).
* Checkout to corresponding branch to get different configuration templates according to the hardware platform.

# Deployment
* Master side's files (sheepdog-master.py and template-master.ini) should be copied to the host while others should be kept in compilation environment.
* It is recommended to place these two files to a local path of the host for faster execution.

# Configuration
* Revise items of the two config files according to your scenario.
* All paths are relative to user's working directory.
* Be aware of the **different path formats** in Windows and Linux.

## The master side
* addr: the IP address of your compilation environment.
* username: the username for login into the compilation environment.
* test_file & config_file: the name of sheepdog-slave.py and template-slave.ini in your compilation environment.
* local_repo: the path to an existing local repo in compilation environment if exist. It would save much time of syncing code.
* remote_path: the path of compiled images in compilation environment.
* local_path: the path of the host to which these compiled images are going to be copied.
* workspace: the path where you want the remote command to be executed in compilation environment.
* names: images' names. If there're more than one image, each name can be separated with space.
* com_port: get it from device manager.
* serial_num: get it from either adb or fastboot
  ```bash
    adb devices -l
    fastboot devices -l
  ```

## The slave side
* url: the URL of the target repository going to be test
* cmdline: the kernel command line for this test
* toolchain_prefix: the prefix of cross compiling tools. It's same with CROSS_COMPILE option * when compiling kernel using 'make'.
* mkbootimg: the path of tool 'mkbootimg'.
* kernel: Kconfig options that should be compiled into kernel during this test.
* module: Kconfig options that should be compiled as module during this test.
* close: Kconfig options that shouldn't be compiled during this test.


# Integrated Execution
* It would trigger sheepdog-slave.py to sync and compile.
* Syncing code usually time consuming. If there's an existing repo in compilation environment * cloned before, just filled out 'local_repo' in REMOTE section of the config file.
* The process starts at the host with the following command:
  ```bash
    <path>\sheepdog-master.py [--config <config file>]
  ```
* --config: specify config file's path of the master side. If this option not provided, it would search the path of the script.
* --local-images: skip syncing and compilation of slave side. Verify existing images in 'local_path' of 'IMAGE' section directly.

# Split Execution
* The two parts can be executed separately if you only want to sync & compile upstream or you want to verify existing meta.
* The script of the host part can be used alone by adding an '--local-images' option.
  ```bash
    <path>\sheepdog-master.py [--config <config file>] [--local-images]
  ```
* It will find images from 'local_path' in 'IMAGE' section of the config file.
* The script of the host part can be used alone as following:
  ```bash
    <path>/sheepdog-slave.py [--config <config file>] [--local <local repo path>]
  ```
