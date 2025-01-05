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
import copy
# import msgspec

# import utils
from . import utils


###############################################
### Parameters

ebooklet_types = ('EVariableLengthValue', 'RemoteConnGroup')


###############################################
### Functions


def get_db_metadata(session, db_key):
    """

    """
    resp_obj = session.head_object(db_key)
    if resp_obj.status == 200:

        meta = resp_obj.metadata
    elif resp_obj.status == 404:
        meta = None
    else:
        raise urllib3.exceptions.HTTPError(resp_obj.error)

    if meta is None:
        return dict(uuid=None, timestamp=None, ebooklet_type=None)
    else:
        meta['uuid'] = uuid6.UUID(hex=meta['uuid'])
        # self.uuid = uuid6.UUID(hex=meta['uuid'])
        # self.ebooklet_type = meta['ebooklet_type']
        # self.timestamp = int(meta['timestamp'])
        return meta


def get_user_metadata(session, db_key):
    """

    """
    resp_obj = session.get_object(f'{db_key}/{booklet.utils.metadata_key_bytes.decode()}')
    if resp_obj.status == 200:

        meta = orjson.loads(resp_obj.data)
    elif resp_obj.status == 404:
        meta = None
    else:
        raise urllib3.exceptions.HTTPError(resp_obj.error)

    return meta


def check_write_config(
        access_key_id: str=None,
        access_key: str=None,
        db_key: str=None,
        bucket: str=None,
        endpoint_url: str=None,
        ):
    """

    """
    if isinstance(access_key_id, str) and isinstance(access_key, str) and isinstance(db_key, str) and isinstance(bucket, str):
        if isinstance(endpoint_url, str):
            if not s3func.utils.is_url(endpoint_url):
                raise TypeError(f'{endpoint_url} is not a proper url.')
        return True
    return False


def create_s3_read_session(
        access_key_id: str=None,
        access_key: str=None,
        db_key: str=None,
        bucket: str=None,
        endpoint_url: str=None,
        db_url: str=None,
        threads: int=20,
        read_timeout: int=60,
        retries: int=3,
        ):
    """

    """
    if isinstance(db_url, str):
        if not s3func.utils.is_url(db_url):
            raise TypeError(f'{db_url} is not a proper url.')
        read_session = s3func.HttpSession(threads, read_timeout=read_timeout, stream=False, max_attempts=retries)
        key = db_url
    elif isinstance(access_key_id, str) and isinstance(access_key, str) and isinstance(db_key, str) and isinstance(bucket, str):
        if isinstance(endpoint_url, str):
            if not s3func.utils.is_url(endpoint_url):
                raise TypeError(f'{endpoint_url} is not a proper url.')
        read_session = s3func.S3Session(access_key_id, access_key, bucket, endpoint_url, threads, read_timeout=read_timeout, stream=False, max_attempts=retries)
        key = db_key
    else:
        read_session = None
        # raise ValueError('Either db_url or a combo of access_key_id, access_key, db_key, and bucket (and optionally endpoint_url) must be passed.')

    return read_session, key


def create_s3_write_session(
        access_key_id: str=None,
        access_key: str=None,
        db_key: str=None,
        bucket: str=None,
        endpoint_url: str=None,
        threads: int=20,
        read_timeout: int=60,
        retries: int=3,
        ):
    """

    """
    if check_write_config(access_key_id, access_key, db_key, bucket, endpoint_url):
        write_session = s3func.S3Session(access_key_id, access_key, bucket, endpoint_url, threads, read_timeout=read_timeout, stream=False, max_attempts=retries)
    else:
        write_session = None
        # raise ValueError('Either db_url or a combo of access_key_id, access_key, db_key, and bucket (and optionally endpoint_url) must be passed.')

    return write_session, db_key


