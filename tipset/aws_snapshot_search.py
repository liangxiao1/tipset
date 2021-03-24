#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/mini_utils

This tool is for clean up snapshot.

'''
import boto3
import logging
import argparse
import csv
import os
import re


def get_ami_state(ami_id):
    '''
    check ami status if the snapshot was created by creating ami process
    "Created by CreateImage(i-042bxxxxx) for ami-0c20e7d78fee1ed04 from vol-0653xxxxx"
    '''

    ec2 = boto3.resource('ec2')
    try:
        image = ec2.Image('id')
        log.debug("%s found" % ami_id)
        return image.state()
    except:
        log.debug("%s not found, consider it as deleted" % ami_id)
        return "deleted"


def get_instance_state(instance_id):
    '''
    check ami status if the snapshot was created by creating ami process
    "Created by CreateImage(i-042bxxxxx) for ami-0c20e7d78fee1ed04 from vol-0653xxxxx"
    '''

    ec2 = boto3.resource('ec2')
    try:
        instance = ec2.Instance(instance_id)
        log.debug("%s found" % instance_id)
        return instance.state()
    except:
        log.debug("%s not found, consider it as deleted" % instance_id)
        return "deleted"

def get_volume_state(vol_id):
    '''
    check the original volume status
    '''
    #for vol in vols_dict:
    #    if vol_id == vol['VolumeId']:
    #        log.info('Found volume %s' % vol_id)
    #        return vol['State']
    #log.info('Not found volume %s' % vol_id)
    #return 'deleted'

    ec2 = boto3.resource('ec2')
    try:
        volume = ec2.Volume(vol_id)
        log.debug("%s found" % vol_id)
        return volume.state()
    except:
        log.debug("%s not found, consider it as deleted" % vol_id)
        return "deleted"

def del_snapshot(snap_id):
    '''
    check ami status if the snapshot was created by creating ami process
    "Created by CreateImage(i-042bxxxxx) for ami-0c20e7d78fee1ed04 from vol-0653xxxxx"
    '''

    ec2 = boto3.resource('ec2')
    try:
        snapshot = ec2.Snapshot(snap_id)
        snapshot.delete()
        log.info("delete %s", snap_id)
        return True
    except Exception as err:
        log.debug("%s is not deleted as %s", snap_id, err)
        return False

parser = argparse.ArgumentParser('To list/clean up instances cross regions')
parser.add_argument('--owner_id', dest='owner_id',action='store',help='specify owner id, seperated by ","',required=False)
#parser.add_argument('--instance_name', dest='instance_name',action='store',help='specify for instance_name, seperated by ","',required=False)
#parser.add_argument('--tags', dest='tags',action='store',help='specify for tags, seperated by ","',required=False)
parser.add_argument('--ami_list', dest='ami_list',action='store',help='ami_list file, deleted snapshot following it',required=False)
parser.add_argument('--delete', dest='delete',action='store_true',help='optional, specify for delete instances, otherwise list only',required=False)
parser.add_argument('-d', dest='is_debug',action='store_true',help='optional, run in debug mode', required=False,default=False)
parser.add_argument('-c', dest='is_relative',action='store_true',help='optional, check related instance, source volume, target ami information', required=False,default=False)
parser.add_argument('--skip_region', dest='skip_region',action='store',help='optional skip regions, seperated by ","',required=False,default=None)
parser.add_argument('--region', dest='only_region',action='store',help='optional only regions for checking, seperated by ","',required=False,default=None)
args = parser.parse_args()


if __name__ == '__main__':
    log = logging.getLogger(__name__)
    if args.is_debug:
        logging.basicConfig(level=logging.DEBUG,format="%(levelname)s:%(message)s")
    else:
        logging.basicConfig(level=logging.INFO,format="%(levelname)s:%(message)s")
    client = boto3.client('ec2')

    region_list = client.describe_regions()
    if os.path.exists('s.csv'):
        os.unlink('s.csv')
    with open('s.csv','a',newline='') as fh:
        csv_file =csv.writer(fh)
        if args.is_relative:
            csv_file.writerow(['Region','SnapshotId','Description','StartTime','VolumeId','VolumeSize',
            'VolumeState','AMIID','AMIStatus','InstanceID','InstanceStatus','DeletedAble?'])
        else:
            csv_file.writerow(['Region','SnapshotId','Description','StartTime','VolumeId','VolumeSize'])

    for region in region_list['Regions']:
        region_name = region['RegionName']
        if args.skip_region is not None and region_name in args.skip_region:
            log.info('Skip %s' % region_name)
            continue
        if args.only_region is not None and region_name not in args.only_region:
            log.info('Skip %s' % region_name)
            continue
        log.info("Check %s " % region_name)
        try:
            client = boto3.client('ec2',region_name=region_name)
            if args.owner_id is not None:
                snaps_dict = client.describe_snapshots(OwnerIds=[args.owner_id])
            else:
                snaps_dict = client.describe_snapshots()
            #the time is not acceptable to dump all images one time
            #if args.is_relative:
            #    log.info("Get images information")
            #    images_dict = client.describe_images()['Images']
            #    log.info("Get instances information")
            #    instances_dict = client.describe_instances()['Reservations']
            #    log.info("Get volumes information")
            #    vols_dict = client.describe_volumes()['Volumes']

        except Exception as err:
            log.info(err)
            continue
        log.debug(snaps_dict)

        for snap in snaps_dict['Snapshots']:
            log.info(snap)
            with open('s.csv','a',newline='') as fh:
                csv_file =csv.writer(fh)
                if args.is_relative:
                    ami_id = 'not found'
                    ami_state = 'unknow'
                    instance_id = 'not found'
                    instance_state = 'unknow'
                    if args.ami_list is not None:
                        with open(args.ami_list,'r') as fh:
	                        ami_list = map(lambda x: x.rstrip('\n'), fh.readlines())
                        log.info("Loaded addtional ami_list for delete existing snapshot!")
                        log.debug(ami_list)

                    vol_state = get_volume_state(snap['VolumeId'])
                    if 'Created by CreateImage' in snap['Description']:
                        ami_id = re.findall("ami-[\d\w]*", snap['Description'])[0]
                        ami_state = get_ami_state(ami_id)
                        if args.ami_list is not None:
                            if ami_id in ami_list:
                                del_snapshot(snap['SnapshotId'])
                        instance_id = re.findall("i-[\d\w]*", snap['Description'])[0]
                        instance_state = get_ami_state(instance_id)
                    if vol_state == 'deleted' and ami_state == 'deleted' and instance_state == 'deleted':
                        log.info('Relatvive AMI, source volume, instance are all deleted, this vol maybe can deleted too!')
                        is_delete = 'Y'
                    else:
                        is_delete = 'N'
                    csv_file.writerow([region_name, snap['SnapshotId'],snap['Description'],snap['StartTime'],
                    snap['VolumeId'],snap['VolumeSize'],vol_state,ami_id,ami_state,instance_id,instance_state,is_delete])
                else:
                    csv_file.writerow([region_name, snap['SnapshotId'],snap['Description'],snap['StartTime'],
                    snap['VolumeId'],snap['VolumeSize']])
