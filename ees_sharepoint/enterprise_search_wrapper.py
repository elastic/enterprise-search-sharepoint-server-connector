#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module perform operations related to Enterprise Search based on the Enterprise Search version
"""
from elastic_enterprise_search import WorkplaceSearch, __version__
from packaging import version

ENTERPRISE_V8 = version.parse("8.0")


class EnterpriseSearchWrapper:
    """This class contains operations related to Enterprise Search such as index documents, delete documents, etc."""

    def __init__(self, logger, config, args):
        self.logger = logger
        self.version = version.parse(__version__)
        self.host = config.get_value("enterprise_search.host_url")
        self.api_key = config.get_value("workplace_search.api_key")
        self.ws_source = config.get_value("workplace_search.source_id")
        if self.version >= ENTERPRISE_V8:
            if hasattr(args, "user") and args.user:
                self.workplace_search_client = WorkplaceSearch(
                    self.host, bearer_auth=(args.user, args.password)
                )
            else:
                self.workplace_search_client = WorkplaceSearch(
                    self.host,
                    bearer_auth=self.api_key,
                )
        else:
            if hasattr(args, "user") and args.user:
                self.workplace_search_client = WorkplaceSearch(
                    f"{self.host}/api/ws/v1/sources",
                    http_auth=(args.user, args.password),
                )
            else:
                self.workplace_search_client = WorkplaceSearch(
                    f"{self.host}/api/ws/v1/sources", http_auth=self.api_key
                )

    def add_permissions(self, user_name, permission_list):
        """Add one or more permission for a given user. Permissions are added atop the existing.
        :param user_name: user to assign permissions
        :param permission_list: list of permissions
        """
        try:
            if self.version >= ENTERPRISE_V8:
                from elastic_enterprise_search.exceptions import ConflictError

                external_user_properties = [
                    {
                        "attribute_name": "_elasticsearch_username",
                        "attribute_value": user_name,
                    }
                ]
                try:
                    self.workplace_search_client.create_external_identity(
                        content_source_id=self.ws_source,
                        external_user_id=user_name,
                        external_user_properties=external_user_properties,
                        permissions=permission_list,
                    )
                except ConflictError:
                    self.logger.debug(
                        f"External entity :{user_name}  already exits. Trying to update the existing permissions.."
                    )
                    self.workplace_search_client.put_external_identity(
                        content_source_id=self.ws_source,
                        external_user_id=user_name,
                        external_user_properties=external_user_properties,
                        permissions=permission_list,
                    )
            else:
                self.workplace_search_client.add_user_permissions(
                    content_source_id=self.ws_source,
                    user=user_name,
                    body={"permissions": permission_list},
                )
            self.logger.info(
                f"Successfully indexed the permissions for user {user_name} to the workplace"
            )
        except Exception as exception:
            self.logger.exception(
                f"Error while indexing the permissions for user: {user_name} to the workplace. Error: {exception}"
            )

    def list_permissions(self):
        """List permissions for one or all users"""
        user_permission = []
        try:
            if self.version >= ENTERPRISE_V8:
                user_permission = self.workplace_search_client.list_external_identities(
                    content_source_id=self.ws_source
                )
            else:
                user_permission = self.workplace_search_client.list_permissions(
                    content_source_id=self.ws_source,
                )
            self.logger.info(
                "Successfully retrieves all permissions from the workplace"
            )
        except Exception as exception:
            self.logger.exception(
                f"Error while retrieving the permissions from the workplace. Error: {exception}"
            )
        return user_permission

    def remove_permissions(self, permission):
        """Removes one or more permissions from an existing set of permissions
        :param permission: dictionary containing permission of perticular user
        """
        try:
            if self.version >= ENTERPRISE_V8:
                user_name = permission["external_user_properties"][0]["attribute_value"]
                self.workplace_search_client.delete_external_identity(
                    content_source_id=self.ws_source, external_user_id=user_name
                )
            else:
                user_name = permission["user"]
                self.workplace_search_client.remove_user_permissions(
                    content_source_id=self.ws_source,
                    user=user_name,
                    body={"permissions": permission["permissions"]},
                )
            self.logger.info("Successfully removed the permissions from the workplace.")
        except Exception as exception:
            self.logger.exception(
                f"Error while removing the permissions from the workplace. Error: {exception}"
            )

    def create_content_source(self, schema, display, name, is_searchable):
        """Create a content source
        :param schema: schema of the content source
        :param display: display schema for the content source
        :param name: name of the content source
        :param is_searchable: boolean to indicate source is searchable or not
        """
        try:
            if self.version >= ENTERPRISE_V8:
                response = self.workplace_search_client.create_content_source(
                    name=name,
                    schema=schema,
                    display=display,
                    is_searchable=is_searchable,
                )
            else:
                body = {
                    "name": name,
                    "schema": schema,
                    "display": display,
                    "is_searchable": is_searchable,
                }
                response = self.workplace_search_client.create_content_source(body=body)
            content_source_id = response.get("id")
            self.logger.info(
                f"Created ContentSource with ID {content_source_id}. \
                    You may now begin indexing with content-source-id= {content_source_id}"
            )
        except Exception as exception:
            self.logger.error(f"Could not create a content source, Error {exception}")

    def delete_documents(self, document_ids):
        """Deletes a list of documents from a custom content source
        :param document_ids: list of document ids to be deleted from Enterprise Search
        """
        try:
            self.workplace_search_client.delete_documents(
                content_source_id=self.ws_source,
                document_ids=document_ids,
            )
        except Exception as exception:
            self.logger.exception(
                f"Error while checking for deleted documents. Error: {exception}"
            )

    def index_documents(self, documents, timeout):
        """Indexes one or more new documents into a custom content source, or updates one
        or more existing documents
        :param documents: list of documents to be indexed
        :param timeout: Timeout in seconds
        """
        try:
            responses = self.workplace_search_client.index_documents(
                content_source_id=self.ws_source,
                documents=documents,
                request_timeout=timeout,
            )
        except Exception as exception:
            self.logger.exception(f"Error while indexing the documents. Error: {exception}")
            raise exception
        return responses
