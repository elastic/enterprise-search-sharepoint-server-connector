# Workplace Search Sharepoint 2016 Connector #

This connector making the following data available for search:

* Site collections
* Sites in a collection
* Lists 
* Items
* Attachments

Some remaining objects to be covered in the upcoming versions:

* Sub-sites
* Drives

If you have a multi-tenant environment, you need to configure one connector instance for each of the tenants / web-applications.

## Requirements ##

This connector requires:

* Python >= 3.6
* Workplace Search >= 7.13.0 and a Platinum+ license.
* Sharepoint server 2016

## Bootstrapping ##

Before indexing can begin, you need a new content source to index against. You can either get it by creating a new custom api source from the admin UI of the Workplace Search Account or you can just bootstrap it using the bootstrap.py file. To do this, run the bootstrap command:
```bash
python3 bootstrap.py --host <Workplace Search Host> --name <Name of Content Source> --user <Admin Username>
```
The bootstrap command will then ask you for the user's password.
Once the content source is created, the ID of the content source is printed on the terminal. You can now move onto modifying the configuration file.

## Configuration file ##

Required fields in the configuration file are:

* sharepoint.client_id
* sharepoint.client_secret
* sharepoint.realm
* sharepoint.host_url
* workplace_search.access_token
* workplace_search.source_id
* enterprise_search.host_url
* sharepoint.site_collections

The remaining parameters have a default value pre-defined inside the code logic. You can either define them according to your requirements in the configuration file or let the connector handle them on its own. 

## Testing ##

Run the run_tests.py file to check the connectivity with Sharepoint and Workplace Search server. 
The file can be run in three different modes:

* Workplace : check connectivity with Workplace Search
* Sharepoint : check connectivity with Sharepoint 
* Ingestion : test the basic ingestion and deletion to the Workplace Search

Use the following command:
```bash
python3 run_tests.py -m <mode>
```
If you do not provide a mode, the connector will run the file for all the modes 

## Indexing ##

Finally, you are all set to begin the indexing to the Workplace Search. Run the python file fetch_index.py. The file will run in intervals and ingest the data from Sharepoint.

If the permission fetching is enabled in the configuration file, fetch_index also handles permission fetching from the Sharepoint server and ingests the documents with document level permissions. This would prevent the users of Workplace Search, who are not having necessary permissions in the Sharepoint server, from accessing the same documents in the Workplace Search.

Once the indexing for an interval is successfully completed, the current execution time is stored in the checkpoint.json file which will be used in the next interval or next invocation of the connector. 

## De-Indexing ##

When items are deleted from Sharepoint, a separate process is required to update Workplace Search accordingly. Run the deindex.py file for deleting the records from the Workplace Search. 
