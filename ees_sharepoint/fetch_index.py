#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""fetch_index module allows to sync data to Elastic Enterprise Search.

It's possible to run full syncs and incremental syncs with this module."""

import copy
import os
import re
import json
from datetime import datetime
from urllib.parse import urljoin
from dateutil.parser import parse

from tika.tika import TikaException
from multiprocessing.pool import ThreadPool

from .checkpointing import Checkpoint
from .usergroup_permissions import Permissions
from .utils import encode, extract, partition_equal_share, split_list_in_chunks, get_partition_time, split_dict_in_chunks
from . import adapter

IDS_PATH = os.path.join(os.path.dirname(__file__), 'doc_id.json')

SITE = "site"
LIST = "list"
ITEM = "item"
SITES = "sites"
LISTS = "lists"
LIST_ITEMS = "list_items"
DRIVE_ITEMS = "drive_items"
BATCH_SIZE = 100


def get_results(logger, response, entity_name):
    """ Attempts to fetch results from a Sharepoint Server response
        :param response: response from the sharepoint client
        :param entity_name: entity name whether it is SITES, LISTS, LIST_ITEMS OR DRIVE_ITEMS
        Returns:
            Parsed response
    """
    if not response:
        logger.error(f"Empty response when fetching {entity_name}")  # TODO: should it be an error?
        return None

    if entity_name == "attachment" and not response.get("d", {}).get("results"):
        logger.info("Failed to fetch attachment")  # TODO: not sure if it's the right message
        return None
    return response.get("d", {}).get("results")


