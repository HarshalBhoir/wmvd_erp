
from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from odoo.tools.translate import _
from odoo import tools, api
from odoo import api, fields, models, _ , registry, SUPERUSER_ID
from odoo.osv import  osv
# import erppeek
import logging
import xmlrpclib
import sys
from openerp.exceptions import UserError , ValidationError

_logger = logging.getLogger(__name__)

import shutil
import os
import time
import psycopg2
import urllib
import tarfile


class posting_error(models.Model):
  _name = "posting.error"
  _description="Posting Error"
  _inherit = 'mail.thread'
  _order  = 'id desc'


  @api.multi
  def unlink(self):
    for order in self:
      if order.state != 'draft':
        raise UserError(_('You can only delete Draft Entries'))
    return super(posting_error, self).unlink()

  # portal_user = fields.Boolean("Portal User" , default=False)
  name = fields.Char('Name', store=True)
  db_name = fields.Char('DB Name')
  config_id = fields.Many2one('external.db.configuration', string='Database', track_visibility='onchange',  
    default=lambda self: self.env['external.db.configuration'].search([('id', '!=', 0)], limit=1))
  note = fields.Text('Text', track_visibility='onchange')
  state = fields.Selection([('draft', 'Draft'),
                       ('select', 'Earlier'), 
                       ('update', 'Updated'), 
                       ('select2', 'Changed')], string='Status',track_visibility='onchange', default='draft')

  idempiere_id = fields.Integer('iDempiere ID', track_visibility='onchange')
  documentno = fields.Char('Document No', track_visibility='onchange')
  requester = fields.Char('Requester')
  posting_error_one2many = fields.One2many('posting.error.lines','posting_error_id',string="Line Details")
  date = fields.Date(string="Date From", default=lambda self: fields.Datetime.now())
  employee_id = fields.Many2one('hr.employee', string="Employee")
  completed = fields.Boolean("completed")
  m_product_id = fields.Char('Product')
  productionqty = fields.Char('Production Quantity')


  @api.multi
  def get_data_from_database(self):
    conn_pg = None
    if self.config_id:
      idempiere_id=self.idempiere_id
      documentno=self.documentno
      # currentqty = qtyused = ''
      print "#-------------Select --TRY----------------------#"
      try:
        conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, password=self.config_id.password, host= self.config_id.ip_address)
        pg_cursor = conn_pg.cursor()

        if len(str(self.idempiere_id)) < 7 or len(str(self.idempiere_id)) > 7 :
          raise UserError("Wrong idempiere ID entered. Select proper ID")


        pg_cursor.execute("select (select M_Product.name from adempiere.M_Product where M_Product.M_Product_ID = prod.M_Product_ID ), productionqty\
         from  adempiere.M_Production prod where  M_Production_ID=%s and documentno = %s",(idempiere_id,documentno))
        record = pg_cursor.fetchall()
        
        if len(record) == 0:
          raise UserError("Wrong Idempiere ID / Document No entered. Recheck Both")

        else:
          m_product_id = record[0][0].encode('utf-8')
          productionqty = record[0][1]



        pg_cursor.execute("select ad_client_id ,qtyused ,M_Product_ID ,M_AttributeSetInstance_ID ,\
(select ad_client.name from adempiere.ad_client where ad_client.ad_client_id = pl.ad_client_id ),\
(select M_Product.name from adempiere.M_Product where M_Product.M_Product_ID = pl.M_Product_ID ),\
(select M_AttributeSetInstance.description from adempiere.M_AttributeSetInstance where M_AttributeSetInstance.M_AttributeSetInstance_ID = pl.M_AttributeSetInstance_ID )\
from  adempiere.M_Productionline pl where  pl.M_Production_ID=%s order by M_Product_ID asc ",[idempiere_id])

        line_records = pg_cursor.fetchall()
        ad_client_id = qtyused = M_Product_ID = M_AttributeSetInstance_ID = ad_client = M_Product = M_AttributeSetInstance = ''
        for records in line_records:
          ad_client_id = ((str(records[0])).split('.'))[0] 
          qtyused = records[1]
          M_Product_ID = ((str(records[2])).split('.'))[0] 
          M_AttributeSetInstance_ID = ((str(records[3])).split('.'))[0] 
          ad_client = records[4]
          M_Product = records[5]
          M_AttributeSetInstance = records[6]


          pg_cursor.execute("select currentqty,m_costelement_id from adempiere.m_cost \
            where M_Product_ID=%s and M_AttributeSetInstance_ID=%s \
  and m_costelement_id = (select m_costelement_id from adempiere.m_costelement where name = 'Average PO' and ad_client_id = %s) order by M_Product_ID asc ",\
            (int(M_Product_ID),int(M_AttributeSetInstance_ID),int(ad_client_id)))

         

          cost_records = pg_cursor.fetchall()
          
          for cost_rec in cost_records:
            currentqty = cost_rec[0]
            m_costelement_id = ((str(cost_rec[1])).split('.'))[0] 


            # if self.state == 'draft':

            # if currentqty !=  qtyused :

            vals_line = {
                'posting_error_id':self.id,
                'client_id':ad_client_id,
                'client_name':ad_client,
                'm_product_id':M_Product_ID,
                'product_name':M_Product,
                'description':M_AttributeSetInstance,
                'm_attributesetinstance_id':M_AttributeSetInstance_ID,
                'qtyused':float(qtyused),
                'qtypresent':float(currentqty),
                'm_costelement_id' : m_costelement_id,
              }

            self.env['posting.error.lines'].create(vals_line)

            # else:
            #   # print "ooooooooooo77777777777777777777777777777777777" , currentqty , qtyused , float(currentqty) , float(qtyused) , M_Product
            #   if currentqty ==  qtyused  :

            #     vals_line = {
            #         'posting_error_id':self.id,
            #         'client_id':ad_client_id,
            #         'client_name':ad_client,
            #         'm_product_id':M_Product_ID,
            #         'product_name':M_Product,
            #         'description':M_AttributeSetInstance,
            #         'm_attributesetinstance_id':M_AttributeSetInstance_ID,
            #         'qtyused':qtyused,
            #         'qtypresent':currentqty,
            #         'm_costelement_id' : m_costelement_id,
            #       }

            #     self.env['posting.error.lines'].create(vals_line)


        if self.state == 'select2':
          self.completed = True
        else:
          self.state = 'select'
          self.m_product_id = m_product_id
          self.productionqty = productionqty

        self.name = 'Posting Error'

      except psycopg2.DatabaseError, e:
        if conn_pg:
          print "#-------------------Except----------------------#"
          conn_pg.rollback()
     
        print 'Error %s' % e    
        # sys.exit(1)

      finally:
        if conn_pg:
          print "#--------------Select ----Finally----------------------#"
          conn_pg.close()


  @api.multi
  def update_data_to_database(self):
    print "#----------Update ---TRY----------------------#"

    conn_pg = None
    idempiere_id=self.idempiere_id
    documentno=self.documentno
    if self.config_id:
      try:

        conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, password=self.config_id.password, host= self.config_id.ip_address)
        pg_cursor = conn_pg.cursor()

        for rec in self.posting_error_one2many:
          addedqty= rec.qtyadded

          # if not rec.qtyadded:
          #   raise UserError(_('Enter Added Quantity in atleast one record.'))

          if rec.qtyadded and not rec.updated:
            pg_cursor.execute("update adempiere.m_cost set currentqty=%s where M_Product_ID=%s and \
              M_AttributeSetInstance_ID=%s and m_costelement_id=%s and ad_client_id=%s",(float(addedqty),int(rec.m_product_id),int(rec.m_attributesetinstance_id),
                int(rec.m_costelement_id),int(rec.client_id)))

            print "Updates .....................................TTTTTTTTTTTTTTTTTTTTTTTTTTTTT"

            entry_id = conn_pg.commit()
            rec.updated = True
        
        self.state = 'select2'


      except psycopg2.DatabaseError, e:
        if conn_pg:
            conn_pg.rollback()
     
        print 'Error %s' % e    

      finally:
        if conn_pg:
          print "#---------------Update ----Finally----------------------#"
          conn_pg.close()



class posting_error_lines(models.Model):
  _name = "posting.error.lines"
  _description="Posting Error lines"

  name = fields.Char('Name')
  posting_error_id = fields.Many2one('posting.error', string='connect', track_visibility='onchange')
  client_id = fields.Char('Client ID')
  client_name = fields.Char('Client')
  m_product_id = fields.Char('Product ID')
  product_name = fields.Char('Product')
  m_costelement_id = fields.Char('Cost Element ID')
  description = fields.Char('Attribute')
  m_attributesetinstance_id = fields.Char('Attribute Set Instance')
  qtyused = fields.Float('Qty Used')
  qtypresent = fields.Float('Qty Present')
  qtyadded = fields.Char('Qty Added')
  updated = fields.Boolean('Updated', default=False)
  synced = fields.Boolean('Synced', default=False)


