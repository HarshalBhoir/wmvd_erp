# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import tools, api, fields, models, _


class res_users_extension(models.Model):
    _inherit = "res.users"

    portal_user = fields.Boolean("Portal User" , default=False)
    erp_credentials_one2many = fields.One2many('wp.erp.credentials','wp_user_id',string="ERP Credentials")
    ad_user_id = fields.Char(string="User ID")
    employee_bool = fields.Boolean(string="Create Employee")

    wp_salesperson = fields.Boolean("Salesperson" , default=False)

    employee_id = fields.Many2one('hr.employee',
                                  string='Related Employee', ondelete='restrict', auto_join=True,
                                  help='Employee-related data of the user')


    @api.onchange('portal_user')
    def onchange_portal_user(self):
        if self.portal_user:
            self.employee_bool = False

    @api.onchange('employee_bool')
    def onchange_employee_bool(self):
        if self.employee_bool:
            self.portal_user = False

    @api.model
    def create(self, vals):
        result = super(res_users_extension, self).create(vals)
        if result['employee_bool']:
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


    # @api.model
    # @api.multi
    # def process_update_erp_c_bp_group_queue(self):

    #     conn_pg = None
    #     config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
    #     if config_id:

    #         print "#-------------Select --TRY----------------------#"
    #         try:
    #             conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
    #              password=config_id.password, host= config_id.ip_address,port=config_id.port)
    #             pg_cursor = conn_pg.cursor()

    #             query = "select name , value, c_bp_group_id , ad_client_id from  adempiere.C_BP_Group where isactive = 'Y' " 

    #             pg_cursor.execute(query)
    #             records = pg_cursor.fetchall()

               
    #             if len(records) > 0:

    #                 for record in records:
    #                     c_bp_group_id = (str(record[2]).split('.'))[0]
    #                     ad_client_id = (str(record[3]).split('.'))[0]

    #                     company_id = self.env['res.company'].search([('ad_client_id','=',ad_client_id)], limit=1)

    #                     print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , company_id , ad_client_id

    #                     vals_line = {
    #                         'c_bp_group_id': c_bp_group_id,
    #                         'ad_client_id': ad_client_id,
    #                         'isactive': True,
    #                         'value':(str(record[1]).split('.'))[0],
    #                         'name':record[0],
    #                         'company_id': company_id.id,


    #                     }

    #                     portal_c_bp_group_id = [ x.c_bp_group_id for x in self.env['res.partner.group'].search([('isactive','!=',False)])]
    #                     if c_bp_group_id not in portal_c_bp_group_id:
    #                         self.env['res.partner.group'].create(vals_line)
    #                         print "0000000000000000000000000000000000 Group Created in CRM  000000000000000000000000000000000000000000000"


    #         except psycopg2.DatabaseError, e:
    #             if conn_pg:
    #                 print "#-------------------Except----------------------#"
    #                 print 'Error %s' % e  
    #                 conn_pg.rollback()
                 
    #             print 'Error %s' % e        

    #         finally:
    #             if conn_pg:
    #                 conn_pg.close()
    #                 print "#--------------Select --44444444--Finally----------------------#" , pg_cursor
