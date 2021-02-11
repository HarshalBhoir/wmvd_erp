# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Avinash Nk(<avinash@cybrosys.in>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class WpAssetPayment(models.Model):
    _name = 'wp.asset.payment'
    _description = 'Asset Payment'
    _inherit = ['mail.thread', 'ir.needaction_mixin']


    @api.depends('payment_line.amount')
    def _amount_all(self):
        """
        Compute the total amounts of the payment.
        """
        for order in self:
            amount_total = amount = 0.0
            for line in order.payment_line:
                if line.payment_type == 'creditnote':
                    amount = -(line.amount)
                else:
                    amount = line.amount
                amount_total += amount

            order.update({
                'amount_total': amount_total,
            })

    name = fields.Char(string="Name"  , copy=False)
    date = fields.Date(string="Date", default=fields.Date.today, required=True)
    partner_id = fields.Many2one('res.partner', string="Vendor", required=True)
    vendor_reference = fields.Char(string="Invoice No." , copy=False)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('paid', 'Paid'), ('cancel', 'Canceled')], string="State", default="draft")
    amount = fields.Float(string="Amount")
    company_id = fields.Many2one('res.company', string="Company")
    payment_category = fields.Selection([('service', 'Service'), ('regular', 'Regular'), ('project', 'Project')], string="Payment Category")
    remarks = fields.Char(string="Remarks")
    payment_line = fields.One2many('wp.asset.payment.line', 'payment_id', string="Lines")
    budget_id = fields.Many2one('bt.budget', string="Budget")
    budget_category_id = fields.Many2one('bt.budget.category', 'Budget Category')

    attach_doc_count = fields.Integer(string="Number of documents attached", compute='_get_attached_docs')
    # payment_attachments = fields.Many2many('ir.attachment' , copy=False, attachment=True)

    tax_value = fields.Float(string='Tax Value')
    total_value = fields.Float(string='Total Value')
    amount_total = fields.Float(string='Amount Total', store=True, readonly=True, compute='_amount_all', track_visibility='always')

    @api.onchange('amount','tax_value')
    def _onchange_value(self):
        if self.amount and not self.tax_value:
            self.total_value = self.amount
        elif self.amount and  self.tax_value:
            self.total_value = self.amount + self.tax_value 
    
    
    @api.multi 
    def _get_attached_docs(self):
        attachment = self.env['ir.attachment']
        try:
            for record in self:
                company_attachments = attachment.search([('res_model', '=', 'wp.asset.payment'), ('res_id', '=',  record.id)])
                record.attach_doc_count = len(company_attachments) or 0
        except:
            pass
    
    @api.multi
    def attachment_tree_view_1(self):
        domain = [('res_model', '=', 'wp.asset.payment'), ('res_id', '=', self.id)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                Documents are attached to the tasks and issues of your project.</p><p>
                Send messages or log internal notes with attachments to link
                documents to your project.
                </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    
    

    @api.model
    def create(self, values):
        sequence=self.env['ir.sequence'].next_by_code('wp.asset.payment')
        values['name']=sequence

        if 'vendor_reference' in values:
            invoiceno = self.env['wp.asset.payment'].search([('vendor_reference','=',values['vendor_reference'])])
            if len(invoiceno) >= 1 :
                raise UserError("Invoice Number already present in the Payment ' " + invoiceno.name + " '")

        return super(WpAssetPayment, self).create(values)


    @api.multi
    def action_confirm(self):
        self.state = 'paid'
        if self.budget_id:
            for budget in self.budget_id:
                budget_line_id = self.env['bt.budget.line'].search([('budget_id','=',budget.id),
                                                                    ('category_id','=',self.budget_category_id.id)])
                if budget_line_id:
                    budget.amount_alloted += self.amount_total
                    for line in budget_line_id:
                        line.claimed += self.amount_total
                else:
                    vals = {
                        'name': self.budget_category_id.name,
                        'category_id': self.budget_category_id.id,
                        'budget_id': budget.id,
                        'claimed': self.amount_total,

                    }

                    retailer_id = self.env['bt.budget.line'].create(vals)

        else:
            raise Warning(_(" Budget not found for below Department and Company")) 

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'

    


class WpAssetPaymentLine(models.Model):
    _name = 'wp.asset.payment.line'
    _description = 'Asset Payment Line'

    name = fields.Char(string="Name")
    asset_id = fields.Many2one('bt.asset', string="Asset")
    payment_id = fields.Many2one('wp.asset.payment', string="Payment")
    amount = fields.Float(string="Amount")
    state = fields.Selection([('done', 'Done'), ('pending', 'Pending')], string="State", default="pending")
    payment_type = fields.Selection([('payment', 'Payment'), ('creditnote', 'Credit Note')], string="Type", default="payment")
    description = fields.Char(string="Description")
    