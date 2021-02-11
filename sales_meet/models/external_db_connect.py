
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
from odoo.exceptions import UserError , ValidationError, Warning

_logger = logging.getLogger(__name__)

import dateutil.parser
import shutil
import os
import time
import psycopg2
import urllib
import tarfile
import base64
import csv
import cStringIO

todaydate = "{:%Y-%m-%d}".format(datetime.now())


class external_db_connect(models.Model):
  _name = "external.db.connect"
  _description=" External DB Connect"
  _inherit = 'mail.thread'
  _order  = 'id desc'


  @api.multi
  def unlink(self):
    for order in self:
      if order.state != 'draft':
        raise UserError(_('You can only delete Draft Entries'))
    return super(external_db_connect, self).unlink()


  @api.multi
  def _get_config(self):
      config = self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1)
      if config:
        config_id = config.id
      else:
        config = self.env['external.db.configuration'].search([('id', '!=',0)], limit=1)
        config_id = config.id
      return config_id

  # portal_user = fields.Boolean("Portal User" , default=False)
  name = fields.Char('Name', store=True)
  db_name = fields.Char('DB Name')
  config_id = fields.Many2one('external.db.configuration', string='Database', track_visibility='onchange' , default=_get_config)
  # ,      default=lambda self: self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1)
  note = fields.Text('Text', track_visibility='onchange')
  state = fields.Selection([('draft', 'Draft'),
                       ('select', 'Earlier'), 
                       ('update', 'Updated'), 
                       ('update2', 'Line Updated'), 
                       ('select2', 'Changed')], string='Status',track_visibility='onchange', default='draft')
  entry_type = fields.Selection([
                        ('invoice', 'Invoice'),
                        ('payment', 'Payment/Receipt'),
                        ('production', 'Production'),
                        ('shipment', 'Shipment / Material Receipt')], 
                        string='Entry Type',track_visibility='onchange')
  idempiere_id = fields.Integer('iDempiere ID', track_visibility='onchange')
  documentno = fields.Char('Document No', track_visibility='onchange')
  requester = fields.Char('Requester')
  connect_lines_one2many = fields.One2many('external.db.lines','connect_id',string="Line Details")
  date = fields.Date(string="Date From", default=lambda self: fields.Datetime.now())
  employee_id = fields.Many2one('hr.employee', string="Employee")
  schedular = fields.Boolean("Schedular")
  completed = fields.Boolean("Completed",copy=False)
  movement_date = fields.Boolean("Movement Date")
  partner_update = fields.Boolean("Partner Update")
  c_bpartner_id = fields.Char("Partner ID",default='Standard')
  ad_client_id = fields.Char('Client ID')
  condition = fields.Selection([
                        ('reactivation', 'Reactivation'),
                        ('date_change', 'Date Change'),
                        ('status_change', 'Status Change'),
                        ('null_partner_updation', 'Null Partner Updation'),
                        ('schedular', 'Schedular'),
                        ('reverse', 'Reverse/Invoice No Change'),], 
                        string='Condition',track_visibility='onchange')
  docstatus = fields.Selection([
                        ('DR', 'DRAFT'),
                        ('CO', 'COMPLETE'),
                        ('CL', 'CLOSE'),], 
                        string='DocStatus',track_visibility='onchange')
  changed_date = fields.Date(string="Changed Date")
  poreference_update = fields.Char("Order Reference Update",default='@WrongEntry')


  @api.onchange('partner_update')
  def onchange_partner_update(self):
      if self.partner_update:
        self.entry_type = 'payment'


  @api.onchange('condition')
  def onchange_condition_update(self):
      if self.condition == 'null_partner_updation':
        self.entry_type = 'payment'
        self.partner_update = True
      elif self.condition == 'schedular':
        self.schedular = True
      elif self.condition == 'date_change':
        self.movement_date = True
      elif self.condition == 'reverse':
        self.entry_type = 'invoice'
      else:
        self.entry_type = ''
        self.partner_update = False
        self.schedular = False
        self.movement_date = False


  # @api.multi
  # def get_schedular(self):
  #   conn_pg = None
  #   if self.schedular:

  #     print "#-------------Select --TRY----------------------#"
  #     try:
  #       conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
          # password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
  #       pg_cursor = conn_pg.cursor()

  #       pg_cursor.execute("select org.name,c.name,documentno,c_doctype_id,issoTrx,inv.dateinvoiced,grandtotal FROM c_invoice inv \
  #         JOIN ad_org org ON org.ad_org_id = inv.ad_org_id \
  #         JOIN ad_client c ON c.ad_client_id = inv.ad_client_id \
  #         WHERE c_invoice_Id IN \
  #         ( SELECT record_id FROM fact_acct WHERE ad_table_id=318 GROUP BY ad_table_id, record_id, account_id, 
            #line_id, ad_org_id, ad_client_id\
  #          HAVING count(line_id) > 1)\
  #         ORDER BY inv.dateinvoiced DESC")
  #       records = pg_cursor.fetchall()

        
  #       if len(records) == 0:
  #         raise UserError("No records Found")

  #       for record in records:
  #         vals_line = {
  #             'connect_id':self.id,
  #             'c_invoice_id':record[0],
  #             'c_bpartner_id':record[1],
  #             'documentno':record[2],
  #             'posted':record[4],
  #             'dateacct':record[5],
  #             'grandtotal':record[6],
              
  #           }
  #         self.env['external.db.lines'].create(vals_line)

  #       self.state = 'select2'
  #       self.name = 'Schedular ' + self.date

  #     except psycopg2.DatabaseError, e:
  #       if conn_pg:
  #         print "#-------------------Except----------------------#"
  #         conn_pg.rollback()
     
  #       print 'Error %s' % e    

  #     finally:
  #       if conn_pg:
  #         print "#--------------Select ----Finally----------------------#"
  #         conn_pg.close()

  @api.multi
  def get_schedular(self):
    conn_pg = None
    if self.schedular:

      print "#-------------Select --TRY----------------------#"
      try:
        conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, password=self.config_id.password, 
          host= self.config_id.ip_address,port=self.config_id.port)
        pg_cursor = conn_pg.cursor()


        # pg_cursor.execute("select org.name, \
        #                           c.name, \
        #                           documentno, \
        #                           c_doctype_id, \
        #                           issoTrx, \
        #                           inv.dateinvoiced, \
        #                           grandtotal \
        #                         FROM adempiere.c_invoice inv \
        #                         JOIN adempiere.ad_org org ON org.ad_org_id = inv.ad_org_id \
        #                         JOIN adempiere.ad_client c ON c.ad_client_id = inv.ad_client_id \
        #                         WHERE \
        #                           inv.c_invoice_Id not in (select inv.c_invoice_id from adempiere.c_invoice inv \
        #                           JOIN adempiere.c_invoiceline cil ON cil.C_Invoice_ID = inv.C_Invoice_ID \
        #                           and cil.C_Charge_ID in (select C_Charge_ID from adempiere.C_Charge where name ilike '%tds%')) \
        #                           and inv.c_invoice_Id IN \
        #                           ( SELECT record_id \
        #                           FROM adempiere.fact_acct \
        #                           WHERE ad_table_id=318 \
        #                           GROUP BY ad_table_id, \
        #                           record_id, \
        #                           account_id, \
        #                           line_id, \
        #                           ad_org_id, \
        #                           ad_client_id \
        #                           HAVING count(line_id) > 1) \
        #                           ORDER BY inv.dateinvoiced DESC")


        pg_cursor.execute("select * from adempiere.daily_schedular_query()")
        records = pg_cursor.fetchall()

        
        if len(records) == 0:
          raise UserError("No records Found")

        for record in records:
          vals_line = {
              'connect_id':self.id,
              'c_invoice_id':record[0],
              'c_bpartner_id':record[1],
              'documentno':record[2],
              'posted':record[4],
              'dateacct':record[5],
              'grandtotal':record[6],
              
            }
          self.env['external.db.lines'].create(vals_line)

        self.state = 'select2'
        self.name = 'Schedular ' + self.date

      except psycopg2.DatabaseError, e:
        print 'Error %s' % e
        if conn_pg:
          print "#-------------------Except----------------------#"
          conn_pg.rollback()
     
        print 'Error %s' % e    

      finally:
        if conn_pg:
          print "#--------------Select ----Finally----------------------#"
          conn_pg.close()

  

  @api.multi
  def get_data_from_database(self):
    conn_pg = None
    if self.config_id:
      idempiere_id=self.idempiere_id
      documentno=self.documentno
      print "#-------------Select --TRY----------------------#"
      try:
        conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
          password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
        pg_cursor = conn_pg.cursor()

        if len(str(self.idempiere_id)) < 7 or len(str(self.idempiere_id)) > 7 :
          raise UserError("Wrong idempiere ID entered. Select proper ID")

        #---------------------------------------------- # Invoice Entry --------------------------------------------#

        if self.entry_type == 'invoice':

          # pg_cursor.execute("select docstatus from C_Invoice where   C_Invoice_ID = %s and documentno = %s  \
          # and docstatus !='RE' ",(idempiere_id,documentno))
          # docstatus_check = pg_cursor.fetchall()
          
          # if len(docstatus_check) == 0:
          #   raise UserError("Invoice Entry is reversed")

          if self.condition == 'status_change':
            raise UserError("Kindly select Reactivation Condition for changing status")


          if self.condition == 'reactivation':

            pg_cursor.execute("select C_AllocationLine_ID from adempiere.C_AllocationLine where C_Invoice_ID = %s ",[idempiere_id])
            allocation = pg_cursor.fetchall()
            
            if len(allocation) > 0:
              raise UserError("Allocation is present for this Entry. Please reset the allocation")

            pg_cursor.execute("select C_Invoice_ID,dateacct, \
              (select c_bpartner.name from adempiere.c_bpartner where c_bpartner.c_bpartner_id = cb.c_bpartner_id ),\
              documentno, totallines, grandtotal, docstatus , posted  ,\
             processed from adempiere.C_Invoice cb where C_Invoice_ID=%s and documentno=%s",(idempiere_id,documentno))
            # print "lllllllllllllllllllllllllll**********************************"

          if self.condition == 'reverse':
            pg_cursor.execute("select C_Invoice_ID,dateacct, \
              (select c_bpartner.name from adempiere.c_bpartner where c_bpartner.c_bpartner_id = cb.c_bpartner_id ), \
              documentno, totallines, grandtotal, docstatus, posted, processed , \
              (select ad_user.name from adempiere.ad_user where ad_user.ad_user_id = cb.createdby ) \
              from adempiere.C_Invoice cb where C_Invoice_ID=%s and documentno=%s",(idempiere_id,documentno))

          if self.condition == 'date_change':
            pg_cursor.execute("select C_Invoice_ID,dateacct, \
              (select c_bpartner.name from adempiere.c_bpartner where c_bpartner.c_bpartner_id = cb.c_bpartner_id ), \
              documentno, totallines, grandtotal, docstatus, posted, processed , \
              (select ad_user.name from adempiere.ad_user where ad_user.ad_user_id = cb.createdby ) \
              from adempiere.C_Invoice cb where C_Invoice_ID=%s and documentno=%s",(idempiere_id,documentno))



        #---------------------------------------------- # Payment Entry --------------------------------------------#

        elif self.entry_type == 'payment': # Payment Entry

          if self.condition == 'date_change':
            raise UserError("Payment / Receipt dates can be changed from ERP")

          if self.condition == 'status_change':
            raise UserError("Kindly select Reactivation Condition for changing status")

          pg_cursor.execute("select C_AllocationLine_ID  from adempiere.C_AllocationLine where   C_Payment_ID = %s",[idempiere_id])
          allocation = pg_cursor.fetchall()
          
          if len(allocation) > 0 and not self.partner_update:
            raise UserError("Allocation is present for this Entry. Please reset the allocation")

          pg_cursor.execute("select ad_client_id  from adempiere.C_Payment where   C_Payment_ID = %s",[idempiere_id])
          ad_client_id = pg_cursor.fetchall()

          print "oooooooooooooooooooooooooooooooooo" , ad_client_id

          self.ad_client_id = ((str(ad_client_id[0][0])).split('.'))[0] 

          pg_cursor.execute("select C_Payment_ID,dateacct, (select c_bpartner.name from adempiere.c_bpartner where \
                        c_bpartner.c_bpartner_id = cb.c_bpartner_id ), \
                        documentno, payamt,payamt, docstatus , posted  , \
                        processed from adempiere.C_Payment cb where C_Payment_ID=%s and documentno=%s",(idempiere_id,documentno))

        #---------------------------------------------- # Production Entry --------------------------------------------#


        elif self.entry_type == 'production': 
          if self.condition == 'reactivation':
            raise UserError("Production cannot be reactivated. Only reversed")

          pg_cursor.execute("select M_Production_ID,MovementDate, (select M_Product.name from adempiere.M_Product where \
                        M_Product.M_Product_ID = mp.M_Product_ID ), \
                        documentno, QtyBatchSize,productionqty, docstatus , posted  , \
                        processed from adempiere.M_Production mp where M_Production_ID=%s and documentno=%s",(idempiere_id,documentno))


        #---------------------------------------------- # Shipment Entry --------------------------------------------#

        elif self.entry_type == 'shipment':
          if self.condition == 'reactivation':
            raise UserError("Shipment cannot be reactivated. Only reversed")

          if self.condition == 'date_change':
            raise UserError("Shipment / Material Receipt dates can be changed from ERP")

          pg_cursor.execute("select M_InOut_ID, dateordered ,  (select c_bpartner.name from adempiere.c_bpartner where \
                        c_bpartner.c_bpartner_id = mio.c_bpartner_id )\
                         ,documentno , totalpricelist,totalnetprice, docstatus , posted  , \
                         processed from  adempiere.M_InOut mio where  M_InOut_ID=%s and documentno=%s ",(idempiere_id,documentno))


        #---------------------------------------------- # Shipment Entry --------------------------------------------#


        entry_id = pg_cursor.fetchall()

        if len(entry_id) == 0:
            raise UserError("Wrong Idempiere ID / Document No entered. Recheck Both")

        vals_line = {
            'connect_id':self.id,
            'c_invoice_id':entry_id[0][0],
            'dateacct':entry_id[0][1],
            'c_bpartner_id':entry_id[0][2],
            'documentno':entry_id[0][3],
            'totallines':entry_id[0][4],
            'grandtotal':entry_id[0][5],
            'docstatus':entry_id[0][6],
            'posted':entry_id[0][7],
            'processed':entry_id[0][8],
          }

        if self.condition == 'reverse':
          self.requester = entry_id[0][9]

        self.env['external.db.lines'].create(vals_line)

        if self.state == 'update2' and self.condition == 'date_change':
          self.state = 'select2'
          self.completed = True
          # print errporro


        # self.note = entry_id
        if self.state == 'update2':
          self.state = 'select2'
          if self.entry_type != 'invoice':
            self.completed = True

        elif self.state == 'select2':
          self.state = 'select2'
          self.completed = True
        else:
          self.state = 'select'

        if self.entry_type and (self.employee_id or self.requester ):
            if self.entry_type == 'invoice':
              entry_type = 'Invoice'
            elif self.entry_type == 'payment':
              entry_type = 'Payment'
            elif self.entry_type == 'production':
              entry_type = 'Production'
            elif self.entry_type == 'shipment':
              entry_type = 'Shipment'
            rep_name = entry_type + " Reactivation by "  + (self.employee_id.name if self.employee_id.name else self.requester)

            self.name = rep_name

      except psycopg2.DatabaseError, e:
          if conn_pg: conn_pg.rollback()
          print 'Error %s' % e    

      finally:
          if conn_pg: conn_pg.close()
          print "#---------------Update Lines----Finally----------------------#"


  @api.multi
  def update_data_from_database(self):
    print "#----------Update ---TRY----------------------#"

    conn_pg = None
    idempiere_id=self.idempiere_id
    documentno=self.documentno
    value = self.c_bpartner_id
    changed_date = self.changed_date
    docstatus = self.docstatus
    poreference = self.poreference_update

    if self.config_id:
      try:

        conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
          password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
        pg_cursor = conn_pg.cursor()

        #---------------------------------------------- # Invoice Entry --------------------------------------------#

        if self.entry_type == 'invoice':
          if self.condition == 'reverse':
            pg_cursor.execute("update adempiere.C_Invoice set poreference = %s  where \
              C_Invoice_ID=%s and documentno=%s",(poreference,idempiere_id,documentno))

          else:

            if self.movement_date == True:
              pg_cursor.execute("update adempiere.C_Invoice set dateacct = %s , dateinvoiced = %s where \
                C_Invoice_ID=%s and documentno=%s",(changed_date, changed_date ,idempiere_id,documentno))
            else: 
              pg_cursor.execute("update adempiere.C_Invoice set docstatus = 'DR' , posted = 'N' , processed = 'N' where \
                C_Invoice_ID=%s and documentno=%s",(idempiere_id,documentno))


        #---------------------------------------------- # Payment Entry --------------------------------------------#

        if self.entry_type == 'payment':

          if self.condition == 'date_change':
            raise UserError("Payment / Receipt dates can be changed from ERP")


          if self.partner_update:
            pg_cursor.execute("select c_bpartner_id from adempiere.c_payment where \
              C_Payment_ID = %s and documentno=%s",(idempiere_id,documentno))
            c_bpartner_check = pg_cursor.fetchall()

            c_bpartner_check2 = c_bpartner_check[0][0]

            if c_bpartner_check2 :
              raise UserError("Partner Already Present")


            pg_cursor.execute("update adempiere.C_Payment set c_bpartner_id = (select c_bpartner_id \
              from adempiere.c_bpartner where value = %s and ad_client_id = \
              ( select ad_client_id from adempiere.c_payment where c_payment_id = %s ))\
             where  documentno=%s and c_payment_id=%s",(value,idempiere_id,documentno,idempiere_id))
            self.c_bpartner_id = ''
          else:
            pg_cursor.execute("update adempiere.C_Payment set docstatus = 'DR' , posted = 'N' , \
              processed = 'N' where C_Payment_ID=%s and documentno=%s",(idempiere_id,documentno))

        #---------------------------------------------- # Production Entry --------------------------------------------#


        if self.entry_type == 'production':
          if self.movement_date == True:
            pg_cursor.execute("update adempiere.M_Production set MovementDate = DatePromised  where \
              M_Production_ID=%s and documentno=%s",(idempiere_id,documentno))
          else:
            pg_cursor.execute("update adempiere.M_Production set docstatus = 'CO'  where \
              M_Production_ID=%s and documentno=%s",(idempiere_id,documentno))

        #---------------------------------------------- # Shipment Entry --------------------------------------------#

        if self.entry_type == 'shipment':
          if self.condition == 'reactivation':
            raise UserError("Shipment cannot be reactivate. Only reversed")

          if self.condition == 'status_change':
            pg_cursor.execute("update adempiere.M_InOut set docstatus = %s  where \
              M_InOut_ID=%s and documentno=%s",(docstatus,idempiere_id,documentno))

          # if self.movement_date == True:
          #   pg_cursor.execute("update M_InOut set dateacct = %s , movementdate = %s where \
          # M_InOut_ID=%s and documentno=%s",(changed_date, changed_date ,idempiere_id,documentno))
          # else:
          #   pg_cursor.execute("update M_InOut set docstatus = 'CO'  where M_InOut_ID=%s and documentno=%s",(idempiere_id,documentno))


        #---------------------------------------------- #  Entry Closed --------------------------------------------#


        # entry_id = pg_cursor.fetchall()
        entry_id = conn_pg.commit()
        # self.note = entry_id
        
        self.state = 'update2'

      except psycopg2.DatabaseError, e:
          if conn_pg: conn_pg.rollback()
          print 'Error %s' % e    

      finally:
          if conn_pg: conn_pg.close()
          print "#---------------Update Lines----Finally----------------------#"


  @api.multi
  def update_line_data_from_database(self):
    print "#---------Update Lines ------TRY----------------------#"

    conn_pg = None
    idempiere_id=self.idempiere_id
    documentno=self.documentno

    if self.config_id:
      try:

        conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
          password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
        pg_cursor = conn_pg.cursor()

        if self.entry_type == 'invoice':
          pg_cursor.execute("update adempiere.C_InvoiceLine set processed = 'N' where C_Invoice_ID=%s",[idempiere_id])
        
        entry_id = conn_pg.commit()
        # self.note = entry_id
        self.state = 'select2'

      except psycopg2.DatabaseError, e:
          if conn_pg: conn_pg.rollback()
          print 'Error %s' % e    

      finally:
          if conn_pg: conn_pg.close()
          print "#---------------Update Lines----Finally----------------------#"


  @api.multi
  def update_null_partner(self):
    print "#---------Update Lines ------TRY----------------------#"

    conn_pg = None
    idempiere_id=self.idempiere_id
    documentno=self.documentno

    if self.config_id:
      try:

        conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
          password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
        pg_cursor = conn_pg.cursor()

        if self.entry_type == 'payment' and self.ad_client_id:

          pg_cursor.execute("select docstatus from adempiere.c_payment where \
            documentno ilike '"+documentno+"%' and ad_client_id = '"+self.ad_client_id+"'")
          docstatus_check = pg_cursor.fetchall()
          docstatus_check2 = docstatus_check[0][0].encode('utf-8')

          if docstatus_check2 not in ('RE','VO') :
              raise UserError("Kindly reverse/Void the entry First")

          pg_cursor.execute("update adempiere.C_Payment set c_bpartner_id = Null where \
            documentno ilike '"+documentno+"%' and ad_client_id = '"+self.ad_client_id+"'")
        
        entry_id = conn_pg.commit()
        # self.note = entry_id
        self.state = 'update2'
        self.completed = False

      except psycopg2.DatabaseError, e:
          if conn_pg: conn_pg.rollback()
          print 'Error %s' % e    

      finally:
          if conn_pg: conn_pg.close()
          print "#---------------Update Lines----Finally----------------------#"


