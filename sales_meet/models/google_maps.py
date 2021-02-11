# -*- coding: utf-8 -*-

import urllib
import urllib2
try:
    import json
except ImportError:
    import simplejson as json
# from openerp.osv import orm
from odoo.tools.translate import _
from odoo.exceptions import UserError , ValidationError


google_key='AIzaSyAueXqmASv23IO3NSdPnVA_TNJOWADjEh8'

def fetch_json(query_url, params={}, headers={}):
    """Retrieve a JSON object from a (parameterized) URL.
    
    :param query_url: The base URL to query
    :type query_url: string
    :param params: Dictionary mapping (string) query parameters to values
    :type params: dict
    :param headers: Dictionary giving (string) HTTP headers and values
    :type headers: dict 
    :return: A `(url, json_obj)` tuple, where `url` is the final,
    parameterized, encoded URL fetched, and `json_obj` is the data 
    fetched from that URL as a JSON-format object. 
    :rtype: (string, dict or array)
    
    """
    encoded_params = urllib.urlencode(params)    
    url = query_url + encoded_params
    request = urllib2.Request(url, headers=headers)
    response = urllib2.urlopen(request)
    return (url, json.load(response))

class GoogleMaps(object):
    _DIRECTIONS_QUERY_URL = 'https://maps.googleapis.com/maps/api/directions/json?'
    # _DIRECTIONS_QUERY_URL = 'https://maps.googleapis.com/maps/api/distancematrix/json?'


    def __init__(self, referrer_url=''):
        self.referrer_url = referrer_url

    def directions(self, origin, destination, mode='driving', **kwargs):
        """
        Get directions from `origin` to `destination`.
        """
        params = {
            'origin': origin,
            'destination': destination,
            'sensor': 'false',
            'mode': mode,
            'key': google_key,
        }
        params.update(kwargs)
        if mode == 'transit':
            if not params.get('departure_time') and not params.get('arrival_time'):
                params['mode'] = 'driving'
        url, response = fetch_json(self._DIRECTIONS_QUERY_URL, params=params)
        # print "aaaaaaaaaaaaaaaaaaaaaaaaaaaaa", url, response
        status_code = response['status']
        if status_code != 'OK':
            # raise orm.except_orm(_('ERROR !'), _('Impossible to access data'))
            raise UserError(_("Impossible to access data. Kindly enter proper City or District Names"))
        return response
    
    def duration(self, origin, destination, mode='driving', **kwargs):
        response = self.directions(origin, destination, mode, **kwargs)
        duration = 0
        routes = response.get('routes')
        if routes:
            legs = routes[0].get('legs')
            if legs:
                # duration = legs[0].get('duration', {}).get('value', 0)
                duration = legs[0].get('duration', {}).get('text', 0)
                
        return duration
    
    def distance(self, origin, destination, mode='driving', **kwargs):
        response = self.directions(origin, destination, mode, **kwargs)
        distance = 0
        routes = response.get('routes')
        if routes:
            legs = routes[0].get('legs')
            if legs:
                # distance = legs[0].get('distance', {}).get('value', 0)
                distance = legs[0].get('distance', {}).get('text', 0)

        return distance
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: