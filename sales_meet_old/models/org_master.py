# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2014-Today BrowseInfo (<http://www.browseinfo.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
from odoo.tools.translate import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import logging
from odoo.osv import  osv
from odoo import SUPERUSER_ID
from time import gmtime, strftime
from openerp.exceptions import UserError , ValidationError
import requests
import urllib
import simplejson



class org_master(models.Model):
    _name = "org.master"

    name = fields.Char('Organisation')
    isactive = fields.Boolean("Active", default=True)
    ad_org_id = fields.Char('Org ID')
    value = fields.Char('Value')
    prefix = fields.Char('Prefix')
    warehouse_master_ids = fields.One2many('warehouse.master', 'org_master_id', 'Pricelist Items')
    company_id = fields.Many2one('res.company', string='Company', index=True )
    default = fields.Boolean("Default", default=False)


    # grade_line_ids = fields.One2many('grade.master.line', 'grade_line_id', 'Claim Lines', copy=True)
    
    

# class grade_master_line(models.Model):
#     _name = "grade.master.line"

#     name = fields.Many2one('product.product', 'Claim Type', ondelete='cascade',  domain=[('can_be_expensed', '=', True)], select=True)
#     value = fields.Char('Value')
#     isactive = fields.Boolean("Active" , default=True)
#     place = fields.Boolean("All Places")
#     fixed_asset = fields.Boolean("Fixed")
#     grade_line_id = fields.Many2one('grade.master', 'Grade', ondelete='cascade', select=True)


class warehouse_master(models.Model):
    _name = "warehouse.master"

    name = fields.Char('Warehouse')
    isactive = fields.Boolean("Active", default=True)
    m_warehouse_id = fields.Char('Warehouse ID')
    value = fields.Char('Value')
    org_master_id = fields.Many2one('org.master', 'Other Pricelist')