# Workplace Search | Sharepoint Server 2016 Connector #

This connector synchronizes and enables searching over following items:

* Site collections
* Sites and sub sites
* Lists
* Items (List items)
* Attachments
* Drives items (files and folders)

If you have a multi-tenant environment, you need to configure one connector instance for each of the tenants / web-applications.

## Requirements ##

This connector requires:

* Python >= 3.6
* Workplace Search >= 7.13.0 and a Platinum+ license.
* SharePoint Server 2016

## Bootstrapping ##

Before indexing can begin, you need a new content source to index against. You can either get it by creating a new [custom API source](https://www.elastic.co/guide/en/workplace-search/current/workplace-search-custom-api-sources.html) from Workplace Search admin dashboard or you can just bootstrap it using the bootstrap.py file. To use bootstrap.py, make sure you have specified 'enterprise_search.host_url' and 'workplace_search.access_token' in the sharepoint_connector_config.yml file. Run the bootstrap command:
```bash
python3 bootstrap.py --name <Name of the Content Source> --user <Admin Username>
```
Here, the parameter 'name' is _required_ while 'user' is _optional_.
You will be prompted to share the user's password if 'user' parameter was specified above. If the parameter 'user' was not specified, the connector would use 'workplace_search.access_token' specified in the configuration file for bootstrapping the content source.

Once the content source is created, the content source ID will be printed on the terminal. You can now move on to modifying the configuration file.

## Configuration file ##

Required fields in the configuration file:

* sharepoint.client_id
* sharepoint.client_secret
* sharepoint.realm
* sharepoint.host_url
* workplace_search.access_token
* workplace_search.source_id
* enterprise_search.host_url
* sharepoint.site_collections

The remaining parameters are optional and have a default value.

## Running the Connector ##

### Running a specific functionality as a daemon process ###

To run any specific functionality as a daemon process, execute the following command:
```bash
python3 filename.py >/dev/null 2>&1 &
```
For example, if you want to run indexing functionality as a daemon process, simply execute the following command:
```bash
python3 fetch_index.py >/dev/null 2>&1 &
```

### Running multiple functionalities as a daemon process ###

To run the connector with multiple functionalies as a daemon process, execute the following shell script command:
```bash
sh runner.sh >/dev/null 2>&1 &
```
This command will run all the functionalities (full sync, indexing documents, deindexing documents, indexing permissions) parallelly. 

## Indexing ##

You are all set to begin synchronizing document to Workplace Search. Run the python file _fetch_index.py_. The file will run in intervals and ingest the data from SharePoint Server 2016.

If the permission fetching is enabled in the configuration file, fetch_index also handles document level permission fetching from the SharePoint server and ingests the documents with document level permissions. This would replicate document permissions from SharePoint Server to Workplace Search.
The connector has two modes for indexing: incremental and fullsync.
The default mode is incremental sync.
Fullsync on the other hand, ensures indexing occurs from the _start_time_ provided in the configuration file till the current time of execution. To run fullsync, execute the python file _full_sync.py_.

Note: Indexing of all the sub sites is guaranteed only in fullsync and not in incremental sync due to an issue in SharePoint, i.e. the parent site does not get updated whenever a subsite inside it is modified. Hence, if we create/modify a sub site, the last updated time of parent site is not altered.

## Sync user permissions ##

This functionality will sync any updates to the users and groups in the Sharepoint with Workplace

## De-Indexing ##

When items are deleted from SharePoint, a separate process is required to update Workplace Search accordingly. Run the _deindex.py_ file for deleting the records from Workplace Search.

## Testing ##

You can run the automated tests using pytest to check the connectivity with Sharepoint and Workplace Search server. 
The automated test can be run in three different modes:

* workplace : check connectivity with Workplace Search
* sharepoint : check connectivity with Sharepoint 
* ingestion : test the basic ingestion and deletion to the Workplace Search

Use the following command:
```bash
pytest -m <mode>
```
If you do not provide a mode, the connector will run the test for all the modes 