#!/usr/bin/env bash
from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT

from odoo.tools.translate import _
from odoo import tools, api
from odoo import api, fields, models, _ , registry, SUPERUSER_ID
from odoo.osv import    osv
# import erppeek
import logging
import xmlrpclib
import sys
from openerp.exceptions import UserError , ValidationError
import dateutil.parser

_logger = logging.getLogger(__name__)

import shutil
import os
import time
import psycopg2
import urllib
import tarfile
import csv
from cStringIO import StringIO
import xlwt
import re
import base64
import pytz
from odoo.addons.web.controllers.main import ExcelExport
from subprocess import Popen
import getpass



class bank_payment_icici(models.Model):
    _name = "bank.payment.icici"
    _description=" Payment to Bank"
    _inherit = 'mail.thread'
    _order    = 'id desc'


    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_('You can only delete Draft Entries'))
        return super(bank_payment_icici, self).unlink()

    # portal_user = fields.Boolean("Portal User" , default=False)
    name = fields.Char('Name', store=True)
    db_name = fields.Char('DB Name')
    config_id = fields.Many2one('external.db.configuration', string='Database', track_visibility='onchange',    
        default=lambda self: self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1))
    note = fields.Text('Text', track_visibility='onchange')
    state = fields.Selection([('draft', 'Draft'),
                             ('generated_invoice', 'Invoice Generated'), 
                             ('submitted_to_manager', 'Submitted to Manager'), 
                             ('generated_payment', 'Payment Generated'), 
                             ('submitted_to_bank', 'Submitted to Bank') ], string='Status',track_visibility='onchange', default='draft')

    transaction_type = fields.Selection([
                                    ('R', 'RTGS'),
                                    ('N', 'NEFT'),
                                    ('I', 'Funds Transfer'),
                                    ('D', 'Demand Draft')], 
                                    string='Transaction Type',track_visibility='onchange')


    requester = fields.Char('Requester')
    payment_lines_one2many = fields.One2many('bank.payment.lines','payment_id',string="Payments Details")
    invoice_icici_lines_one2many = fields.One2many('bank.invoice.lines','invoice_icici_id',string="Invoice Details" )
    date = fields.Date(string="Date", default=lambda self: fields.Datetime.now())
    employee_id = fields.Many2one('hr.employee', string="Employee")
    completed = fields.Boolean("Completed")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    c_bpartner_id = fields.Char("Partner ID",default='Standard')
    ad_client_id = fields.Char('Client ID')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    output_file = fields.Binary('Prepared file', filters='.xls', attachment=True)
    export_file = fields.Char(string="Export")
    delegate_user_id = fields.Many2many('res.users',  string='Delegate To')


    @api.multi
    def name_creation(self):
        daymonth = datetime.strptime(self.date, "%Y-%m-%d")
        month2 = daymonth.strftime("%b")
        day = daymonth.strftime("%d")
        week_day = daymonth.strftime("%A")
        year = daymonth.strftime("%Y")
        self.name = 'Bank Statement for ' + str(day) + ' ' + str(month2) + ' ' + str(week_day) + ' ' + str(year)



