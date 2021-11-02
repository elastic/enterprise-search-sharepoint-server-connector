# Workplace Search Sharepoint 2016 Connector #

The Sharepoint 2016 Connector makes the following data available in the Workplace to search:

* Site collections
* Sites in a collection
* Lists 
* Items
* Attachments

If you have a multi-tenant environment, you need to configure one connector instance for each of the tenants/web applications.

## Requirements ##

This connector requires:

* Python >= 3.6
* Workplace Search >= 7.13.0 and a Platinum+ license.
* Sharepoint Server 2016

## Installing the Connector ##
* Clone the [repository](https://github.com/elastic/workplace-search-sharepoint16-connector) into your local machine
* Make sure to allow Anonymous Access for your Sharepoint server to provide the Connector access to the Sharepoint farm
* Go to the directory where the repository is cloned and install the python dependencies using the following command:
```bash
pip3 install -r requirements.txt
```

## Configuring the Connector ##
Go to sharepoint_connector_config.yaml file and add the details for the following fields to configure and use the connector

Following are the mandatory fields:
* **sharepoint.domain**: The domain name of the sharepoint server for the NTLM authentication
* **sharepoint.username**: The username used to login to the Sharepoint server 
* **sharepoint.password**: The password for the user used to login to the Sharepoint server 
* **sharepoint.host_url**: The address of the sharepoint farm. Example: "http://sharepoint-host:14293/"
* **workplace_search.access_token**: Access token for Workplace search authentication. You can get the Access Token from the source overview from the Workplace
* **workplace_search.source_id**: Source identifier for the custom source created on the workplace search server either via bootstrapping or directly from the Admin UI of the Enterprise Search server
* **enterprise_search.host_url**: Enterprise Search server address. For the on-prem version this will be the IP Address where the server is hosted, e.g. "http://ent-host:3002", and for the cloud version, use the API endpoint specified in the home page of the deployment, e.g. "https://elastic-deployment-name.ent.us-central1.aws.cloud.es.io"
* **sharepoint.site_collections**: Specifies the list of site collections whose contents the user wants to fetch and index.

Following are the optional fields i.e. the connector uses the default values in case the configuration is empty
* **enable_document_permission**: Denotes whether the document level permissions will be replicated or not (e.g. Yes). Default: Yes

* **objects**: Specifies the objects to be fetched and indexed in the WorkPlace search along with fields that need to be included/excluded. The list of the objects supported are sites, lists, and items. You can specify the fields to be included or excluded in the include_fields and exclude_fields under the object name. By default, all the objects are fetched

* **start_time**: The Zulu time after which all the objects that are modified or created are fetched from Sharepoint. By default, all the objects present in the last 180 days in the SharePoint are fetched (e.g. "2021-06-16T13:58:12Z")

* **end_time**: The Zulu time before which all the updated objects need to be fetched i.e. the connector won't fetch any object updated/created after the end_time. By default, all the objects updated/added till the current time are fetched (e.g. "2021-10-24T06:52:22Z")

* **indexing_interval**: The interval in minutes after which the connector looks for new/updated objects from SharePoint, (e.g. 180), The unit of the interval is minutes and by default, the interval is considered to be 60

* **deletion_interval**: The interval in minutes after which the connector looks for the deleted objects from SharePoint, (e.g. 180), The unit of the interval is minutes and by default, the interval is considered to be 60

* **full_sync_interval**: The interval after which the connector fetches all the objects from sharepoint server from a given start_time in the configuration file

* **log_level**: The level of logging in the log files. The possible values include: debug, info, warn, error, (e.g. info). By default, the level is info

* **retry_count**: The number of retries to perform in case of a server error. The connector will use exponential backoff for the retry mechanism, (e.g. 3). By default, the connector retries for 3 times

* **worker_process**: Number of worker processes to be used for indexing/updating documents by the connector. The ideal value should be equal to the number of CPU cores in the machine, (e.g. 4). By default, the number of processes will be equal to the number of CPU cores in the machine

* **sharepoint_workplace_user_mapping**: The absolute path of CSV file containing a mapping of sharepoint user ID to Workplace user ID for permission replication. By default, if no path is specified the connector considers that the Workplace user ID is the same as the Sharepoint user ID

## Bootstrapping ##

Before indexing can begin, you need a new content source to index against. You can either get it by creating a new custom API source from the Admin UI of the Workplace Search Account or you can just bootstrap it using the bootstrap.py file and then configure it in the sharepoint_connector_config.yml file under workplace_search.source_id parameter. To use bootstrap.py, make sure you have specified the 'enterprise_search.host_url' within your sharepoint_connector_config.yaml file and then run the bootstrap command:
```bash
python3 bootstrap.py --name <Name of Content Source> --user <Admin Username>
```
Here, the parameter 'name' is the required one and, the parameter 'user' is optional.
The connector will then ask you for the user's password if the 'user' parameter was specified in the above command. If the parameter 'user' was not specified, the connector would use 'workplace_search.access_token' specified in the configuration file for bootstrapping the content source.

Once the content source is created, the ID of the content source is printed on the terminal.

## Connectivity Tests ##

You can run the automated tests using pytest to check the connectivity with Sharepoint and Workplace Search server. 
The automated test can be run in three different modes:

* workplace: Validates the connectivity with the Enterprise Search server
* sharepoint: Validates the connectivity with the Sharepoint server
* ingestion: Validates the basic ingestion and deletion to the Workplace Search

Use the following command:
```bash
pytest -m <mode>
```
If you do not provide a mode, the connector will run the test for all the modes 

## Indexing ##

Once the connection is assured, you are all set to begin the indexing to the Workplace Search. Run the python file fetch_index.py. The file will run in intervals and ingest the data from Sharepoint.
```bash
python3 fetch_index.py
```

If permission fetching is enabled in the configuration file, fetch_index also handles permission fetching from the Sharepoint server and ingests the documents with document-level permissions. This would prevent the users of Workplace Search, who are not having the necessary permissions in the Sharepoint server, from accessing the same documents in the Workplace Search.

Once the indexing for an interval is successfully completed, the current execution time is stored in the checkpoint.json file which will be used in the next interval or next invocation of the connector. 

## De-Indexing ##

When items are deleted from Sharepoint, a separate process is required to update Workplace Search accordingly. Run the python file deindex.py for deleting the records from the Workplace Search. 
```bash
python3 deindex.py
```
For better efficiency, it is recommended to have the indexing interval is smaller than the deindexing interval in the yaml file

## Troubleshooting ##

The connector actively logs the information in the respective log files in the same directory as the connector is cloned. The connector uses the ECS log format. The user can troubleshoot any error by visiting or searching for errors in the respective log files: 
* Indexing: "sharepoint_connector_index.log"
* De-indexing: "sharepoint_connector_deindex.log"
* Connectivity Tests: "sharepoint_connector_test.log"
* Bootstrapping: "sharepoint_connector_bootstrap.log"

## Limitations ##

* Some of the Sharepoint API endpoint responses have a delay of around 15 minutes. The response contains timestamps that are not in sync with the current UTC time. The [issue](https://github.com/SharePoint/sp-dev-docs/issues/5369) is still open. Hence, you might see a delay in fetching recently created/updated documented from the Sharepoint
* The connector does not index Drives and Sub-Sites in this initial version
