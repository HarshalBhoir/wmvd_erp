# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo import tools
from email import _name
import string

from datetime import datetime,date , timedelta
from time import gmtime, strftime

class kr_kra(models.Model):   
    _name = "kr.kra"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "KRA"
    _rec_name = 'display_name'

    @api.multi
    def unlink(self):
        for order in self:
          if order.state != 'draft':
            raise UserError(_('You can only Delete Draft Entries'))
        return super(kr_kra, self).unlink()
   
    name = fields.Many2one('hr.job', string="Designation")
    display_name = fields.Char(string='name', compute="_name_get" , store=True)
    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string="Company")
    state = fields.Selection([
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('disapproved', 'Dis-Approved')], string='State',track_visibility='onchange', default='draft', copy=False)

    date_year = fields.Date(string='Date')
    year = fields.Char(string='Year')
    line_ids = fields.One2many('kr.kra.line','budget_id', string='Components')
    is_created = fields.Boolean('Created', copy=False)


    @api.multi
    @api.depends('name','department_id','company_id','date_year')
    def _name_get(self):
        for ai in self:
            if ai.name and ai.department_id and ai.company_id and ai.date_year:
                date_year = datetime.strptime(self.date_year, "%Y-%m-%d")
                year = date_year.strftime('%y')
                month = int(date_year.strftime('%m'))

                if month <= 3:
                    pre_year = int(year) - 1
                    pre_year_1 = year
                elif month > 3:
                    pre_year = year
                    pre_year_1 = int(year) + 1

                ai.year = str(pre_year)+ '-' + str(pre_year_1)
                ai.display_name = ai.name.name + '-' + ai.department_id.name + ' (' + ai.year + ' )'



class kr_kraCategory(models.Model): 
    _name = "kr.kra.category"
    _description = "KRA Category"
    
    name = fields.Char(string='Name', required=True)  
    categ_no = fields.Char(string='Category No')



class KrKraLine(models.Model):   
    _name = "kr.kra.line"
    _description = "KRA Lines" 
    
  
    name = fields.Text(string='KPI')
    category_id = fields.Many2one('kr.kra.category', 'KRA')
    weightage = fields.Integer(string='Weightage')
    budget_id = fields.Many2one('kr.kra', 'Budget')
    
