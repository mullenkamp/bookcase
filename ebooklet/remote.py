#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 15 08:36:26 2024

@author: mike
"""
import os
import uuid6
import urllib3
import booklet
from typing import Any, Generic, Iterator, Union, List, Dict
import s3func
import weakref
import orjson
import base64
# import msgspec

import utils
# from . import utils


###############################################
### Parameters

ebooklet_types = ('EVariableLengthValue', 'RemoteConnGroup')

###############################################
### Classes

# class ConnParams(msgspec.Struct):
#     db_key: str
#     bucket: str
#     endpoint_url: str
#     type: str
#     uuid: uuid6.UUID


class JsonSerializer:
    def dumps(self):
        d1 = dict(db_key=self.db_key,
                  bucket=self.bucket,
                  endpoint_url=self.endpoint_url,
                  ebooklet_type=self.ebooklet_type,
                  )
        uuid1 = self.uuid
        if uuid1 is not None:
            d1['uuid'] = uuid1.hex
        return orjson.dumps(
            d1
            )


class BaseConn(JsonSerializer):
    """

    """
    # def __enter__(self):
    #     return self

    # def __exit__(self, *args):
    #     self.close()

    def load_metadata(self, session):
        """

        """
        resp_obj = session.head_object(self.db_key)
        if resp_obj.status == 200:

            meta = resp_obj.metadata
        elif resp_obj.status == 404:
            meta = None
        else:
            raise urllib3.exceptions.HTTPError(resp_obj.error)

        if meta is None:
            self.uuid = None
            self.ebooklet_type = None
            # self.timestamp = None
        else:
            self.uuid = uuid6.UUID(hex=meta['uuid'])
            self.ebooklet_type = meta['ebooklet_type']
            # self.timestamp = int(meta['timestamp'])

        self.meta = meta


    def get_uuid(self, session):
        """

        """
        if self.uuid is None:
            self.get_metadata(session)

        return self.uuid


    def get_ebooklet_type(self, session):
        """

        """
        if self.ebooklet_type is None:
            self.get_metadata(session)

        return self.ebooklet_type

    # def uuid(self):
    #     """
    #     UUID of the remote object
    #     """
    #     raise NotImplementedError()

    def open(self):
        """

        """
        raise NotImplementedError()


class BaseConnOpenRead:
    """

    """
    def __bool__(self):
        """
        Test to see if remote read access is possible. Same as .read_access.
        """
        return self.read_access

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """
        Close the remote connection. Should return None.
        """
        if hasattr(self, '_finalizer'):
            self._finalizer()

    def load_metadata(self):
        """

        """
        resp_obj = self.head_db_object()
        if resp_obj.status == 200:
            meta = resp_obj.metadata
            self._init_bytes = base64.b64decode(meta['init_bytes'])

            self.timestamp = int(meta['timestamp'])
            self.uuid = uuid6.UUID(hex=meta['uuid'])
            self.ebooklet_type = meta['ebooklet_type']
        elif resp_obj.status == 404:
            self._init_bytes = None
            self.uuid = None
            self.timestamp = None
            self.ebooklet_type = None
        else:
            raise urllib3.exceptions.HTTPError(resp_obj.error)


    def get_uuid(self):
        """

        """
        if self.uuid is None:
            self.load_metadata()

        return self.uuid


    def get_ebooklet_type(self):
        """

        """
        if self.ebooklet_type is None:
            self.load_metadata()

        return self.ebooklet_type

    def get_timestamp(self):
        """

        """
        resp_obj = self.head_db_object()
        if resp_obj.status == 200:
            self.timestamp = int(resp_obj.metadata['timestamp'])

        elif resp_obj.status == 404:
            self.timestamp = None
        else:
            raise urllib3.exceptions.HTTPError(resp_obj.error)

        return self.timestamp

    # @property
    # def timestamp(self):
    #     """
    #     Timestamp as int_us of the last modified date
    #     """
    #     raise NotImplementedError()

    # @property
    # def readable(self):
    #     """
    #     Test to see if remote read access is possible. Returns a bool.
    #     """
    #     return True

    # @property
    # def writable(self):
    #     """
    #     Test to see if remote write access is possible. Returns a bool.
    #     """
    #     return False

    # def get_db_index_object(self):
    #     """

    #     """
    #     return self._session.get_object(self.db_key + '.remote_index')

    def get_db_object(self):
        """

        """
        return self._session.get_object(self.db_key)

    def head_db_object(self):
        """

        """
        resp_obj = self._session.head_object(self.db_key)

        return resp_obj

    def get_object(self, key: str):
        """
        Get a remote object/file. The input should be a key as a str. It should return an object with a .status attribute as an int, a .data attribute in bytes, and a .error attribute as a dict.
        """
        return self._session.get_object(self.db_key + '/' + key)

    def head_object(self, key: str):
        """
        Get the header for a remote object/file. The input should be a key as a str.
        """
        return self._session.head_object(self.db_key + '/' + key)


