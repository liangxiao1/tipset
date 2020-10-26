# tipset

## Introduction

tipset is a colletion of mini tools about various tips under linux.

## Installation

### Install from pip

`# pip install tipset`

### Install from source code

```bash
# git clone https://github.com/liangxiao1/tipset.git
# cd tipset
# python3 setup.py install
```

### Build wheel from source code and install it

```bash
# python3 setup.py sdist bdist_wheel
# pip install -U dist/tipsearch-0.0.1-py3-none-any.whl
```

### Public new wheels on [pypi](https://pypi.org/project/tipset/) (maintainer use only)

`# python3 -m twine upload  dist/*`

## Enjoy it

There are 3 utils included currently.  
**tipsearch**: a colletion of tips under linux, get to know the command usage with examples instead of looking for manual.  
**json_parser**: convert json to yaml or plain text.  
**pkgone**: install required pkg from specify pkg name, pkg's file or pkg url(only yum/dnf supported now)

### **tipsearch** usage

Below is a simple example to search manually keywords when boot menu was broken.

```bash
$ tipsearch -k 'manually'
INFO:Run in mode: keywords:manually fields: None tipids: None sum_only: False
INFO:Loading baseline data file from /home/xiliang/p3_venv/lib/python3.6/site-packages/tipset/data/tips_data.json
INFO:---------------------------------------------------------------------------
INFO:tipid:tip_6 subject:Boot from grub manually
INFO:step:insmod lvm
INFO:step:linux16 (hd0,msdos1)/vmlinuz-5.0.3-300.fc30.x86_64 root=/dev/mapper/fedora_wasa-root ro rd.lvm.lv=fedora_wasa/root
INFO:step:initrd16 (hd0,msdos1)/initramfs-5.0.3-300.fc30.x86_64.img
INFO:step:set root=(lvm,fedora_wasa-root)/
INFO:step:boot
INFO:tags:grub, boot
INFO:comments:useful when boot menu was broken
INFO:link:
```

### **json_parser usage**

Please refer to json_parser help guide.

### The installed files

All test files are locating in "tipset" directory.

```bash
$ pip3 show -f tipset
Name: tipset
Version: 0.0.1
Summary: tipset is a colletion of mini tools.
Home-page: https://github.com/liangxiao1/tipset
Author: Xiao Liang
Author-email: xiliang@redhat.com
License: GPLv3+
Location: /home/xiliang/p3_venv/lib/python3.6/site-packages
Requires: argparse
Required-by: 
Files:
  ../../../bin/json_parser
  ../../../bin/tipsearch
  tipsearch/__init__.py
  tipsearch/data/tips_data.json
  tipsearch/tipsearch.py
  tipset/__init__.py
  tipset/data/tips_data.json
  tipset/json_parser.py
  tipset/tipsearch.py

```

### Contribution

You are welcomed to create pull request or raise issue.
