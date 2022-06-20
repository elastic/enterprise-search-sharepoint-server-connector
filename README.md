![](logo-enterprise-search.png)

[Elastic Enterprise Search](https://www.elastic.co/guide/en/enterprise-search/current/index.html) | [Elastic Workplace Search](https://www.elastic.co/guide/en/workplace-search/current/index.html)

# SharePoint Server connector package

Use this _Elastic Enterprise Search SharePoint Server connector package_ to deploy and run a SharePoint Server connector on your own infrastructure. The connector extracts and syncs data from a [Microsoft 365 SharePoint Server](https://docs.microsoft.com/en-us/sharepoint/sharepoint-server) service or tenant. The data is indexed into a Workplace Search content source within an Elastic deployment.

ℹ️ _This connector package requires a compatible Elastic subscription level._
Refer to the Elastic subscriptions pages for [Elastic Cloud](https://www.elastic.co/subscriptions/cloud) and [self-managed](https://www.elastic.co/subscriptions) deployments.

**Table of contents:**

- [Setup and basic usage](#setup-and-basic-usage)
  - [Gather SharePoint Server details](#gather-sharepoint-server-details)
  - [Gather Elastic details](#gather-elastic-details)
  - [Create a Workplace Search API key](#create-a-workplace-search-api-key)
  - [Create a Workplace Search content source](#create-a-workplace-search-content-source)
  - [Choose connector infrastructure and satisfy dependencies](#choose-connector-infrastructure-and-satisfy-dependencies)
  - [Install the connector](#install-the-connector)
  - [Configure the connector](#configure-the-connector)
  - [Test the connection](#test-the-connection)
  - [Sync data](#sync-data)
  - [Log errors and exceptions](#log-errors-and-exceptions)
  - [Schedule recurring syncs](#schedule-recurring-syncs)
- [Troubleshooting](#troubleshooting)
  - [Troubleshoot extraction](#troubleshoot-extraction)
  - [Troubleshoot syncing](#troubleshoot-syncing)
- [Advanced usage](#advanced-usage)
  - [Customize extraction and syncing](#customize-extraction-and-syncing)
  - [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)
- [Connector reference](#connector-reference)
  - [Data extraction and syncing](#data-extraction-and-syncing)
  - [Sync operations](#sync-operations)
  - [Command line interface (CLI)](#command-line-interface-cli)
  - [Configuration settings](#configuration-settings)
  - [Enterprise Search compatibility](#enterprise-search-compatibility)
  - [SharePoint Server compatibility](#sharepoint-server-compatibility)
  - [Runtime dependencies](#runtime-dependencies)

## Setup and basic usage

Complete the following steps to deploy and run the connector:

1. [Gather SharePoint Server details](#gather-sharepoint-server-details)
1. [Gather Elastic details](#gather-elastic-details)
1. [Create a Workplace Search API key](#create-a-workplace-search-api-key)
1. [Create a Workplace Search content source](#create-a-workplace-search-content-source)
1. [Choose connector infrastructure and satisfy dependencies](#choose-connector-infrastructure-and-satisfy-dependencies)
1. [Install the connector](#install-the-connector)
1. [Configure the connector](#configure-the-connector)
1. [Test the connection](#test-the-connection)
1. [Sync data](#sync-data)
1. [Log errors and exceptions](#log-errors-and-exceptions)
1. [Schedule recurring syncs](#schedule-recurring-syncs)

The steps above are relevant to all users. Some users may require additional features. These are covered in the following sections:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Gather SharePoint Server details

Before deploying the connector, you’ll need to gather relevant details about your SharePoint Server. If you plan to connect to multiple servers or tenants, choose one to use for the initial setup.

First, ensure your SharePoint Server is [compatible](#sharepoint-server-compatibility) with the SharePoint Server connector package.

Then, collect the information that is required to connect to SharePoint Server:

- The address of the SharePoint farm.
- The domain name of the SharePoint Server for NTLM authentication.
- The username the connector will use to log in to SharePoint Server.
- The password the connector will use to log in to SharePoint Server.

ℹ️ The username and password must be the admin account for the SharePoint server.

Later, you will [configure the connector](#configure-the-connector) with these values.

Some connector features require additional details. Review the following documentation if you plan to use these features:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Gather Elastic details

First, ensure your Elastic deployment is [compatible](#enterprise-search-compatibility) with the SharePoint Server connector package.

Next, determine the [Enterprise Search base URL](https://www.elastic.co/guide/en/enterprise-search/current/endpoints-ref.html#enterprise-search-base-url) for your Elastic deployment.

Later, you will [configure the connector](#configure-the-connector) with this value.

You also need a Workplace Search API key and a Workplace Search content source ID. You will create those in the following sections.

If you plan to use document-level permissions, you will also need user identity information. See [Use document-level permissions (DLP)](#use-document-level-permissions-dlp) for details.

### Create a Workplace Search API key

Each SharePoint Server connector authorizes its connection to Elastic using a Workplace Search API key.

Create an API key within Kibana. See [Workplace Search API keys](https://www.elastic.co/guide/en/workplace-search/current/workplace-search-api-authentication.html#auth-token).

### Create a Workplace Search content source

Each SharePoint Server connector syncs data from SharePoint Server into a Workplace Search content source.

Create a content source within Kibana:

1. Navigate to **Enterprise Search** → **Workplace Search** → **Sources** → **Add Source** → **SharePoint Server**.
1. Choose **Configure SharePoint Server**.

Record the ID of the new content source. This value is labeled *Source Identifier* within Kibana. Later, you will [configure the connector](#configure-the-connector) with this value.

**Alternatively**, if you have already deployed a SharePoint Server connector, you can use the connector’s `bootstrap` command to create the content source. See [`bootstrap` command](#bootstrap-command).

### Choose connector infrastructure and satisfy dependencies

After you’ve prepared the two services, you are ready to connect them.

Provision a Windows, MacOS, or Linux server for your SharePoint Server connectors.

The infrastructure must provide the necessary runtime dependencies. See [Runtime dependencies](#runtime-dependencies).

Clone or copy the contents of this repository to your infrastructure.

### Install the connector

After you’ve provisioned infrastructure and copied the package, use the provided `make` target to install the connector:

```shell
make install_package
```

This command runs as the current user and installs the connector and its dependencies.
Note: By Default, the package installed supports Enterprise Search version 8.0 or above. In order to use the connector for older versions of Enterprise Search(less than version 8.0) use the ES_VERSION_V8 argument while running make install_package or make install_locally command:


```shell

make install_package ES_VERSION_V8=no

```

ℹ️ Within a Windows environment, first install `make`:

```
winget install -e --id GnuWin32.Make
```

Next, ensure the `ees_sharepoint` executable is on your `PATH`. For example, on macOS:

```shell
export PATH=/Users/shaybanon/Library/Python/3.8/bin:$PATH
```

The following table provides the installation location for each operating system:

| Operating system | Installation location                                        |
| ---------------- | ------------------------------------------------------------ |
| Linux            | `./local/bin`                                                |
| macOS            | `/Users/<user_name>/Library/Python/3.8/bin`                  |
| Windows          | `\Users\<user_name>\AppData\Roaming\Python\Python38\Scripts` |

### Configure the connector

You must configure the connector to provide the information necessary to communicate with each service. You can provide additional configuration to customize the connector for your needs.

Create a [YAML](https://yaml.org/) configuration file at any pathname. Later, you will include the [`-c` option](#-c-option) when running [commands](#command-line-interface-cli) to specify the pathname to this configuration file.

_Alternatively, in Linux environments only_, locate the default configuration file created during installation. The file is named `sharepoint_server_connector.yml` and is located within the `config` subdirectory where the package files were installed. See [Install the connector](#install-the-connector) for a listing of installation locations by operating system. When you use the default configuration file, you do not need to include the `-c` option when running commands.

After you’ve located or created the configuration file, populate each of the configuration settings. Refer to the [settings reference](#configuration-settings). You must provide a value for all required settings.

Use the additional settings to customize the connection and manage features such as document-level permissions. See:

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

### Test the connection

After you’ve configured the connector, you can test the connection between Elastic and SharePoint Server. Use the following `make` target to test the connection:

```shell
make test_connectivity
```

### Sync data

After you’ve confirmed the connection between the two services, you are ready to sync data from SharePoint to Elastic.

The following table lists the available [sync operations](#sync-operations), as well as the [commands](#command-line-interface-cli) to perform the operations.

| Operation                             | Command                                         |
| ------------------------------------- | ----------------------------------------------- |
| [Incremental sync](#incremental-sync) | [`incremental-sync`](#incremental-sync-command) |
| [Full sync](#full-sync)               | [`full-sync`](#full-sync-command)               |
| [Deletion sync](#deletion-sync)       | [`deletion-sync`](#deletion-sync-command)      |
| [Permission sync](#permission-sync)   | [`permission-sync`](#permission-sync-command)   |

Begin syncing with an *incremental sync*. This operation begins [extracting and syncing content](#data-extraction-and-syncing) from SharePoint Server to Elastic. If desired, [customize extraction and syncing](#customize-extraction-and-syncing) for your use case.

Review the additional sync operations to learn about the different types of syncs. Additional configuration is required to use [document-level permissions](#use-document-level-permissions-dlp).

You can use the command line interface to run sync operations on demand, but you will likely want to [schedule recurring syncs](#schedule-recurring-syncs).

### Log errors and exceptions

The various [sync commands](#command-line-interface-cli) write logs to standard output and standard error.

To persist logs, redirect standard output and standard error to a file. For example:

```shell
ees_sharepoint -c ~/config.yml incremental-sync >>~/incremental-sync.log 2>&1
```

You can use these log files to implement your own monitoring and alerting solution.

Configure the log level using the [`log_level` setting](#log_level).

### Schedule recurring syncs

Use a job scheduler, such as `cron`, to run the various [sync commands](#command-line-interface-cli) as recurring syncs.

The following is an example crontab file:

```crontab
0 */2 * * * ees_sharepoint -c ~/config.yml incremental-sync >>~/incremental-sync.log 2>&1
0 0 */2 * * ees_sharepoint -c ~/config.yml full-sync >>~/full-sync.log 2>&1
0 * * * * ees_sharepoint -c ~/config.yml deletion-sync >>~/deletion-sync.log 2>&1
*/5 * * * * ees_sharepoint -c ~/config.yml permission-sync >>~/permission-sync.log 2>&1
```

This example redirects standard output and standard error to files, as explained here: [Log errors and exceptions](#log-errors-and-exceptions).

Use this example to create your own crontab file. Manually add the file to your crontab using `crontab -e`. Or, if your system supports cron.d, copy or symlink the file into `/etc/cron.d/`.

## Troubleshooting

To troubleshoot an issue, first view your [logged errors and exceptions](#log-errors-and-exceptions).

Use the following sections to help troubleshoot further:

- [Troubleshoot extraction](#troubleshoot-extraction)
- [Troubleshoot syncing](#troubleshoot-syncing)

If you need assistance, use the Elastic community forums or Elastic support:

- [Enterprise Search community forums](https://discuss.elastic.co/c/enterprise-search/84)
- [Elastic Support](https://support.elastic.co)

### Troubleshoot extraction

The following sections provide solutions for content extraction issues.

#### Issues extracting content from attachments

The connector uses the [Tika module](https://pypi.org/project/tika/) for parsing file contents from attachments. [Tika-python](https://github.com/chrismattmann/tika-python) uses Apache Tika REST server. To use this library, you need to have Java 7+ installed on your system as tika-python starts up the Tika REST server in the background.

At times, the TIKA server fails to start hence content extraction from attachments may fail. To avoid this, make sure Tika is running in the background.

#### Issues extracting content from images

Tika Server also detects contents from images by automatically calling Tesseract OCR. To allow Tika to also extract content from images, you need to make sure tesseract is on your path and then restart tika-server in the background (if it is already running). For example, on a Unix-like system, try:

```shell
ps aux | grep tika | grep server # find PID
kill -9 <PID>
```

To allow Tika to extract content from images, you need to manually install Tesseract OCR.

### Troubleshoot syncing

The following sections provide solutions for issues related to syncing.

#### Syncing from SharePoint is delayed

Some of the SharePoint API endpoint responses have a delay of around 15 minutes. The response contains timestamps that are not in sync with the current UTC time. The problem is described in [this issue](https://github.com/SharePoint/sp-dev-docs/issues/5369).

#### Some subsites are not syncing

[Full sync](#full-sync) is the only sync operation that guarantees syncing of all subsites. This limitation is due to a SharePoint issue. A SharePoint parent site is not always updated when its child subsite is created or modified.

## Advanced usage

The following sections cover additional features that are not covered by the basic usage described above.

After you’ve set up your first connection, you may want to further customize that connection or scale to multiple connections.

- [Customize extraction and syncing](#customize-extraction-and-syncing)
- [Use document-level permissions (DLP)](#use-document-level-permissions-dlp)

## Customize extraction and syncing

By default, each connection syncs all [supported SharePoint data](#data-extraction-and-syncing) across all SharePoint site collections.

You can limit which SharePoint site collections are synced. [Configure](#configure-the-connector) the setting [`sharepoint.site_collections`](#sharepointsite_collections-required).

You can also customize which objects are synced, and which fields are included and excluded for each object. [Configure](#configure-the-connector) the setting [`objects`](#objects).

Finally, you can set custom timestamps to control which objects are synced, based on their created or modified timestamps. [Configure](#configure-the-connector) the following settings:

- [`start_time`](#start_time)
- [`end_time`](#end_time)

### Use document-level permissions (DLP)

Complete the following steps to use document-level permissions:

1. Enable document-level permissions
1. Map user identities
1. Sync document-level permissions data

#### Enable document-level permissions

Within your configuration, enable document-level permissions using the following setting: [`enable_document_permission`](#enable_document_permission).

#### Map user identities

Copy to your server a CSV file that provides the mapping of user identities. The file must follow this format:

- First column: SharePoint Server AD username
- Second column: Elastic username

Then, configure the location of the CSV file using the following setting: [`sharepoint_workplace_user_mapping`](#sharepoint_workplace_user_mapping).

#### Sync document-level permissions data

Sync document-level permissions data from SharePoint to Elastic.

The following sync operations include permissions data:

- [Permission sync](#permission-sync)
- [Incremental sync](#incremental-sync)

Sync this information continually to ensure correct permissions. See [Schedule recurring syncs](#schedule-recurring-syncs).

## Connector reference

The following reference sections provide technical details:

- [Data extraction and syncing](#data-extraction-and-syncing)
- [Sync operations](#sync-operations)
- [Command line interface (CLI)](#command-line-interface-cli)
- [Configuration settings](#configuration-settings)
- [Enterprise Search compatibility](#enterprise-search-compatibility)
- [SharePoint Server compatibility](#sharepoint-server-compatibility)
- [Runtime dependencies](#runtime-dependencies)

### Data extraction and syncing

Each SharePoint Server connector extracts and syncs the following data from SharePoint Server:

- Site Collections
- Sites and Subsites
- Lists
- Items (List Items)
- Attachments
- Drives (Files & Folders)

The connector handles SharePoint pages comprised of various web parts, it extracts content from various document formats, and it performs optical character recognition (OCR) to extract content from images.

You can customize extraction and syncing per connector. See [Customize extraction and syncing](#customize-extraction-and-syncing).

### Sync operations

The following sections describe the various operations to [sync data](#sync-data) from SharePoint Server to Elastic.

#### Incremental sync

Syncs to Enterprise Search all [supported SharePoint data](#data-extraction-and-syncing) *created or modified* since the previous incremental sync.

When [using document-level permissions (DLP)](#use-document-level-permissions-dlp), each incremental sync will also perform a [permission sync](#permission-sync).

Perform this operation with the [`incremental-sync` command](#incremental-sync-command).

#### Full sync

Syncs to Enterprise Search all [supported SharePoint data](#data-extraction-and-syncing) *created or modified* since the configured [`start_time`](#start_time). Continues until the current time or the configured [`end_time`](#end_time).

This is the only sync operation that guarantees syncing of all subsites. This limitation is due to a SharePoint issue. A SharePoint parent site is not always updated when its child subsite is created or modified.

Perform this operation with the [`full-sync` command](#full-sync-command).

#### Deletion sync

Deletes from Enterprise Search all [supported SharePoint data](#data-extraction-and-syncing) *deleted* since the previous deletion sync.

Perform this operation with the [`deletion-sync` command](#deletion-sync-command).

#### Permission sync

Syncs to Enterprise Search all SharePoint document permissions since the previous permission sync.

When [using document-level permissions (DLP)](#use-document-level-permissions-dlp), use this operation to sync all updates to users and groups within SharePoint Server.

Perform this operation with the [`permission-sync` command](#permission-sync-command).

### Command line interface (CLI)

Each SharePoint Server connector has the following command line interface (CLI):

```shell
ees_sharepoint [-c <pathname>] <command>
```

#### `-c` option

The pathname of the [configuration file](#configure-the-connector) to use for the given command.

```shell
ees_sharepoint -c ~/config.yml full-sync
```

#### `bootstrap` command

Creates a Workplace Search content source with the given name. Outputs its ID.

```shell
ees_sharepoint bootstrap --name 'Accounting documents' --user 'shay.banon'
```

See also [Create a Workplace Search content source](#create-a-workplace-search-content-source).

To use this command, you must [configure](#configure-the-connector) the following settings:

- [`enterprise_search.host_url`](#enterprise_searchhost_url-required)
- [`workplace_search.api_key`](#workplace_searchapi_key-required)

And you must provide on the command line any of the following arguments that are required:

- `--name` (required): The name of the Workplace Search content source to create.
- `--user` (optional): The username of the Elastic user who will own the content source. If provided, the connector will prompt for a password. If omitted, the connector will use the configured API key to create the content source.

#### `incremental-sync` command

Performs a [incremental sync](#incremental-sync) operation.

#### `full-sync` command

Performs a [full sync](#full-sync) operation.

#### `deletion-sync` command

Performs a [deletion sync](#deletion-sync) operation.

#### `permission-sync` command

Performs a [permission sync](#permission-sync) operation.

### Configuration settings

[Configure](#configure-the-connector) any of the following settings for a connector:

#### `sharepoint.domain` (required)

The domain name of the SharePoint Server for NTLM authentication.

```yaml
sharepoint.domain: example.com
```

#### `sharepoint.username` (required)

The username of the admin account for the SharePoint Server. See [Gather SharePoint Server details](#gather-sharepoint-server-details).

```yaml
sharepoint.username: bill.gates
```

#### `sharepoint.password` (required)

The password of the admin account for the SharePoint Server. See [Gather SharePoint Server details](#gather-sharepoint-server-details).

```yaml
sharepoint.password: 'L,Ct%ddUvNTE5zk;GsDk^2w)(;,!aJ|Ip!?Oi'
```

#### `sharepoint.host_url` (required)

The address of the SharePoint farm. The port should represent the web application containing the site collections, not Central Administration.

```yaml
sharepoint.host_url: https://example.com:14682/
```

#### `sharepoint.site_collections` (required)

Specifies which SharePoint site collections to sync to Enterprise Search.

```yaml
sharepoint.site_collections:
  - Sales
  - Marketing
```

#### `workplace_search.api_key` (required)

The Workplace Search API key. See [Create a Workplace Search API key](#create-a-workplace-search-api-key).

```yaml
workplace_search.api_key: 'zvksftxrudcitxa7ris4328b'
```

#### `workplace_search.source_id` (required)

The ID of the Workplace Search content source. See [Create a Workplace Search content source](#create-a-workplace-search-content-source).

```yaml
workplace_search.source_id: '62461219647336183fc7652d'
```

#### `enterprise_search.host_url` (required)

The [Enterprise Search base URL](https://www.elastic.co/guide/en/enterprise-search/current/endpoints-ref.html#enterprise-search-base-url) for your Elastic deployment.

```yaml
enterprise_search.host_url: https://my-deployment.ent.europe-west1.gcp.elastic-cloud.com:9243
```

Note: While using Elastic Enterprise Search version 8.0.0 and above, port must be specified in [`enterprise_search.host_url`](#enterprise_searchhost_url-required)

#### `enable_document_permission`

Whether the connector should sync [document-level permissions (DLP)](#use-document-level-permissions-dlp) from SharePoint.

```yaml
enable_document_permission: Yes
```

By default, it is set to `Yes` i.e. by default the connector will try to sync document-level permissions.

#### `objects`

Specifies which SharePoint objects to sync to Enterprise Search, and for each object, which fields to include and exclude. When the include/exclude fields are empty, all fields are synced.

```yaml
objects:
  sites:
    include_fields:
    exclude_fields:
  lists:
    include_fields:
    exclude_fields:
  list_items:
    include_fields:
    exclude_fields:
  drive_items:
    include_fields:
    exclude_fields:
```

#### `start_time`

A UTC timestamp the connector uses to determine which objects to extract and sync from SharePoint. Determines the *starting* point for a [full sync](#full-sync).

```yaml
start_time: 2022-04-01T04:44:16Z
```

By default it is set to 180 days from the current execution time.

#### `end_time`

A UTC timestamp the connector uses to determine which objects to extract and sync from SharePoint. Determines the *stopping* point for a [full sync](#full-sync).

```yaml
end_time: 2022-04-01T04:44:16Z
```

By default, it is set to current execution time.

#### `log_level`

The level or severity that determines the threshold for [logging](#log-errors-and-exceptions) a message. One of the following values:

- `DEBUG`
- `INFO` (default)
- `WARN`
- `ERROR`

```yaml
log_level: INFO
```

By default, it is set to `INFO`.

#### `retry_count`

The number of retries to perform when there is a server error. The connector applies an exponential backoff algorithm to retries.

```yaml
retry_count: 3
```

By default, it is set to `3`.

#### `sharepoint_sync_thread_count`

The number of threads the connector will run in parallel when fetching documents from the SharePoint server. By default, the connector uses 5 threads.

```yaml
sharepoint_sync_thread_count: 5
```

#### `enterprise_search_sync_thread_count`

The number of threads the connector will run in parallel when indexing documents to the Enterprise Search instance. By default, the connector uses 5 threads.

```yaml
enterprise_search_sync_thread_count: 5
```

For a Linux distribution with at least 2 GB RAM and 4 vCPUs, you can increase thread counts— if the overall CPU and RAM are underutilized, i.e. below 60-70%.

#### `sharepoint_workplace_user_mapping`

The pathname of the CSV file containing the user identity mappings for [document-level permissions (DLP)](#use-document-level-permissions-dlp).

```yaml
sharepoint_workplace_user_mapping: 'C:/Users/banon/sharepoint_1/identity_mappings.csv'
```

#### Enterprise Search compatibility

The SharePoint Server connector package is compatible with Elastic deployments that meet the following criteria:

- Elastic Enterprise Search version greater than or equal to 7.13.0.
- An Elastic subscription that supports this feature. Refer to the Elastic subscriptions pages for [Elastic Cloud](https://www.elastic.co/subscriptions/cloud) and [self-managed](https://www.elastic.co/subscriptions) deployments.

#### SharePoint Server compatibility

The SharePoint Server connector package is compatible with the following versions of SharePoint Server:

- SharePoint Server 2013
- SharePoint Server 2016
- SharePoint Server 2019

#### Runtime dependencies

Each SharePoint Server connector requires a runtime environment that satisfies the following dependencies:

- Windows, MacOS, or Linux server. The connector has been tested with CentOS 7, MacOS Monterey v12.0.1, and Windows 10.
- Python version 3.6 or later.
- To extract content from images: Java version 7 or later, and [`tesseract` command](https://github.com/tesseract-ocr/tesseract) installed and added to `PATH`
- To schedule recurring syncs: a job scheduler, such as `cron`
