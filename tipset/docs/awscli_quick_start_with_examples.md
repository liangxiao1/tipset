# awscli quick start with examples

## Introduction

This doc is giving some common operations using awscli to access aws resources. For more detail guide, please visit [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/latest/index.html).

## Setup

Install awscli.
```
$ pip install -U awscli
```
Configure you access credentials.
```
$ aws configure
```
You also can view or edit this file directly.
```
$ cat ~/.aws/credentials
```
## Examples to access aws resources
You can remove all filters to list all avaiable resources from below examples.

### List AMIs for creating instance
List RHEL-9.1 amis in region us-west-2 provided by Red Hat ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-images.html)).
```
$ aws ec2 describe-images  --owners 309956199498 --region us-west-2 --filters "Name=name,Values=RHEL-9.1.0_HVM-*" --query 'reverse(sort_by(Images,&CreationDate))[:10].{id:ImageId,date:CreationDate,name:Name}'
2022-11-03T18:06:21.000Z	ami-02920de0ff5afcc73	RHEL-9.1.0_HVM-20221101-arm64-2-Hourly2-GP2
2022-11-03T17:21:45.000Z	ami-0e4841c3bb7d47d69	RHEL-9.1.0_HVM-20221101-x86_64-2-Hourly2-GP2
2022-11-03T16:47:40.000Z	ami-0f5b11b0103837b0d	RHEL-9.1.0_HVM-20221101-x86_64-2-Access2-GP2
2022-11-03T16:24:57.000Z	ami-04e42c641a8a74fd9	RHEL-9.1.0_HVM-20221101-arm64-2-Access2-GP2
```
### Manage key pairs for ssh access
List key pairs name startswith virt([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-key-pairs.html)). The key pair is using for access instances you created, if you do not have a key pair yet, upload one or create a new one.
```
$ aws ec2 describe-key-pairs --filters "Name=key-name,Values=virt*" --region us-west-2
```
Create a new keypair ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/create-key-pair.html)).
```
$ aws ec2 create-key-pair --key-name $yourname --region us-west-2
```
Import a keypair ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/import-key-pair.html)).
```
$ aws ec2 import-key-pair --key-name $yourname --public-key-material fileb://~/.ssh/xxx.pub --region us-west-2
```
### List subnets for creating instance
List subnets ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-subnets.html)). You usually do not need to create new subnet except no one used this region before.
```
$ aws ec2 describe-subnets --query "Subnets[*].SubnetId" --region us-west-2
```
### List security groups for creating instance
List security groups ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-security-groups.html)).
```
$ aws ec2 describe-security-groups --filters Name=ip-permission.from-port,Values=22 Name=ip-permission.to-port,Values=22 Name=ip-permission.cidr,Values='0.0.0.0/0' --query "SecurityGroups[*].{Name:GroupName,ID:GroupId}" --region us-west-2
```
### Instance create and management
Launch instances ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/run-instances.html)).
```
$ aws ec2 run-instances --image-id ami-02920de0ff5afcc73 --key-name testuser --instance-type t3.small  --security-group-ids sg-xxxxx --subnet-id subnet-xxxxxx --associate-public-ip-address
```
List instances ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-instances.html)).
```
$ aws ec2 describe-instances --instance-id i-0d3d462a9d3b1cbaa --region us-west-2
```
Now you can access your instance via private key via publicdnsname.
```
$ ssh -i /path/my-key-pair.pem ec2-user@xxxxxxxxx
```
Stop instances ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/stop-instances.html)).
```
$ aws ec2 stop-instances --instance-id i-0d3d462a9d3b1cbaa --region us-west-2
```
Start instances ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/start-instances.html)).
```
$ aws ec2 start-instances --instance-id i-0d3d462a9d3b1cbaa --region us-west-2
```
Terminate instances ([link](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-instances.html)).
```
$ aws ec2 terminate-instances --instance-id i-0d3d462a9d3b1cbaa --region us-west-2
```