class BaseConnOpenReadWrite(BaseConnOpenRead):
    """

    """
    @property
    def writable(self):
        """

        """
        if not self._writable_check:
            test_key = self.db_key + uuid6.uuid6().hex[:13]
            put_resp = self._session.put_object(test_key, b'0')
            if put_resp.status // 100 == 2:
                self._writable = True
                _ = self._session.delete_object(test_key, put_resp.metadata['version_id'])

            self._writable_check = True

        return self._writable


    def put_db_object(self, data: bytes, metadata):
        """

        """
        if self.writable:
            return self._session.put_object(self.db_key, data, metadata=metadata)
        else:
            raise ValueError('Conn is not writable.')


    # def put_db_index_object(self, data: bytes, metadata={}):
    #     """

    #     """
    #     if self.writable:
    #         return self._session.put_object(self.db_key + '.remote_index', data, metadata=metadata)
    #     else:
    #         raise ValueError('Conn is not writable.')


    def put_object(self, key: str, data: bytes, metadata={}):
        """

        """
        if self.writable:
            return self._session.put_object(self.db_key + '/' + key, data, metadata=metadata)
        else:
            raise ValueError('Conn is not writable.')


    def delete_objects(self, keys):
        """
        Delete objects
        """
        if self.writable:
            del_list = []
            resp = self._session.list_object_versions(prefix=self.db_key + '/')
            for obj in resp.iter_objects():
                key0 = obj['key']
                key = key0.split('/')[-1]
                if key in keys:
                    del_list.append({'Key': key0, 'VersionId': obj['version_id']})

            if del_list:
                del_resp = self._session.delete_objects(del_list)
                if del_resp.status // 100 != 2:
                    raise urllib3.exceptions.HTTPError(del_resp.error)
        else:
            raise ValueError('Conn is not writable.')


    def delete_remote(self):
        """

        """
        if self.writable:
            del_list = []
            resp = self._session.list_object_versions(prefix=self.db_key)
            for obj in resp.iter_objects():
                key0 = obj['key']
                del_list.append({'Key': key0, 'VersionId': obj['version_id']})

            self._session.delete_objects(del_list)
            self._init_bytes = None
            self.uuid = None
        else:
            raise ValueError('Conn is not writable.')

    # def rebuild_index(self):
    #     """
    #     Rebuild the remote index file from all the objects in the remote.
    #     """
    #     if self.writable:
    #         resp = self._session.list_object_versions(prefix=self.db_key + '/')


    def list_objects(self):
        """

        """
        return self._session.list_objects(prefix=self.db_key)


    def list_object_versions(self):
        """

        """
        return self._session.list_object_versions(prefix=self.db_key)

    # def lock(self):
    #     """

    #     """
    #     if self.writable:
    #         lock = self._session.s3lock(self.db_key)
    #         return lock
    #     else:
    #         raise ValueError('Conn is not writable.')


# class BaseS3ConnOpenReadWrite(BaseConnOpenReadWrite):
#     """

#     """
#     def list_objects(self):
#         """

#         """
#         return self._session.list_objects(prefix=self.db_key)


#     def list_object_versions(self):
#         """

#         """
#         return self._session.list_object_versions(prefix=self.db_key)

#     def lock(self):
#         """

#         """
#         if self.writable:
#             lock = self._session.s3lock(self.db_key)
#             return lock
#         else:
#             raise ValueError('Conn is not writable.')


