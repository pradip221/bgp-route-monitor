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
sns = boto3.client('sns')


def get_vpc_propagated_routes_from_tgw(tgw_route_table_id):
    '''Get the routes for the transit gateway for route_type=Propagated & resource_type=VPC'''
    client = boto3.client('ec2')

    response = client.search_transit_gateway_routes(
        TransitGatewayRouteTableId=tgw_route_table_id,
        Filters=[
            {
                'Name': 'resource-type',
                'Values': [
                    'vpc',
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
    logger.debug("Routes of TransitGatewayRouteTableId: %s is %s",
                tgw_route_table_id, response["Routes"])
    tgw_routes_dict = massage_tgw_data(tgw_route_table_id, response["Routes"])
    return tgw_routes_dict

def massage_tgw_data(tgw_route_table_id, tgw_routes):
    '''Convert the records from transit gateway route table into a Dictionary.
    Keys of the Dictionary are the combination of DestinationCidrBlock, ResourceId,
    TransitGatewayAttachmentId & ResourceType, seperated by #'''
    tgw_routes_dict = dict()
    for route in tgw_routes:
        tgw_attachments = route['TransitGatewayAttachments']
        for tgw_attachment in tgw_attachments:
            #pylint: disable=[C0303:line-too-long]
            key = route['DestinationCidrBlock'] + "#" + tgw_attachment['ResourceId'] + "#" + tgw_attachment['TransitGatewayAttachmentId'] + "#" + tgw_attachment['ResourceType']
            item = {
                'HashKey': tgw_route_table_id,
                'SortKey': key,
                'DestinationCidrBlock': route['DestinationCidrBlock'],
                'TransitGatewayAttachmentId': tgw_attachment['TransitGatewayAttachmentId'],
                'ResourceType': tgw_attachment['ResourceType'],
                'RouteType': route['Type'],
                'State': route['State'],
            }
            logger.debug("massage_tgw_data:item:: %s", item)
            tgw_routes_dict[key] = item
    return tgw_routes_dict

def get_vpc_propagated_routes_from_ddb_table(table_name, tgw_route_table_id):
    '''Fetches the list of records by HashKey (tgw_route_table_id)'''
    logger.info("table_name:: %s, hash_key:: %s",
                table_name, tgw_route_table_id)

    table = dynamodb.Table(table_name)
    records = table.query(
        KeyConditionExpression=Key('HashKey').eq(tgw_route_table_id)
    )
    logger.debug('records:: %s', records)
    records_dict = massage_table_data(records['Items'])
    return records_dict

def massage_table_data(records):
    '''Convert the records from DynamoDB table into a Dictionary.
    Keys of the Dictionary are the SortKeys of the table records'''
    records_dict = dict()
    for record in records:
        key = record['SortKey']
        value = {
            'HashKey': record['HashKey'],
            'SortKey': key,
        }
        logger.debug("massage_table_data:value:: %s", value)
        records_dict[key] = value
    return records_dict

def compare_tgw_and_table_data(tgw_routes_dict, records_dict):
    '''compare the list of data from transit gateway route table & the same from DynamoDB table
    to identify the new routes added in route table since last execution of the lambda
    or to identify the removed routes from route table which needs cleanup in the DynamoDB table'''
    tgw_routes_dict_keys = set(tgw_routes_dict.keys())
    records_dict_keys = set(records_dict.keys())

    new_keys = tgw_routes_dict_keys - records_dict_keys
    logger.info("new_keys to be added:: %s", new_keys)
    new_routes = [tgw_routes_dict[key] for key in new_keys]

    removed_keys = records_dict_keys - tgw_routes_dict_keys
    logger.info("removed_keys to be deleted:: %s", removed_keys)
    removed_routes = [records_dict[key] for key in removed_keys]

    return new_routes, removed_routes


def upsert_vpc_routes(table_name, new_routes, removed_routes):
    '''Write Adds the new routes identified into the DynamoDB table
    or cleanup invalid entries in table
    '''
    logger.debug("table_name: %s, new_routes: %s, removed_routes: %s",
                    table_name, new_routes, removed_routes)

    table = dynamodb.Table(table_name)

    if new_routes:
        for item in new_routes:
            table.put_item(Item=item)
        logger.info("%s new routes been inserted into the %s", len(new_routes), table_name)
    else:
        logger.info("No new routes to be inserted into the %s", table_name)

    if removed_routes:
        for item in removed_routes:
            table.delete_item(Key=item)
        logger.info("%s removed routes been deleted from the %s", len(removed_routes), table_name)
    else:
        logger.info("No routes to be deleted from the %s", table_name)

def format_message(new_routes, env):
    '''Prepares the messgae & subject to publish to SNS'''
    subject = f"New VPC routes have been propagated to mccz-{env}-tgw-route-table"
    message = f'New VPC routes have been propagated to mccz-{env}-tgw-route-table.'
    message += '''
    ------------------------------------------------------------------------------------
    Details:
    ------------------------------------------------------------------------------------
    '''
    for route in new_routes:
        args = {
            'destinationCidrBlock': route['DestinationCidrBlock'],
            'transitGatewayAttachmentId': route['TransitGatewayAttachmentId'],
            'resourceType': route['ResourceType'],
            'routeType': route['RouteType'],
            'state': route['State']
        }
        details = '''
    DestinationCidrBlock            :   {destinationCidrBlock}
    TransitGatewayAttachmentId      :   {transitGatewayAttachmentId}
    ResourceType                    :   {resourceType}
    RouteType                       :   {routeType}
    State                           :   {state}
    ------------------------------------------------------------------------------------
    '''.format(**args)
        message += details

    return subject, message

def send_message(new_routes, env):
    '''Sends the message to the SNS Topic'''
    if new_routes:
        subject, message = format_message(new_routes, env)
        logger.info('subject: %s', subject)
        logger.info('message: %s', message)
        response = sns.publish(
            TargetArn=os.environ['SNS_TOPIC_ARN'],
            Message=message,
            Subject=subject
        )
        logger.info('sns response: %s', response)

def lambda_handler(_event, _context):
    '''Lambda handler'''
    table_name = os.environ['TABLE_MCCZ_VPC_ROUTES']
    logger.info("table_name: %s", table_name)

    envs = ['prod', 'nonprod']
    for env in envs:
        # Get the mccz-{env}-tgw-route-table_id from environment variable
        mccz_tgw_route_table_id = os.environ[f"MCCZ_TGW_ROUTE_TABLE_ID_{env.upper()}"]

        # Fetch the list of VPC propagated routes from mccz-{env}-tgw-route-table
        tgw_routes_dict = get_vpc_propagated_routes_from_tgw(mccz_tgw_route_table_id)

        # Fetch the list of routes from DynamoDB
        records_dict = get_vpc_propagated_routes_from_ddb_table(table_name, mccz_tgw_route_table_id)

        # Compare the data from route_table & DynamoDB & identify
        # new routes added / invalid route entries in DDB table
        new_routes, removed_routes = compare_tgw_and_table_data(tgw_routes_dict, records_dict)

        # Add new routes/ delete invalid route entries in DDB table
        upsert_vpc_routes(table_name, new_routes, removed_routes)

        #Send SNS notification about the new routes added
        send_message(new_routes, env)

    logger.info("Lambda execution completed successfully...")
