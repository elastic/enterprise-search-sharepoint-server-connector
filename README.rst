.. image:: https://github.com/elastic/enterprise-search-sharepoint-server-connector/blob/main/logo-enterprise-search.png
    :alt: Elastic Enterprise Search 
    
Enterprise Search | Workplace Search | SharePoint Server Connector
===================================================

SharePoint Server is a collaboration platform in the Microsoft 365 solution suite which is often used as a centralized content management system.
The SharePoint Server connector provided with Workplace Search automatically synchronizes and enables searching over following items:

* Site Collections
* Sites and Subsites
* Lists 
* Items (List Items)
* Attachments
* Drives (Files & Folders)

If you have a multi-tenant environment, configure one connector instance for each of the tenants / web-applications. 

This connector supports SharePoint Server versions: 2013, 2016 and 2019

Note: The SharePoint Server Connector is a **beta** feature. Beta features are subject to change and are not covered by the support SLA of general release (GA) features. Elastic plans to promote this feature to GA in a future release. 

Requirements
------------

This connector requires:

* Python >= 3.6
* Workplace Search >= 7.13.0 and a Platinum+ license.
* Java 7 or higher
* SharePoint Server 2013, 2016 or 2019 
* Windows, MacOS or Linux Server (Latest tests occurred on CentOS 7, MacOS (Monterey v12.0.1), &  Windows 10) 

Installation
------------

This connector is a python package that can be installed as a package locally::

    make install_package

This will install all pre-requisites for the package and the package itself for the current user.
In case you use a specific command to run python files, such as 'py', you can add `PYTHON=py` in the above command ::

    make PYTHON_CMD=py install_package 

By default, it uses the command 'python3'

Note: If you are running the connector on a Windows environment, you need to install 'make' from the command Prompt via ::

    winget install make

Further, provide the path of ees_sharepoint executable in the environment variables, if not available. By default, the package is installed in following paths:

MacOS: '/Users/<user_name>/Library/Python/3.8/bin'
Linux: './local/bin'
Windows: '\Users\<user_name>\AppData\Roaming\Python\Python38\Scripts'

Considering you are using python 3.8

After the package is installed, you can open a new shell and run the connector itself::

    ees_sharepoint <cmd>

<cmd> is the connector command, such as:

- 'bootstrap' to create a content source in Enterprise Search
- 'full-sync' to synchronize all data from SharePoint Server to Enterprise Search
- 'incremental-sync' to synchronize recent data from SharePoint Server to Enterprise Search
- 'deletion-sync' to remove from Enterprise Search the data recently deleted from SharePoint Server
- 'permission-sync' to synchronize permissions of the users from SharePoint Server Enterprise Search

The connector will install the supplied sharepoint_server_connector.yml file into the package data files and use it when run without the -c option.
You can either edit supplied sharepoint_server_connector.yml file **before** installing the package, or run the connector with '-c <FILE_NAME>' pointing
to the config file you're willing to use, for example::

    ees_sharepoint -c ~/server-1-sharepoint_server_connector.yml full-sync

Note: -c option is optional only for Linux environments. For Windows and MacOS the user needs to provide the config file via -c option.

In Linux, By default the connector will put its default config file into a `config` directory along the executable. To find the config file
you can run 'which ees_sharepoint' to see where the executable of the connector is, then run 'cd ../config' and you'll find yourself
in the directory with a default 'sharepoint_server_connector.yml' file.

Bootstrapping
-------------

Before indexing can begin, you need a new content source to index against. You
can either get it by creating a new `custom API source <https://www.elastic.co/guide/en/workplace-search/current/workplace-search-custom-api-sources.html>`_
from the Workplace Search admin dashboard or you can just bootstrap it using the
'bootstrap.py' file. To use 'bootstrap.py', make sure you have specified
'enterprise_search.host_url' and 'workplace_search.api_key' in the
'sharepoint_connector_sharepoint_server_connector.yml' file. Follow the instructions in the Workplace Search guide to `create a Workplace Search API key <https://www.elastic.co/guide/en/workplace-search/current/workplace-search-api-authentication.html#auth-token>`_. 

Run the bootstrap command ::

    ees_sharepoint bootstrap --name <Name of the Content Source> --user <Admin Username>

Here, the parameter 'name' is _required_ while 'user' is _optional_.
You will be prompted to share the user's password if 'user' parameter was specified above. If the parameter 'user' was not specified, the connector would use 'workplace_search.api_key' specified in the configuration file for bootstrapping the content source.

Once the content source is created, the content source ID will be printed on the terminal. You can now move on to modifying the configuration file.

Configuration file
------------------

Required fields in the configuration file:

* sharepoint.domain
* sharepoint.username
* sharepoint.password
* sharepoint.host_url
* workplace_search.api_key
* workplace_search.source_id
* enterprise_search.host_url
* sharepoint.site_collections