# API/VPF1819/200155

    @api.multi
    def sync_invoices(self):
        conn_pg = None
        
        print "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii", self.config_id


        if not self.config_id:
            print " No Records Found   iiiiiiiiiiiiiiiiiiiiiiiiiii"
            raise UserError(" DB Connection not set / Disconnected " )

        else:
            self.state='generated_invoice'
            self.name_creation()
            ad_client_id=self.company_id.ad_client_id
            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, password=self.config_id.password, host= self.config_id.ip_address)
                pg_cursor = conn_pg.cursor()

                if self.company_id:

                    # pg_cursor.execute("select C_Invoice_ID,dateacct, \
                    #     (select c_bpartner.name from c_bpartner where c_bpartner.c_bpartner_id = cb.c_bpartner_id ),\
                    #     documentno, totallines, grandtotal, docstatus , posted    ,\
                    #  processed from C_Invoice cb where C_Invoice_ID=%s and documentno=%s",(idempiere_id,documentno))


                    pg_cursor.execute("select ci.C_Invoice_ID,\
                        ci.documentno, ci.dateacct, ci.grandtotal, cb.name, ci.description, \
                        (select A_Name  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) ,\
                        (select A_Ident_SSN  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) ,\
                        (select name from AD_User au where au.AD_User_ID = cb.SalesRep_ID ),\
                        (select EMail from C_BPartner_Location cbl where cbl.C_BPartner_ID = cb.C_BPartner_ID ),\
                        (select NetDays from C_PaymentTerm cpt where cpt.C_PaymentTerm_id = ci.C_PaymentTerm_ID),\
                        (select EMail from AD_User au where au.AD_User_ID = cb.SalesRep_ID )\
                    from C_Invoice ci \
                    JOIN C_BPartner cb ON cb.C_BPartner_ID = ci.C_BPartner_ID\
                    left outer  JOIN C_AllocationLine alln ON alln.C_Invoice_ID = ci.C_Invoice_ID\
                    WHERE  \
                        (now()::date - ci.dateacct::date  ) >=  (select NetDays from C_PaymentTerm cpt where cpt.C_PaymentTerm_id = ci.C_PaymentTerm_ID) and \
                        ci.ISSOTRX = 'N' and \
                        ci.ad_client_id = %s and  \
                        not  COALESCE(alln.C_Invoice_ID::text, '') <> '' and \
                        ci.docstatus not in ('RE','VO') and \
                        ci.ispaid = 'N'  and ci.C_PaymentTerm_id != 1000000 "  ,[ad_client_id])
                        # and ci.C_PaymentTerm_id != 1000000
                


                entry_id = pg_cursor.fetchall()

                if entry_id == []:
                    print " No Records Found   iiiiiiiiiiiiiiiiiiiiiiiiiii"
                    raise UserError(" No Records Found " )

                for record in entry_id:
                    user_ids = self.env['res.users'].sudo().search([("login","=",record[11])])
                    print "LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL" , user_ids , self.env.user.id
                    vals_line = {
                            'invoice_id':self.id,
                            'documentno':record[1],
                            'value_date':record[2],
                            'transaction_amount':record[3],
                            'beneficiary_name':record[4],
                            'description':record[5],
                            'beneficiary_account_number':record[6],
                            'ifsc_code':record[7],
                            'owner':record[8],
                            'beneficiary_email_id':record[9],
                            'payment_term':record[10],
                            'owner_email':record[11],
                            'transaction_type':self.transaction_type,
                            'user_id':user_ids.id,
                            
                        }
                    create_ids = self.env['bank.invoice.lines'].create(vals_line)
                    
                    # write_line={
                    # 'create_uid':self.env.user.id,
                    # }
                    # write_ids = create_ids.sudo().write(write_line)
                    # print "5555555555555555555555555555555555555555555" , create_ids , write_ids

                    
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
    def sync_payments(self):
        conn_pg = None
        

        if not self.config_id:
            print " No Records Found   iiiiiiiiiiiiiiiiiiiiiiiiiii"
            raise UserError(" DB Connection not set / Disconnected " )

        else:
            self.state='generated_payment'
            self.name_creation()
            ad_client_id=self.company_id.ad_client_id
            # documentno=self.documentnox
            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, password=self.config_id.password, host= self.config_id.ip_address)
                pg_cursor = conn_pg.cursor()

                if self.company_id:

                    # pg_cursor.execute("select C_Invoice_ID,dateacct, \
                    #     (select c_bpartner.name from c_bpartner where c_bpartner.c_bpartner_id = cb.c_bpartner_id ),\
                    #     documentno, totallines, grandtotal, docstatus , posted    ,\
                    #  processed from C_Invoice cb where C_Invoice_ID=%s and documentno=%s",(idempiere_id,documentno))


                    # pg_cursor.execute("select \
                    #     cp.c_payment_ID, \
                    #     cp.documentno, \
                    #     cp.dateacct, \
                    #     cp.payamt, \
                    #     cb.name, \
                    #     cp.description, \
                    #     (select a_name  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                    #     (select a_email  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                    #     (select x_ifc_code  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                    #     (select x_drawee_location  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                    #     (select X_BeneBankBranchName  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                    #     (select accountno  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                    #     (select name from AD_User au where au.AD_User_ID = cb.SalesRep_ID ),\
                    #     (select EMail from C_BPartner_Location cbl where cbl.C_BPartner_ID = cb.C_BPartner_ID ), \
                    #     (select EMail from AD_User au where au.AD_User_ID = cb.SalesRep_ID )\
                    # from c_payment cp \
                    # JOIN C_BPartner cb ON cb.C_BPartner_ID = cp.C_BPartner_ID \
                    # WHERE \
                    #     cp.docstatus not in ('RE','VO') and \
                    #     ( cp.dateacct::date = %s::date  ) and \
                    #     cp.isreceipt = 'N'  and \
                    #     cp.ad_client_id = %s"  ,(self.date,ad_client_id))


                    pg_cursor.execute("select \
                        cp.c_payment_ID, \
                        cp.documentno, \
                        cp.dateacct, \
                        cp.payamt, \
                        cb.name, \
                        cp.description, \
                        (select a_name  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select a_email  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select x_ifc_code  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select x_drawee_location  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select X_BeneBankBranchName  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select accountno  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select name from AD_User au where au.AD_User_ID = cb.SalesRep_ID ),\
                        (select EMail from C_BPartner_Location cbl where cbl.C_BPartner_ID = cb.C_BPartner_ID ), \
                        (select EMail from AD_User au where au.AD_User_ID = cb.SalesRep_ID )\
                    from c_payment cp \
                    JOIN C_BPartner cb ON cb.C_BPartner_ID = cp.C_BPartner_ID \
                    WHERE \
                        cp.docstatus in ('DR') and \
                        ( cp.dateacct::date = %s::date  ) and \
                        cp.isreceipt = 'N'  and \
                        cp.ad_client_id = %s"  ,(self.date,ad_client_id))
                            # and ci.C_PaymentTerm_id != 1000000
                


                entry_id = pg_cursor.fetchall()

                if entry_id == []:
                    print " No Records Found   iiiiiiiiiiiiiiiiiiiiiiiiiii"
                    raise UserError(" No Records Found " )

                print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , entry_id
                # print eerroror

                for record in entry_id:
                    user_ids = self.env['res.users'].search([("login","=",record[10])])
                    if float(record[3]) > 2500000:
                        transaction_type = 'R'
                    else:
                        transaction_type = 'N'
                    vals_line = {
                            'payment_id':self.id,
                            'documentno':record[1],
                            'owner':record[8],
                            'owner_email':record[10],
                            'transaction_type':transaction_type,
                            'user_id':user_ids.id,
                            'beneficiary_account_number':record[11],
                            'transaction_amount':record[3],
                            'beneficiary_name':record[6] if record[6] else record[4],
                            'description':record[5],
                            'value_date':record[2],
                            'ifsc_code':record[8],
                            'bank_name':record[10],
                            'beneficiary_email_id':record[7] if record[7] else record[13],
                            
                        }
                    self.env['bank.payment.icici.lines'].sudo().create(vals_line)


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
    def submit_manager(self):
        if self.date:
            self.state='submitted_to_manager'
            for records in self.invoice_lines_one2many:
                records.submit_manager_line()

        return True

    @api.multi
    def delegate_user(self):
        if self.delegate_user_id:
            
            for res in self.delegate_user_id:
                for rec in self.invoice_lines_one2many:
                    if rec.user_id.id == self.env.user.id:
                        rec.delegate_user_id = self.delegate_user_id

        self.delegate_user_id = ''

        return True
                       

    @api.multi
    def update_to_bank(self):

        if self.date:
            self.state='submitted_to_bank'

            item_list = []
            today = datetime.now()

            daymonth = datetime.strptime(self.date, "%Y-%m-%d")
            month = daymonth.strftime("%m")
            day = daymonth.strftime("%d")
            year = daymonth.strftime("%Y")
            pay_date = datetime.strptime(self.date, "%Y-%m-%d").strftime("%d/%m/%Y")

            file_extension =  self.env['bank.payment.icici'].search([("date","=",self.date)])
            ext = str(len(file_extension)+1).zfill(3)

            for rec in self.payment_lines_one2many:
                if rec.transaction_amount > 2500000:
                    transaction_type = 'R'
                else:
                    transaction_type = 'N'
                item_list.append([transaction_type , 
                    rec.beneficiary_code if rec.beneficiary_code else ext, 
                    rec.beneficiary_account_number if rec.beneficiary_account_number else '', 
                    rec.transaction_amount  if rec.transaction_amount else '', 
                    rec.beneficiary_name if rec.beneficiary_name else '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    rec.description if rec.description else '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    '',
                    pay_date ,
                    '',
                    rec.ifsc_code  if rec.ifsc_code else '', 
                    rec.bank_name  if rec.bank_name else '',
                    '',
                    rec.beneficiary_email_id  if rec.beneficiary_email_id else '',
                    ])


            fileName="/tmp/WALPLAST_W020_W020"+str(day)+str(month)+"." + str(ext)
            realfilename = "/WALPLAST_W020_W020"+str(day)+str(month)+"." + str(ext)

            with open(fileName, 'wb') as f:

                writer = csv.writer(f, delimiter=',')
                # writer.writerow(['Transaction Type','Beneficiary Code','Beneficiary Account Number','Transaction Amount',
                #         'Beneficiary Name','Customer Reference Number','Value Date ','IFSC Code','Beneficiary Email Id'])
                for val in item_list:
                    writer.writerow(val)


            mount = os.path.isdir("/media/BACKUP/notmounted")
            print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , mount

            destination = '/media/BACKUP/'


            # p = Popen(['cp','-p','--preserve',fileName,destination])
            # p.wait()

            # shutil.copy(fileName, destination+realfilename)
            # shutil.copyfile(fileName, '/media/BACKUP/', *, follow_symlinks=True)
            if mount == True:
                os.system('sudo mount -t cifs -o username=bankuser,password=Bank@2004 //192.168.40.7/users/Public/BankPayments/tobank /media/BACKUP/' )

            os.system('sudo cp ' + fileName +  ' /media/BACKUP/ ' )

            print "DDDDDDDDDDDDDDDDDDDoooooooooooooooooooooneeeeeeeeeeeeeeeeee"