class FetchIndex:
    """This class allows ingesting data from Sharepoint Server to Elastic Enterprise Search."""
    def __init__(self, config, logger, workplace_search_client, sharepoint_client, start_time, end_time):
        self.config = config
        self.logger = logger
        self.workplace_search_client = workplace_search_client
        self.sharepoint_client = sharepoint_client

        self.ws_source = config.get_value("workplace_search.source_id")
        self.objects = config.get_value("objects")
        self.site_collections = config.get_value("sharepoint.site_collections")
        self.enable_permission = config.get_value("enable_document_permission")
        self.start_time = start_time
        self.end_time = end_time
        self.max_threads = config.get_value("max_threads")
        self.mapping_sheet_path = config.get_value("sharepoint_workplace_user_mapping")

        self.checkpoint = Checkpoint(config, logger)
        self.permissions = Permissions(self.sharepoint_client, self.workplace_search_client, logger)

    def index_document(self, document, param_name):
        """ This method indexes the documents to the workplace.
            :param document: document to be indexed
            :param param_name: parameter name whether it is SITES, LISTS LIST_ITEMS OR DRIVE_ITEMS
        """
        if document:
            total_documents_indexed = 0
            for chunk in split_list_in_chunks(document, BATCH_SIZE):
                response = self.workplace_search_client.index_documents(
                    content_source_id=self.ws_source,
                    documents=chunk
                )
                for each in response['results']:
                    if not each['errors']:
                        total_documents_indexed += 1
                    else:
                        self.logger.error("Error while indexing %s. Error: %s" % (each['id'], each['errors']))
        self.logger.info("Successfully indexed %s %s to the workplace" % (
            total_documents_indexed, param_name))

    def threaded_index_documents(self, document, param_name):
        """ Applies multithreading on indexing functionality
            :param document: documents to be indexed equally in each thread
            :param param_name: parameter name whether it is SITES, LISTS LIST_ITEMS OR DRIVE_ITEMS
        """
        chunk_documents = partition_equal_share(document, self.max_threads)
        thread_pool = ThreadPool(self.max_threads)
        for doc in chunk_documents:
            thread_pool.apply_async(self.index_document, (doc, param_name))

        thread_pool.close()
        thread_pool.join()

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

    def fetch_sites(self, parent_site_url, sites, ids, index, start_time, end_time):
        """This method fetches sites from a collection and invokes the
            index permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            :param parent_site_url: parent site relative path
            :param sites: dictionary of site path and it's last updated time
            :param ids: structure containing id's of all objects
            :param index: index, boolean value
            :param start_time: start time for fetching the data
            :param end_time: end time for fetching the data
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        rel_url = f"{parent_site_url}/_api/web/webs"
        self.logger.info("Fetching the sites detail from url: %s" % (rel_url))
        query = self.sharepoint_client.get_query(
            start_time, end_time, SITES)
        response = self.sharepoint_client.get(rel_url, query, SITES)

        response_data = get_results(self.logger, response, SITES)
        if not response_data:
            self.logger.info("No sites were created in %s for this interval: start time: %s and end time: %s" % (parent_site_url, start_time, end_time))
            return sites
        self.logger.info(
            "Successfully fetched and parsed %s sites response from SharePoint" % len(response_data)
        )

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
        for result in response_data:
            site_server_url = result.get("ServerRelativeUrl")
            sites.update({site_server_url: result.get("LastItemModifiedDate")})
            self.fetch_sites(site_server_url, sites, ids, index, start_time, end_time)
        return sites, document

    def fetch_lists(self, sites, ids, index):
        """This method fetches lists from all sites in a collection and invokes the
            index permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            :param sites: dictionary of site path and it's last updated time
            :param ids: structure containing id's of all objects
            :param index: index, boolean value
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        self.logger.info("Fetching lists for all the sites")
        responses = []
        document = []
        if not sites:
            self.logger.info("No list was created in this interval: start time: %s and end time: %s" % (self.start_time, self.end_time))
            return [], []
        schema_list = self.get_schema_fields(LISTS)
        for site_details in sites:
            for site, time_modified in site_details.items():
                if parse(self.start_time) > parse(time_modified):
                    continue
                rel_url = f"{site}/_api/web/lists"
                self.logger.info(
                    "Fetching the lists for site: %s from url: %s"
                    % (site, rel_url)
                )

                query = self.sharepoint_client.get_query(
                    self.start_time, self.end_time, LISTS)
                response = self.sharepoint_client.get(
                    rel_url, query, LISTS)

                response_data = get_results(self.logger, response, LISTS)
                if not response_data:
                    self.logger.info("No list was created for the site : %s in this interval: start time: %s and end time: %s" % (site, self.start_time, self.end_time))
                    continue
                self.logger.info(
                    "Successfully fetched and parsed %s list response for site: %s from SharePoint"
                    % (len(response_data), site)
                )

                base_list_url = f"{site}/Lists/"

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
        return lists, libraries, document

    def fetch_items(self, lists, ids):
        """This method fetches items from all the lists in a collection and
            invokes theindex permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            :param lists: document lists
            :param ids: structure containing id's of all objects
            Returns:
                document: response of sharepoint GET call, with fields specified in the schema
        """
        responses = []
        #  here value is a list of url and title
        self.logger.info("Fetching all the items for the lists")
        if not lists:
            self.logger.info("No item was created in this interval: start time: %s and end time: %s" % (self.start_time, self.end_time))
        else:
            for value in lists.values():
                if not ids["list_items"].get(value[0]):
                    ids["list_items"].update({value[0]: {}})
            schema_item = self.get_schema_fields(LIST_ITEMS)
            for list_content, value in lists.items():
                if parse(self.start_time) > parse(value[2]):
                    continue
                rel_url = f"{value[0]}/_api/web/lists(guid'{list_content}')/items"
                self.logger.info(
                    "Fetching the items for list: %s from url: %s"
                    % (value[1], rel_url)
                )

                query = self.sharepoint_client.get_query(
                    self.start_time, self.end_time, LIST_ITEMS)
                response = self.sharepoint_client.get(rel_url, query, LIST_ITEMS)

                response_data = get_results(self.logger, response, LIST_ITEMS)
                if not response_data:
                    self.logger.info("No item was created for the list %s in this interval: start time: %s and end time: %s" % (value[1], self.start_time, self.end_time))
                    continue
                self.logger.info(
                    "Successfully fetched and parsed %s listitem response for list: %s from SharePoint"
                    % (len(response_data), value[1])
                )

                list_name = re.sub(r'[^ \w+]', '', value[1])
                base_item_url = f"{value[0]}/Lists/{list_name}/DispForm.aspx?ID="
                document = []
                if not ids["list_items"][value[0]].get(list_content):
                    ids["list_items"][value[0]].update({list_content: []})
                rel_url = f'{value[0]}/_api/web/lists(guid\'{list_content}\')/items?$select=Attachments,AttachmentFiles,Title&$expand=AttachmentFiles'

                new_query = "&" + query.split("?")[1]
                file_response_data = self.sharepoint_client.get(rel_url, query=new_query, param_name="attachment")
                if file_response_data:
                    file_response_data = get_results(self.logger, file_response_data.json(), "attachment")

                for i, _ in enumerate(response_data):
                    doc = {'type': ITEM}
                    if response_data[i].get('Attachments') and file_response_data:
                        for data in file_response_data:
                            if response_data[i].get('Title') == data['Title']:
                                file_relative_url = data[
                                    'AttachmentFiles']['results'][0]['ServerRelativeUrl']
                                url_s = f"{value[0]}/_api/web/GetFileByServerRelativeUrl(\'{encode(file_relative_url)}\')/$value"
                                response = self.sharepoint_client.get(
                                    url_s, query='', param_name="attachment")
                                doc['body'] = {}
                                if response and response.ok:
                                    try:
                                        doc['body'] = extract(response.content)
                                    except TikaException as exception:
                                        self.logger.error('Error while extracting the contents from the attachment, Error %s' % (exception))

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
                responses.extend(document)
        return responses

    def fetch_drive_items(self, libraries, ids):
        """This method fetches items from all the lists in a collection and
            invokes theindex permission method to get the document level permissions.
            If the fetching is not successful, it logs proper message.
            :param libraries: document lists
            :param ids: structure containing id's of all objects
        """
        responses = []
        #  here value is a list of url and title of the library
        self.logger.info("Fetching all the files for the library")
        if not libraries:
            self.logger.info("No file was created in this interval: start time: %s and end time: %s" % (self.start_time, self.end_time))
        else:
            schema_drive = self.get_schema_fields(DRIVE_ITEMS)
            for lib_content, value in libraries.items():
                if parse(self.start_time) > parse(value[2]):
                    continue
                if not ids["drive_items"].get(value[0]):
                    ids["drive_items"].update({value[0]: {}})
                rel_url = f"{value[0]}/_api/web/lists(guid'{lib_content}')/items?$select=Modified,Id,GUID,File,Folder&$expand=File,Folder"
                self.logger.info(
                    "Fetching the items for libraries: %s from url: %s"
                    % (value[1], rel_url)
                )
                query = self.sharepoint_client.get_query(
                    self.start_time, self.end_time, DRIVE_ITEMS)
                response = self.sharepoint_client.get(rel_url, query, DRIVE_ITEMS)
                response_data = get_results(self.logger, response, DRIVE_ITEMS)
                if not response_data:
                    self.logger.info("No item was created for the library %s in this interval: start time: %s and end time: %s" % (value[1], self.start_time, self.end_time))
                    continue
                self.logger.info(
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
                        response = self.sharepoint_client.get(url_s, query='', param_name="attachment")
                        doc['body'] = {}
                        if response and response.ok:
                            try:
                                doc['body'] = extract(response.content)
                            except TikaException as exception:
                                self.logger.error('Error while extracting the contents from the file at %s, Error %s' % (response_data[i].get('Url'), exception))
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
                    doc["url"] = response_data[i][obj_type]["ServerRelativeUrl"]
                    document.append(doc)
                    if doc['id'] not in ids["drive_items"][value[0]][lib_content]:
                        ids["drive_items"][value[0]][lib_content].append(doc['id'])
                responses.extend(document)
        return responses

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
            rel_url = site
            roles = self.permissions.fetch_users(key, rel_url)

        elif key == LISTS:
            rel_url = list_url
            roles = self.permissions.fetch_users(
                key, rel_url, list_id=list_id
            )

        else:
            rel_url = list_url
            roles = self.permissions.fetch_users(
                key, rel_url, list_id=list_id, item_id=itemid
            )

        return roles

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
        roles = self.get_roles(key, site, list_url, list_id, itemid)

        groups = []

        if not roles:
            return []
        roles = get_results(self.logger, roles.json(), "roles")

        for role in roles:
            title = role["Member"]["Title"]
            groups.append(title)
        return groups

    def index_sites(self, parent_site_url, ids, sites_path):
        """ Indexes the site details to the Workplace Search
            :param parent_site_url: parent site relative path
            :param ids: id collection of the all the objects
            :param sites_path: dictionary of site path and it's last updated time
        """
        _, datelist = get_partition_time(self.max_threads, self.start_time, self.end_time)
        results = []
        thread_pool = ThreadPool(self.max_threads)
        for num in range(0, self.max_threads):
            start_time_partition = datelist[num]
            end_time_partition = datelist[num + 1]
            thread = thread_pool.apply_async(
                self.fetch_sites, (parent_site_url, {}, ids, (SITES in self.objects),
                                   start_time_partition, end_time_partition))
            results.append(thread)

        sites, documents = [], []
        for result in [r.get() for r in results]:
            if result:
                sites.append(result[0])
                documents.extend(result[1])
        thread_pool.close()
        thread_pool.join()
        self.threaded_index_documents(documents, SITES)
        sites_path.extend(sites)

    def index_lists(self, sites_path, ids, lists_details, libraries_details):
        """ Indexes the list details to the Workplace Search
            :param sites_path: dictionary of site path and it's last updated time
            :param ids: id collection of the all the objects
            :param lists_details: dictionary containing list name, list path and id
            :param libraries_details: dictionary containing library name, library path and id
        """
        results = []
        thread_pool = ThreadPool(self.max_threads)
        partitioned_sites = partition_equal_share(sites_path, self.max_threads)
        for site in partitioned_sites:
            thread = thread_pool.apply_async(self.fetch_lists, (site, ids, (LISTS in self.objects)))
            results.append(thread)
        documents = []
        for result in [r.get() for r in results]:
            if result:
                lists_details.update(result[0])
                libraries_details.update(result[1])
                documents.extend(result[2])
        thread_pool.close()
        thread_pool.join()
        self.threaded_index_documents(documents, LISTS)

    def index_items(self, job_type, lists_details, libraries_details, ids):
        """ Indexes the list_items and drive_items to the Workplace Search
            :param job_type: denotes the type of sharepoint object being fetched in a particular process
            :param lists_details: dictionary containing list name, list path and id
            :param libraries_details: dictionary containing library name, library path and id
            :param ids: id collection of the all the objects
        """
        results = []
        partition = []
        if job_type == "list_items" and LIST_ITEMS in self.objects:
            thread_pool = ThreadPool(self.max_threads)
            func = self.fetch_items
            partition = split_dict_in_chunks(lists_details, self.max_threads)
        elif job_type == "drive_items" and DRIVE_ITEMS in self.objects:
            thread_pool = ThreadPool(self.max_threads)
            func = self.fetch_drive_items
            partition = split_dict_in_chunks(libraries_details, self.max_threads)
        for list_data in partition:
            thread = thread_pool.apply_async(func, (list_data, ids))
            results.append(thread)
        documents = []
        for result in [r.get() for r in results]:
            if result:
                documents.extend(result)
        thread_pool.close()
        thread_pool.join()
        self.threaded_index_documents(documents, job_type)

    def indexing(self, collection, ids, storage, job_type, parent_site_url, sites_path, lists_details, libraries_details):
        """This method fetches all the objects from sharepoint server and
            ingests them into the workplace search
            :param collection: collection name
            :param ids: id collection of the all the objects
            :param storage: temporary storage for storing all the documents
            :param job_type: denotes the type of sharepoint object being fetched in a particular process
            :param parent_site_url: parent site relative path
            :param sites_path: dictionary of site path and it's last updated time
            :param lists_details: dictionary containing list name, list path and id
            :param libraries_details: dictionary containing library name, library path and id
        """
        if job_type == "sites":
            self.index_sites(parent_site_url, ids, sites_path)

        elif job_type == "lists":
            self.index_lists(sites_path, ids, lists_details, libraries_details)

        elif job_type in ["list_items", "drive_items"]:
            self.index_items(job_type, lists_details, libraries_details, ids)

        self.logger.info(
            "Completed fetching all the objects for site collection: %s"
            % (collection)
        )

        self.logger.info(
            "Saving the checkpoint for the site collection: %s" % (collection)
        )
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


def start(indexing_type, config, logger, workplace_search_client, sharepoint_client):
    """Runs the indexing logic
        :param indexing_type: The type of the indexing i.e. incremental or full
        :param config: instance of Configuration class
        :param logger: instance of Logger class
        :param workplace_search_client: instance of WorkplaceSearch
        :param sharepoint_client: instance of SharePoint
    """
    logger.info(f"Starting the {indexing_type} indexing..")
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
    check = Checkpoint(config, logger)

    try:
        for collection in config.get_value("sharepoint.site_collections"):
            storage = {"sites": {}, "lists": {}, "list_items": {}, "drive_items": {}}
            logger.info(
                "Starting the data fetching for site collection: %s"
                % (collection)
            )

            if indexing_type == "incremental":
                start_time, end_time = check.get_checkpoint(
                    collection, current_time)
            else:
                start_time = config.get_value("start_time")
                end_time = current_time

            if not ids_collection["global_keys"].get(collection):
                ids_collection["global_keys"][collection] = {
                    "sites": {}, "lists": {}, "list_items": {}, "drive_items": {}}

            parent_site_url = f"/sites/{collection}"
            sites_path = [{parent_site_url: end_time}]
            lists_details = {}
            libraries_details = {}
            logger.info(
                "Starting to index all the objects configured in the object field: %s"
                % (str(config.get_value("objects")))
            )

            indexer = FetchIndex(config, logger, workplace_search_client, sharepoint_client, start_time, end_time)
            for job_type in ["sites", "lists", "list_items", "drive_items"]:
                logger.info(f"Indexing {job_type}")
                indexer.indexing(
                    collection,
                    ids_collection["global_keys"][collection],
                    storage,
                    job_type,
                    parent_site_url,
                    sites_path,
                    lists_details,
                    libraries_details
                )

            storage_with_collection["global_keys"][collection] = storage.copy()

            check.set_checkpoint(collection, end_time, indexing_type)
    except Exception as exception:
        raise exception

    with open(IDS_PATH, "w") as file:
        try:
            json.dump(storage_with_collection, file, indent=4)
        except ValueError as exception:
            logger.warning(
                'Error while adding ids to json file. Error: %s' % (exception))
