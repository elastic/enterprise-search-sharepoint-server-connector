#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""sync_sharepoint module allows to sync data to Elastic Enterprise Search.

It's possible to run full syncs and incremental syncs with this module."""

import copy
import json
import os
import re
from datetime import datetime
from urllib.parse import urljoin
from dateutil.parser import parse
from multiprocessing.pool import ThreadPool
from tika.tika import TikaException

from . import adapter
from .base_command import BaseCommand
from .checkpointing import Checkpoint
from .usergroup_permissions import Permissions
from .utils import (
    encode,
    extract,
    split_list_into_buckets,
    split_date_range_into_chunks,
    split_documents_into_equal_chunks,
)

IDS_PATH = os.path.join(os.path.dirname(__file__), "doc_id.json")

SITE = "site"
LIST = "list"
ITEM = "item"
SITES = "sites"
LISTS = "lists"
LIST_ITEMS = "list_items"
DRIVE_ITEMS = "drive_items"


def get_results(logger, response, entity_name):
    """Attempts to fetch results from a Sharepoint Server response
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


class SyncSharepoint:
    """This class allows synching objects from the SharePoint Server."""

    def __init__(self, config, logger, workplace_search_client, sharepoint_client, start_time, end_time, queue):
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
        self.sharepoint_thread_count = config.get_value("sharepoint_sync_thread_count")
        self.mapping_sheet_path = config.get_value("sharepoint_workplace_user_mapping")

        self.checkpoint = Checkpoint(config, logger)
        self.permissions = Permissions(self.sharepoint_client, self.workplace_search_client, logger)

        self.thread_pool = ThreadPool(self.sharepoint_thread_count)
        self.queue = queue

    def get_schema_fields(self, document_name):
        """returns the schema of all the include_fields or exclude_fields specified in the configuration file.
        :param document_name: document name from SITES, LISTS, LIST_ITEMS OR DRIVE_ITEMS
        Returns:
            schema: included and excluded fields schema
        """
        fields = self.objects.get(document_name)
        adapter_schema = adapter.DEFAULT_SCHEMA[document_name]
        field_id = adapter_schema["id"]
        if fields:
            include_fields = fields.get("include_fields")
            exclude_fields = fields.get("exclude_fields")
            if include_fields:
                adapter_schema = {key: val for key, val in adapter_schema.items() if val in include_fields}
            elif exclude_fields:
                adapter_schema = {key: val for key, val in adapter_schema.items() if val not in exclude_fields}
            adapter_schema["id"] = field_id
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
        query = self.sharepoint_client.get_query(start_time, end_time, SITES)
        response = self.sharepoint_client.get(rel_url, query, SITES)

        response_data = get_results(self.logger, response, SITES)
        if not response_data:
            self.logger.info(
                "No sites were created in %s for this interval: start time: %s and end time: %s"
                % (parent_site_url, start_time, end_time)
            )
            return sites
        self.logger.info("Successfully fetched and parsed %s sites response from SharePoint" % len(response_data))

        schema = self.get_schema_fields(SITES)
        document = []

        if index:
            for i, _ in enumerate(response_data):
                doc = {"type": SITE}
                # need to convert date to iso else workplace search throws error on date format Invalid field value: Value '2021-09-29T08:13:00' cannot be parsed as a date (RFC 3339)"]}
                response_data[i]["Created"] += "Z"
                for field, response_field in schema.items():
                    doc[field] = response_data[i].get(response_field)
                if self.enable_permission is True:
                    doc["_allow_permissions"] = self.fetch_permissions(
                        key=SITES, site=response_data[i]["ServerRelativeUrl"]
                    )
                document.append(doc)
                ids["sites"].update({doc["id"]: response_data[i]["ServerRelativeUrl"]})
        for result in response_data:
            site_server_url = result.get("ServerRelativeUrl")
            sites.update({site_server_url: result.get("LastItemModifiedDate")})
            self.fetch_sites(site_server_url, sites, ids, index, start_time, end_time)

        documents = {"type": SITES, "data": document}
        return sites, documents

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
            self.logger.info(
                "No list was created in this interval: start time: %s and end time: %s"
                % (self.start_time, self.end_time)
            )
            return [], []
        schema_list = self.get_schema_fields(LISTS)
        for site_details in sites:
            for site, time_modified in site_details.items():
                if parse(self.start_time) > parse(time_modified):
                    continue
                rel_url = f"{site}/_api/web/lists"
                self.logger.info("Fetching the lists for site: %s from url: %s" % (site, rel_url))

                query = self.sharepoint_client.get_query(self.start_time, self.end_time, LISTS)
                response = self.sharepoint_client.get(rel_url, query, LISTS)

                response_data = get_results(self.logger, response, LISTS)
                if not response_data:
                    self.logger.info(
                        "No list was created for the site : %s in this interval: start time: %s and end time: %s"
                        % (site, self.start_time, self.end_time)
                    )
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
                        doc = {"type": LIST}
                        for field, response_field in schema_list.items():
                            doc[field] = response_data[i].get(response_field)
                        if self.enable_permission is True:
                            doc["_allow_permissions"] = self.fetch_permissions(
                                key=LISTS,
                                site=site,
                                list_id=doc["id"],
                                list_url=response_data[i]["ParentWebUrl"],
                                itemid=None,
                            )
                        doc["url"] = urljoin(base_list_url, re.sub(r"[^ \w+]", "", response_data[i]["Title"]))
                        document.append(doc)
                        ids["lists"][site].update({doc["id"]: response_data[i]["Title"]})

                responses.append(response_data)
            lists = {}
            libraries = {}
            for response in responses:
                for result in response:
                    if result.get("BaseType") == 1:
                        libraries[result.get("Id")] = [
                            result.get("ParentWebUrl"),
                            result.get("Title"),
                            result.get("LastItemModifiedDate"),
                        ]
                    else:
                        lists[result.get("Id")] = [
                            result.get("ParentWebUrl"),
                            result.get("Title"),
                            result.get("LastItemModifiedDate"),
                        ]
        documents = {"type": LISTS, "data": document}
        return lists, libraries, documents

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
            self.logger.info(
                "No item was created in this interval: start time: %s and end time: %s"
                % (self.start_time, self.end_time)
            )
        else:
            for value in lists.values():
                if not ids["list_items"].get(value[0]):
                    ids["list_items"].update({value[0]: {}})
            schema_item = self.get_schema_fields(LIST_ITEMS)
            for list_content, value in lists.items():
                if parse(self.start_time) > parse(value[2]):
                    continue
                rel_url = f"{value[0]}/_api/web/lists(guid'{list_content}')/items"
                self.logger.info("Fetching the items for list: %s from url: %s" % (value[1], rel_url))

                query = self.sharepoint_client.get_query(self.start_time, self.end_time, LIST_ITEMS)
                response = self.sharepoint_client.get(rel_url, query, LIST_ITEMS)

                response_data = get_results(self.logger, response, LIST_ITEMS)
                if not response_data:
                    self.logger.info(
                        "No item was created for the list %s in this interval: start time: %s and end time: %s"
                        % (value[1], self.start_time, self.end_time)
                    )
                    continue
                self.logger.info(
                    "Successfully fetched and parsed %s listitem response for list: %s from SharePoint"
                    % (len(response_data), value[1])
                )

                list_name = re.sub(r"[^ \w+]", "", value[1])
                base_item_url = f"{value[0]}/Lists/{list_name}/DispForm.aspx?ID="
                document = []
                if not ids["list_items"][value[0]].get(list_content):
                    ids["list_items"][value[0]].update({list_content: []})
                rel_url = f"{value[0]}/_api/web/lists(guid'{list_content}')/items?$select=Attachments,AttachmentFiles,Title&$expand=AttachmentFiles"

                new_query = "&" + query.split("?")[1]
                file_response_data = self.sharepoint_client.get(rel_url, query=new_query, param_name="attachment")
                if file_response_data:
                    file_response_data = get_results(self.logger, file_response_data.json(), "attachment")

                for i, _ in enumerate(response_data):
                    doc = {"type": ITEM}
                    if response_data[i].get("Attachments") and file_response_data:
                        for data in file_response_data:
                            if response_data[i].get("Title") == data["Title"]:
                                file_relative_url = data["AttachmentFiles"]["results"][0]["ServerRelativeUrl"]
                                url_s = f"{value[0]}/_api/web/GetFileByServerRelativeUrl('{encode(file_relative_url)}')/$value"
                                response = self.sharepoint_client.get(url_s, query="", param_name="attachment")
                                doc["body"] = {}
                                if response and response.ok:
                                    try:
                                        doc["body"] = extract(response.content)
                                    except TikaException as exception:
                                        self.logger.error(
                                            "Error while extracting the contents from the attachment, Error %s"
                                            % (exception)
                                        )

                                break
                    for field, response_field in schema_item.items():
                        doc[field] = response_data[i].get(response_field)
                    if self.enable_permission is True:
                        doc["_allow_permissions"] = self.fetch_permissions(
                            key=LIST_ITEMS, list_id=list_content, list_url=value[0], itemid=str(response_data[i]["Id"])
                        )
                    doc["url"] = base_item_url + str(response_data[i]["Id"])
                    document.append(doc)
                    if response_data[i].get("GUID") not in ids["list_items"][value[0]][list_content]:
                        ids["list_items"][value[0]][list_content].append(response_data[i].get("GUID"))
                responses.extend(document)
        documents = {"type": LIST_ITEMS, "data": responses}
        return documents

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
            self.logger.info(
                "No file was created in this interval: start time: %s and end time: %s"
                % (self.start_time, self.end_time)
            )
        else:
            schema_drive = self.get_schema_fields(DRIVE_ITEMS)
            for lib_content, value in libraries.items():
                if parse(self.start_time) > parse(value[2]):
                    continue
                if not ids["drive_items"].get(value[0]):
                    ids["drive_items"].update({value[0]: {}})
                rel_url = f"{value[0]}/_api/web/lists(guid'{lib_content}')/items?$select=Modified,Id,GUID,File,Folder&$expand=File,Folder"
                self.logger.info("Fetching the items for libraries: %s from url: %s" % (value[1], rel_url))
                query = self.sharepoint_client.get_query(self.start_time, self.end_time, DRIVE_ITEMS)
                response = self.sharepoint_client.get(rel_url, query, DRIVE_ITEMS)
                response_data = get_results(self.logger, response, DRIVE_ITEMS)
                if not response_data:
                    self.logger.info(
                        "No item was created for the library %s in this interval: start time: %s and end time: %s"
                        % (value[1], self.start_time, self.end_time)
                    )
                    continue
                self.logger.info(
                    "Successfully fetched and parsed %s drive item response for library: %s from SharePoint"
                    % (len(response_data), value[1])
                )
                document = []
                if not ids["drive_items"][value[0]].get(lib_content):
                    ids["drive_items"][value[0]].update({lib_content: []})
                for i, _ in enumerate(response_data):
                    if response_data[i]["File"].get("TimeLastModified"):
                        obj_type = "File"
                        doc = {"type": "file"}
                        file_relative_url = response_data[i]["File"]["ServerRelativeUrl"]
                        url_s = f"{value[0]}/_api/web/GetFileByServerRelativeUrl('{encode(file_relative_url)}')/$value"
                        response = self.sharepoint_client.get(url_s, query="", param_name="attachment")
                        doc["body"] = {}
                        if response and response.ok:
                            try:
                                doc["body"] = extract(response.content)
                            except TikaException as exception:
                                self.logger.error(
                                    "Error while extracting the contents from the file at %s, Error %s"
                                    % (response_data[i].get("Url"), exception)
                                )
                    else:
                        obj_type = "Folder"
                        doc = {"type": "folder"}
                    for field, response_field in schema_drive.items():
                        doc[field] = response_data[i][obj_type].get(response_field)
                    doc["id"] = response_data[i].get("GUID")
                    if self.enable_permission is True:
                        doc["_allow_permissions"] = self.fetch_permissions(
                            key=DRIVE_ITEMS,
                            list_id=lib_content,
                            list_url=value[0],
                            itemid=str(response_data[i].get("ID")),
                        )
                    doc["url"] = response_data[i][obj_type]["ServerRelativeUrl"]
                    document.append(doc)
                    if doc["id"] not in ids["drive_items"][value[0]][lib_content]:
                        ids["drive_items"][value[0]][lib_content].append(doc["id"])
                responses.extend(document)
        documents = {"type": DRIVE_ITEMS, "data": responses}
        return documents

    def get_roles(self, key, site, list_url, list_id, itemid):
        """Checks the permissions and returns the user roles.
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
            roles = self.permissions.fetch_users(key, rel_url, list_id=list_id)

        else:
            rel_url = list_url
            roles = self.permissions.fetch_users(key, rel_url, list_id=list_id, item_id=itemid)

        return roles

    def fetch_permissions(
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

    def fetch_and_append_sites_to_queue(self, ids, end_time, collection):
        """Fetches and appends site details to queue
        :param ids: id collection of the all the objects
        :param end_time: end time for fetching the data
        :param collection: collection name
        """
        _, datelist = split_date_range_into_chunks(self.start_time, self.end_time, self.sharepoint_thread_count)
        results = []
        parent_site_url = f"/sites/{collection}"
        sites_path = [{parent_site_url: end_time}]
        for num in range(0, self.sharepoint_thread_count):
            start_time_partition = datelist[num]
            end_time_partition = datelist[num + 1]
            thread = self.thread_pool.apply_async(
                self.fetch_sites,
                (parent_site_url, {}, ids, (SITES in self.objects), start_time_partition, end_time_partition),
                callback=self.queue.append_to_queue,
            )
            results.append(thread)

        sites = []
        for result in [r.get() for r in results]:
            if result:
                sites.append(result[0])

        sites_path.extend(sites)
        return sites_path

    def fetch_and_append_lists_to_queue(self, sites_path, ids):
        """Fetches and appends list details to queue
        :param sites_path: dictionary of site path and it's last updated time
        :param ids: id collection of the all the objects
        """
        results, lists_details, libraries_details = [], {}, {}
        partitioned_sites = split_list_into_buckets(sites_path, self.sharepoint_thread_count)
        for site in partitioned_sites:
            thread = self.thread_pool.apply_async(
                self.fetch_lists, (site, ids, (LISTS in self.objects)), callback=self.queue.append_to_queue
            )
            results.append(thread)
        for result in [r.get() for r in results]:
            if result:
                lists_details.update(result[0])
                libraries_details.update(result[1])
        return [lists_details, libraries_details]

    def fetch_and_append_list_items_to_queue(self, lists_details, ids):
        """Fetches and appends list_items to the queue
        :param lists_details: dictionary containing list name, list path and id
        :param ids: id collection of the all the objects
        """
        partition = []
        partition = split_documents_into_equal_chunks(lists_details, self.sharepoint_thread_count)
        for list_data in partition:
            self.thread_pool.apply_async(self.fetch_items, (list_data, ids), callback=self.queue.append_to_queue)

    def fetch_and_append_drive_items_to_queue(self, libraries_details, ids):
        """Fetches and appends the drive items to the queue
        :param libraries_details: dictionary containing library name, library path and id
        :param ids: id collection of the all the objects
        """
        partition = []
        partition = split_documents_into_equal_chunks(libraries_details, self.sharepoint_thread_count)
        for list_data in partition:
            self.thread_pool.apply_async(self.fetch_drive_items, (list_data, ids), callback=self.queue.append_to_queue)

    def perform_sync(self, collection, ids, storage, job_type, collected_objects, end_time):
        """This method fetches all the objects from sharepoint server
        :param collection: collection name
        :param ids: id collection of the all the objects
        :param storage: temporary storage for storing all the documents
        :param job_type: denotes the type of sharepoint object being fetched in a particular process
        :param collected_objects: helper variable to provide the data to children object
        :param end_time: end time for fetching the data
        """
        if job_type == "sites":
            collected_objects = self.fetch_and_append_sites_to_queue(ids, end_time, collection)

        elif job_type == "lists":
            collected_objects = self.fetch_and_append_lists_to_queue(collected_objects, ids)

        elif job_type == LIST_ITEMS and LIST_ITEMS in self.objects:
            self.fetch_and_append_list_items_to_queue(collected_objects[0], ids)

        elif job_type == DRIVE_ITEMS and DRIVE_ITEMS in self.objects:
            self.fetch_and_append_drive_items_to_queue(collected_objects[1], ids)

        self.logger.info("Completed fetching all the objects for site collection: %s" % (collection))

        self.logger.info("Saving the checkpoint for the site collection: %s" % (collection))
        if ids.get(job_type):
            prev_ids = storage[job_type]
            if job_type == "sites":
                prev_ids.update(ids[job_type])
            elif job_type == "lists":
                for site, list_content in ids[job_type].items():
                    prev_ids[site] = {**prev_ids.get(site, {}), **ids[job_type][site]}
            else:
                for site, list_content in ids[job_type].items():
                    prev_ids[site] = ids[job_type][site] if not prev_ids.get(site) else prev_ids[site]
                    for list_name in list_content.keys():
                        prev_ids[site][list_name] = list(
                            set([*prev_ids[site].get(list_name, []), *ids[job_type][site][list_name]])
                        )
            storage[job_type] = prev_ids
        return collected_objects


def init_sharepoint_sync(indexing_type, config, logger, queue, args):
    """Initialize the process for synching
    :param indexing_type: The type of the indexing i.e. incremental or full
    :param config: instance of Configuration class
    :param logger: instance of Logger class
    :param queue: Shared queue to push the objects fetched from SharePoint
    :param args: The command line arguments passed from the base command
    """
    logger.info(f"Starting the {indexing_type} indexing..")
    current_time = (datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids_collection = {"global_keys": {}}
    storage_with_collection = {"global_keys": {}, "delete_keys": {}}
    # Added this workaround of initializing the base_command since workplace_search_client and sharepoint_client cannot be passed in the Process argument as doing so would throw pickling errors on Windows
    base_command = BaseCommand(args)
    workplace_search_client = base_command.workplace_search_client
    sharepoint_client = base_command.sharepoint_client

    if os.path.exists(IDS_PATH) and os.path.getsize(IDS_PATH) > 0:
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
            logger.info("Starting the data fetching for site collection: %s" % (collection))

            if indexing_type == "incremental":
                start_time, end_time = check.get_checkpoint(collection, current_time)
            else:
                start_time = config.get_value("start_time")
                end_time = current_time

            if not ids_collection["global_keys"].get(collection):
                ids_collection["global_keys"][collection] = {
                    "sites": {},
                    "lists": {},
                    "list_items": {},
                    "drive_items": {},
                }

            logger.info(
                "Starting to index all the objects configured in the object field: %s"
                % (str(config.get_value("objects")))
            )

            sync_sharepoint = SyncSharepoint(
                config, logger, workplace_search_client, sharepoint_client, start_time, end_time, queue
            )
            returned_documents = None
            for job_type in ["sites", "lists", "list_items", "drive_items"]:
                logger.info(f"Indexing {job_type}")
                returned_documents = sync_sharepoint.perform_sync(
                    collection,
                    ids_collection["global_keys"][collection],
                    storage,
                    job_type,
                    returned_documents,
                    end_time,
                )
            sync_sharepoint.thread_pool.close()
            sync_sharepoint.thread_pool.join()
            queue.put_checkpoint(collection, end_time, indexing_type)

            storage_with_collection["global_keys"][collection] = storage.copy()
        queue.end_signal()
    except Exception as exception:
        raise exception

    with open(IDS_PATH, "w") as file:
        try:
            json.dump(storage_with_collection, file, indent=4)
        except ValueError as exception:
            logger.warning("Error while adding ids to json file. Error: %s" % (exception))
