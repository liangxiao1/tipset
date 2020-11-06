#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

Search amis status in all regions and check whether they are supported.

'''
import json
import os
import copy
import sys
import logging
import argparse
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Please install boto3")
    sys.exit(1)
from operator import itemgetter
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
import concurrent.futures

log = logging.getLogger(__name__)
credential_file = 'data/aws_keys.yaml'

ACCESS_KEY = None
SECRET_KEY = None

def check_boot(ec2_resource=None,instance_type=None,ami=None,subnet=None,region=None):
    try:
        vm = ec2_resource.create_instances(
            ImageId=ami,
            InstanceType=instance_type,
            SubnetId=subnet,
            MaxCount=1,
            MinCount=1,
            DryRun=True,
        )[0]
    except ClientError as err:
        if 'DryRunOperation' in str(err):
            log.debug("%s can create in %s", region, ami)
            bootable = True
        elif 'Unsupported' in str(err):
            bootable = 'Unsupported'
            log.debug("Can not create in %s %s: %s", region, bootable, err)
        elif 'Elastic Network Adapter' in str(err):
            bootable = 'FalseNoENA'
            log.debug("Can not create in %s %s: %s. Try d2.xlarge without ENA,", region, bootable,err)
        else:
            bootable = False
            logging.info("Can not create in %s %s: %s", region, bootable, err)

    return bootable

def check_item(region, regionids, result_list, is_check, filter_json, filter,amiids):
    bootable = False
    if ACCESS_KEY is None:
        client = boto3.client('ec2', region_name=region)
    else:
        client = boto3.client(
            'ec2',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            region_name=region,
        )

    filters = []
    if filter_json is not None:
        for filter in filter_json.split(';'):
            filters.append(json.loads(filter))
    if filter is not None:
        filters.append(
                    {
                        'Name': 'name',
                        'Values': [
                            '*{}*'.format(filter),
                            ]
                    }
                )
    if amiids is not None:
        amiids_list = amiids.split(',')
        images_list = client.describe_images(
                Filters=filters,
                ImageIds=amiids_list,
            )
    else:
        images_list = client.describe_images(
                Filters=filters,
            )
    subnet_list = client.describe_subnets()['Subnets']
    if ACCESS_KEY is None:
        ec2 = boto3.resource('ec2', region_name=region)
    else:
        ec2 = boto3.resource(
            'ec2',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            region_name=region,
        )
    if len(images_list['Images']) > 0:
        regionids.remove(region)
    for img in images_list['Images']:
        if 'x86_64' in img['Name']:
            instance_type = 'm5.large'
        else:
            instance_type = 'a1.large'
        if is_check:
            bootable = check_boot(ec2_resource=ec2,instance_type=instance_type,ami=img['ImageId'],subnet=subnet_list[0]['SubnetId'],region=region)
            if 'FalseNoENA' in str(bootable):
                log.info("Failed as ENA, 2nd check with d2.xlarge instance type without ENA.")
                instance_type = 'd2.xlarge'
                bootable = check_boot(ec2_resource=ec2,instance_type=instance_type,ami=img['ImageId'],subnet=subnet_list[0]['SubnetId'],region=region)
        if img['Public']:
            public_status = 'Public'
        else:
            public_status = 'Private'
        if is_check:
            result_list.append([img['Name'], img['ImageId'], "{}({})".format(region, len(images_list['Images'])), public_status, bootable])
        else:
            result_list.append([img['Name'], img['ImageId'], "{}({})".format(region, len(images_list['Images'])), public_status])
def main():
    parser = argparse.ArgumentParser(
        'Search/Filter AMIs crossing regions.')
    parser.add_argument('--filter', dest='filter', action='store',
                        help='SAP, RHEL-8.3 or other keywords, default is search name', required=False)
    parser.add_argument('--region', dest='region', action='store',
                        help='regions to check, split by comma, default is all', required=False)
    parser.add_argument('--region_skip', dest='region_skip', action='store',
                        help='regions not check, split by comma, default is none', required=False)
    parser.add_argument('--filter_json', dest='filter_json', action='store',
                        help='{"Name":"name","Values":["*SAP*"]};{"Name": "tag:Name","Values": ["*baseami*"]};{"Name":"description","Values":["*Provided by Red Hat*"]} \
                            For all supported filed: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_images', required=False)
    parser.add_argument('--dir', dest='dir', action='store', default='/tmp',
                        help='save files to dir', required=False)
    parser.add_argument('--tokenfile', dest='tokenfile', action='store', default="data/aws_keys.yaml",
                        help='optional, credential file, default data/aws_keys.yaml', required=False)
    parser.add_argument('--target', dest='target', action='store', default="aws",
                        help='optional, can be aws or aws-china or aws-us-gov', required=False)
    parser.add_argument('-d', dest='is_debug', action='store_true', default=False,
                        help='Run in debug mode', required=False)
    parser.add_argument('-c', dest='is_check', action='store_true', default=False,
                        help='Check whether AMI bootable', required=False)
    parser.add_argument('--amiids', dest='amiids', action='store',
                        help='specify amiids split by comman', required=False)
    args = parser.parse_args()
    log = logging.getLogger(__name__)
    if args.is_debug:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(levelname)s:%(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
    if args.filter_json == None and args.filter == None and args.amiids == None:
        log.info("Please specify filter_json, filter or amiids in cmd")
        sys.exit(1)
    credential_file = args.tokenfile
    credential_file_format = "aws-us-gov: ['ec2_access_key','ec2_secret_key','subscription_username','subscription_password']"
    if not os.path.exists(credential_file):
        log.info("%s not found, you can add your key into it to check in different account" % credential_file)
        log.info(credential_file_format)
        log.info("Use your default credential set")
        ACCESS_KEY = None
        SECRET_KEY = None
    else:
        with open(credential_file,'r') as fh:
             keys_data = load(fh, Loader=Loader)
        try:
            ACCESS_KEY = keys_data[args.target][0]
            SECRET_KEY = keys_data[args.target][1]
        except KeyError:
            log.info("%s credential cfg file read error, try use default", args.target)
            ACCESS_KEY = None
            SECRET_KEY = None
    
    if ACCESS_KEY is None:
        client = boto3.client('ec2',region_name='us-west-2')
    else:
        client = boto3.client(
            'ec2',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            region_name='us-west-2',
        )
    
    if args.is_check:
        log.info("AMI Name | AMI ID | Region Name | Public | Bootable")
    else:
        log.info("AMI Name | AMI ID | Region Name | Public")
    result_list = []
    if args.region is not None:
        log.info("Only checking {}".format(args.region.split(',')))
        regionids = args.region.split(',')
    else:
        region_list = client.describe_regions()['Regions']
        regionids = []
        for region in region_list:
            regionids.append(region['RegionName'])
    if args.region_skip is not None:
        log.info("skip region: {}".format(args.region_skip.split(',')))
        for r in args.region_skip.split(','):
            regionids.remove(r)
    with concurrent.futures.ThreadPoolExecutor(max_workers=150) as executor:
            check_all_regions_tasks = {executor.submit(check_item, region, regionids, result_list, args.is_check, args.filter_json, args.filter, args.amiids): region for region in sorted(regionids)}
            for r in concurrent.futures.as_completed(check_all_regions_tasks):
                x = check_all_regions_tasks[r]
                try:
                    data = r.result()
                except Exception as exc:
                    log.error("{} generated an exception: {}".format(r,exc))
                else:
                    pass
    result_list = sorted(result_list, key=lambda x:x[2])
    for i in result_list:
        if args.is_check:
            log.info("%s %s %s %s %s", i[0], i[1], i[2], i[3], i[4])
        else:
            log.info("%s %s %s %s", i[0], i[1], i[2], i[3])
    log.info("Found total AMIs: {}".format(len(result_list)))    
    if len(regionids) > 0:
        log.info('Below regions no ami found: %s', regionids)

if __name__ == '__main__':
    main()