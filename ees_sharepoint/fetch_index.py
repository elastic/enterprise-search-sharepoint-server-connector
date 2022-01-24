#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""fetch_index module allows to sync data to Elastic Enterprise Search.

It's possible to run full syncs and incremental syncs with this module."""

import multiprocessing
import time
import copy
import os
import re
import json
from datetime import datetime
from urllib.parse import urljoin
from dateutil.parser import parse

from elastic_enterprise_search import WorkplaceSearch
from tika.tika import TikaException

from .util import logger
from .sharepoint_utils import encode
from .checkpointing import Checkpoint
from .sharepoint_client import SharePoint
from .configuration import Configuration
from .usergroup_permissions import Permissions
from .sharepoint_utils import extract
from . import adapter

IDS_PATH = os.path.join(os.path.dirname(__file__), 'doc_id.json')

SITE = "site"
LIST = "list"
ITEM = "item"
SITES = "sites"
LISTS = "lists"
LIST_ITEMS = "list_items"
DRIVE_ITEMS = "drive_items"
DOCUMENT_SIZE = 100
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def check_response(response, error_message, exception_message, param_name):
    """ Checks the response received from sharepoint server
        :param response: response from the sharepoint client
        :param error_message: error message if not getting the response
        :param exception message: exception message
        :param param_name: parameter name whether it is SITES, LISTS, LIST_ITEMS OR DRIVE_ITEMS
        Returns:
            Parsed response, and is_error flag
    """
    if not response:
        logger.error(error_message)
        return (False, True)
    if param_name == "attachment" and not response.get("d", {}).get("results"):
        logger.info(error_message)
        return (False, False)
    try:
        response_data = response.get("d", {}).get("results")
        return (response_data, False)
    except ValueError as exception:
        logger.exception("%s Error: %s" % (exception_message, exception))
        return (False, True)


