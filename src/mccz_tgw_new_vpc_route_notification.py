'''This lambda upserts the vpc propagated routes of the mccz transit gateway
route table (prod/nonprod) in DynamoDB'''

import os
import logging
import boto3
from boto3.dynamodb.types import TypeDeserializer

# Logger
logLevel = os.environ["LOG_LEVEL"]
logger = logging.getLogger()
logger.setLevel(logLevel)

sns = boto3.client('sns')


def format_message(new_vpc_route):
    '''Prepares the messgae & subject to publish to SNS'''
    type_ds = TypeDeserializer()
    keys = type_ds.deserialize({'M': new_vpc_route['Keys']})
    record = type_ds.deserialize({'M': new_vpc_route['NewImage']})
    record['mccz_tgw_route_table_id'] = keys['HashKey']
    logger.info('formatMessage: %s', record)

    subject = f"A new VPC route propagated to Mccz Tgw Route Table {keys['HashKey']}"

    args = {
        'mcczTgwRouteTableId': keys['HashKey'],
        'destinationCidrBlock': record['DestinationCidrBlock'],
        'transitGatewayAttachmentId': record['TransitGatewayAttachmentId'],
        'resourceType': record['ResourceType'],
        'routeType': record['RouteType'],
        'state': record['State']
    }

    message = '''
    A new VPC route has been propagated to Mccz Tgw Route Table {mcczTgwRouteTableId}.

    ------------------------------------------------------------------------------------
    Details:
    ------------------------------------------------------------------------------------
    RouteTableId                    :   {mcczTgwRouteTableId}
    DestinationCidrBlock            :   {destinationCidrBlock}
    TransitGatewayAttachmentId      :   {transitGatewayAttachmentId}
    ResourceType                    :   {resourceType}
    RouteType                       :   {routeType}
    State                           :   {state}
    ------------------------------------------------------------------------------------
    '''.format(**args)

    return subject, message


def send_message(subject, message):
    '''Sends the message to the SNS Topic'''
    response = sns.publish(
        TargetArn=os.environ['SNS_TOPIC_ARN'],
        Message=message,
        Subject=subject
    )
    logger.info('sns response: %s', response)


def get_new_vpc_route(event):
    '''Get the vpc route information from the dynamodb stream'''
    if not (event and event['Records']
            and event['Records'][0]['eventName'] == 'INSERT'
            and event['Records'][0]['dynamodb']):
        return None
    return event['Records'][0]['dynamodb']


def lambda_handler(event, _context):
    '''Lambda handler'''
    logger.info('event: %s', event)

    # Read the dynamodb stream from event
    new_vpc_route = get_new_vpc_route(event)
    logger.info('new_vpc_route: %s', new_vpc_route)

    if new_vpc_route:
        # Format the stream record to a user-friendly message and send via SNS
        subject, message = format_message(new_vpc_route)
        send_message(subject, message)
    else:
        # Skips any Modify/Remove stream record
        logger.info('No new VPC route identified...')
