# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo import tools
from email import _name
import string

from datetime import datetime,date , timedelta
from time import gmtime, strftime

class BtAssetSurveillance(models.Model):   
    _name = "bt.asset.surveillance"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Asset Surveillance"
    _order  = 'id desc'

    @api.multi
    def unlink(self):
        for order in self:
          if order.state != 'draft' and self.env.uid != 1:
            raise UserError(_('You can only Delete Draft Entries'))
        return super(BtAssetSurveillance, self).unlink()
   
    name = fields.Char(string='Name')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('postponed', 'Postponed')], string='State',track_visibility='onchange', default='draft', copy=False)

    line_ids = fields.One2many('bt.asset.surveillance.line','surveillance_id', string='Components')
    is_created = fields.Boolean('Created', copy=False)
    user_id = fields.Many2one('res.users', string='User', copy=False , index=True, track_visibility='onchange', default=lambda self: self.env.user)
    current_loc_id = fields.Many2one('bt.asset.location', string="Location")
    date = fields.Date('Date', default=lambda self: fields.Datetime.now())
    remark = fields.Char(string='Remark')
    category_id = fields.Many2one('bt.asset.category', 'Category')


    @api.multi
    def action_done(self):
        for res in self.line_ids:
            res.action_done()
        
        self.state='done'


class BtAssetSurveillanceLine(models.Model):   
    _name = "bt.asset.surveillance.line"
    _description = "Surveillance Lines" 
    
  
    name = fields.Char(string='Name')
    asset_id = fields.Many2one('bt.asset', 'Asset')
    category_id = fields.Many2one('bt.asset.category', 'Category')
    remark = fields.Char(string='Remark')
    surveillance_id = fields.Many2one('bt.asset.surveillance', 'Surveillance')
    date = fields.Date('Date')
    asset_code = fields.Char(string='Asset Code')
    model_name = fields.Char(string='Model Name')
    serial_no = fields.Char(string='Serial No')
    warranty_end = fields.Date(string='Warranty End')
    state = fields.Selection([
            ('active', 'Active'),
            ('scrapped', 'Scrapped')], string='State',track_visibility='onchange', default='active', copy=False)

    @api.multi
    def action_done(self):
        if not self.maintenance_id.state in ('done','postponed'):
            if not self.state == 'done':
                self.state = 'done'
                self.date = self.maintenance_id.date
                self.remark = self.maintenance_id.remark