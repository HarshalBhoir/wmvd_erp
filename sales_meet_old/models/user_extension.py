# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import tools, api
from odoo import api, fields, models, _
from odoo.osv import  osv


class res_users_extension(models.Model):
    _inherit = "res.users"

    portal_user = fields.Boolean("Portal User" , default=False)
    erp_credentials_one2many = fields.One2many('wp.erp.credentials','wp_user_id',string="ERP Credentials")
    ad_user_id = fields.Char(string="User ID")

    wp_salesperson = fields.Boolean("Salesperson" , default=False)

    employee_id = fields.Many2one('hr.employee',
                                  string='Related Employee', ondelete='restrict', auto_join=True,
                                  help='Employee-related data of the user')

    @api.model
    def create(self, vals):
        result = super(res_users_extension, self).create(vals)
        result['employee_id'] = self.env['hr.employee'].create({'name': result['name'],
                                                                'user_id': result['id'],
                                                                'address_home_id': result['partner_id'].id})
        return result
    
    
class WpErpCredentials(models.Model):
    _name = "wp.erp.credentials"
    _description = "Wp Erp Credentials"
    _order= "sequence"

    wp_user_id = fields.Many2one('res.users', string='User', ondelete='cascade')
    sequence = fields.Integer(string='sequence')
    ad_user_id = fields.Char(string="User ID")
    erp_user = fields.Char(string="ERP User")
    erp_pass = fields.Char(string="ERP Pass")
    erp_roleid = fields.Char(string="Role ID")
    company_id = fields.Many2one('res.company', string='Company')
