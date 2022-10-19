'''This lambda retireves the count of propagated vpn routes of the mccz transit gateway route table
   and pushes the same as the cloudwatch custom metric'''

import os
import logging
from datetime import datetime
import boto3

# Environment variables
CW_METRIC_NAMESPACE = os.environ["CW_METRIC_NAMESPACE"]  # 'ato'
# 'tgw_route_tbl_routes_count_prod'
CW_METRIC_PROD = os.environ["CW_METRIC_PROD"]
# 'tgw_route_tbl_routes_count_nonprod'
CW_METRIC_NONPROD = os.environ["CW_METRIC_NONPROD"]

# Logger
logLevel = os.environ["LOG_LEVEL"]
logger = logging.getLogger()
logger.setLevel(logLevel)


def get_tgw_rt_vpn_propagated_routes_count(tgw_route_table_id):
    '''Get the routes for the transit gateway for route_type=Propagated & resource_type=VPN'''
    client = boto3.client('ec2')
    response = client.search_transit_gateway_routes(
        TransitGatewayRouteTableId=tgw_route_table_id,
        Filters=[
            {
                'Name': 'resource-type',
                'Values': [
                    'vpn',
                ]
            },
            {
                'Name': 'type',
                'Values': [
                    'propagated',
                ]
            },
        ],
    )
    logger.info("count of routes of TransitGatewayRouteTableId: %s is %s",
                tgw_route_table_id, len(response["Routes"]))
    return len(response["Routes"])


def put_metric_data(namespace, metric_name, tgw_route_table_id, value):
    '''Puts custom metric data in cloudwatch, also create custom metric if not present'''
    client = boto3.client('cloudwatch')
    client.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                'MetricName': metric_name,
                'Dimensions': [
                    {
                        'Name': 'tgw_route_table_id',
                        'Value': tgw_route_table_id
                    },
                ],
                'Timestamp': datetime.now(),
                'Value': value,
                'Unit': 'Count',
            },
        ]
    )
    logger.info(
        'Successfully published %s metric in %s namespace with value = %s',
        metric_name, namespace, value
    )


def lambda_handler(_event, _context):
    '''Lambda handler'''
    # Prod Alarms
    mccz_tgw_route_table_id_prod = os.environ["MCCZ_TGW_ROUTE_TABLE_ID_PROD"]
    count_prod = get_tgw_rt_vpn_propagated_routes_count(
        mccz_tgw_route_table_id_prod)
    put_metric_data(CW_METRIC_NAMESPACE, CW_METRIC_PROD,
                    mccz_tgw_route_table_id_prod, count_prod)

    # Non-prod alarms
    mccz_tgw_route_table_id_nonprod = os.environ["MCCZ_TGW_ROUTE_TABLE_ID_NONPROD"]
    count_nonprod = get_tgw_rt_vpn_propagated_routes_count(
        mccz_tgw_route_table_id_nonprod)
    put_metric_data(CW_METRIC_NAMESPACE, CW_METRIC_NONPROD, mccz_tgw_route_table_id_nonprod,
                    count_nonprod)
