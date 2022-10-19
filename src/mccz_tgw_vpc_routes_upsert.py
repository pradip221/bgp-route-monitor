'''This lambda upserts the vpc propagated routes of the mccz transit gateway
   route table (prod/nonprod) in DynamoDB'''

import os
import logging
import boto3
from boto3.dynamodb.conditions import Key


# Logger
logLevel = os.environ["LOG_LEVEL"]
logger = logging.getLogger()
logger.setLevel(logLevel)

dynamodb = boto3.resource('dynamodb')


def get_vpc_propagated_routes(tgw_route_table_id):
    '''Get the routes for the transit gateway for route_type=Propagated & resource_type=VPC'''
    client = boto3.client('ec2')
    
    # response = client.search_transit_gateway_routes(
    #     TransitGatewayRouteTableId=tgw_route_table_id,
    #     Filters=[
    #         {
    #             'Name': 'resource-type',
    #             'Values': [
    #                 'vpc',
    #             ]
    #         },
    #         {
    #             'Name': 'type',
    #             'Values': [
    #                 'propagated',
    #             ]
    #         },
    #     ],
    # )
    response = {
        "Routes": [
            {
                "DestinationCidrBlock": "10.0.2.0/24",
                "TransitGatewayAttachments": [
                    {
                        "ResourceId": "abc",
                        "TransitGatewayAttachmentId": "xyz",
                        "ResourceType": "vpc"
                    }
                ],
                "Type": "static",
                "State": "active"
            },
            {
                "DestinationCidrBlock": "10.1.0.0/24",
                "TransitGatewayAttachments": [
                    {
                        "ResourceId": "abc",
                        "TransitGatewayAttachmentId": "xyz",
                        "ResourceType": "vpc"
                    }
                ],
                "Type": "static",
                "State": "active"
            },
            {
                "DestinationCidrBlock": "10.0.2.0/24",
                "TransitGatewayAttachments": [
                    {
                        "ResourceId": "def",
                        "TransitGatewayAttachmentId": "xyz",
                        "ResourceType": "vpc"
                    }
                ],
                "Type": "static",
                "State": "active"
            },
            {
                "DestinationCidrBlock": "10.0.2.0/24",
                "TransitGatewayAttachments": [
                    {
                        "ResourceId": "abc",
                        "TransitGatewayAttachmentId": "pqr",
                        "ResourceType": "vpc"
                    }
                ],
                "Type": "static",
                "State": "active"
            },
            {
                "DestinationCidrBlock": "10.0.2.0/24",
                "TransitGatewayAttachments": [
                    {
                        "ResourceId": "def",
                        "TransitGatewayAttachmentId": "pqr",
                        "ResourceType": "vpc"
                    }
                ],
                "Type": "static",
                "State": "active"
            },
        ],
        "AdditionalRoutesAvailable": False
    }
    logger.info("Routes of TransitGatewayRouteTableId: %s is %s",
                tgw_route_table_id, response["Routes"])
    return response["Routes"]


def get_vpc_routes_from_dynamodb(table_name, tgw_route_table_id):
    '''Fetches the list of records by HashKey (tgw_route_table_id)'''
    logger.info("table_name:: %s, hash_key:: %s",
                table_name, tgw_route_table_id)

    table = dynamodb.Table(table_name)
    records = table.query(
        KeyConditionExpression=Key('HashKey').eq(tgw_route_table_id)
    )
    logger.debug('records:: %s', records)
    return records['Items']


def batch_upsert_vpc_routes(tgw_route_table_id, vpc_routes):
    '''Write into Forecast DynamoDB table'''
    logger.info("tgw_route_table_id: %s, vpc_routes: %s", tgw_route_table_id, vpc_routes)
    table_name = os.environ['TABLE_MCCZ_VPC_ROUTES']
    logger.info("table_name: %s", table_name)

    table = dynamodb.Table(table_name)
    logger.info("Starting to write to %s", table_name)

    with table.batch_writer() as batch:
        for route in vpc_routes:
            tgw_attachments = route['TransitGatewayAttachments']
            for tgw_attachment in tgw_attachments:
                item = {
                    'HashKey': tgw_route_table_id,
                    'SortKey': route['DestinationCidrBlock'] + "#" + tgw_attachment['ResourceId'] + "#" + tgw_attachment['TransitGatewayAttachmentId'] + "#" + tgw_attachment['ResourceType'],
                    'DestinationCidrBlock': route['DestinationCidrBlock'],
                    'TransitGatewayAttachmentId': tgw_attachment['TransitGatewayAttachmentId'],
                    'ResourceType': tgw_attachment['ResourceType'],
                    'RouteType': route['Type'],
                    'State': route['State'],
                }
                logger.info("item: %s", item)
                batch.put_item(item)

    logger.info(
        "All required rows has been inserted/updated into the %s", table_name)


def lambda_handler(_event, _context):
    '''Lambda handler'''
    # Upsert Prod Entries
    mccz_tgw_route_table_id_prod = os.environ["MCCZ_TGW_ROUTE_TABLE_ID_PROD"]
    vpc_routes_tgw_prod = get_vpc_propagated_routes(mccz_tgw_route_table_id_prod)
    batch_upsert_vpc_routes(mccz_tgw_route_table_id_prod, vpc_routes_tgw_prod)

    # Upsert NonProd Entries
    mccz_tgw_route_table_id_nonprod = os.environ["MCCZ_TGW_ROUTE_TABLE_ID_NONPROD"]
    vpc_routes_tgw_nonprod = get_vpc_propagated_routes(mccz_tgw_route_table_id_nonprod)
    batch_upsert_vpc_routes(mccz_tgw_route_table_id_nonprod, vpc_routes_tgw_nonprod)