class S3Conn(BaseConn):
    """

    """
    def __init__(self,
                db_key: str,
                bucket: str,
                access_key_id: str=None,
                access_key: str=None,
                endpoint_url: str=None,
                threads: int=20,
                read_timeout: int=60,
                retries: int=3,
                uuid: Union[str, uuid6.UUID]=None,
                ebooklet_type: str=None,
                ):
        """

        """
        # if isinstance(db_url, str):
        #     http_remote = HttpConn(db_url, threads, read_timeout, retries, headers)
        # else:
        #     http_remote = None

        if not isinstance(access_key_id, str) or access_key_id is None:
            raise TypeError(access_key_id)

        if not isinstance(access_key, str) or access_key is None:
            raise TypeError(access_key)

        if not isinstance(endpoint_url, str) or endpoint_url is None:
            raise TypeError(endpoint_url)

        ## Assign properties
        self.db_key = db_key
        self.bucket = bucket
        self.access_key_id = access_key_id
        self.access_key = access_key

        if isinstance(endpoint_url, str):
            if not s3func.utils.is_url(endpoint_url):
                raise TypeError(f'{endpoint_url} is not a proper url.')
        self.endpoint_url = endpoint_url
        # self.connection_config = dict(
        #     service_name='s3',
        #     aws_access_key_id=access_key_id,
        #     aws_secret_access_key=access_key,
        #     endpoint_url=endpoint_url
        #     )
        self.threads = threads
        self.read_timeout = read_timeout
        self.retries = retries
        self.type = 's3_conn'
        # self._lock_timeout = lock_timeout
        # self.lock = lock

        ## Get uuid
        if isinstance(uuid, (str, uuid6.UUID)) and ebooklet_type in ebooklet_types:
            if isinstance(uuid, str):
                self.uuid = uuid6.UUID(hex=uuid)
            elif isinstance(uuid, uuid6.UUID):
                self.uuid = uuid
            self.ebooklet_type = ebooklet_type
        elif isinstance(access_key_id, str) and isinstance(access_key, str):
            self.load_metadata()
        else:
            self.uuid = None


    def load_metadata(self):
        """

        """
        session = s3func.S3Session(self.access_key_id, self.access_key, self.bucket, self.endpoint_url, self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        super().load_metadata(session)


    def get_uuid(self):
        """

        """
        session = s3func.S3Session(self.access_key_id, self.access_key, self.bucket, self.endpoint_url, self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        self.uuid = super().get_uuid(session)

        return self.uuid

    def get_ebooklet_type(self):
        """

        """
        session = s3func.S3Session(self.access_key_id, self.access_key, self.bucket, self.endpoint_url, self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        self.ebooklet_type = super().get_ebooklet_type(session)

        return self.ebooklet_type


    def add_credentials(self, access_key_id, access_key, endpoint_url: str=None):
        """

        """
        if isinstance(access_key_id, str):
            self.access_key_id = access_key_id
        else:
            raise TypeError(access_key_id)

        if isinstance(access_key, str):
            self.access_key = access_key
        else:
            raise TypeError(access_key)

        if isinstance(endpoint_url, str):
            if not s3func.utils.is_url(endpoint_url):
                raise TypeError(f'{endpoint_url} is not a proper url.')
            self.endpoint_url = endpoint_url
        elif endpoint_url is not None:
            raise TypeError(access_key)


    def open(self,
             object_lock=False,
             break_other_locks=False,
             lock_timeout=-1,
             ):
        """

        """
        if self.access_key_id is None or self.access_key is None:
            raise ValueError("access_key_id and access_key must be assigned to open a connection. Add them via the add_credentials method.")
        if self.uuid is None:
            self.get_uuid()

        return S3ConnOpen(self,
                          object_lock=False,
                          break_other_locks=False,
                          lock_timeout=-1,
                          )


class S3ConnOpen(BaseConnOpenReadWrite):
    """

    """
    def __init__(self,
                 s3_conn,
                 # check_timestamp=True,
                 object_lock=False,
                 break_other_locks=False,
                 lock_timeout=-1,
                ):
        """

        """
        ## Set up the session
        session = s3func.S3Session(s3_conn.access_key_id, s3_conn.access_key, s3_conn.bucket, s3_conn.endpoint_url, s3_conn.threads, read_timeout=s3_conn.read_timeout, stream=False, max_attempts=s3_conn.retries)
        self._session = session

        self.db_key = s3_conn.db_key
        # self._init_bytes = s3_conn._init_bytes
        self.uuid = s3_conn.uuid

        ## Check for read and write access
        # self._readable_check = False
        self._writable_check = False
        # self._readable = False
        self._writable = False


        self.get_init_bytes()

        if object_lock:
            lock = session.s3lock(self.db_key)

            if break_other_locks:
                lock.break_other_locks()

            lock.aquire(timeout=lock_timeout)
        else:
            lock = None

        # if check_timestamp:
        #     self.get_timestamp_db_object()
        # else:
        #     self.timestamp = None

        ## Finalizer
        self._finalizer = weakref.finalize(self, utils.s3remote_finalizer, self._session, lock)

        ## Assign properties
        # self._bucket = s3_conn.bucket
        # self._connection_config = s3_conn.connection_config
        # self._threads = s3_conn.threads
        # self._read_timeout = s3_conn.read_timeout
        # self._retries = s3_conn.retries
        self.type = 's3_conn_open'
        self._conn = s3_conn
        # self._lock_timeout = lock_timeout
        self.lock = lock


class HttpConn(BaseConn):
    """
    Only get requests work.
    """
    def __init__(self,
                db_url: str,
                threads: int=20,
                read_timeout: int=60,
                retries: int=3,
                headers=None,
                uuid: Union[str, uuid6.UUID]=None,
                ebooklet_type: str=None,
                ):
        """

        """
        ## Assign properties
        self.db_key = db_url
        self.threads = threads
        self.read_timeout = read_timeout
        self.retries = retries
        self._headers = headers
        self.type = 'http_conn'

        ## Get uuid
        if isinstance(uuid, (str, uuid6.UUID)) and ebooklet_type in ebooklet_types:
            if isinstance(uuid, str):
                self.uuid = uuid6.UUID(hex=uuid)
            elif isinstance(uuid, uuid6.UUID):
                self.uuid = uuid
            self.ebooklet_type = ebooklet_type
        else:
            self.load_metadata()

    def load_metadata(self):
        """

        """
        session = s3func.HttpSession(self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        super().load_metadata(session)


    def get_uuid(self):
        """

        """
        session = s3func.HttpSession(self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        self.uuid = super().get_uuid(session)

        return self.uuid

    def get_ebooklet_type(self):
        """

        """
        session = s3func.HttpSession(self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        self.ebooklet_type = super().get_ebooklet_type(session)

        return self.ebooklet_type


    def open(self):
        """

        """
        return HttpConnOpen(self)


class HttpConnOpen(BaseConnOpenRead):
    """
    Only get requests work.
    """
    def __init__(self,
                http_conn,
                # check_timestamp=True,
                ):
        """

        """
        # self._readable_check = False
        # self._writable_check = False
        # self._readable = False
        self.writable = False

        session = s3func.HttpSession(http_conn.threads, read_timeout=http_conn.read_timeout, stream=False, max_attempts=http_conn.retries)
        self._session = session
        self.db_key = http_conn.db_key
        # self._init_bytes = http_conn._init_bytes
        self.uuid = http_conn.uuid

        self.get_init_bytes()

        # if check_timestamp:
        #     self.get_timestamp_db_object()
        # else:
        #     self.timestamp = None

        self._finalizer = weakref.finalize(self, session._session.clear)

        ## Assign properties
        # self._threads = http_conn.threads
        # self._read_timeout = http_conn.read_timeout
        # self._retries = http_conn.retries
        # self._headers = http_conn._headers
        self.type = 'http_conn_open'
        self._conn = http_conn


class Conn(BaseConn):
    """

    """
    def __init__(self,
                db_key: str=None,
                bucket: str=None,
                access_key_id: str=None,
                access_key: str=None,
                endpoint_url: str=None,
                db_url: str=None,
                threads: int=20,
                read_timeout: int=60,
                retries: int=3,
                headers=None,
                uuid: Union[str, uuid6.UUID]=None,
                ebooklet_type: str=None,
                ):
        """

        """
        # if isinstance(http_conn, HttpConn):
        #     http_conn = http_conn
        # elif isinstance(db_url, str):
        #     http_conn = HttpConn(db_url, threads, read_timeout, retries, headers)
        # else:
        #     http_conn = None

        # if isinstance(s3_conn, S3Conn):
        #     s3_conn = s3_conn
        # elif isinstance(db_key, str) and isinstance(bucket, str):
        #     s3_conn = S3Conn(db_key, bucket, access_key_id, access_key, endpoint_url, threads, read_timeout, retries)
        # else:
        #     s3_conn = None

        # if http_conn is None and s3_conn is None:
        #     raise ValueError('Both connections are None.')

        # self.http_conn = http_conn
        # self.s3_conn = s3_conn
        # self.type = 'conn'

        # self.check_uuids()

        if not isinstance(access_key_id, str) or access_key_id is None:
            raise TypeError(access_key_id)

        if not isinstance(access_key, str) or access_key is None:
            raise TypeError(access_key)

        if not isinstance(endpoint_url, str) or endpoint_url is None:
            raise TypeError(endpoint_url)

        ## Assign properties
        self.db_key = db_key
        self.bucket = bucket
        self.access_key_id = access_key_id
        self.access_key = access_key

        if isinstance(endpoint_url, str):
            if not s3func.utils.is_url(endpoint_url):
                raise TypeError(f'{endpoint_url} is not a proper url.')
        self.endpoint_url = endpoint_url

        if isinstance(db_url, str):
            if not s3func.utils.is_url(db_url):
                raise TypeError(f'{db_url} is not a proper url.')
        self.db_url = db_url

        self.threads = threads
        self.read_timeout = read_timeout
        self.retries = retries
        self.type = 'conn'
        # self._lock_timeout = lock_timeout
        # self.lock = lock

        ## Get uuid
        if isinstance(uuid, (str, uuid6.UUID)) and ebooklet_type in ebooklet_types:
            if isinstance(uuid, str):
                self.uuid = uuid6.UUID(hex=uuid)
            elif isinstance(uuid, uuid6.UUID):
                self.uuid = uuid
            self.ebooklet_type = ebooklet_type
        elif isinstance(access_key_id, str) and isinstance(access_key, str):
            self.load_metadata()
        else:
            if isinstance(access_key_id, str) and isinstance(access_key, str):
                self.load_metadata()
            self.uuid = None


    def _make_http_session(self):
        """

        """
        session = s3func.HttpSession(self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        return session

    def _make_s3_session(self):
        """

        """
        session = s3func.S3Session(self.access_key_id, self.access_key, self.bucket, self.endpoint_url, self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        return session

    def load_metadata(self):
        """

        """
        session = s3func.S3Session(self.access_key_id, self.access_key, self.bucket, self.endpoint_url, self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        super().load_metadata(session)


    def get_uuid(self):
        """

        """
        session = s3func.S3Session(self.access_key_id, self.access_key, self.bucket, self.endpoint_url, self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        self.uuid = super().get_uuid(session)

        return self.uuid

    def get_ebooklet_type(self):
        """

        """
        session = s3func.S3Session(self.access_key_id, self.access_key, self.bucket, self.endpoint_url, self.threads, read_timeout=self.read_timeout, stream=False, max_attempts=self.retries)

        self.ebooklet_type = super().get_ebooklet_type(session)

        return self.ebooklet_type


    def add_credentials(self, access_key_id, access_key, endpoint_url: str=None):
        """

        """
        if isinstance(access_key_id, str):
            self.access_key_id = access_key_id
        else:
            raise TypeError(access_key_id)

        if isinstance(access_key, str):
            self.access_key = access_key
        else:
            raise TypeError(access_key)

        if isinstance(endpoint_url, str):
            if not s3func.utils.is_url(endpoint_url):
                raise TypeError(f'{endpoint_url} is not a proper url.')
            self.endpoint_url = endpoint_url
        elif endpoint_url is not None:
            raise TypeError(access_key)


    def open(self,
             object_lock=False,
             break_other_locks=False,
             lock_timeout=-1,
             ):
        """

        """
        if self.access_key_id is None or self.access_key is None:
            raise ValueError("access_key_id and access_key must be assigned to open a connection. Add them via the add_credentials method.")
        if self.uuid is None:
            self.get_uuid()

        return S3ConnOpen(self,
                          object_lock=False,
                          break_other_locks=False,
                          lock_timeout=-1,
                          )


    def add_credentials(self, access_key_id, access_key, endpoint_url: str=None):
        """

        """
        if isinstance(access_key_id, str):
            self.access_key_id = access_key_id
        else:
            raise TypeError(access_key_id)

        if isinstance(access_key, str):
            self.access_key = access_key
        else:
            raise TypeError(access_key)

        if isinstance(endpoint_url, str):
            if not s3func.utils.is_url(endpoint_url):
                raise TypeError(f'{endpoint_url} is not a proper url.')
            self.endpoint_url = endpoint_url
        elif endpoint_url is not None:
            raise TypeError(access_key)


    def check_uuids(self):
        """

        """
        if isinstance(self.s3_conn.uuid, uuid6.UUID):
            assert self.s3_conn.uuid == self.http_conn.uuid


    def open(self,
             object_lock=False,
             break_other_locks=False,
             lock_timeout=-1,
             ):
        """

        """
        return ConnOpen(self,
                        object_lock=False,
                        break_other_locks=False,
                        lock_timeout=-1,
                        )


class ConnOpen:
    """

    """
    def __init__(self,
                 conn,
                 # check_timestamp=True,
                 object_lock=False,
                 break_other_locks=False,
                 lock_timeout=-1,
                 ):
        """

        """
        if conn.s3_conn is not None:
            s3_conn_open = conn.s3_conn.open(
                object_lock=False,
                break_other_locks=False,
                lock_timeout=-1,
                )
        else:
            s3_conn_open = None

        if conn.http_conn is not None:
            http_conn_open = conn.http_conn.open()
        else:
            http_conn_open = None

        conn.check_uuids()

        self.s3_conn_open = s3_conn_open
        self.http_conn_open = http_conn_open
        self.type = 'conn_open'
        self._conn = conn

        def close(self):
            if self.s3_conn_open is not None:
                self.s3_conn_open.close()

            if self.http_conn_open is not None:
                self.http_conn_open.close()



























































