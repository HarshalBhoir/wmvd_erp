# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo import tools
from email import _name
import string
from datetime import datetime,date , timedelta
from time import gmtime, strftime

class BtAssetMaintenance(models.Model):   
    _name = "bt.asset.maintenance"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Asset Maintenance"
    _order  = 'id desc'

    @api.multi
    def unlink(self):
        for order in self:
          if order.state != 'draft' and self.env.uid != 1:
            raise UserError(_('You can only Delete Draft Entries'))
        return super(BtAssetMaintenance, self).unlink()
   
    name = fields.Char(string='Name')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('postponed', 'Postponed')], string='State',track_visibility='onchange', default='draft', copy=False)

    line_ids = fields.One2many('bt.asset.maintenance.line','maintenance_id', string='Components')
    is_created = fields.Boolean('Created', copy=False)
    user_id = fields.Many2one('res.users', string='User', copy=False , index=True, track_visibility='onchange', default=lambda self: self.env.user)
    current_loc_id = fields.Many2one('bt.asset.location', string="Current Location")
    duration = fields.Float(string='Duration', help='Maintenance duration in hours')
    date = fields.Date('Date', default=lambda self: fields.Datetime.now())
    next_maintenance_date = fields.Date('Next maintenance date')
    team_user_id = fields.Many2many('res.users', string='Team Members')
    remark = fields.Char(string='Remark')


    @api.multi
    def action_done(self):
        for res in self.line_ids:
            res.action_done()
        
        self.state='done'


    @api.multi
    def action_postponed(self):
        for res in self.line_ids:
            res.action_postponed()
        
        self.state='postponed'



    @api.multi
    def action_search(self):
        if self.current_loc_id.short_name:

            assets_id = self.env['bt.asset'].search([('current_loc_id','=',self.current_loc_id.id)])

            for res in assets_id:
                vals_line = {
                    'maintenance_id':self.id,
                    'asset_id':res.id,
                    'date':self.date,
                }
                self.line_ids.create(vals_line)

            self.name = "AM/"+self.current_loc_id.short_name+"/"+str(self.id).zfill(5)
            self.is_created = True
        else:
            raise UserError(_('Add Shortname for Location '+ self.current_loc_id.name + ' from "Asset Location" Menu'))




class BtAssetMaintenanceLine(models.Model):   
    _name = "bt.asset.maintenance.line"
    _description = "Maintenance Lines" 
    
  
    name = fields.Char(string='Name')
    asset_id = fields.Many2one('bt.asset', 'Category')
    remark = fields.Char(string='Remark')
    maintenance_id = fields.Many2one('bt.asset.maintenance', 'Maintenance')
    date = fields.Date('Date')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('postponed', 'Postponed')], string='State',track_visibility='onchange', default='draft', copy=False)

    @api.multi
    def action_done(self):
        if not self.maintenance_id.state in ('done','postponed'):
            if not self.state == 'done':
                self.state = 'done'
                self.date = self.maintenance_id.date
                self.remark = self.maintenance_id.remark

    @api.multi
    def action_postponed(self):
        if not self.maintenance_id.state in ('done','postponed'):
            if not self.state == 'postponed':
                self.state = 'postponed'
                self.date = self.maintenance_id.date
                self.remark = self.maintenance_id.remark



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
    code = fields.Char(string='Code')
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

    @api.model
    def create(self, values):
        sequence=self.env['ir.sequence'].next_by_code('bt.asset.surveillance')
        values['code']=sequence
        return super(BtAssetSurveillance, self).create(values)


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