# def create_connection(
#         access_key_id: str=None,
#         access_key: str=None,
#         db_key: str=None,
#         bucket: str=None,
#         endpoint_url: str=None,
#         db_url: str=None,
#         threads: int=20,
#         read_timeout: int=60,
#         retries: int=3,
#         meta: dict={},
#         ):
#     """

#     """
#     ## temp read session
#     read_session, key = create_s3_read_session(
#             access_key_id,
#             access_key,
#             db_key,
#             bucket,
#             endpoint_url,
#             db_url,
#             threads,
#             read_timeout,
#             retries,
#             )
#     if read_session is None:
#         raise ValueError('Either db_url or a combo of access_key_id, access_key, db_key, and bucket (and optionally endpoint_url) must be passed.')

#     ## Get metadata if necessary
#     if all([k in meta for k in ('uuid', 'ebooklet_type', 'user_meta')]):
#         uuid = meta['uuid']
#         if isinstance(uuid, (str, uuid6.UUID)):
#             if isinstance(uuid, str):
#                 meta['uuid'] = uuid6.UUID(hex=uuid)
#             else:
#                 raise TypeError('uuid in meta must be either a string or UUID')

#         ebooklet_type = meta['ebooklet_type']
#         if ebooklet_type not in ebooklet_types:
#             raise ValueError(f'ebooklet_type in meta must be one of {ebooklet_types}')
#         if not isinstance(meta['user_meta'], dict):
#             raise TypeError('user_meta in meta must be a dict')
#     else:
#         meta = get_db_metadata(read_session, key)
#     read_session.clear()










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
                  db_url=self.db_url,
                  # ebooklet_type=self.ebooklet_type,
                  # timestamp=self.timestamp,
                   user_meta=self.user_meta,
                  )
        db_meta = dict(
            ebooklet_type=self.ebooklet_type,
            timestamp=self.timestamp,
            )
        uuid1 = self.uuid
        if uuid1 is not None:
            db_meta['uuid'] = uuid1.hex
        else:
            db_meta['uuid'] = None
        d1['db_meta'] = db_meta

        return orjson.dumps(
            d1
            )


class S3SessionReader:
    """

    """
    def __init__(self,
                 read_session,
                 read_db_key,
                 threads,
                 # timestamp,
                 # uuid,
                 # ebooklet_type,
                 # init_bytes,
                 ):
        self._read_session = read_session
        self.read_db_key = read_db_key
        self.threads = threads
        # self.timestamp = timestamp
        # self.uuid = uuid
        # self.ebooklet_type = ebooklet_type
        # self.init_bytes = init_bytes
        self.load_db_metadata()

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

    def load_db_metadata(self):
        """

        """
        resp_obj = self._read_session.head_object(self.read_db_key)
        if resp_obj.status == 200:
            meta = resp_obj.metadata
            self._init_bytes = base64.urlsafe_b64decode(meta['init_bytes'])
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
        return self._read_session.get_object(self.read_db_key)

    # def head_db_object(self):
    #     """

    #     """
    #     resp_obj = self.read_session.head_object(self.db_key)

    #     return resp_obj

    def get_object(self, key: str):
        """
        Get a remote object/file. The input should be a key as a str. It should return an object with a .status attribute as an int, a .data attribute in bytes, and a .error attribute as a dict.
        """
        return self._read_session.get_object(self.read_db_key + '/' + key)

    # def head_object(self, key: str):
    #     """
    #     Get the header for a remote object/file. The input should be a key as a str.
    #     """
    #     return self.read_session.head_object(self.db_key + '/' + key)