class FetchIndex:
    """This class allows ingesting data from Sharepoint Server to Elastic Enterprise Search."""
    def __init__(self, config, start_time, end_time):
        logger.debug("Initializing the Indexing class")
        self.is_error = False
        self.ws_host = config.get_value("enterprise_search.host_url")
        self.ws_token = config.get_value("workplace_search.access_token")
        self.ws_source = config.get_value("workplace_search.source_id")
        self.sharepoint_host = config.get_value("sharepoint.host_url")
        self.objects = config.get_value("objects")
        self.site_collections = config.get_value("sharepoint.site_collections")
        self.enable_permission = config.get_value("enable_document_permission")
        self.start_time = start_time
        self.end_time = end_time
        self.checkpoint = Checkpoint(config)
        self.sharepoint_client = SharePoint()
        self.permissions = Permissions(self.sharepoint_client)
        self.ws_client = WorkplaceSearch(self.ws_host, http_auth=self.ws_token)
        self.mapping_sheet_path = config.get_value("sharepoint_workplace_user_mapping")

    def index_document(self, document, parent_object, param_name):
        """ This method indexes the documents to the workplace.
            :param document: document to be indexed
            :param parent_object: parent of the objects to be indexed
            :param param_name: parameter name whether it is SITES, LISTS LIST_ITEMS OR DRIVE_ITEMS
        """
        try:
            if document:
                total_documents_indexed = 0
                document_list = [document[i * DOCUMENT_SIZE:(i + 1) * DOCUMENT_SIZE] for i in range((len(document) + DOCUMENT_SIZE - 1) // DOCUMENT_SIZE)]
                for chunk in document_list:
                    response = self.ws_client.index_documents(
                        http_auth=self.ws_token,
                        content_source_id=self.ws_source,
                        documents=chunk
                    )
                    for each in response['results']:
                        if not each['errors']:
                            total_documents_indexed += 1
                        else:
                            logger.error("Error while indexing %s. Error: %s" % (each['id'], each['errors']))
            logger.info("Successfully indexed %s %s for %s to the workplace" % (
                total_documents_indexed, param_name, parent_object))
        except Exception as exception:
            logger.exception(
                "Error while indexing the %s for %s. Error: %s"
                % (param_name, parent_object, exception)
            )
            self.is_error = True

    def get_schema_fields(self, document_name):
        """ returns the schema of all the include_fields or exclude_fields specified in the configuration file.
            :param document_name: document name from SITES, LISTS, LIST_ITEMS OR DRIVE_ITEMS
            Returns:
                schema: included and excluded fields schema
        """
        fields = self.objects.get(document_name)
        adapter_schema = adapter.DEFAULT_SCHEMA[document_name]
        field_id = adapter_schema['id']
        if fields:
            include_fields = fields.get("include_fields")
            exclude_fields = fields.get("exclude_fields")
            if include_fields:
                adapter_schema = {key: val for key, val in adapter_schema.items() if val in include_fields}
            elif exclude_fields:
                adapter_schema = {key: val for key, val in adapter_schema.items() if val not in exclude_fields}
            adapter_schema['id'] = field_id
        return adapter_schema

    def index_sites(self, parent_site_url, sites, ids, index):
        """This method fetches sites from a collection and invokes the
            index permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            :param parent_site_url: parent site relative path
            :param sites: dictionary of site path and it's last updated time
            :param ids: structure containing id's of all objects
            :param index: index, boolean value
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        rel_url = urljoin(
            self.sharepoint_host, f"{parent_site_url}/_api/web/webs"
        )
        logger.info("Fetching the sites detail from url: %s" % (rel_url))
        query = self.sharepoint_client.get_query(
            self.start_time, self.end_time, SITES)
        response = self.sharepoint_client.get(rel_url, query, SITES)

        response_data, self.is_error = check_response(
            response,
            "Could not fetch the sites, url: %s" % (rel_url),
            "Error while parsing the get sites response from url: %s."
            % (rel_url),
            SITES,
        )
        if not response_data:
            logger.info("No sites were created in %s for this interval: start time: %s and end time: %s" % (parent_site_url, self.start_time, self.end_time))
            return sites
        logger.info(
            "Successfully fetched and parsed %s sites response from SharePoint" % len(response_data)
        )
        logger.info("Indexing the sites to the Workplace")

        schema = self.get_schema_fields(SITES)
        document = []

        if index:
            for i, _ in enumerate(response_data):
                doc = {'type': SITE}
                # need to convert date to iso else workplace search throws error on date format Invalid field value: Value '2021-09-29T08:13:00' cannot be parsed as a date (RFC 3339)"]}
                response_data[i]['Created'] += 'Z'
                for field, response_field in schema.items():
                    doc[field] = response_data[i].get(response_field)
                if self.enable_permission is True:
                    doc["_allow_permissions"] = self.index_permissions(
                        key=SITES, site=response_data[i]['ServerRelativeUrl'])
                document.append(doc)
                ids["sites"].update({doc["id"]: response_data[i]["ServerRelativeUrl"]})
            self.index_document(document, parent_site_url, SITES)
        for result in response_data:
            site_server_url = result.get("ServerRelativeUrl")
            sites.update({site_server_url: result.get("LastItemModifiedDate")})
            self.index_sites(site_server_url, sites, ids, index)
        return sites

    def index_lists(self, sites, ids, index):
        """This method fetches lists from all sites in a collection and invokes the
            index permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            :param sites: dictionary of site path and it's last updated time
            :param index: index, boolean value
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        logger.info("Fetching lists for all the sites")
        responses = []
        document = []
        if not sites:
            logger.info("No list was created in this interval: start time: %s and end time: %s" % (self.start_time, self.end_time))
            return [], []
        schema_list = self.get_schema_fields(LISTS)
        for site, time_modified in sites.items():
            if parse(self.start_time) > parse(time_modified):
                continue
            rel_url = urljoin(self.sharepoint_host, f"{site}/_api/web/lists")
            logger.info(
                "Fetching the lists for site: %s from url: %s"
                % (site, rel_url)
            )

            query = self.sharepoint_client.get_query(
                self.start_time, self.end_time, LISTS)
            response = self.sharepoint_client.get(
                rel_url, query, LISTS)

            response_data, self.is_error = check_response(
                response,
                "Could not fetch the list for site: %s" % (site),
                "Error while parsing the get list response for site: %s from url: %s."
                % (site, rel_url),
                LISTS,
            )
            if not response_data:
                logger.info("No list was created for the site : %s in this interval: start time: %s and end time: %s" % (site, self.start_time, self.end_time))
                continue
            logger.info(
                "Successfully fetched and parsed %s list response for site: %s from SharePoint"
                % (len(response_data), site)
            )

            base_list_url = urljoin(self.sharepoint_host, f"{site}/Lists/")

            if index:
                if not ids["lists"].get(site):
                    ids["lists"].update({site: {}})
                for i, _ in enumerate(response_data):
                    doc = {'type': LIST}
                    for field, response_field in schema_list.items():
                        doc[field] = response_data[i].get(
                            response_field)
                    if self.enable_permission is True:
                        doc["_allow_permissions"] = self.index_permissions(
                            key=LISTS, site=site, list_id=doc["id"], list_url=response_data[i]['ParentWebUrl'], itemid=None)
                    doc["url"] = urljoin(base_list_url, re.sub(
                        r'[^ \w+]', '', response_data[i]["Title"]))
                    document.append(doc)
                    ids["lists"][site].update({doc["id"]: response_data[i]["Title"]})
                logger.info(
                    "Indexing the list for site: %s to the Workplace" % (site)
                )

                self.index_document(document, site, LISTS)

            responses.append(response_data)
        lists = {}
        libraries = {}
        for response in responses:
            for result in response:
                if result.get('BaseType') == 1:
                    libraries[result.get("Id")] = [result.get(
                        "ParentWebUrl"), result.get("Title"), result.get("LastItemModifiedDate")]
                else:
                    lists[result.get("Id")] = [result.get(
                        "ParentWebUrl"), result.get("Title"), result.get("LastItemModifiedDate")]
        return lists, libraries

    def index_items(self, lists, ids):
        """This method fetches items from all the lists in a collection and
            invokes theindex permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            :param lists: document lists
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        responses = []
        #  here value is a list of url and title
        logger.info("Fetching all the items for the lists")
        if not lists:
            logger.info("No item was created in this interval: start time: %s and end time: %s" % (self.start_time, self.end_time))
        else:
            for value in lists.values():
                if not ids["list_items"].get(value[0]):
                    ids["list_items"].update({value[0]: {}})
            schema_item = self.get_schema_fields(LIST_ITEMS)
            for list_content, value in lists.items():
                if parse(self.start_time) > parse(value[2]):
                    continue
                rel_url = urljoin(
                    self.sharepoint_host,
                    f"{value[0]}/_api/web/lists(guid'{list_content}')/items",
                )
                logger.info(
                    "Fetching the items for list: %s from url: %s"
                    % (value[1], rel_url)
                )

                query = self.sharepoint_client.get_query(
                    self.start_time, self.end_time, LIST_ITEMS)
                response = self.sharepoint_client.get(rel_url, query, LIST_ITEMS)

                response_data, self.is_error = check_response(
                    response,
                    "Could not fetch the items for list: %s" % (value[1]),
                    "Error while parsing the get items response for list: %s from url: %s."
                    % (value[1], rel_url),
                    LIST_ITEMS,
                )
                if not response_data:
                    logger.info("No item was created for the list %s in this interval: start time: %s and end time: %s" % (value[1], self.start_time, self.end_time))
                    continue
                logger.info(
                    "Successfully fetched and parsed %s listitem response for list: %s from SharePoint"
                    % (len(response_data), value[1])
                )

                list_name = re.sub(r'[^ \w+]', '', value[1])
                base_item_url = urljoin(self.sharepoint_host,
                                        f"{value[0]}/Lists/{list_name}/DispForm.aspx?ID=")
                document = []
                if not ids["list_items"][value[0]].get(list_content):
                    ids["list_items"][value[0]].update({list_content: []})
                rel_url = urljoin(
                    self.sharepoint_host, f'{value[0]}/_api/web/lists(guid\'{list_content}\')/items?$select=Attachments,AttachmentFiles,Title&$expand=AttachmentFiles')

                new_query = "&" + query.split("?")[1]
                file_response_data = self.sharepoint_client.get(rel_url, query=new_query, param_name="attachment")
                if file_response_data:
                    file_response_data, self.is_error = check_response(file_response_data.json(), "No attachments were found at url %s in the interval: start time: %s and end time: %s" % (
                        rel_url, self.start_time, self.end_time), "Error while parsing file response for file at url %s." % (rel_url), "attachment")

                for i, _ in enumerate(response_data):
                    doc = {'type': ITEM}
                    if response_data[i].get('Attachments') and file_response_data:
                        for data in file_response_data:
                            if response_data[i].get('Title') == data['Title']:
                                file_relative_url = data[
                                    'AttachmentFiles']['results'][0]['ServerRelativeUrl']
                                url_s = f"{value[0]}/_api/web/GetFileByServerRelativeUrl(\'{encode(file_relative_url)}\')/$value"
                                response = self.sharepoint_client.get(
                                    urljoin(self.sharepoint_host, url_s), query='', param_name="attachment")
                                doc['body'] = {}
                                if response and response.ok:
                                    try:
                                        doc['body'] = extract(response.content)
                                    except TikaException as exception:
                                        logger.error('Error while extracting the contents from the attachment, Error %s' % (exception))

                                break
                    for field, response_field in schema_item.items():
                        doc[field] = response_data[i].get(
                            response_field)
                    if self.enable_permission is True:
                        doc["_allow_permissions"] = self.index_permissions(
                            key=LIST_ITEMS, list_id=list_content, list_url=value[0], itemid=str(response_data[i]["Id"]))
                    doc["url"] = base_item_url + str(response_data[i]["Id"])
                    document.append(doc)
                    if response_data[i].get("GUID") not in ids["list_items"][value[0]][list_content]:
                        ids["list_items"][value[0]][list_content].append(
                            response_data[i].get("GUID"))
                logger.info(
                    "Indexing the listitem for list: %s to the Workplace"
                    % (value[1])
                )

                self.index_document(document, value[1], LIST_ITEMS)

                responses.append(document)
        return responses

    def index_drive_items(self, libraries, ids):
        """This method fetches items from all the lists in a collection and
            invokes theindex permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            :param libraries: document lists
            :param ids: structure containing id's of all objects
        """
        #  here value is a list of url and title of the library
        logger.info("Fetching all the files for the library")
        if not libraries:
            logger.info("No file was created in this interval: start time: %s and end time: %s" % (self.start_time, self.end_time))
        else:
            schema_drive = self.get_schema_fields(DRIVE_ITEMS)
            for lib_content, value in libraries.items():
                if parse(self.start_time) > parse(value[2]):
                    continue
                if not ids["drive_items"].get(value[0]):
                    ids["drive_items"].update({value[0]: {}})
                rel_url = urljoin(
                    self.sharepoint_host,
                    f"{value[0]}/_api/web/lists(guid'{lib_content}')/items?$select=Modified,Id,GUID,File,Folder&$expand=File,Folder",
                )
                logger.info(
                    "Fetching the items for libraries: %s from url: %s"
                    % (value[1], rel_url)
                )
                query = self.sharepoint_client.get_query(
                    self.start_time, self.end_time, DRIVE_ITEMS)
                response = self.sharepoint_client.get(rel_url, query, DRIVE_ITEMS)
                response_data, self.is_error = check_response(
                    response,
                    "Could not fetch the items for library: %s" % (value[1]),
                    "Error while parsing the get items response for library: %s from url: %s."
                    % (value[1], rel_url),
                    DRIVE_ITEMS,
                )
                if not response_data:
                    logger.info("No item was created for the library %s in this interval: start time: %s and end time: %s" % (value[1], self.start_time, self.end_time))
                    continue
                logger.info(
                    "Successfully fetched and parsed %s drive item response for library: %s from SharePoint"
                    % (len(response_data), value[1])
                )
                document = []
                if not ids["drive_items"][value[0]].get(lib_content):
                    ids["drive_items"][value[0]].update({lib_content: []})
                for i, _ in enumerate(response_data):
                    if response_data[i]['File'].get('TimeLastModified'):
                        obj_type = 'File'
                        doc = {'type': "file"}
                        file_relative_url = response_data[i]['File']['ServerRelativeUrl']
                        url_s = f"{value[0]}/_api/web/GetFileByServerRelativeUrl(\'{encode(file_relative_url)}\')/$value"
                        response = self.sharepoint_client.get(
                            urljoin(self.sharepoint_host, url_s), query='', param_name="attachment")
                        doc['body'] = {}
                        if response and response.ok:
                            try:
                                doc['body'] = extract(response.content)
                            except TikaException as exception:
                                logger.error('Error while extracting the contents from the file at %s, Error %s' % (response_data[i].get('Url'), exception))
                    else:
                        obj_type = 'Folder'
                        doc = {'type': "folder"}
                    for field, response_field in schema_drive.items():
                        doc[field] = response_data[i][obj_type].get(
                            response_field)
                    doc['id'] = response_data[i].get("GUID")
                    if self.enable_permission is True:
                        doc["_allow_permissions"] = self.index_permissions(
                            key=DRIVE_ITEMS, list_id=lib_content, list_url=value[0], itemid=str(response_data[i].get("ID")))
                    doc["url"] = urljoin(self.sharepoint_host, response_data[i][obj_type]["ServerRelativeUrl"])
                    document.append(doc)
                    if doc['id'] not in ids["drive_items"][value[0]][lib_content]:
                        ids["drive_items"][value[0]][lib_content].append(doc['id'])
                if document:
                    logger.info("Indexing the drive items for library: %s to the Workplace" % (value[1]))
                    self.index_document(document, value[1], DRIVE_ITEMS)
                else:
                    logger.info("No item was present in the library %s for the interval: start time: %s and end time: %s" % (
                        value[1], self.start_time, self.end_time))

    def get_roles(self, key, site, list_url, list_id, itemid):
        """ Checks the permissions and returns the user roles.
            :param key: key, a string value
            :param site: site name to check the permission
            :param list_url: list url to access the list
            :param list_id: list id to check the permission
            :param itemid: item id to check the permission
            Returns:
                roles: user roles
        """
        if key == SITES:
            rel_url = urljoin(self.sharepoint_host, site)
            roles = self.permissions.fetch_users(key, rel_url)

        elif key == LISTS:
            rel_url = urljoin(self.sharepoint_host, list_url)
            roles = self.permissions.fetch_users(
                key, rel_url, list_id=list_id
            )

        else:
            rel_url = urljoin(self.sharepoint_host, list_url)
            roles = self.permissions.fetch_users(
                key, rel_url, list_id=list_id, item_id=itemid
            )

        return roles, rel_url

    def index_permissions(
        self,
        key,
        site=None,
        list_id=None,
        list_url=None,
        itemid=None,
    ):
        """This method when invoked, checks the permission inheritance of each object.
            If the object has unique permissions, the list of users having access to it
            is fetched using sharepoint api else the permission levels of the that object
            is taken same as the permission level of the site collection.
            :param key: key, a string value
            :param site: site name to index the permission for the site
            :param list_id: list id to index the permission for the list
            :param list_url: url of the list
            :param itemid: item id to index the permission for the item
            Returns:
                groups: list of users having access to the given object
        """
        roles, rel_url = self.get_roles(key, site, list_url, list_id, itemid)

        groups = []

        if not roles:
            return []
        roles, self.is_error = check_response(roles.json(), "Cannot fetch the roles for the given object %s at url %s" % (
            key, rel_url), "Error while parsing response for fetch_users for %s at url %s." % (key, rel_url), "roles")

        for role in roles:
            title = role["Member"]["Title"]
            groups.append(title)
        return groups

    def indexing(self, collection, ids, storage, is_error_shared, job_type, parent_site_url, sites_path, lists_details, libraries_details):
        """This method fetches all the objects from sharepoint server and
            ingests them into the workplace search
            :param collection: collection name
            :param ids: id collection of the all the objects
            :param storage: temporary storage for storing all the documents
            :is_error_shared: list of all the is_error values
            :job_type: denotes the type of sharepoint object being fetched in a particular process
            :parent_site_url: parent site relative path
            :sites_path: dictionary of site path and it's last updated time
            :lists_details: dictionary containing list name, list path and id
            :library_details: dictionary containing library name, library path and id
        """
        if job_type == "sites":
            sites = self.index_sites(parent_site_url, {}, ids, index=(SITES in self.objects))
            sites_path.update(sites)
        elif job_type == "lists":
            if not self.is_error:
                lists, libraries = self.index_lists(sites_path, ids, index=(LISTS in self.objects))
                lists_details.update(lists)
                libraries_details.update(libraries)
        elif job_type == "list_items":
            if LIST_ITEMS in self.objects and not self.is_error:
                self.index_items(lists_details, ids)
        else:
            if DRIVE_ITEMS in self.objects and not self.is_error:
                self.index_drive_items(libraries_details, ids)

            logger.info(
                "Completed fetching all the objects for site collection: %s"
                % (collection)
            )

            logger.info(
                "Saving the checkpoint for the site collection: %s" % (collection)
            )
        is_error_shared.append(self.is_error)
        self.is_error = False
        if ids.get(job_type):
            prev_ids = storage[job_type]
            if job_type == 'sites':
                prev_ids.update(ids[job_type])
            elif job_type == "lists":
                for site, list_content in ids[job_type].items():
                    prev_ids[site] = {**prev_ids.get(site, {}), **ids[job_type][site]}
            else:
                for site, list_content in ids[job_type].items():
                    prev_ids[site] = ids[job_type][site] if not prev_ids.get(site) else prev_ids[site]
                    for list_name in list_content.keys():
                        prev_ids[site][list_name] = list(set([*prev_ids[site].get(list_name, []), *ids[job_type][site][list_name]]))
            storage[job_type] = prev_ids


def datetime_partitioning(start_time, end_time, processes):
    """ Divides the timerange in equal partitions by number of processors
        :param start_time: start time of the interval
        :param end_time: end time of the interval
        :param processes: number of processors the device have
    """
    start_time = datetime.strptime(start_time, DATETIME_FORMAT)
    end_time = datetime.strptime(end_time, DATETIME_FORMAT)

    diff = (end_time - start_time) / processes
    for idx in range(processes):
        yield start_time + diff * idx
    yield end_time


def init_multiprocessing(data, start_time, end_time, collection, ids, storage, is_error_shared, job_type, parent_site_url, sites_path, lists_details, libraries_details):
    """This method initializes the FetchIndex class and kicks-off the multiprocessing. This is a wrapper method added to fix the pickling issue while using multiprocessing in Windows
            :param data: configuration dictionary
            :param start_time: start time of the indexing
            :param end_time: end time of the indexing
            :param collection: collection name
            :param ids: id collection of the all the objects
            :param storage: temporary storage for storing all the documents
            :is_error_shared: list of all the is_error values
            :job_type: denotes the type of sharepoint object being fetched in a particular process
            :parent_site_url: parent site relative path
            :sites_path: dictionary of site path and it's last updated time
            :lists_details: dictionary containing list name, list path and id
            :library_details: dictionary containing library name, library path and id
        """
    indexer = FetchIndex(data, start_time, end_time)
    indexer.indexing(collection, ids, storage, is_error_shared, job_type, parent_site_url, sites_path, lists_details, libraries_details)


def start(indexing_type):
    """Runs the indexing logic regularly after a given interval
        or puts the connector to sleep
        :param indexing_type: The type of the indexing i.e. Incremental Sync or Full sync
    """
    logger.info("Starting the indexing..")
    config = Configuration("sharepoint_connector_config.yml")
    is_error_shared = multiprocessing.Manager().list()
    while True:
        current_time = (datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")
        ids_collection = {"global_keys": {}}
        storage_with_collection = {"global_keys": {}, "delete_keys": {}}

        if (os.path.exists(IDS_PATH) and os.path.getsize(IDS_PATH) > 0):
            with open(IDS_PATH) as ids_store:
                try:
                    ids_collection = json.load(ids_store)
                except ValueError as exception:
                    logger.exception(
                        "Error while parsing the json file of the ids store from path: %s. Error: %s"
                        % (IDS_PATH, exception)
                    )

        storage_with_collection["delete_keys"] = copy.deepcopy(ids_collection.get("global_keys"))

        for collection in config.get_value("sharepoint.site_collections"):
            storage = multiprocessing.Manager().dict({"sites": {}, "lists": {}, "list_items": {}, "drive_items": {}})
            logger.info(
                "Starting the data fetching for site collection: %s"
                % (collection)
            )
            check = Checkpoint(config)

            worker_process = config.get_value("worker_process")
            if indexing_type == "incremental":
                start_time, end_time = check.get_checkpoint(
                    collection, current_time)
            else:
                start_time = config.get_value("start_time")
                end_time = current_time

            # partitioning the data collection timeframe in equal parts by worker processes
            partitions = list(datetime_partitioning(
                start_time, end_time, worker_process))

            datelist = []
            for sub in partitions:
                datelist.append(sub.strftime(DATETIME_FORMAT))

            jobs = {"sites": [], "lists": [], "list_items": [], "drive_items": []}
            if not ids_collection["global_keys"].get(collection):
                ids_collection["global_keys"][collection] = {
                    "sites": {}, "lists": {}, "list_items": {}, "drive_items": {}}

            parent_site_url = f"/sites/{collection}"
            sites_path = multiprocessing.Manager().dict()
            sites_path.update({parent_site_url: end_time})
            lists_details = multiprocessing.Manager().dict()
            libraries_details = multiprocessing.Manager().dict()
            logger.info(
                "Starting to index all the objects configured in the object field: %s"
                % (str(config.get_value("objects")))
            )
            for num in range(0, worker_process):
                start_time_partition = datelist[num]
                end_time_partition = datelist[num + 1]

                logger.info(
                    "Successfully fetched the checkpoint details: start_time: %s and end_time: %s, calling the indexing"
                    % (start_time_partition, end_time_partition)
                )

                for job_type, job_list in jobs.items():
                    process = multiprocessing.Process(target=init_multiprocessing, args=(config, start_time_partition, end_time_partition, collection, ids_collection["global_keys"][collection], storage, is_error_shared, job_type, parent_site_url, sites_path, lists_details, libraries_details))
                    job_list.append(process)

            for job_list in jobs.values():
                for job in job_list:
                    job.start()
                for job in job_list:
                    job.join()
            storage_with_collection["global_keys"][collection] = storage.copy()

            if True in is_error_shared:
                check.set_checkpoint(collection, start_time, indexing_type)
            else:
                check.set_checkpoint(collection, end_time, indexing_type)

        with open(IDS_PATH, "w") as file:
            try:
                json.dump(storage_with_collection, file, indent=4)
            except ValueError as exception:
                logger.warning(
                    'Error while adding ids to json file. Error: %s' % (exception))
        if indexing_type == "incremental":
            interval = config.get_value("indexing_interval")
        else:
            interval = config.get_value("full_sync_interval")
        # TODO: need to use schedule instead of time.sleep
        logger.info("Sleeping..")
        time.sleep(interval * 60)
