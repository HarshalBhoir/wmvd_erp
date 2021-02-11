# -*- coding: utf-8 -*-

import hashlib

from odoo import models, fields, api, tools, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
import logging

_logCache = logging.getLogger(__name__+'_Cache')

PREFETCH_MAX=models.PREFETCH_MAX

class View(models.Model):
    _inherit='ir.ui.view'
    
    @api.model
    @api.returns('self',
        upgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else self.browse(value),
        downgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else value.ids)
    def search(self, args, offset=0, limit=None, order=None, count=False,_cache={}):
            res=[]
            groups_id=self.env.user.groups_id.ids
            key=str(self.ids)+str(offset)+str(args)+str(limit or 'limit')+str(order or 'order')+str(count or 'count')+str(groups_id)
            key_hash=str(hashlib.sha1(key or '').hexdigest())
            if not _cache.has_key(key_hash):
                """ search(args[, offset=0][, limit=None][, order=None][, count=False])

                Searches for records based on the ``args``
                :ref:`search domain <reference/orm/domains>`.

                :param args: :ref:`A search domain <reference/orm/domains>`. Use an empty
                             list to match all records.
                :param int offset: number of results to ignore (default: none)
                :param int limit: maximum number of records to return (default: all)
                :param str order: sort string
                :param bool count: if True, only counts and returns the number of matching records (default: False)
                :returns: at most ``limit`` records matching the search criteria

                :raise AccessError: * if user tries to bypass access rules for read on the requested object.
                """
                res = self._search(args, offset=offset, limit=limit, order=order, count=count)
                _cache[key_hash]=res
                #~ _logCache.info('SET ir.ui.view search %s - %d ' % (key_hash, len(_cache)))
            return _cache[key_hash] if count else self.browse(_cache[key_hash])
            
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None,_cache={}):
        """
        Performs a ``search()`` followed by a ``read()``.

        :param domain: Search domain, see ``args`` parameter in ``search()``. Defaults to an empty domain that will match all records.
        :param fields: List of fields to read, see ``fields`` parameter in ``read()``. Defaults to all fields.
        :param offset: Number of records to skip, see ``offset`` parameter in ``search()``. Defaults to 0.
        :param limit: Maximum number of records to return, see ``limit`` parameter in ``search()``. Defaults to no limit.
        :param order: Columns to sort result, see ``order`` parameter in ``search()``. Defaults to no sort.
        :return: List of dictionaries containing the asked fields.
        :rtype: List of dictionaries.

        """
        groups_id=self.env.user.groups_id.ids
        key=str(domain)+str(fields or 'fields')+str(offset or 'offset')+str(limit or 'limit')+str(order or 'order')+str(groups_id)
        key_hash=str(hashlib.sha1(key or '').hexdigest())
        if not _cache.has_key(key_hash):
            records = self.search(domain or [], offset=offset, limit=limit, order=order)
            if not records:
                if not self.env.context.get('install_mode') and self.env.context.get('website_id'):
                    _cache[key_hash]=[]
                return []

            if fields and fields == ['id']:
                # shortcut read if we only want the ids
                if not self.env.context.get('install_mode') and self.env.context.get('website_id'):
                    _cache[key_hash]=[{'id': record.id} for record in records]
                return [{'id': record.id} for record in records]

            # read() ignores active_test, but it would forward it to any downstream search call
            # (e.g. for x2m or function fields), and this is not the desired behavior, the flag
            # was presumably only meant for the main search().
            # TODO: Move this to read() directly?
            if 'active_test' in self._context:
                context = dict(self._context)
                del context['active_test']
                records = records.with_context(context)

            result = records.read(fields)
            if len(result) <= 1:
                if not self.env.context.get('install_mode') and self.env.context.get('website_id'):
                    _cache[key_hash]=result
                return result

            # reorder read
            index = {vals['id']: vals for vals in result}
            #~ _logCache.info('SET ir.ui.view search_read %s - %d ' % (key_hash, len(_cache)))
            if not self.env.context.get('install_mode') and self.env.context.get('website_id'):
                _cache[key_hash]=[index[record.id] for record in records if record.id in index]
        if not self.env.context.get('install_mode') and self.env.context.get('website_id'):
           return _cache[key_hash]
        return [index[record.id] for record in records if record.id in index]
    
    @api.multi
    def read(self, fields=None, load='_classic_read',_cache={}):
        """ read([fields])

        Reads the requested fields for the records in ``self``, low-level/RPC
        method. In Python code, prefer :meth:`~.browse`.

        :param fields: list of field names to return (default is all fields)
        :return: a list of dictionaries mapping field names to their values,
                 with one dictionary per record
        :raise AccessError: if user has no read rights on some of the given
                records
        """
        groups_id=self.env.user.groups_id.ids
        key=str(self.ids)+str(fields or 'fields')+str(load)+str(groups_id)
        key_hash=str(hashlib.sha1(key or '').hexdigest())
        if not _cache.has_key(key_hash) or self.env.context.get('install_mode'):
            # check access rights
            self.check_access_rights('read')
            fields = self.check_field_access_rights('read', fields)

            # split fields into stored and computed fields
            stored, inherited, computed = [], [], []
            for name in fields:
                field = self._fields.get(name)
                if field:
                    if field.store:
                        stored.append(name)
                    elif field.base_field.store:
                        inherited.append(name)
                    else:
                        computed.append(name)
                else:
                    _logger.warning("%s.read() with unknown field '%s'", self._name, name)

            # fetch stored fields from the database to the cache; this should feed
            # the prefetching of secondary records
            self._read_from_database(stored, inherited)

            # retrieve results from records; this takes values from the cache and
            # computes remaining fields
            result = []
            name_fields = [(name, self._fields[name]) for name in (stored + inherited + computed)]
            use_name_get = (load == '_classic_read')
            for record in self:
                try:
                    values = {'id': record.id}
                    for name, field in name_fields:
                        values[name] = field.convert_to_read(record[name], record, use_name_get)
                    result.append(values)
                except MissingError:
                    pass
            if not self.env.context.get('install_mode'):
                #~ _logCache.info('SET ir.ui.view read %s - %d ' % (key_hash, len(_cache)))
                _cache[key_hash]=result
        if not self.env.context.get('install_mode') and _cache.has_key(key_hash):
            # store result in cache for POST fields
            result=_cache[key_hash]
            for vals in result:
                record = self.browse(vals['id'], self._prefetch)
                record._cache.update(record._convert_to_cache(vals, validate=False))
            return result
        return result
        
