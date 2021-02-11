# -*- coding: utf-8 -*-

from odoo import api, fields, models,tools, _
from odoo.exceptions import ValidationError, UserError, AccessError, Warning
from email import _name
import string

from datetime import datetime,date , timedelta
from time import gmtime, strftime

class BtBudget(models.Model):   
    _name = "bt.budget"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Budget"

    @api.multi
    def unlink(self):
        for order in self:
          if order.state != 'draft':
            raise UserError(_('You can only Delete Draft Entries'))
        return super(BtBudget, self).unlink()
   
    name = fields.Char(string='Name')
    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string="Company")
    state = fields.Selection([
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('disapproved', 'Dis-Approved')], string='State',track_visibility='onchange', default='draft', copy=False)
    requester_id = fields.Many2one('res.users', string='Requester')
    approve_id = fields.Many2one('res.users', string='Approver')
    budget_amount = fields.Float(string='Budget', track_visibility='always')
    amount_alloted = fields.Float(string='Alloted', track_visibility='always')
    amount_pending = fields.Float(string='Pending', track_visibility='always', compute="_calc_pending", store=True)
    date_year = fields.Date(string='Date')
    year = fields.Char(string='Year')
    line_ids = fields.One2many('bt.budget.line','budget_id', string='Components')
    payment_ids = fields.One2many('wp.asset.payment','budget_id', string='Payments')
    is_created = fields.Boolean('Created', copy=False)


    @api.model
    def create(self, vals):
        vals.update({'is_created':True})
        lot = super(BtBudget, self).create(vals)
        for a in lot:
            budget_id = self.env['bt.budget'].search([('name','=',a.name)])
            b = [x.id for x in budget_id]
            if len(b) >1:
                raise Warning(_(a.department_id.name + " Budget already present for year " + a.year)) 
        return lot


    @api.multi
    @api.depends('budget_amount','amount_alloted')
    def _calc_pending(self):
        for ai in self:
            if ai.budget_amount and ai.amount_alloted:
                ai.amount_pending = ai.budget_amount - ai.amount_alloted


    @api.multi
    @api.onchange('date_year')
    def _calc_year(self):
        if self.date_year:
            today = datetime.now()
            date_year = datetime.strptime(self.date_year, "%Y-%m-%d")
            year = date_year.strftime('%y')
            month = int(date_year.strftime('%m'))

            if month <= 3:
                pre_year = int(year) - 1
                pre_year_1 = year
            elif month > 3:
                pre_year = year
                pre_year_1 = int(year) + 1

            self.year = str(pre_year)+ '-' + str(pre_year_1)

        if self.department_id:
            self.name = self.department_id.name + ' Budget ' + '(' + self.year + ')'

    @api.multi
    def action_approve(self):
        self.state = 'approved'

    @api.multi
    def action_disapprove(self):
        self.state = 'disapproved'

    @api.multi
    def action_reset(self):
        self.state = 'draft'




class BtBudgetCategory(models.Model): 
    _name = "bt.budget.category"
    _description = "Budget Category"
    
    name = fields.Char(string='Name', required=True)  
    categ_no = fields.Char(string='Category No')



class BtBudgetLine(models.Model):   
    _name = "bt.budget.line"
    _description = "Budget Lines" 
    
  
    name = fields.Char(string='Name', related="category_id.name")
    category_id = fields.Many2one('bt.budget.category', 'Category')
    vendor_name = fields.Char(string='Vendor Name')
    amount = fields.Float(string='Amount', track_visibility='always')
    claimed = fields.Float(string='Claimed', track_visibility='always')
    purchase_date = fields.Date(string='Date')
    budget_id = fields.Many2one('bt.budget', 'Budget')
    amount_pending = fields.Float(string='Pending', track_visibility='always', compute="_calc_pending", store=True)

    @api.multi
    @api.depends('amount','claimed')
    def _calc_pending(self):
        for ai in self:
            if ai.amount and ai.claimed:
                ai.amount_pending = ai.amount - ai.claimed
