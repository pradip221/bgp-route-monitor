# mccz-tgw-alarms

This repository configure cloudwatch alarms when new VPC routes are propagated to mccz transit gateways OR the count of total VPN propagted routes breaches the thresold.

## Architecture
The repo is used for the following use cases - 

### Raise CW Alarms when VPN propagated routes in the mccz-tgw-route-table breaches thresold

- tgw_rt_routes_count - Lambda function to raise CW alarms when the count of total VPN propagted routes breaches the thresold. This is scheduled to run every 5 min and pushes the count of VPN propagted routes in mccz transit gateway for both prod & nonprod into 2 cloudwatch metrics - 'tgw_route_tbl_routes_count_prod' and 'tgw_route_tbl_routes_count_nonprod' respectivately, under the namepsace - 'ato'.
- TgwRouteTblRoutesCountProdAlarm - Cloudwatch alarm which notifies to AlarmNotificationTopic when thresold is breached for 'tgw_route_tbl_routes_count_prod'
- TgwRouteTblRoutesCountNonProdAlarm - Cloudwatch alarm which notifies to AlarmNotificationTopic when thresold is breached for 'tgw_route_tbl_routes_count_nonprod'

### Send SNS notification when a new VPC route is propagated into the mccz-tgw-route-table

- mccz_tgw_vpc_routes_upsert - Lambda function to retrieve the VPC propagated routes of the mccz-tgw-route-table and write them into DynamoDB 
- McczVpcRoutes - DynamoDB tables for Prod & nonProd entries of the VPC propagated routes
- mccz_tgw_new_vpc_route_notification - Lambda function which is inovked by the dynamodb stream and sends SNS notification for any new VPC propagated route entry

## Repo Structure 
- src - Code for the Lambda function
- events - Scheduled cloudwatch events that can be used to invoke the lambda functions
- tests - place to put any unit/integration tests
- template.yaml - A template that defines the application's AWS resources

## Pre-requisites

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3.9 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

## Build & Deploy
To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

## Use the SAM CLI to build and test locally

Build your application with the `sam build --use-container` command. The SAM CLI installs dependencies defined in `src/requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

```bash
mccz-tgw-alarms$ sam build --use-container
```

Test a single function by invoking it directly with a test event. An event is a JSON document that represents the input that the function receives from the event source. Test events are included in the `events` folder in this project.

Run functions locally and invoke them with the `sam local invoke` command.

```bash
mccz-tgw-alarms$ sam local invoke TgwRtRoutesCountFunction --event events/event_tgw_rt_routes_count.json
```

## Tests

Tests are defined in the `tests` folder in this project. Use PIP to install the test dependencies and run tests.

```bash
mccz-tgw-alarms$ pip install -r tests/requirements.txt --user
# unit test
mccz-tgw-alarms$ python -m pytest tests/unit -v
# integration test, requiring deploying the stack first.
# Create the env variable AWS_SAM_STACK_NAME with the name of the stack we are testing
mccz-tgw-alarms$ AWS_SAM_STACK_NAME=<stack-name> python -m pytest tests/integration -v
```

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name mccz-tgw-alarms
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
