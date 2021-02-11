# -*- coding: utf-8 -*-


from odoo.tools.translate import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import logging
from odoo.osv import  osv
from odoo import SUPERUSER_ID
from time import gmtime, strftime
from openerp.exceptions import UserError , ValidationError
import requests
import urllib
import simplejson
import odoo.addons.decimal_precision as dp

import shutil
import os
import time
import psycopg2
import urllib
import tarfile

class sale_order_extension(models.Model):
    _inherit = "sale.order"

    def _default_portal_user(self):
        if self.user_id:
            user = self.env['res.users'].search([('id', '=', user_id.id)]).portal_user
            return user

    portal_user = fields.Boolean("Portal User" ,default=_default_portal_user)
    org_id = fields.Many2one('org.master', string="Organisation")
    warehouse_master_id = fields.Many2one('warehouse.master', string='Warehouse')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('confirmed_erp', 'ERP Confirmed'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    @api.onchange('org_id')
    def _onchange_org_id(self):
        for res in self:
            if res.org_id:
                res.warehouse_master_id = res.org_id.warehouse_master_ids[0].id

            return {'domain': {
                'warehouse_master_id': [('id', 'in', [x.id for x in res.org_id.warehouse_master_ids])],
            }}



    @api.multi
    def create_idempiere_saleorder(self):        
        conn_pg = None
        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')])
        if config_id:
            try:


                print "#-------------Select --TRY----------------------#"
                conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, password=config_id.password, host= config_id.ip_address)
                pg_cursor = conn_pg.cursor()

                # state_code = self.state_id.code

                # pg_cursor.execute("select value FROM c_bpartner where value ilike '"+state_code+"%' order by value desc limit 1")
                # bp_code_check2 = pg_cursor.fetchall()
                # bp_code_check3 = str(bp_code_check2[0][0])
                # self.bp_code = state_code + str(int(([x.strip() for x in bp_code_check3.split('.')][0]).strip(state_code)) + 1)


                print " --------------------------- Order ----------------------------------------------"
                # if self.bp_code:

                #     pg_cursor.execute("select c_bpartner_id FROM c_bpartner where value = '%s'" %(self.bp_code.encode("utf-8")))
                #     bp_code_check = pg_cursor.fetchall()

                #     if  len(bp_code_check) != 0:
                #         raise UserError("Partner Code already exists. Kindly change the partner code and update")

                pg_cursor.execute("select MAX(c_order_id)+1 FROM c_order ")
                c_order_id2 = pg_cursor.fetchall()
                c_order_id3 = str(c_order_id2[0][0])
                c_order_id = int([x.strip() for x in c_order_id3.split('.')][0])

                

                # c_order_id, ad_client_id, ad_org_id, isactive, createdby, updatedby,issotrx,docstatus, docaction,processing, processed
                # c_doctype_id, c_doctypetarget_id , salesrep_id,dateordered,datepromised,dateacct, c_bpartner_id, c_bpartner_location_id , c_paymentterm_id
                # ad_user_id

                createdby= self.user_id.ad_user_id
                c_bpartner_id= self.partner_id.c_bpartner_id


                pg_cursor.execute("Insert INTO c_order(c_order_id, ad_client_id, ad_org_id, isactive, createdby, updatedby,issotrx,docstatus, docaction,processing, processed, \
                c_doctype_id, c_doctypetarget_id , salesrep_id,dateordered,datepromised,dateacct, c_bpartner_id, ad_user_id,documentno,c_bpartner_location_id , \
                c_currency_id,paymentrule , c_paymentterm_id,invoicerule,deliveryrule,freightcostrule,deliveryviarule,priorityrule,m_warehouse_id,m_pricelist_id,description) \
                                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",\
                                (c_order_id,1000000, 1000009, 'Y',int(createdby), int(createdby) , 'Y' , 'DR', 'CO' , 'N' , 'N',1000032 , 1000032, int(createdby) , self.date_order,
                                    self.date_order,self.date_order , int(c_bpartner_id) , int(createdby) , self.name , 1002193 ,304,'P',1000000,'D','A','I','P',5,1000002,
                                    1000006,self.note))
                 # commit the changes to the database
                conn_pg.commit()

                # print "kkkkkkkkkkkkkkkkkkkkkkkkk" , c_order_id , self.env.uid , c_order_id
                # print error
                # self.c_bpartner_id = c_bpartner_id


                print " --------------------------- Order Line ----------------------------------------------"

                for res in self.order_line:
                    line = 10
                    c_charge_id = ''

                    m_product_id= res.product_id.m_product_id
                    if res.product_id.type == 'service':
                        c_charge_id = res.product_id.m_product_id

                    c_uom_id= res.product_uom.c_uom_id
                    product_uom_qty= res.product_uom_qty
                    priceentered = res.price_unit
                    hsn_code = res.product_id.hsn_code


                    pg_cursor.execute("select MAX(C_OrderLine_ID)+1 FROM C_OrderLine ")
                    c_orderline_id2 = pg_cursor.fetchall()
                    c_orderline_id3 = str(c_orderline_id2[0][0])
                    c_orderline_id = int([x.strip() for x in c_orderline_id3.split('.')][0])


                    pg_cursor.execute('Insert into C_OrderLine(c_order_id, c_orderline_id, line, m_product_id, qtyentered, c_uom_id, priceentered, priceactual, \
                     hsn_code , ad_client_id, ad_org_id ,isactive, createdby, updatedby ,c_bpartner_id,c_bpartner_location_id , dateordered ,datepromised, \
                    m_warehouse_id , qtyordered , c_currency_id  ,iscrm , c_tax_id)  \
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
                 (c_order_id, c_orderline_id , line , m_product_id , product_uom_qty , c_uom_id , priceentered , priceentered,hsn_code ,1000000 , 1000009 ,'Y', int(createdby),
                    int(createdby) , int(c_bpartner_id),1002193 , self.date_order, self.date_order , 1000002, product_uom_qty ,304 , 'N' , 1000926  ))
                 # commit the changes to the database
                    conn_pg.commit()
                    line += 10





