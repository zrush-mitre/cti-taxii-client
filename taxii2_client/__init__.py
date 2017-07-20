import os

import requests

os.environ["NO_PROXY"] = "localhost"

MEDIA_TYPE_STIX_V20 = "application/vnd.oasis.stix+json; version=2.0"
MEDIA_TYPE_TAXII_V20 = "application/vnd.oasis.taxii+json; version=2.0"


# TODO: Should this object allow refreshing itself (have its own URL?)
class Status(object):
    def __init__(self, id, status, total_count, success_count, failure_count, pending_count, request_timestamp=None,
                 successes=None, failures=None, pendings=None):
        self.id_ = id
        self.status = status
        self.total_count = total_count
        self.success_count = success_count
        self.failure_count = failure_count
        self.pending_count = pending_count


class Collection(object):
    def __init__(self, url, client=None, **kwargs):
        self.url = url

        self._client = client
        self._loaded = False

        # Since the API Root "Get Collections" endpoint returns information on
        # all collections as a list, it's possible that we can create multiple
        # Collection objects from a single HTTPS request, and not need to call
        # `refresh` for each one.
        if kwargs:
            self._populate_fields(**kwargs)
            self._loaded = True

    @property
    def id(self):
        self._ensure_loaded()
        return self._id

    @property
    def title(self):
        self._ensure_loaded()
        return self._title

    @property
    def description(self):
        self._ensure_loaded()
        return self._description

    @property
    def can_read(self):
        self._ensure_loaded()
        return self._can_read

    @property
    def can_write(self):
        self._ensure_loaded()
        return self._can_write

    @property
    def media_types(self):
        self._ensure_loaded()
        return self._media_types

    def _populate_fields(self, **kwargs):
        self._id = kwargs.pop('id', None)
        # TODO: ensure id doesn't change (or at least matches self.url)
        self._title = kwargs.pop('title', None)
        self._description = kwargs.pop('description', None)
        self._can_read = kwargs.pop('can_read', False)
        self._can_write = kwargs.pop('can_write', False)
        self._media_types = kwargs.pop('media_types', [])

        # TODO: Check for unexpected kwargs

    def _ensure_loaded(self):
        if not self._loaded:
            self.refresh()

    def refresh(self):
        response = self._client.get(self.url)
        self._populate_fields(**response)

        self._loaded = True

    # TODO: update this function
    def get_object(self, obj_id):
        if not self.can_read:
            raise ValueError("Collection %s of %s does not allow reading" % (self.id_, self.api_root.uri))
        return self.taxii_client.send_request("get",
                                              "/".join([self.api_root.url, "collections", self.id_, "objects", obj_id]),
                                              {"Accept": MEDIA_TYPE_STIX_V20})

    # TODO: update this function
    def get_objects(self, filters=None):
        if not self.can_read:
            raise ValueError("Collection %s of %s does not allow reading" % (self.id_, self.api_root.uri))
        return self.taxii_client.send_request("get",
                                              "/".join([self.api_root.url, "collections", self.id_, "objects"]),
                                              {"Accept": MEDIA_TYPE_STIX_V20},
                                              params=filters)

    # TODO: update this function
    def add_objects(self, bundle):
        if not self.can_write:
            raise ValueError("Collection %s of %s does not allow writing" % (self.id_, self.api_root.uri))
        info = self.taxii_client.send_request("post",
                                              "/".join([self.api_root.url, "collections", self.id_, "objects"])+"/",
                                              {"Accept": MEDIA_TYPE_TAXII_V20,
                                               "Content-Type": MEDIA_TYPE_STIX_V20},
                                              json=bundle)
        return Status(**info)

    # TODO: update this function
    def get_manifest(self, filters=None):
        return self.taxii_client.send_request("get",
                                              "/".join([self.api_root.url, "collections", self.id_, "manifest"]),
                                              {"Accept": MEDIA_TYPE_TAXII_V20})


class ApiRoot(object):

    def __init__(self, url, client=None):
        self.url = url

        self._client = client
        self._loaded_collections = False
        self._loaded_information = False

        # TODO: Consider adding a `name` @property: the last URL path component
        # self.name = name

    @property
    def collections(self):
        if not self._loaded_collections:
            self.refresh_collections()
        return self._collections

    @property
    def title(self):
        self._ensure_loaded_information()
        return self._title

    @property
    def description(self):
        self._ensure_loaded_information()
        return self._description

    @property
    def versions(self):
        self._ensure_loaded_information()
        return self._versions

    @property
    def max_content_length(self):
        self._ensure_loaded_information()
        return self._max_content_length

    def _ensure_loaded_information(self):
        if not self._loaded_information:
            self.refresh_information()

    def refresh():
        self.refresh_information()
        self.refresh_collections()

    def refresh_information(self):
        response = self._client.get(self.url)

        self._title = response['title']
        self._description = response['description']
        self._versions = response['versions']
        self._max_content_length = response['max_content_length']

        self._loaded_information = True

    def refresh_collections(self):
        url = self.url + 'collections/'
        response = self._client.get(url)  # {"Accept": MEDIA_TYPE_TAXII_V20})

        self._collections = []
        print(response)
        for item in response['collections']:
            collection_url = url + item['id'] + "/"
            collection = Collection(collection_url, client=self._client, **item)
            self._collections.append(collection)

        self._loaded_collections = True

    # TODO: update this function
    def get_collection(self, id_, refresh=False):
        for c in self.get_collections(refresh):
            if c.id_ == id_:
                return c

    # TODO: update this function
    def get_status(self, id_):
        info = self.taxii_client.send_request("get",
                                              "/".join([self.url, "status", id_]),
                                              {"Accept": MEDIA_TYPE_TAXII_V20})
        return Status(**info)


class ServerInfo(object):

    def __init__(self, hostname, client=None):
        self.hostname = hostname

        self._client = client
        self._loaded = False

    @property
    def title(self):
        self._ensure_loaded()
        return self._title

    @property
    def description(self):
        self._ensure_loaded()
        return self._description

    @property
    def contact(self):
        self._ensure_loaded()
        return self._contact

    @property
    def default(self):
        self._ensure_loaded()
        return self._default

    @property
    def api_roots(self):
        self._ensure_loaded()
        return self._api_roots

    def _ensure_loaded(self):
        if not self._loaded:
            self.refresh()

    def refresh(self):
        # TODO: ensure client exists
        url = "https://{}/taxii/".format(self.hostname)
        response = self._client.get(url)  # {"Accept": MEDIA_TYPE_TAXII_V20})

        self._title = response['title']
        self._description = response['description']
        self._contact = response['contact']
        # TODO: if same URL is in api_roots, re-use the same object
        self._default = ApiRoot(response['default'], client=self._client)
        self._api_roots = [ApiRoot(url, client=self._client)
                           for url in response['api_roots']]

        self._loaded = True


class TAXII2Client(object):

    def __init__(self, user, password):
        self.session = requests.Session()
        self.session.auth = requests.auth.HTTPBasicAuth(user, password)

    def get(self, url, headers=None, params=None):
        resp = self.session.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, url, headers=None, param=None, json=None):
        resp = self.session.post(url, headers=headers, params=params, json=json)
        resp.raise_for_status()
        return resp.json()


# TODO: are these needed?
def canonicalize_api_root_url(api_root_url):
    if api_root_url.endswith("/"):
        api_root_url = api_root_url[:-1]
    return api_root_url


def get_api_root_name(api_root_url):
    if api_root_url.endswith("/"):
        api_root_url = api_root_url[:-1]
    return api_root_url.split('/')[-1]
