# -*- coding: utf-8 -*-

import string
from datetime import datetime, timedelta, date , time
from odoo import api, fields, models, _ , registry, tools, SUPERUSER_ID
from odoo.exceptions import UserError, Warning, ValidationError
import time
import psycopg2

headers = {'content-type': 'text/xml'}

class ProductCategory(models.Model):
    _inherit = "product.category"

    active = fields.Boolean(string="Active", default=True)


class product_uom_extension(models.Model):
    _inherit = "product.uom"

    c_uom_id = fields.Char(string="UOM ID")
    uom_code = fields.Integer(string="UOM Code")


class product_product_extension(models.Model):
    _inherit = "product.product"

    transport_mode = fields.Selection([('road', 'By Road') ,
        ('rail', 'By Railway'), ('flight', 'By Flight')], 'Mode Of Transport')
    m_product_id = fields.Char(string="Product ID")
    value = fields.Char(string="Search Key")
    hsn_code = fields.Char(string="HSN Code")
    charge_name = fields.Char(string="Charge Name")
    erp_charge_one2many = fields.One2many('wp.erp.charge','product_charge_id',string="ERP Charge")
    u_productcategory_id = fields.Char(string="ERP Product Category")
    sku = fields.Char(string="SKU")


class WpErpCharge(models.Model):
    _name = "wp.erp.charge"
    _order= "sequence"

    product_charge_id  = fields.Many2one('product.product', string='Product', ondelete='cascade')
    sequence = fields.Integer(string='sequence')
    c_charge_id = fields.Char(string="Charge ID")
    name = fields.Char(string="Charge")
    company_id = fields.Many2one('res.company', string='Company')


class product_pricelist_extension(models.Model):
    _inherit = "product.pricelist"

    partner_id = fields.Many2one('res.partner', string="Customer", track_visibility='always')
    pricelist_type = fields.Selection(string='Type',
        selection=[('customer', 'Customer'), ('other', 'Other')],
        default='customer')
    m_pricelist_id = fields.Char('Pricelist ID')
    issopricelist = fields.Boolean('Sales Price list')
    m_pricelist_version_id = fields.Char('Pricelist Version ID')
    org_id = fields.Many2one('org.master', string="Customer", track_visibility='always')


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.name


    @api.model
    @api.multi
    def process_update_erp_m_pricelist_version_queue(self):

        conn_pg = None
        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
        if config_id:

            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
                 password=config_id.password, host= config_id.ip_address,port=config_id.port)
                pg_cursor = conn_pg.cursor()

                query = "select c_elementvalue_id,ad_client_id,isactive,value,name,description,accounttype, \
                accountsign,isdoccontrolled, c_element_id,issummary,postactual,postbudget,postencumbrance, \
                poststatistical,isbankaccount,c_bankaccount_id, isforeigncurrency,c_currency_id,account_id, \
                isdetailbpartner,isdetailproduct,bpartnertype from adempiere.C_ElementValue where isactive = 'Y' \
                and IsSummary = 'N' and c_element_id in ('1000005','1000008','1000013','1000017') " 

                pg_cursor.execute(query)
                records = pg_cursor.fetchall()

#                 select ad_client_id , ad_org_id , ValidFrom, name , M_PriceList_Version_ID ,
# (select name from M_PriceList where M_PriceList_ID = M_PriceList_Version.M_PriceList_ID),
# M_PriceList_ID, isactive from M_PriceList_Version mpv , M_PriceList mp where mp.isactive = 'Y'

               
                if len(records) > 0:
                    portal_c_elementvalue_id = [ x.c_elementvalue_id for x in self.env['wp.c.elementvalue'].search([('active','!=',False)])]


                    for record in records:
                        c_elementvalue_id = (str(record[0]).split('.'))[0]
                        ad_client_id = (str(record[1]).split('.'))[0]
                        company_id = self.env['res.company'].search([('ad_client_id','=',ad_client_id)], limit=1)

                        vals_line = {
                            'c_elementvalue_id': c_elementvalue_id,
                            'ad_client_id': ad_client_id,
                            'active': True,
                            'value':(str(record[3]).split('.'))[0],
                            'name':record[4],
                            'description':record[5],
                            'accounttype':record[6],
                            'accountsign':record[7],
                            'isdoccontrolled':record[8],
                            'c_element_id':(str(record[9]).split('.'))[0],
                            'issummary':record[10],
                            'postactual':record[11],
                            'postbudget':record[12],
                            'postencumbrance':record[13],
                            'poststatistical':record[14],
                            'isbankaccount':record[15],
                            'c_bankaccount_id':record[16],
                            'isforeigncurrency':record[17],
                            'c_currency_id':(str(record[18]).split('.'))[0],
                            'account_id':record[19],
                            'isdetailbpartner':record[20],
                            'isdetailproduct':record[21],
                            'bpartnertype':record[22],
                            'company_id': company_id.id,
                        }

                        if c_elementvalue_id not in portal_c_elementvalue_id:
                            self.env['wp.c.elementvalue'].create(vals_line)
                            print "-------------- elementvalue Created in CRM  -------------------"


            except psycopg2.DatabaseError, e:
                if conn_pg:
                    conn_pg.rollback()
                print '-------------------Error %s' % e        

            finally:
                if conn_pg:
                    conn_pg.close()
                    print "#--------------Select --44444444--Finally----------------------#" , pg_cursor


class product_pricelist_item_extension(models.Model):
    _inherit = "product.pricelist.item"

    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    applied_on = fields.Selection([('1_product', 'Product')], "Apply On",
        default='1_product', required=True,
        help='Pricelist Item applicable on selected option')


class product_erp_update(models.TransientModel):
    _name = 'product.erp.update'
    _description = "product ERP Update"


    name = fields.Char(string = "Product Code")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('product.erp.update'))


    @api.multi
    def update_product(self):

        conn_pg = None
        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
        if config_id:

            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
                 password=config_id.password, host= config_id.ip_address,port=config_id.port)
                pg_cursor = conn_pg.cursor()

                records2 = self.env['product.product'].sudo().search([('value','=',self.name)])

                if len(records2) > 0:
                    raise UserError("Already present")

                query = " select m_product_id, \
                            value,name,sku,m_product_category_id, \
                             (select name from adempiere.M_Product_Category where M_Product_Category_ID= mp.m_product_category_id), \
                            producttype,c_uom_to_id, \
                            (select name from adempiere.C_UOM where  C_UOM_ID= mp.c_uom_to_id), \
                            hsn_code,u_productcategory_id \
                            from adempiere.m_product mp where ad_client_id = %s and value = '%s' " %(self.company_id.ad_client_id, self.name)
          

                pg_cursor.execute(query)
                records = pg_cursor.fetchall()

                for record in records:
                    m_product_id = (str(record[0]).split('.'))[0]
                    c_uom_id = self.env['product.uom'].sudo().search([('name','=',record[8])]).id
                    
                    vals_line = {
                        'm_product_id': m_product_id ,
                        'active':  True,
                        'value':  record[1],
                        'default_code':  record[1],
                        'name':  record[2],
                        'sku': record[3]  ,
                        'uom_id': c_uom_id ,
                        'uom_po_id': c_uom_id ,
                        'hsn_code': record[9] ,
                        'u_productcategory_id': record[10] ,
                        'company_id': self.company_id.id,
                    }

                    self.env['product.product'].create(vals_line)
                    print "----------- Product Created in CRM  -----------------------------"


            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print '#-------------------Except--------------------- %s' % e  
                    conn_pg.rollback()
                 
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    conn_pg.close()
                    print "#--------------Select --44444444--Finally----------------------#" , pg_cursor