class external_db_configuration(models.Model):
  _name = "external.db.configuration"
  _description=" External DB Configuration"

  name= fields.Char('Name')
  ip_address = fields.Char('DB Ip Address', track_visibility='onchange')
  app_ip_address = fields.Char('App Ip Address', track_visibility='onchange')
  database_name = fields.Char('Database')
  username = fields.Char('User Name')
  password = fields.Char('Password')
  port = fields.Char('Port')
  idempiere_url = fields.Char('iDempiere URL' , track_visibility='onchange')
  idempiere_url_dns = fields.Char('iDempiere URL DNS', track_visibility='onchange')
  state = fields.Selection([('draft', 'Draft'),
                       ('connected', 'Connected'), 
                       ('rejected', 'Rejected')], string='Status',track_visibility='onchange', default='draft')

  @api.multi
  def check_connection(self):
    print "#--------- check_connection ------TRY----------------------#"

    conn_pg = None

    if self.ip_address:

      obj =  self.env['external.db.configuration'].search([("state","=",'connected')])
      if len(obj) > 0 :
          raise ValidationError(_("Default Database have already been set. Multiple Database Connections are not allowed"))

      try:

        conn_pg = psycopg2.connect(dbname= self.database_name, user=self.username, 
          password=self.password, host= self.ip_address, port= self.port)
        pg_cursor = conn_pg.cursor()

        self.state = 'connected'
        self.name = self.ip_address + ' - ' + self.database_name

      except psycopg2.DatabaseError, e:
          if conn_pg: conn_pg.rollback()
          print 'Error %s' % e    

      finally:
          if conn_pg: conn_pg.close()
          print "#---------------Update Lines----Finally----------------------#"


  @api.multi
  def disconnect(self):
    self.state = 'rejected'


