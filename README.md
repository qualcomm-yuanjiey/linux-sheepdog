# linux-sheepdog
* The principle and how-to can be found on [this](https://confluence.qualcomm.com/confluence/display/LK/Linux+Kernel+Test+Tool) confluence page.
* This tool was designed to verify upstream kernels on different physical platforms.
* It can implement syncing, compiling, flashing and verification automatically.
* Two parts of this tool can be used either unified or seperately.

# Preparation
* A compilation environment with enough space.
* Ensure network connectivity between the compilation environment with the host of test device (will be abbreviated as 'the host').
* Install corresponding Python modules for each environment. GitPython for compilation environment and pyserial, TACDev, paramiko for the host. The steps for installing TACDev can be found on [this](https://qualcomm.sharepoint.com/teams/SAGA/SitePages/TAC-Python-Automation.aspx) page.
  ```bash
    python -m pip install <module name>

# Download
* Clone this tool from GitHub to you compiling environment.
  ```bash
    git clone https://github.qualcomm.com/yijiyang/linux-sheepdog
* Also get it from '\\qrdshare\qrdshare\yijieyang'

# Deployment
* Place sheepdog-master.py and template-master.ini in a path of the host. It is recommended to place these two files to a local path of the host instead of a network filesystem for faster execution.

# Configuration
* Revise items of the two config files according to your situation.

# Integrated Execution
* The process starts at the host with the following command:
  ```bash
    <path>\sheepdog-master.py [--config <config file>]
* It would trigger sheepdog-slave.py to sync and compile.
* Syncing code usually time consuming. If there's an existing repo in compilation environment cloned before, just filled out 'local_repo' in REMOTE section of the config file.
* If '--config' option not provided, it will search the path of the script.

# Split Execution
* The two scripts can be executed separately if you only want to sync & compile upstream or you want to test existing meta.
* The script of the host part can be used alone by adding an '--local-images' option.
  ```bash
    <path>\sheepdog-master.py [--config <config file>] [--local-images]
* It will find images from 'local_path' in 'IMAGE' section of the config file.
* The script of the host part can be used alone as following:
  ```bash
    <path>/sheepdog-slave.py [--config <config file>] [--local <local repo path>]
