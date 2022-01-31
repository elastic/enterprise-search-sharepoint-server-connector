Workplace Search | Sharepoint Server 2016 Connector
===================================================

This connector synchronizes and enables searching over following items:

* Site collections
* Sites and sub sites
* Lists
* Items (List items)
* Attachments
* Drives items (files and folders)

If you have a multi-tenant environment, you need to configure one connector instance for each of the tenants / web-applications.

Requirements
------------

This connector requires:

* Python >= 3.6
* Workplace Search >= 7.13.0 and a Platinum+ license.
* SharePoint Server 2016

Installation
------------
This connector is a python package that can be installed as a package locally::

    make install_package

This will install all pre-requisites for the package and the package itself for the current user.
After the package is installed, you can open a new shell and run the connector itself::

    ees_sharepoint <cmd>

<cmd> is the connector command, such as:

- bootstrap to create a content source in Enterprise Search
- full-sync to synchronize all data from Sharepoint Server to Enterprise Search
- incremental-sync to synchronize recent data from Sharepoint Server to Enterprise Search
- deletion-sync to remove from Enterprise Search the data recently deleted from Sharepoint Server
- permission-sync to synchronize permissions of the users from Sharepoint Server Enterprise Search

The connector will install supplied config.yml file into the package data files and use it when ran without -c option.
You can either edit supplied config.yml file before installing the package, or run connector with -c <FILE_NAME> pointing
to the config file you're willing to use, for example::

    ees_sharepoint -c ~/server-1-config.yml full-sync

By default the connector will put its default config file into a `config` directory along the executable. To find the config file
you can run `which ees_sharepoint` to see where the executable of the connector is, then run `cd ../config` and you'll find yourself
in the directory with a default `config.yml` file.

Bootstrapping
-------------

Before indexing can begin, you need a new content source to index against. You
can either get it by creating a new [custom API
source](https://www.elastic.co/guide/en/workplace-search/current/workplace-search-custom-api-sources.html)
from Workplace Search admin dashboard or you can just bootstrap it using the
bootstrap.py file. To use bootstrap.py, make sure you have specified
'enterprise_search.host_url' and 'workplace_search.api_key' in the
sharepoint_connector_config.yml file. Run the bootstrap command ::

    ees_sharepoint bootstrap --name <Name of the Content Source> --user <Admin Username>

Here, the parameter 'name' is _required_ while 'user' is _optional_.
You will be prompted to share the user's password if 'user' parameter was specified above. If the parameter 'user' was not specified, the connector would use 'workplace_search.api_key' specified in the configuration file for bootstrapping the content source.

Once the content source is created, the content source ID will be printed on the terminal. You can now move on to modifying the configuration file.

Configuration file
------------------

Required fields in the configuration file:

* sharepoint.client_id
* sharepoint.client_secret
* sharepoint.realm
* sharepoint.host_url
* workplace_search.api_key
* workplace_search.source_id
* enterprise_search.host_url
* sharepoint.site_collections

The remaining parameters are optional and have a default value.

Running the Connector
---------------------

Running a specific functionality as a recurring process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's possible to run the connectors as a cron job. A sample crontab file is provided in `cron/connector.example` file.
You can edit and then add it manually to your crontab with `crontab -e` or if your system supports cron.d copy or symlink it into /etc/cron.d/ directory.

The connector will emit logs into stdout and stderr, if logs are needed consider simply piping the output of connectors into
desired file, for example the crontab if you've put config file into `~/.config/sharepoint-connector-config.yml` and
want to have logs in `~/` can look like::

    0 */2 * * * ees_sharepoint incremental-sync >> ~/incremental-sync.log
    0 0 */2 * * ees_sharepoint full-sync >> ~/full-sync.log
    0 * * * * ees_sharepoint deletion-sync >> ~/deletion-sync.log
    */5 * * * * ees_sharepoint permission-sync >> ~/permission-sync.log

Indexing
========

You are all set to begin synchronizing document to Workplace Search. Run the `incremental-sync` command to start the synchronization. Each consequitive run of `incremental-sync` will restart from the same place where the previous run ended.
If the permission fetching is enabled in the configuration file, incremental sync also handles document level permission fetching from the SharePoint server and ingests the documents with document level permissions. This would replicate document permissions from SharePoint Server to Workplace Search.

Full sync ensures indexing occurs from the _start_time_ provided in the configuration file till the current time of execution. To run full sync, execute the `full-sync` command.

Note: Indexing of all the sub sites is guaranteed only in full sync and not in incremental sync due to an issue in SharePoint, i.e. the parent site does not get updated whenever a subsite inside it is modified. Hence, if we create/modify a sub site, the last updated time of parent site is not altered.

Sync user permissions
=====================

This functionality will sync any updates to the users and groups in the Sharepoint with Workplace. Run the `permission-sync` command to sync user permissions into Workplace Search.

Removing files deleted in Sharepoint Server from Enterprise Search
==================================================================

When items are deleted from SharePoint, a separate process is required to update Workplace Search accordingly. Run the `deletion-sync` command for deleting the records from Workplace Search.

Testing connectivity
====================

You can check the connectivity with Sharepoint and Workplace Search server using.

Use the following command ::bash

    make test_connectivity

This command will attempt to to:
* check connectivity with Workplace Search
* check connectivity with Sharepoint
* test the basic ingestion and deletion to the Workplace Search
