# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2014-Today BrowseInfo (<http://www.browseinfo.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
from odoo.tools.translate import _
from odoo import tools, api
from odoo import api, fields, models, _
from odoo.osv import  osv
import shutil
import os
import time
import psycopg2
import urllib
import tarfile
import string
from datetime import datetime, timedelta, date , time
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT

class ProductCategory(models.Model):
    _inherit = "product.category"

    active = fields.Boolean(string="Active", default=True)


class product_uom_extension(models.Model):
    _inherit = "product.uom"

    c_uom_id = fields.Char(string="UOM ID")



class product_product_extension(models.Model):
    _inherit = "product.product"

    transport_mode = fields.Selection([('road', 'By Road') ,('rail', 'By Railway'), ('flight', 'By Flight')], 'Mode Of Transport')
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
    # erp_pass = fields.Char(string="ERP Pass")
    # erp_roleid = fields.Char(string="Role ID")
    company_id = fields.Many2one('res.company', string='Company')


class product_pricelist_extension(models.Model):
    _inherit = "product.pricelist"

    partner_id = fields.Many2one('res.partner', string="Customer", track_visibility='always')
    pricelist_type = fields.Selection(string='Type',
        selection=[('customer', 'Customer'), ('other', 'Other')],
        default='customer')
    m_pricelist_id = fields.Char('Pricelist ID')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.name


class product_pricelist_item_extension(models.Model):
    _inherit = "product.pricelist.item"

    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    # applied_on = fields.Selection([
    #     ('3_global', 'Global'),
    #     ('2_product_category', ' Product Category'),
    #     ('1_product', 'Product'),
    #     ('0_product_variant', 'Product Variant')], "Apply On",
    #     default='3_global', required=True,
    #     help='Pricelist Item applicable on selected option')

    applied_on = fields.Selection([('1_product', 'Product')], "Apply On",
        default='1_product', required=True,
        help='Pricelist Item applicable on selected option')






class product_erp_update(models.TransientModel):
    _name = 'product.erp.update'
    _description = "product ERP Update"


    name = fields.Char(string = "Product Code")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('product.erp.update'))


    @api.multi
    def update_product(self):

        conn_pg = None
        state_id = 596
        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
        if config_id:

            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
                 password=config_id.password, host= config_id.ip_address,port=config_id.port)
                pg_cursor = conn_pg.cursor()

                records2 = self.env['product.product'].sudo().search([('value','=',self.name)])

                print "ooooooooooooooooooooooooooooofffffffffffffffffffffffff" , records2 , len(records2)

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

                print "RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR" , records

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
                    print "0000000000000000000000000000000000 Product Created in CRM  000000000000000000000000000000000000000000000"


            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    print 'Error %s' % e  
                    conn_pg.rollback()
                 
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#" , pg_cursor
                    conn_pg.close()
                    print "#--------------Select --44444444--Finally----------------------#" , pg_cursor