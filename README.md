# Workplace Search | Sharepoint Server 2016 Connector #

This connector synchronizes and enables searching over following items:

* Site collections
* Sites in a collection
* Lists 
* Items
* Attachments

Support for following items expected in the upcoming versions:

* Sub-sites
* Drives

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

## Indexing ##

You are all set to begin synchronizing document to Workplace Search. Run the python file _fetch_index.py_. The file will run in intervals and ingest the data from SharePoint Server 2016.

If the permission fetching is enabled in the configuration file, fetch_index also handles permission fetching from the SharePoint server and ingests the documents with document level permissions. This would replicate document permissions from SharePoint Server to Workplace Search.

## De-Indexing ##

When items are deleted from SharePoint, a separate process is required to update Workplace Search accordingly. Run the deindex.py file for deleting the records from Workplace Search.

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
