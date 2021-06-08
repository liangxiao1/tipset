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

There are 4 utils included currently(under /usr/local/bin by default).  
**tipsearch**: a colletion of tips under linux, get to know the command usage with examples instead of looking for manual.  
**json_parser**: convert json to yaml or plain text.  
**html_parser**: dump information from html to yaml and plain text.  
**aws_amis_search**: search and delete aws amis status in all regions and check whether they are supported.  
**aws_instance_search**: search and delete aws running instances in all supported regions by keyname/tag

### **tipsearch** usage

Below is a simple example to search sed examples from subject.

```bash
$ tipsearch -k sed -f subject
INFO:Run in mode: keywords:sed fields: subject tipids: None sum_only: False
INFO:Loading baseline data file from /home/xiliang/p3_venv/lib/python3.6/site-packages/tipset/data/tips_data.json
INFO:---------------------------------------------------------------------------
INFO:tipid:tip_61 subject:sed examples
INFO:step:sed -i "97d;98d" /tmp/1 (delete line 97, 98)
INFO:step:sed -n '22,30p' /tmp/2 (display 22~30 line)
INFO:step:sed -i "/foos/d" /tmp/1 (find and delete the match line)
INFO:step:sed -i '1s/^/add to new top line\n/' /tmp/1 (add new line at top)
INFO:step:sed -i 's/\(^.*100.*$\)///\1/' /tmp/1 (insert \\ at the head of matched line)
INFO:step:sed -i 's/^foo/#comment out as bug 1464851\n&/g' /tmp/1 (add one line before matched)
INFO:step:sed -e 's/^foo.*/report/g' /tmp/1 (replace entire line with other)
INFO:step:sed '1!G;h;$!d' /tmp/2 (revers file line, move top to down)
INFO:tags:bash, sed
INFO:comments:
INFO:link:
INFO:Total found: 1

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
