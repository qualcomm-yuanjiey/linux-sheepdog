# linux-sheepdog
* The principle and how-to can be found on [this](https://confluence.qualcomm.com/confluence/display/LK/Linux+Kernel+Test+Tool) confluence page.
* This tool was designed to verify upstream kernels on different physical platforms.
* It can implement syncing, compiling, flashing and verification automatically.
* Two parts of this tool can be used either unified or seperately.

# Terms
* slave: refer to the environment where code can be synced and compiled. Usually a server or a gv. It also referred to as 'compilation environment'.
* master/host: refer to the environment where the target test device connected to. 

# Preparation
* A slave with enough disk space.
* Ensure **network connectivity** between master and slave.
* **Install necessary Python modules**.
  ```bash
    python -m pip install <module name>
  ```
  Modules for compilation environment:
  ```bash
    GitPython
  ``` 
  Modules for the host:
  ```bash
    pyserial, TACDev, paramiko, pydevicetree, python-magic-win64, pyfatfs, extract-dtb, fs
  ``` 

## Steps for installing TACDev
* Python greater than 3.8 should be installed on both sides.
* Install the Alpaca software suite from the QPM.
* Navigate to the path 'C:\ProgramData\Qualcomm\Alpaca\Python\XPlatform' and execute the setup.bat


# Download
* Clone this tool from GitHub to you compiling environment.
  ```bash
    git clone https://github.qualcomm.com/yijiyang/linux-sheepdog
  ```
* This tool consists of two parts. Files for master side including sheepdog-master.py and template-master.ini. While files for the slave side including sheepdog-slave.py and template-slave.ini.
* Tracking origin/main is recommended.

# Deployment
* Files of two parts should be deployed manually. Both copying files or sharing directories is okay. There's no restrictions on where files should be placed.
* Ensure files for master side can be accessed from master. The same goes for slave.
* It is recommended to place files to local path for faster execution.

# Configuration
* Revise config files according to requirements.
* Relative paths are based on user's working directory.
* Be aware of the **different path formats** in Windows and Linux.

## The master side
* addr: the IP address or  hostname of your compilation environment.
* username: the username for login into the compilation environment.
* slave_script & slave_config: the name of sheepdog-slave.py and template-slave.ini in your compilation environment.
* local_repo: the path of an existing local repo (usually upstream kernel) in compilation environment if it has been downloaded before. Using this option would save much time on syncing code.
* remote_path: a path of the slave side where artifacts (the images) of sheepdog-slave stored.
* local_path: the path of the host to which these artifacts (the images) are going to be copied.
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
* username and password are required after execution if no-password of ssh hasn't been configured.

# Split Execution
* The two parts can be executed separately if you only want to sync & compile upstream or you want to verify existing meta.
* The script of the host part can be used alone by adding an '--local-images' option.
  ```bash
    <path>\sheepdog-master.py [--config <config file>] [--local-images]
  ```
* It will find images from 'local_path' in 'IMAGE' section of the config file.
* The script of the host part can be used separately as follows:
  ```bash
    <path>/sheepdog-slave.py [--config <config file>] [--local <local repo path>]
  ```