Note: The username and password must be of the admin/ system account of the SharePoint server.
The remaining parameters are optional and have a default value.

The field ``site_collections`` specifies the site collections whose contents the user wants to fetch and index.
For Example, if the wants to fetch collections: Collection1, Collection2, he can provide th following in the cofig file::

sharepoint.site_collections: 
    - Collection1
    - Collection2

The field ``object`` Specifies what fields are indexed/excluded in workplace search.
By default all the fields are added if both the ``exclude_fields`` and ``include_fields`` parameter is not specified. 
Example:

objects:
   sites:
        include_fields:
             -id
             -title
        exclude_fields:
             -author
    lists:
        include_fields:
             -GUID


Running the Connector
---------------------

Running a specific functionality as a recurring process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's possible to run the connectors as a cron job. A sample crontab file is provided in the 'cron/connector.example' file.
You can edit and then add it manually to your crontab with 'crontab -e' or if your system supports cron.d copy or symlink it into '/etc/cron.d/' directory.

The connector will emit logs into stdout and stderr, if logs are needed consider simply piping the output of connectors into
desired file, for example the crontab if you've put config file into '~/.config/sharepoint-connector-sharepoint_server_connector.yml' and
want to have logs in '~/' can look like::

    0 */2 * * * ees_sharepoint incremental-sync >> ~/incremental-sync.log 2>&1
    0 0 */2 * * ees_sharepoint full-sync >> ~/full-sync.log 2>&1
    0 * * * * ees_sharepoint deletion-sync >> ~/deletion-sync.log 2>&1
    */5 * * * * ees_sharepoint permission-sync >> ~/permission-sync.log 2>&1

Indexing
========

You are all set to begin synchronizing documents to Workplace Search. Run the 'incremental-sync' command to start the synchronization. Each consecutive run of 'incremental-sync' will restart from the same place where the previous run ended.
If the permission fetching is enabled in the configuration file, incremental sync also handles document level permission fetching from the SharePoint server and ingests the documents with document level permissions. This will replicate document permissions from SharePoint Server to Workplace Search.

Full sync ensures indexing occurs from the 'start_time' provided in the configuration file till the current time of execution. To run full sync, execute the 'full-sync' command.

Note: Indexing of all the subsites is guaranteed only in full sync and not in incremental sync due to an issue in SharePoint, i.e. the parent site does not get updated whenever a subsite inside it is modified. Hence, if we create/modify a subsite, the last updated time of the parent site is not altered.

The connector inherently uses the `Tika module <https://pypi.org/project/tika/>`_ for parsing file contents from attachments. `Tika-python <https://github.com/chrismattmann/tika-python>`_ uses Apache Tika REST server. To use this library, you need to have Java 7+ installed on your system as tika-python starts up the Tika REST server in the background.
Tika Server also detects contents from images by automatically calling Tesseract OCR. To allow Tika to also extract content from images, you need to make sure tesseract is on your path and then restart tika-server in the backgroud(if it is already running), by doing ``ps aux | grep tika | grep server`` and then ``kill -9 <pid>``

Note: To allow Tika to extract content from images, you need to manually install Tesseract OCR.

Sync user permissions
=====================

Run the `permission-sync` command to sync any updates to users and groups in SharePoint Server with Workplace Search
To sync permissions, you need to provide a path of csv file in the config field: ``sharepoint_workplace_user_mapping``. The first column of each row in this csv is the SharePoint Server AD username 
while the second column is the Workplace Search username.

Removing files deleted in SharePoint Server from Enterprise Search
==================================================================

When items are deleted from SharePoint, a separate process is required to update Workplace Search accordingly. Run the 'deletion-sync' command for deleting the records from Workplace Search.

Testing connectivity
====================

You can check the connectivity between the SharePoint server and Workplace Search server. 

Use the following command ::bash

    make test_connectivity

This command will attempt to to:
* check connectivity with Workplace Search
* check connectivity with SharePoint
* test the basic ingestion and deletion to the Workplace Search

Common Issues
=============

1. Some of the SharePoint API endpoint responses have a delay of around 15 minutes.
The response contains timestamps that are not in sync with the current UTC time. Here is the link to the `issue <https://github.com/SharePoint/sp-dev-docs/issues/5369>`_
Hence, you might see a delay in fetching recently created/updated documented from the SharePoint
2. At times, the TIKA server fails to start hence content extraction from attachments may fail. To avoid this, make sure Tika is running in the background.

Where can I go to get help?
===========================

The Enterprise Search team at Elastic maintains this library and are happy to help. Try posting your question to the Elastic Enterprise Search `discuss forums <https://discuss.elastic.co/c/enterprise-search/84>`_. 

If you are an Elastic customer, please contact Elastic Support for assistance.