class external_db_lines(models.Model):
  _name = "external.db.lines"
  _description=" External DB lines"

  name = fields.Char('Name')
  connect_id = fields.Many2one('external.db.connect', string='connect', track_visibility='onchange')
  c_bpartner_id = fields.Char('Partner / Client')
  documentno = fields.Char('Document No')
  c_invoice_id = fields.Char('Invoice/Payment')
  totallines = fields.Char('Total')
  grandtotal = fields.Char('Grand Total')
  docstatus = fields.Char('Status')
  processed = fields.Char('Processed')
  posted = fields.Char('Posted')
  dateacct = fields.Char('Account Date')


class wp_grn_import(models.Model):
    _name = 'wp.grn.import'
    _description = "GRN Import"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    name = fields.Char(string = "Doc No.")
    date_start = fields.Date(string="From Date" , default=lambda self: fields.datetime.now())
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid, track_visibility='always')
    state = fields.Selection([
            ('draft', 'Draft'),
            ('done', 'Generated'),
            ('validated', 'Validated'),
            ('import_template', 'Template Imported'),
            ('cancel', 'Rejected'),
            ], string='Status', readonly=True,
            copy=False, index=True, track_visibility='always', default='draft')
    company_id = fields.Many2one('res.company', 'Company', 
      default=lambda self: self.env['res.company']._company_default_get('wp.grn.import'))
    grn_import_line_one2many = fields.One2many('wp.grn.import.line','grn_import_id',string="GRN Import Line")
    check_lines = fields.Boolean(string = "", nolabel="1" , default=False)
    grn_data = fields.Char('Name', size=256)
    file_name = fields.Binary('CSV Import', readonly=True)
    delimeter = fields.Char('Delimeter', default=',')
    condition = fields.Selection([
                        ('grn', 'GRN'),
                        ('trans', 'Trans')], string='Condition')


    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and self.env.uid != 1:
                raise UserError(_('You can only delete Draft Entries'))
        return super(wp_grn_import, self).unlink()



    @api.multi
    def add_lines(self):

        if self.state == 'draft':
            data = base64.b64decode(self.file_name)
            file_input = cStringIO.StringIO(data)
            file_input.seek(0)
            reader_info = []
            delimeter = ','
            reader = csv.reader(file_input, delimiter=delimeter,lineterminator='\r\n')
            try:
                reader_info.extend(reader)
            except Exception:
                reader_info.extend(reader)
                raise Warning(_("Not a valid file!"))
            keys = reader_info[0]
            # check if keys exist
            if not isinstance(keys, list) or ('documentno' not in keys ):
                raise Warning(
                    _("'Documentno' keys not found"))
            del reader_info[0]
            values = {}
            
            for i in range(len(reader_info)):
                val = {}
                field = reader_info[i]
                values = dict(zip(keys, field))

                if values['grn_date']:
                  try:
                    grn_date2 = dateutil.parser.parse(values['grn_date'])
                    grn_date = grn_date2.strftime("%Y-%m-%d")
                    val['grn_date'] = grn_date #values['grn_date']
                  except:
                    val['grn_date']= ''

                if values['ssc_date']:
                  try:

                    ssc_date2 = dateutil.parser.parse(values['ssc_date'])
                    ssc_date = ssc_date2.strftime("%Y-%m-%d")
                    val['ssc_date'] = ssc_date #values['ssc_date']

                  except:
                    val['ssc_date']= ''
             
                val['documentno'] = values['documentno'] or ''
                val['inbound_no'] = values['inbound_no'] or ''
                val['grn_no'] = values['grn_no'] or ''
                val['grn_import_id'] = self.id

                if values['remarks'] :               
                  val['remarks'] = (values['remarks']).encode('ascii', 'ignore').decode('ascii') or ''
                
                grn_lines = self.grn_import_line_one2many.sudo().create(val)

            self.name = 'GRN Import (' + todaydate + ')'
            self.state = 'done'
               
        else:
            raise Warning(_("GRN can be imported only in 'Draft' Stage"))



    @api.multi
    def update_invoices(self):
      conn_pg = None
      inbound = grn_no = grn_date = ssc_date = remarks = ''
      config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)

      if config_id:
        try:
          print "#---------Update Lines ------TRY----------------------#"
          isactive =  "isactive =  'Y' "
          main_query = " update adempiere.c_invoice ci SET "
          ad_client_id = self.company_id.ad_client_id

          conn_pg = psycopg2.connect(dbname= self.database_name, user=self.username, 
          password=self.password, host= self.ip_address, port= self.port)
          pg_cursor = conn_pg.cursor()

          for res in self.grn_import_line_one2many:
            if res.inbound_no:
              inbound = "inbound_no = '%s' "  %(res.inbound_no)

            if  res.grn_no:
              grn_no =  "grn_no =  '%s' "  %(res.grn_no)

            if  res.grn_date:
              grn_date =  "grn_date =  '%s' "  %(res.grn_date)

            if  res.ssc_date:
              ssc_date =  "ssc_date =  '%s' "  %(res.ssc_date)

            if  res.remarks:
              remarks =  "remarks =  '%s' "  %(res.remarks)

            end_query = "Where documentno = '%s' and ad_client_id = %s " %(res.documentno, ad_client_id)

            query_grn = main_query + ( (inbound + ', ' ) if res.inbound_no else '' ) + \
                        ( (grn_no + ', ') if res.grn_no else '' ) + \
                        ( (grn_date + ', ') if res.grn_date else '' ) + \
                        ( (ssc_date + ', ')   if res.ssc_date  else '' ) + \
                        ( (remarks + ', ') if res.remarks else '' ) +  isactive + end_query


            print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" , query_grn
            pg_cursor.execute(query_grn)
            entry_id = conn_pg.commit()

          self.state = 'import_template'

        except psycopg2.DatabaseError, e:
          if conn_pg: conn_pg.rollback()
          print '------------Error %s' % e    

        finally:
          if conn_pg: conn_pg.close()
          print "#---------------Update Lines----Finally----------------------#"


    @api.multi
    def add_trans_lines(self):
        if self.state == 'draft':
            data = base64.b64decode(self.file_name)
            file_input = cStringIO.StringIO(data)
            file_input.seek(0)
            reader_info = []
            delimeter = ','
            reader = csv.reader(file_input, delimiter=delimeter,lineterminator='\r\n')
            try:
                reader_info.extend(reader)
            except Exception:
                reader_info.extend(reader)
                raise Warning(_("Not a valid file!"))
            keys = reader_info[0]
            if not isinstance(keys, list) or ('invoiceno' not in keys ):
                raise Warning(
                    _("'Invoiceno' keys not found"))
            del reader_info[0]
            values = {}
            
            for i in range(len(reader_info)):
                val = {}
                field = reader_info[i]
                values = dict(zip(keys, field))

                val['documentno'] = values['invoiceno'] or ''
                val['wpp_trans_charged'] = values['Trans Charges (per ton)'] or ''
                val['wpp_trans_pmt_rcvd'] = values['Trans Charged (per ton)'] or ''
                val['wpp_trans_pmt_bal'] = values['Trans Charges Diff (per ton)'] or ''
                val['wpp_trans_charges'] = values['Trans Bal Payment'] or ''
                val['grn_import_id'] = self.id
                
                grn_lines = self.grn_import_line_one2many.sudo().create(val)

            self.name = 'Transport Charges (' + todaydate + ')'
            self.state = 'done'
               
        else:
            raise Warning(_("Dispatch Details can be imported only in 'Draft' Stage"))


    @api.multi
    def validate_trans_invoices(self):
      conn_pg = None
      wpp_trans_charged = wpp_trans_pmt_rcvd = wpp_trans_pmt_bal = wpp_trans_charges = ''
      config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)

      if config_id:
        try:
          print "#---------Update Lines ------TRY----------------------#"
          ad_client_id = self.company_id.ad_client_id
          isactive =  "isactive =  'Y' "
          main_query = " select poreference from adempiere.c_invoice "

          conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, password=config_id.password,
           host= config_id.ip_address,port= config_id.port)
          pg_cursor = conn_pg.cursor()

          for res in self.grn_import_line_one2many:
            end_query = "Where POReference = '%s' and ad_client_id = %s " %(res.documentno, ad_client_id)

            query_grn = main_query + end_query

            pg_cursor.execute(query_grn)
            record_query = pg_cursor.fetchall()

            if record_query != []:
                for rec in record_query:
                    print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" , rec
            else:
                raise ValidationError(_('Invoice No Not Found %s' % (res.documentno)))

            entry_id = conn_pg.commit()
          self.state = 'validated'

        except psycopg2.DatabaseError, e:
            if conn_pg: conn_pg.rollback()
            print 'Error %s' % e    

        finally:
            if conn_pg: conn_pg.close()
            print "#---------------Update Lines----Finally----------------------#"


    @api.multi
    def update_trans_invoices(self):
      
      conn_pg = None
      wpp_trans_charged = wpp_trans_pmt_rcvd = wpp_trans_pmt_bal = wpp_trans_charges = ''
      config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)

      if config_id:
        try:
          print "#---------Update Lines ------TRY----------------------#"
          ad_client_id = self.company_id.ad_client_id
          isactive =  "isactive =  'Y' "
          main_query = " update adempiere.c_invoice ci SET "

          conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, password=config_id.password,
           host= config_id.ip_address,port= config_id.port)
          pg_cursor = conn_pg.cursor()

          for res in self.grn_import_line_one2many:

            if res.wpp_trans_charged:
              wpp_trans_charged = "wpp_trans_charged = %s "  %(res.wpp_trans_charged)

            if  res.wpp_trans_pmt_rcvd:
              wpp_trans_pmt_rcvd =  "wpp_trans_pmt_rcvd =  %s "  %(res.wpp_trans_pmt_rcvd)

            if  res.wpp_trans_pmt_bal:
              wpp_trans_pmt_bal =  "wpp_trans_pmt_bal =  %s "  %(res.wpp_trans_pmt_bal)

            if  res.wpp_trans_charges:
              wpp_trans_charges =  "wpp_trans_charges =  '%s' "  %(res.wpp_trans_charges)

            end_query = "Where POReference = '%s' and ad_client_id = %s " %(res.documentno, ad_client_id)

            query_grn = main_query + ( (wpp_trans_charged + ', ' ) if res.wpp_trans_charged else '' ) + \
                        (  (wpp_trans_pmt_rcvd + ', '  ) if res.wpp_trans_pmt_rcvd else '' ) + \
                        ( (wpp_trans_pmt_bal + ', ') if res.wpp_trans_pmt_bal else '' ) + \
                        ( (wpp_trans_charges + ', ')   if res.wpp_trans_charges  else '' )  \
                         +  isactive + end_query

            print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" , query_grn

            pg_cursor.execute(query_grn)
            entry_id = conn_pg.commit()
          self.state = 'import_template'

        except psycopg2.DatabaseError, e:
          if conn_pg: conn_pg.rollback()
          print 'Error %s' % e    

        finally:
          if conn_pg: conn_pg.close()
          print "#---------------Update Lines----Finally----------------------#"



class wp_grn_import_line(models.Model):
    _name = 'wp.grn.import.line'
    _description = "GRN Import Line"

    # location = fields.Char(string = "Location")
    grn_import_id  = fields.Many2one('wp.grn.import', ondelete='cascade')

    name = fields.Char('Name')
    documentno = fields.Char('Documentno')
    inbound_no = fields.Char('Inbound No')
    grn_no = fields.Char('Grn No')
    grn_date = fields.Date('GRN Date')
    ssc_date = fields.Date('SSC Date')
    remarks = fields.Char("Remarks")

    wpp_trans_charged = fields.Float('Trans Charges (per ton)')
    wpp_trans_pmt_rcvd = fields.Float('Trans Charged (per ton)')
    wpp_trans_pmt_bal = fields.Float('Trans Charges Diff (per ton)')
    wpp_trans_charges = fields.Float('Trans Bal Payment')
    # poreference = order reference