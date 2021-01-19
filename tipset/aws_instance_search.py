#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

This tool is for clean up running instances in all supported regions by keyname/tag

'''
import argparse
import logging
import concurrent.futures
import sys
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Please install boto3")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser('To list/clean up instances cross regions')
    parser.add_argument('--key_name', dest='key_name', action='store',\
        help='specify for owner, seperated by ","', required=False)
    parser.add_argument('--tags', dest='tags', action='store',\
        help='specify for tags, seperated by ","', required=False)
    parser.add_argument('--delete', dest='delete', action='store_true',\
        help='optional, specify for delete instances, otherwise list only', required=False)
    parser.add_argument('-d', dest='is_debug', action='store_true',\
        help='optional, run in debug mode', required=False, default=False)
    parser.add_argument('--skip_region', dest='skip_region', action='store',\
        help='optional skip regions, seperated by ","', required=False, default=None)
    parser.add_argument('--only_region', dest='only_region', action='store',\
        help='optional only regions for checking, seperated by ","', required=False, default=None)
    parser.add_argument('--profile', dest='profile', default='default', action='store',
        help='option, profile name in aws credential config file, default is default', required=False)
    args = parser.parse_args()

    log = logging.getLogger(__name__)
    if args.is_debug:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
    for default_region in ['us-west-2','us-gov-east-1','cn-northwest-1']:
        log.info('Try to init default region:{}'.format(default_region))
        try:
            session = boto3.session.Session(profile_name=args.profile)
            client = session.client('ec2', region_name=default_region)
            region_list = client.describe_regions()
            break
        except ClientError as err:
            log.info(err)
    if args.delete:
        delete_confirm = input("Are you sure want to delete instances found?(yes/no)")
        if 'yes' not in delete_confirm:
            log.info("Please remove --delete if you do not want to delete")
            sys.exit(0)
    for region in region_list['Regions']:
        region_name = region['RegionName']
        if args.skip_region is not None and region_name in args.skip_region:
            log.info('Skip %s', region_name)
            continue
        if args.only_region is not None and region_name not in args.only_region:
            log.info('Skip %s', region_name)
            continue
        log.info("Check %s ", region_name)
        try:
            session = boto3.session.Session(profile_name=args.profile, region_name=region_name)
            client = session.client('ec2', region_name=region_name)
            s = client.describe_instances()
        except Exception as err:
            log.info(err)
            continue
        #log.info(s)
        for instance in s['Reservations']:
            #log.info(instance)
            try:
                if args.key_name is not None:
                    for key_name in args.key_name.split(','):
                        if 'KeyName' in instance['Instances'][0].keys():
                            if key_name in instance['Instances'][0]['KeyName']:
                                instance_id = instance['Instances'][0]['InstanceId']
                                if 'Tags' in instance['Instances'][0].keys():
                                    log.info('Key:%s Tag: %s, LaunchTime: %s id:%s', instance['Instances'][0]['KeyName'],
                                             instance['Instances'][0]['Tags'][0]['Value'], instance['Instances'][0]['LaunchTime'], instance_id )
                                else:
                                    log.info('Key:%s Tag: N/A LaunchTime: %s id:%s', instance['Instances'][0]['KeyName'],
                                             instance['Instances'][0]['LaunchTime'], instance_id )
                                if args.delete:
                                    session = boto3.session.Session(profile_name=args.profile, region_name=region_name)
                                    ec2 = session.resource('ec2', region_name=region_name)
                                    vm = ec2.Instance(instance_id)
                                    vm.terminate()
                                    log.info('%s terminated', instance_id)
                if args.tags is not None:
                    for tag in args.tags.split(','):
                        if 'Tags' in instance['Instances'][0].keys():
                            for val  in instance['Instances'][0]['Tags'][0].values():
                                if tag in val:
                                    instance_id = instance['Instances'][0]['InstanceId']
                                    log.info('Key:%s Tag: %s, LaunchTime: %s id:%s', instance['Instances'][0]['KeyName'],
                                             instance['Instances'][0]['Tags'][0]['Value'], instance['Instances'][0]['LaunchTime'], instance_id )
                                    if args.delete:
                                        session = boto3.session.Session(profile_name=args.profile, region_name=region_name)
                                        ec2 = session.resource('ec2', region_name=region_name)
                                        vm = ec2.Instance(instance_id)
                                        vm.terminate()
                                        log.info('%s terminated', instance_id)
            except KeyError as err:
                log.info("No such words found %s", err)

if __name__ == '__main__':
    main()