class S3SessionWriter(S3SessionReader):
    """

    """
    def __init__(self,
                 read_session,
                 write_session,
                 read_db_key,
                 write_db_key,
                 threads,
                 # timestamp,
                 # uuid,
                 # ebooklet_type,
                 # init_bytes,
                 object_lock=False,
                 break_other_locks=False,
                 lock_timeout=-1
                 ):
        self._read_session = read_session
        self._write_session = write_session
        self.read_db_key = read_db_key
        self.write_db_key = write_db_key
        self.threads = threads
        # self.timestamp = timestamp
        # self.uuid = uuid
        # self.ebooklet_type = ebooklet_type
        # self.init_bytes = init_bytes

        if object_lock:
            lock = write_session.s3lock(self.write_db_key)

            if break_other_locks:
                lock.break_other_locks()

            lock.aquire(timeout=lock_timeout)

            self._writable_check = True
            self._writable = True
        else:
            lock = None

            self._writable_check = False
            self._writable = False

        ## Finalizer
        self._finalizer = weakref.finalize(self, utils.s3session_finalizer, self._write_session, lock)

        ## Get latest metadata
        self.load_db_metadata()

    @property
    def writable(self):
        """
        Should I include this? Or should I simply let the other methods fail if it's not writable? I do like having an explicit test...
        """
        if not self._writable_check:
            test_key = self.write_db_key + uuid6.uuid6().hex[:13]
            put_resp = self._write_session.put_object(test_key, b'0')
            if put_resp.status // 100 == 2:
                del_resp = self._write_session.delete_object(test_key, put_resp.metadata['version_id'])
                if del_resp.status // 100 == 2:
                    self._writable = True

            self._writable_check = True

        return self._writable


    def put_db_object(self, data: bytes, metadata):
        """

        """
        if self.writable:
            return self._write_session.put_object(self.write_db_key, data, metadata=metadata)
        else:
            raise ValueError('Session is not writable.')


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
            return self._write_session.put_object(self.write_db_key + '/' + key, data, metadata=metadata)
        else:
            raise ValueError('Session is not writable.')


    def delete_objects(self, keys):
        """
        Delete objects
        """
        if self.writable:
            del_list = []
            resp = self._write_session.list_object_versions(prefix=self.write_db_key + '/')
            for obj in resp.iter_objects():
                key0 = obj['key']
                key = key0.split('/')[-1]
                if key in keys:
                    del_list.append({'Key': key0, 'VersionId': obj['version_id']})

            if del_list:
                del_resp = self._write_session.delete_objects(del_list)
                if del_resp.status // 100 != 2:
                    raise urllib3.exceptions.HTTPError(del_resp.error)
        else:
            raise ValueError('Session is not writable.')


    def delete_remote(self):
        """

        """
        if self.writable:
            del_list = []
            resp = self._write_session.list_object_versions(prefix=self.write_db_key)
            for obj in resp.iter_objects():
                key0 = obj['key']
                del_list.append({'Key': key0, 'VersionId': obj['version_id']})

            self._write_session.delete_objects(del_list)
            self._init_bytes = None
            self.uuid = None
        else:
            raise ValueError('Session is not writable.')

    # def rebuild_index(self):
    #     """
    #     Rebuild the remote index file from all the objects in the remote.
    #     """
    #     if self.writable:
    #         resp = self._session.list_object_versions(prefix=self.db_key + '/')


    # def list_objects(self):
    #     """

    #     """
    #     return self.write_session.list_objects(prefix=self.write_db_key)


    # def list_object_versions(self):
    #     """

    #     """
    #     return self.write_session.list_object_versions(prefix=self.write_db_key)

    # def lock(self):
    #     """

    #     """
    #     if self.writable:
    #         lock = self._session.s3lock(self.db_key)
    #         return lock
    #     else:
    #         raise ValueError('Conn is not writable.')


