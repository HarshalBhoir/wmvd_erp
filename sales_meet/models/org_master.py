# -*- coding: utf-8 -*-

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
from odoo.exceptions import UserError , ValidationError
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
    cir_bool = fields.Boolean("Visible in CIR", default=False)


class warehouse_master(models.Model):
    _name = "warehouse.master"

    name = fields.Char('Warehouse')
    isactive = fields.Boolean("Active", default=True)
    m_warehouse_id = fields.Char('Warehouse ID')
    value = fields.Char('Value')
    org_master_id = fields.Many2one('org.master', 'Other Pricelist')