# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
# import csv
from odoo import models, fields, api
import csv
from cStringIO import StringIO
import xlwt
import re
import base64
import pytz
from odoo import tools, api
from odoo import api, fields, models, _ , registry, SUPERUSER_ID
from odoo.exceptions import UserError, Warning, ValidationError

class BaseSynchroServer(models.Model):
    """Class to store the information regarding server."""

    _name = "base.synchro.server"
    _description = "Synchronized server"

    name = fields.Char('Server name', required=True)
    server_url = fields.Char('Server URL', required=True)
    server_port = fields.Integer('Server Port', required=True, default=8069)
    server_db = fields.Char('Server Database', required=True)
    login = fields.Char('User Name', required=True)
    password = fields.Char('Password', required=True)
    obj_ids = fields.One2many('base.synchro.obj', 'server_id', string='Models',
                              ondelete='cascade')


class BaseSynchroObj(models.Model):
    """Class to store the operations done by wizard."""

    _name = "base.synchro.obj"
    _description = "Register Class"
    _order = 'sequence'

    name = fields.Char('Name', required=True)
    domain = fields.Char('Domain', required=True, default='[]')
    server_id = fields.Many2one('base.synchro.server', 'Server',
                                ondelete='cascade',  required=True)
    model_id = fields.Many2one('ir.model', string='Object to synchronize',
                               required=True)
    action = fields.Selection([('d', 'Download'), ('u', 'Upload'), ('b',
                                                                    'Both')],
                              'Synchronization direction', required=True,
                              default='d')
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active', default=True)
    synchronize_date = fields.Datetime('Latest Synchronization', readonly=True)
    line_id = fields.One2many('base.synchro.obj.line', 'obj_id',
                              'IDs Affected', ondelete='cascade')
    avoid_ids = fields.One2many('base.synchro.obj.avoid', 'obj_id',
                                'Fields Not Sync.')

    @api.model
    def get_ids(self, obj, dt, domain=None, action=None):
        """Method to get ids."""
        if action is None:
            action = {}
        return self._get_ids(obj, dt, domain, action=action)

    @api.model
    def _get_ids(self, obj, dt, domain=None, action=None):
        if action is None:
            action = {}
        pool = self.env[obj]
        result = []
        if dt:
            w_date = domain + [('write_date', '>=', dt)]
            c_date = domain + [('create_date', '>=', dt)]
        else:
            w_date = c_date = domain
        obj_rec = pool.search(w_date)
        obj_rec += pool.search(c_date)
        for r in obj_rec.read(['create_date', 'write_date']):
            result.append((r['write_date'] or r['create_date'], r['id'],
                           action.get('action', 'd')))
        return result

    @api.multi
    def update_csv_records(self):
        print "111111111111111111111111111111"

        barcode_lines = self.env['barcode.marketing.line']
        partner_ids = self.env['res.partner']
        
        filename = "/tmp/barcode_lines.csv"

        # initializing the titles and rows list 
        fields = [] 
        rows = [] 

        # reading csv file 
        with open(filename, 'r') as csvfile: 
            print "22222222222222222222222222222222222"
            reader_info = []

            delimeter = ','
            reader = csv.reader(csvfile, delimiter=delimeter,lineterminator='\r\n')
            try:
                reader_info.extend(reader)
            except Exception:
                reader_info.extend(reader)
                raise Warning(_("Not a valid file!"))
            keys = reader_info[0]
            # check if keys exist

            # id,name,barcode_marketing_id,flag,date,bp_code,amount,product_name
            if not isinstance(keys, list) or ('id' not in keys or
                                              'name' not in keys or
                                              'flag' not in keys or
                                              'date' not in keys ):
                raise Warning(
                    _("'id' or 'name' or  'flag'  keys not found"))
            del reader_info[0]
            values = {}
            # credit_note.write({'imported': True,})
            count = 0
            
            for i in range(len(reader_info)):
                
                val = {}
                field = reader_info[i]
                values = dict(zip(keys, field))
    
                partner_list = partner_ids.search([('bp_code', '=',values['bp_code'])], limit= 1)
                if partner_list:
                    if  partner_list[0].id:

                        val['partner_id'] = partner_list[0].id
                        print "666666666666666666" , values['bp_code']
                    else:
                        print "7777777777777777777777" , values['bp_code']
                        raise Warning(_("Partner not found"))
                
                val['id'] = values['id']
                val['name'] = values['name']
                val['barcode_marketing_id'] = values['barcode_marketing_id']
                
                if values['flag'] == 'f':
                    flag = False
                else:
                    flag = True
                # print "3333333333333333333333333333333333" , values['flag'] , type(values['flag']) , flag
                val['flag'] = flag
                val['date'] = values['date']
                val['amount'] = values['amount']
                val['product_name'] = values['product_name']
                
                barcode_lines = barcode_lines.sudo().create(val)
                count += 1
                print "3333333333333333333333333333333333" , barcode_lines, count




    

class BaseSynchroObjAvoid(models.Model):
    """Class to avoid the base syncro object."""

    _name = "base.synchro.obj.avoid"
    _description = "Fields to not synchronize"

    name = fields.Char('Field Name',  required=True)
    obj_id = fields.Many2one('base.synchro.obj', 'Object', required=True,
                             ondelete='cascade')


class BaseSynchroObjLine(models.Model):
    """Class to store object line in base syncro."""

    _name = "base.synchro.obj.line"
    _description = "Synchronized instances"

    name = fields.Datetime('Date', required=True,
                           default=lambda *args:
                           time.strftime('%Y-%m-%d %H:%M:%S'))
    obj_id = fields.Many2one('base.synchro.obj', 'Object', ondelete='cascade')
    local_id = fields.Integer('Local ID', readonly=True)
    remote_id = fields.Integer('Remote ID', readonly=True)