class S3Connection(JsonSerializer):
    """

    """
    def __init__(self,
                access_key_id: str=None,
                access_key: str=None,
                db_key: str=None,
                bucket: str=None,
                endpoint_url: str=None,
                db_url: str=None,
                threads: int=20,
                read_timeout: int=60,
                retries: int=3,
                db_meta: dict=None,
                user_meta: dict=None,
                ):
        """

        """
        ## temp read session
        read_session, key = create_s3_read_session(
                access_key_id,
                access_key,
                db_key,
                bucket,
                endpoint_url,
                db_url,
                threads,
                read_timeout,
                retries,
                )
        if read_session is None:
            raise ValueError('Either db_url or a combo of access_key_id, access_key, db_key, and bucket (and optionally endpoint_url) must be passed.')

        ## Get metadata if necessary
        if db_meta is None:
            meta = get_db_metadata(read_session, key)
        elif all([k in db_meta for k in ('uuid', 'ebooklet_type', 'timestamp')]):
            uuid = db_meta['uuid']
            if isinstance(uuid, (str, uuid6.UUID)):
                if isinstance(uuid, str):
                    db_meta['uuid'] = uuid6.UUID(hex=uuid)
                else:
                    raise TypeError('uuid in meta must be either a string or UUID')

            ebooklet_type = db_meta['ebooklet_type']
            if ebooklet_type not in ebooklet_types:
                raise ValueError(f'ebooklet_type in meta must be one of {ebooklet_types}')
        else:
            meta = get_db_metadata(read_session, key)

        if user_meta is not None:
            if not isinstance(user_meta, dict):
                raise TypeError('user_meta in meta must be a dict or None')

        # read_session.clear()

        ## Assign properties
        self.db_key = db_key
        self.bucket = bucket
        self.access_key_id = access_key_id
        self.access_key = access_key
        self.endpoint_url = endpoint_url
        self.db_url = db_url
        self.threads = threads
        self.read_timeout = read_timeout
        self.retries = retries
        # self.type = 'connection'

        self.uuid = meta['uuid']
        self.timestamp = meta['timestamp']
        self.ebooklet_type = meta['ebooklet_type']
        self.user_meta = user_meta


    def _make_read_session(self):
        """

        """
        read_session, key = create_s3_read_session(
                self.access_key_id,
                self.access_key,
                self.db_key,
                self.bucket,
                self.endpoint_url,
                self.db_url,
                self.threads,
                self.read_timeout,
                self.retries,
                )

        return read_session, key


    def load_db_metadata(self):
        """

        """
        read_session, key = self._make_read_session()

        meta = get_db_metadata(read_session, key)
        self.uuid = meta['uuid']
        self.ebooklet_type = meta['ebooklet_type']
        self.timestamp = meta['timestamp']


    def load_user_metadata(self):
        """

        """
        read_session, key = self._make_read_session()

        self.user_meta = get_user_metadata(read_session, key)


    def open(self,
             flag: str='r',
             object_lock: bool=False,
             break_other_locks: bool=False,
             lock_timeout: int=-1,
             ):
        """

        """
        if (flag != 'r') and (self.access_key_id is None or self.access_key is None):
            raise ValueError("access_key_id and access_key must be assigned to open a connection for writing.")

        # ## Check and load uuid if it isn't assigned
        # if self.uuid is None:
        #     self.load_db_metadata()

        ## Read session
        read_session, read_db_key = self._make_read_session()

        if flag == 'r':
            return S3SessionReader(read_session, read_db_key, self.threads)
        else:
            write_session, write_db_key = create_s3_write_session(
                    self.access_key_id,
                    self.access_key,
                    self.db_key,
                    self.bucket,
                    self.endpoint_url,
                    self.threads,
                    self.read_timeout,
                    self.retries,
                    )

            if write_session is None:
                raise ValueError("A write session could not be created. Check that all the inputs are assigned.")

            session_writer = S3SessionWriter(
                                    read_session,
                                    write_session,
                                    read_db_key,
                                    write_db_key,
                                    self.threads,
                                    object_lock,
                                    break_other_locks,
                                    lock_timeout,
                                    )

            # Check to make sure the uuids are the same if the read and write sessions are different
            if isinstance(read_session, s3func.HttpSession) and self.uuid is not None:
                if self.uuid != session_writer.uuid:
                    raise ValueError('The UUIDs of the http connection and the S3 connection are different. Check to make sure the they are pointing to the right file.')

            return session_writer




















































