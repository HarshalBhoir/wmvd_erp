# -*- coding: utf-8 -*-

from odoo import api, fields, tools, models, _
from odoo.exceptions import ValidationError, Warning
from email import _name
import string
from werkzeug import url_encode



class BtAssetAllocation(models.Model):   
    _name = "bt.asset.allocation"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Asset Allocation"


    name = fields.Char(string="Name")
    employee = fields.Many2one('hr.employee', string='Employee')
    manager_id = fields.Many2one('hr.employee', string='Manager')
    resigned_employee = fields.Many2one('hr.employee', string='Resigned Employee')
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string="Designation")
    current_loc_id = fields.Many2one('bt.asset.location', string="Current Location")
    handed_over = fields.Boolean('Handed Over', copy=False)
    requisition_date = fields.Date(string='Requisition Date')
    handed_over_date = fields.Date(string='Hand Over Date')
    component_id = fields.Many2one('bt.component.item', string='Component')
    component_ids = fields.Many2many('bt.component.item', string='Components')
    asset_id = fields.Many2one('bt.asset', string="Asset")
    asset_name = fields.Char(string="Specific Name")
    description = fields.Text(string="Description")
    signature = fields.Binary('Signature')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('Mail Sent', 'Mail Sent'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')


    @api.model
    def create(self, values):
        sequence=self.env['ir.sequence'].next_by_code('bt.asset.allocation')
        values['name']=sequence
        return super(BtAssetAllocation, self).create(values)


    @api.onchange('employee')
    def onchange_employee(self):
        if self.employee :
            self.job_id = self.employee.job_id.id
            self.department_id = self.employee.department_id.id
            # self.manager_id = self.employee.manager_id.id


    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id :
            self.asset_name = self.asset_id.model_name

    @api.multi
    def accept_asset(self):
        if self.signature :
            self.state = 'Accepted'
            template = self.env.ref('website_support.email_template_bt_asset_allocation')
            self.env['mail.template'].sudo().browse(template.id).send_mail(self.id)

    @api.multi
    def send_allocation_details(self):
        body = """ """
        main_id = self.id

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <h3>Hello Candidate,</h3>
            <h4>Kindly Click on the button for Submitting handover of the asset. </h4>

            <br/>

        """ 

        subject = "Asset Allocation Detail Forms"
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        allocation_form = base_url + '/web#%s' % (url_encode({
            'model': self._name,
            'view_type': 'form',
            'id': main_id,
        }))
       

        full_body = body + """<br/>
        <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
            <tbody>
                <tr class="text-center">
                    
                    <td>
                        <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
                        border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                         vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                          margin-right: 10px;">Asset Allocation Form</a>
                    </td>

                </tr>
            </tbody>
        </table>
        """ % (allocation_form)

        self.state = 'Mail Sent'
        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': self.id,
                'email_from': 'helpdesk@walplast.com',
                'email_to': self.employee.work_email,
                'subject': subject,
                'body_html': full_body,
            })
        composed_mail.sudo().send()