# c_order_id, c_orderline_id, line, m_product_id, c_charge_id,qtyentered, c_uom_id, priceentered, priceactual,pricelist,m_rprice, accessible_value,freightamt,c_tax_id ,discount ,link_orderline_id, discountamt
# , hsn_code , ad_client_id, ad_org_id ,isactive, createdby, updatedby ,c_bpartner_id,c_bpartner_location_id , dateordered ,datepromised, m_warehouse_id ,c_uom_id, qtyordered ,
#  c_currency_id  ,pricelist ,priceactual ,priceentered , iscrm, hsn_code




# c_tax_id , discount

                # pg_cursor.execute('Insert into C_OrderLine(c_order_id, c_orderline_id, line, m_product_id, c_charge_id,qtyentered, c_uom_id, priceentered, priceactual, \
                #      hsn_code , ad_client_id, ad_org_id ,isactive, createdby, updatedby ,c_bpartner_id,c_bpartner_location_id , dateordered ,datepromised, \
                #     m_warehouse_id , qtyordered , c_currency_id  ,iscrm)  \
                #     VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
                #  (c_order_id, c_orderline_id , line , m_product_id , c_charge_id if c_charge_id else 'Null' ,product_uom_qty , c_uom_id , priceentered , priceentered,hsn_code ,1000000 , 1000009 ,'Y', int(createdby),
                #     int(createdby) , int(c_bpartner_id),1002193 , self.date_order, self.date_order , 1000002, product_uom_qty ,304 , 'N'  ))



                
                # self.c_location_id = c_bpartneraddress_id

                # print " --------------------------- Adresss ---------------------------------------------- "


                # pg_cursor.execute("Select MAX(c_bpartner_location_id)+1 FROM c_bpartner_location")
                # c_bpartnerlocation_id2 = pg_cursor.fetchall()
                # c_bpartnerlocation_id3 = str(c_bpartnerlocation_id2[0][0])
                # c_bpartnerlocation_id = int([x.strip() for x in c_bpartnerlocation_id3.split('.')][0])

                # pg_cursor.execute('Insert into C_BPartner_Location(c_bpartner_location_id,c_location_id,c_bpartner_id,ad_client_id,ad_org_id,createdby,\
                #     updatedby,isbillto,isactive,isshipto,ispayfrom,isremitto,phone,phone2,email,name) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
                #     (c_bpartnerlocation_id,c_bpartneraddress_id,c_bpartner_id,int(self.company_id.ad_client_id),0,int(self.user_id.ad_user_id),
                #         int(self.user_id.ad_user_id),'Y','Y','Y','Y','Y',self.phone,self.mobile, self.email,
                #          self.city))
                #  # commit the changes to the database
                # conn_pg.commit()
                # self.c_bpartner_location_id = c_bpartnerlocation_id

                # print "ooooooooooooooooooooooooooooooooooooooooooooooooooooooo"

                # if self.contact_name:
                #     pg_cursor.execute("Select MAX(AD_User_ID)+1 FROM AD_User")
                #     AD_User_ID2 = pg_cursor.fetchall()
                #     AD_User_ID3 = str(AD_User_ID2[0][0])
                #     ad_user_id = int([x.strip() for x in AD_User_ID3.split('.')][0])

                #     contact_value = ((self.contact_name)[0] + self.contact_name.split(' ')[1]).lower()
                #     print "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" , contact_value

                #     pg_cursor.execute('Insert into AD_User(ad_user_id,ad_client_id,ad_org_id,isactive,createdby,updatedby,name,c_bpartner_id,processing,\
                #         notificationtype,isfullbpaccess,isinpayroll,islocked,isnopasswordreset,isexpired,issaleslead,issmssubscription,iserpuser,iscrm,\
                #         isaddmailtextautomatically,salesrep_id,value) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
                #         (ad_user_id,int(self.company_id.ad_client_id),0,'Y',int(self.user_id.ad_user_id),int(self.user_id.ad_user_id),
                #             self.contact_name,c_bpartner_id,'N','E','Y','N','N','N','N','N','N','N','N','N',int(self.user_id.ad_user_id),contact_value))
                #      # commit the changes to the database
                #     conn_pg.commit()
                #     # self.c_bpartner_location_id = c_bpartnerlocation_id


                # self.state = 'created'
                
                # close communication with the database
                self.state = 'confirmed_erp'
                pg_cursor.close()



            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    conn_pg.rollback()

                print 'Error %s' % e    

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#"
                    conn_pg.close()

        else:
            raise UserError("DB Configuration not found.")



    @api.model
    def create(self, vals):
        result = super(sale_order_extension, self).create(vals)
        if result.state == 'draft':
            result.force_quotation_send()
        return result


    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        price_list_id =  self.env['product.pricelist'].search([('partner_id', '=', self.partner_id.id)], order="id desc", limit=1)
        print "1111111111111111111111111111111111111111111111111 price_list_id" , price_list_id
        values = {
            'pricelist_id': price_list_id and price_list_id[0].id or 1,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        if self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

        if self.partner_id.user_id:
            values['user_id'] = self.partner_id.user_id.id
        if self.partner_id.team_id:
            values['team_id'] = self.partner_id.team_id.id
        self.update(values)



class sale_order_line_extension(models.Model):
    _inherit = "sale.order.line"

    @api.depends('price_unit')
    def _compute_price_unit(self):
        for line in self:
            if line.price_unit and line.price_unit > 0:
                line.price_unit_compute = line.price_unit


    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0, store=True, track_visibility='onchange')
    price_unit_compute = fields.Float('Unit Price', compute='_compute_price_unit', default=0.0, store=True, track_visibility='onchange')


    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        result = super(sale_order_line_extension, self).product_id_change()
        customer_pricelist = self.order_id.pricelist_id
        if len(customer_pricelist):
            for price in customer_pricelist[0]:
                for line in price.item_ids:
                    if self.product_id.product_tmpl_id.id == line.product_tmpl_id.id:
                        self.tax_id = line.tax_id or ''
        return result