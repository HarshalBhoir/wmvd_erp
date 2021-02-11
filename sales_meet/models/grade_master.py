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



class grade_master(models.Model):
    _name = "grade.master"

    name = fields.Char('Grade')
    isactive = fields.Boolean("Active", default=True)
    grade_line_ids = fields.One2many('grade.master.line', 'grade_line_id', 'Claim Lines', copy=True)
    
    

class grade_master_line(models.Model):
    _name = "grade.master.line"

    name = fields.Many2one('product.product', 'Claim Type', ondelete='cascade',  domain=[('can_be_expensed', '=', True)])
    value = fields.Char('Value')
    isactive = fields.Boolean("Active" , default=True)
    place = fields.Boolean("All Places")
    fixed_asset = fields.Boolean("Fixed")
    once_only = fields.Boolean("Only Once")
    grade_line_id = fields.Many2one('grade.master', 'Grade', ondelete='cascade')
