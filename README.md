# tipset

## Introduction

tipset is a tool collection about various tips under linux.

## Installation

### Install from pip

`# pip install tipset`

### Install from code repo directly

```bash
# pip install git+https://github.com/liangxiao1/tipset.git@main
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
**aws_resource_monitor**: monitor resources on aws.  
**json_parser**: convert json to yaml or plain text.  
**rhcert_manager**: interact with rhcert web console in cli.  
**rp_manager**: interact with reportportal in cli.  
**tipsearch**: a collection of tips under linux, get to know the command usage with examples instead of looking for man page.

### **aws_resource_monitor usage examples**
```bash
# query resources with specific tag
$ aws_resource_monitor --filters '[{"Name":"tag:Name","Values":["xiliang*"]}]' --profile xxx --region us-west-2
# query ami with specific id
$ aws_resource_monitor --filters '[{"Name":"image-id","Values":["ami-xxxxxx"]}]' --profile xxx --region us-east-1 --type ami
# query volumes exist days over 300 and delete them
$ aws_resource_monitor --days 300 --profile xxx --region us-west-2 --type volume --delete
# query instance with specific id and delete it directly
$ aws_resource_monitor --filters '[{"Name":"instance-id","Values":["i-0cf52ed8ea39xxxxxx"]}]' --profile xxx --region us-west-2 --type instance --delete
# delete resources from csv file
$ aws_resource_monitor --profile rhui-dev --region us-west-2 --type ami --resource /tmp/aws_images.csv --delete
```
Filters Ref: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html


### **rhcert_manager usage examples ([cfg template](https://github.com/liangxiao1/tipset/blob/main/tipset/cfg/rhcert_manager.yaml))**  

```bash
# init token firstly
$ rhcert_manager token --init
# create new product
$ rhcert_manager product --partnerId xxx --category 'Cloud Instance Type' --name xxx --make xxx --model xxx --description xxx --productUrl xxx --specUrl xxx --supportUrl xxx --new
# create new cert for RHEL-8.7 x86_64 arch
$ rhcert_manager cert --classificationId 1 --partnerProductId xxx --certificationTypeId 61 --content '{"versionId":"2327","platformId":"7"}' --new
# query the cert ticket info
$ rhcert_manager cert --id xxx --list
# upload the attachment to cert ticket
$ rhcert_manager cert --id xxx --caseNumber xxx --attachment xxx --attachment_desc 'Auto uploaded.' --attachment_upload
```


### **rp_manager usage examples ([cfg template](https://github.com/liangxiao1/tipset/blob/main/tipset/cfg/rp_manager.yaml))**  

```bash
# create new launch by uploading test logdir
$ rp_manager launch  --cfg rp_manager.yaml --new --logdir XXXX
# list launch by launch uuid or id
$ rp_manager launch  --cfg rp_manager.yaml --uuid <launch UUID> --list
# trigger auto analyze by launch uuid
$ rp_manager launch  --cfg rp_manager.yaml --uuid <launch UUID> --analyze
# delete launch by launch uuid
$ rp_manager launch  --cfg rp_manager.yaml --uuid <launch UUID> --delete
# list current user information
$ rp_manager user --list
```

### **tipsearch usage examples**

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
