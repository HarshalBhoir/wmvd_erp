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
from odoo import http

from collections import Counter

import requests

# idempiere_url="http://35.200.227.4/ADInterface/services/compositeInterface"
idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"

headers = {'content-type': 'text/xml'}


header_fields = ['ReversalDate',
                'AD_Org_ID[Name]',
                'C_BankAccount_ID[Value]',
                'C_DocType_ID[Name]',
                'IsReceipt',
                'DateTrx',
                'DateAcct',
                'Description',
                'C_BPartner_ID[Value]',
                'PayAmt',
                'C_Currency_ID',
                'C_ConversionType_ID[Value]',
                'DiscountAmt',
                'WriteOffAmt',
                'IsOverUnderPayment',
                'OverUnderAmt',
                'TenderType',
                'IsOnline',
                'CreditCardType',
                'TrxType',
                'CreditCardExpMM',
                'CreditCardExpYY',
                'TaxAmt',
                'IsVoided',
                'C_PaymentAllocate>AD_Org_ID[Name]',
                'C_PaymentAllocate>C_Payment_ID[DocumentNo]',
                'C_PaymentAllocate>IsActive',
                'C_PaymentAllocate>C_Invoice_ID[DocumentNo]',
                'C_PaymentAllocate>Amount',
                'C_PaymentAllocate>DiscountAmt',
                'C_PaymentAllocate>WriteOffAmt',
                'C_PaymentAllocate>OverUnderAmt'
                ]

header_fields2 = [
                'AD_Org_ID[Name]',
                'C_BankAccount_ID[Value]',
                'DocumentNo',
                'IsReceipt',
                'C_DocType_ID[Name]',
                'DateTrx',
                'C_BPartner_ID[Value]',
                'InvoiceDocumentNo',
                'C_Invoice_ID[DocumentNo]',
                'C_Currency_ID',
                'PayAmt',
                'DiscountAmt',
                'WriteOffAmt',
                'IsOverUnderPayment',
                'OverUnderAmt',
                'TenderType',
                'TrxType',
                'CreditCardExpMM',
                'CreditCardExpYY',
                'RoutingNo',
                'IsApproved'
                ]


class bank_payment(models.Model):
    _name = "bank.payment"
    _description=" Payment to Bank"
    _inherit = 'mail.thread'
    _order    = 'id desc'

    def _get_csv_url(self):
        self.csv_url = "/csv/download/{}/".format(self.id)


    @api.multi
    def _compute_can_edit_name(self):
        print "1111111111111111111111111111111111111111 _compute_can_edit_name"
        self.can_edit_name = self.env.user.has_group('sales_meet.group_sales_meet_hidden')


    @api.multi
    def _get_config(self):
        config = self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1)
        if config:
            config_id = config.id
        else:
            config = self.env['external.db.configuration'].search([('id', '!=',0)], limit=1)
            config_id = config.id
        return config_id

#close

    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and self.env.uid != 1:
                raise UserError(_('You can only delete Draft Entries'))
        return super(bank_payment, self).unlink()


    @api.multi
    def _amount_calc(self,condition=False,amount=False):
        if condition == 'deduct':
            self.amount_total -= amount

        elif condition == 'add':
            self.amount_total += amount


    # portal_user = fields.Boolean("Portal User" , default=False)
    name = fields.Char('Name', store=True)
    db_name = fields.Char('DB Name')
    config_id = fields.Many2one('external.db.configuration', string='Database', track_visibility='onchange' , default=_get_config)
    note = fields.Text('Text', track_visibility='onchange')
    state = fields.Selection([('draft', 'Draft'),
                             ('generated_invoice', 'Invoice Generated'), 
                             ('generated_invoice_template', 'Template Generated'), 
                             ('erp_posted', 'Posted'), 
                             ('submitted_to_manager', 'Submitted to Manager'), 
                             ('generated_payment', 'Payment Generated'), 
                             ('submitted_to_bank', 'Submitted to Bank') 
                             ], string='Status',track_visibility='onchange', default='draft')

    transaction_type = fields.Selection([
                                    ('R', 'RTGS'),
                                    ('N', 'NEFT'),
                                    ('I', 'Funds Transfer'),
                                    ('D', 'Demand Draft')], 
                                    string='Transaction Type',track_visibility='onchange')


    requester = fields.Char('Requester')
    payment_lines_one2many = fields.One2many('bank.payment.lines','payment_id',string="Payments Details")
    invoice_lines_one2many = fields.One2many('bank.invoice.lines','invoice_id',string="Invoice Details" )
    invoice_selected_one2many = fields.One2many('bank.invoice.selected','invoice_selected_id',string="Selected Invoice" )
    invoice_filter_one2many = fields.One2many('bank.invoice.filter','invoice_filter_id',string="Selected Invoice" )
    
    
    date = fields.Date(string="Date", default=lambda self: fields.Datetime.now())
    employee_id = fields.Many2one('hr.employee', string="Employee")
    completed = fields.Boolean("Completed")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    # ad_org_id = fields.Many2one('org.master', string='Organisation' )
    ad_org_id = fields.Many2one('org.master', string='Organisation',  domain="[('company_id','=',company_id)]" )
    c_bpartner_id = fields.Char("Partner ID")
    ad_client_id = fields.Char('Client ID')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    
    delegate_user_id = fields.Many2many('res.users',  string='Delegate To')

    custgroup = fields.Char(string="Group")
    hr_payment_data = fields.Char('Rep Name')
    file_name = fields.Binary('Expense Report', readonly=True)

    output_file = fields.Binary('Prepared file', filters='.xls', attachment=True)
    export_file = fields.Char(string="Export")

    pmt_output_file = fields.Binary('Prepared file', filters='.xls', attachment=True)
    pmt_export_file = fields.Char(string="Export")
    

    partner_name = fields.Char('Partner')

    csv_url = fields.Char(compute=_get_csv_url)
    hr_payment_data2 = fields.Char('Rep Name2')
    file_name2 = fields.Binary('Due Invoices Report')
    inv_rep_bool = fields.Boolean('Inv Rep Generated' , default=False)
    condition = fields.Selection([
        ('invoice', 'Invoice'),
        ('payment', 'Payment')], string='Condition')
    erp_bank_id = fields.Many2one('erp.bank.master', string='Bank Account',  domain="[('company_id','=',company_id)]" )
    filter_rep_bool = fields.Boolean('Filter Rep Generated' , default=False)

    amount_total = fields.Float(string='Total', store=True)
    can_edit_name = fields.Boolean(compute='_compute_can_edit_name')


    @api.model
    def create(self, vals):
        result = super(bank_payment, self).create(vals)

        for res in result.invoice_filter_one2many:
            if res.unallocated > res.unallocated2:
                raise ValidationError(" Unallocated Amount cannot be greater in line %s " %(res.beneficiary_name) ) 
        
        return result


    @api.multi
    def write(self, vals):
        result = super(bank_payment, self).write(vals)

        for res in self.invoice_filter_one2many:
            if res.unallocated :
                if res.unallocated > res.unallocated2:
                    raise ValidationError(" Unallocated Amount cannot be greater" )

        return result


    @api.multi
    def select_all(self):
        filtered_lines = [x.documentno for x in self.invoice_filter_one2many]

        for res in self.invoice_selected_one2many:
            if res.documentno not in filtered_lines:

                vals_line = {
                        'invoice_filter_id':self.id,
                        'documentno':res.documentno,
                        'value_date':res.value_date,
                        'transaction_amount':res.transaction_amount,
                        'beneficiary_name':res.beneficiary_name,
                        'invoiceno' :res.invoiceno,
                        'totalamt' : abs(res.totalamt),
                        'allocatedamt' :abs(res.allocatedamt),
                        'unallocated' : abs(res.unallocated),
                        'unallocated2' : abs(res.unallocated),
                        'duedays' : res.duedays,
                        'customercode': res.customercode,
                        'ad_org': res.ad_org,
                        'selected_id': res.invoice_selected_id.id,
                        'c_bpartner_id': res.c_bpartner_id,
                        'ad_org_id': res.ad_org_id.id,
                        'c_invoice_id': res.c_invoice_id,
                    }
                self.invoice_filter_one2many.create(vals_line)

        self.invoice_selected_one2many.unlink()


    @api.multi
    def refresh_form(self):
        return True


    @api.multi
    def name_creation(self):
        name =''
        daymonth = datetime.strptime(self.date, "%Y-%m-%d")
        month2 = daymonth.strftime("%b")
        day = daymonth.strftime("%d")
        week_day = daymonth.strftime("%A")
        year = daymonth.strftime("%Y")
        self.name = name = 'Bank Statement for ' + str(day) + ' ' + str(month2) + ' ' + str(week_day) + ' ' + str(year)

        return name

    @api.multi
    def sync_selected_invoices(self):
        self.invoice_selected_one2many.unlink()

        if self.partner_name:
            for rec in self.invoice_selected_one2many:
                if self.partner_name == rec.beneficiary_name:
                    raise UserError(" Partner already selected" )
                else:
                    continue

            for res in self.invoice_lines_one2many:
                if self.partner_name == res.beneficiary_name:
                    vals_line = {
                            'invoice_selected_id':self.id,
                            'documentno':res.documentno,
                            'value_date':res.value_date,
                            'transaction_amount':res.transaction_amount,
                            'beneficiary_name':res.beneficiary_name,
                            'invoiceno' :res.invoiceno,
                            'totalamt' :res.totalamt,
                            'allocatedamt' :res.allocatedamt,
                            'unallocated' :res.unallocated,
                            'duedays' : res.duedays,
                            'customercode': res.customercode,
                            'ad_org': res.ad_org,
                            'c_bpartner_id': res.c_bpartner_id,
                            'c_invoice_id': res.c_invoice_id,
                            'ad_org_id': res.ad_org_id.id,

                        }
                    self.invoice_selected_one2many.create(vals_line)

        else:
            raise UserError(" Partner Not Selected" )

        self.partner_name = ''
        self.amount_total = 0.0



    @api.multi
    def sync_invoices(self):
        conn_pg = None
        
        # print "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii", self.config_id , self.partner_name


        if not self.config_id:
            print " No Records Found   iiiiiiiiiiiiiiiiiiiiiiiiiii"
            raise UserError(" DB Connection not set / Disconnected " )

        else:

            self.state='generated_invoice'
            self.name = 'Due Invoices' + '(' + str(date.today()) + ')'
            ad_client_id=self.company_id.ad_client_id
            print "#-------------Select --TRY----------------------#"
            try:

                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
                password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
                # dbname='idempiere51'
                # user='postgres'
                # password='YW4JGJ3nkqVDgTHR51'
                # host='35.200.135.16'
                # conn_pg = psycopg2.connect(dbname= dbname, user=user, 
                #     password=password, host= host, port=5433)
                pg_cursor = conn_pg.cursor()
                if self.company_id:

                    # pg_cursor.execute("select C_Invoice_ID,dateacct, \
                    #     (select c_bpartner.name from c_bpartner where c_bpartner.c_bpartner_id = cb.c_bpartner_id ),\
                    #     documentno, totallines, grandtotal, docstatus , posted    ,\
                    #  processed from C_Invoice cb where C_Invoice_ID=%s and documentno=%s",(idempiere_id,documentno))

                    # pg_cursor.execute("select ci.C_Invoice_ID,\
                    #     ci.documentno, ci.dateacct, ci.grandtotal, cb.name, ci.description, \
                    #     (select A_Name  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) ,\
                    #     (select A_Ident_SSN  from C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) ,\
                    #     (select name from AD_User au where au.AD_User_ID = cb.SalesRep_ID ),\
                    #     (select EMail from C_BPartner_Location cbl where cbl.C_BPartner_ID = cb.C_BPartner_ID ),\
                    #     (select NetDays from C_PaymentTerm cpt where cpt.C_PaymentTerm_id = ci.C_PaymentTerm_ID),\
                    #     (select EMail from AD_User au where au.AD_User_ID = cb.SalesRep_ID )\
                    # from C_Invoice ci \
                    # JOIN C_BPartner cb ON cb.C_BPartner_ID = ci.C_BPartner_ID\
                    # left outer  JOIN C_AllocationLine alln ON alln.C_Invoice_ID = ci.C_Invoice_ID\
                    # WHERE  \
                    #     (now()::date - ci.dateacct::date  ) >=  (select NetDays from C_PaymentTerm cpt where cpt.C_PaymentTerm_id = ci.C_PaymentTerm_ID) and \
                    #     ci.ISSOTRX = 'N' and \
                    #     ci.ad_client_id = %s and  \
                    #     not  COALESCE(alln.C_Invoice_ID::text, '') <> '' and \
                    #     ci.docstatus not in ('RE','VO') and \
                    #     ci.ispaid = 'N'  and ci.C_PaymentTerm_id != 1000000 "  ,[ad_client_id])
                        # and ci.C_PaymentTerm_id != 1000000

                    pg_cursor.execute("select \
    (Select Value from adempiere.AD_Client where AD_Client_ID=invc.AD_Client_ID) as Client, \
    (Select Name from adempiere.AD_Org where AD_Org_ID=invc.AD_Org_ID) as Org, \
    invc.documentno as entryno, \
    invc.dateacct as date, \
    invc.poreference as invno, \
    (select name from adempiere.c_doctype where c_doctype_id = invc.c_doctypetarget_id) as entrytype, \
    (select Name from adempiere.C_BP_Group where C_BP_Group_ID=(select C_BP_Group_ID from adempiere.C_BPartner where C_BPartner_ID=invc.C_BPartner_ID)) as CustGroup, \
    invc.c_bpartner_id as CustomerID, \
    (select name from adempiere.c_bpartner where c_bpartner_id=invc.c_bpartner_id) as CustomerName, \
    (select value from adempiere.c_bpartner where c_bpartner_id=invc.c_bpartner_id) as CustomerCode, \
    invc.grandtotal * -1 as totalamt, \
    (select Sum(ABS(Amount)) from adempiere.C_AllocationLine WHERE Invc.C_Invoice_ID=C_AllocationLine.C_Invoice_ID) As AllocatedAmt, \
    (Sum(Invc.GrandTotal) - COALESCE( (Select Sum(ABS(Amount)) from adempiere.C_AllocationLine WHERE Invc.C_Invoice_ID=C_AllocationLine.C_Invoice_ID),0))* -1 AS UnAllocated, \
    (Select (Date_PART('day',  Now() - invc.DateAcct)))  As DueDays, \
    Invc.C_Invoice_ID \
    from adempiere.c_invoice invc \
    where (select DocBaseType from adempiere.C_DocType where c_doctype_id = invc.c_doctype_id) in ('API','APC') \
    and invc.docstatus in ('CL', 'CO') \
    and (select IsCustomer from adempiere.c_bpartner where invc.c_bpartner_ID=C_BPartner_ID ) = 'N' \
    and invc.ad_client_id= %s \
    and invc.dateacct >= '2018-04-01 00:00:00' \
    and (select C_BP_Group_ID from adempiere.C_BP_Group where C_BP_Group_ID=(select C_BP_Group_ID from adempiere.C_BPartner where C_BPartner_ID=invc.C_BPartner_ID)) not in  (1000024,1000021) \
    group by invc.AD_Client_ID,invc.AD_Org_ID,invc.documentno,invc.dateacct,invc.poreference,invc.c_doctypetarget_id,invc.C_BPartner_ID,invc.grandtotal,Invc.C_Invoice_ID \
    HAVING \
    Sum(invc.GrandTotal - COALESCE( (Select Sum(ABS(Amount)) from adempiere.C_AllocationLine WHERE invc.C_Invoice_ID=C_AllocationLine.C_Invoice_ID),0)) > 1 \
    order by invc.dateacct asc" ,[ad_client_id])


                # print "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh" , record[2], type(record[2])
                entry_id = pg_cursor.fetchall()

                if entry_id == []:
                    raise UserError(" No Records Found " )

                for record in entry_id:
                    user_ids = self.env['res.users'].sudo().search([("login","=",record[11])])
                    vals_line = {
                            'invoice_id':self.id,
                            'documentno':record[2],
                            'value_date':record[3],
                            'transaction_amount':record[10],
                            'beneficiary_name':record[8],
                            'invoiceno' :record[4],
                            'totalamt' :record[10],
                            'allocatedamt' :record[11],
                            'unallocated' :record[12],
                            'duedays' :record[13],
                            'customercode':record[9],
                            'ad_org':record[1],
                            'c_bpartner_id': record[7],
                            'c_invoice_id': record[14],
                            'ad_org_id':self.ad_org_id.id,

                            
                        }
                    create_ids = self.env['bank.invoice.lines'].create(vals_line)


            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    conn_pg.rollback()
         
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#"
                    conn_pg.close()


                    

    @api.multi
    def generate_filter_invoice_report(self):

        file = StringIO()
        
        self.ensure_one()
        status = payment_no = ''
        name = 'Filtered Invoices' + '(' + str(date.today()) + ')'

        order_list = []
        second_heading = approval_status = ''
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Filtered INVOICE')
        fp = StringIO()
        row_index = 0

        main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
        sp_style = xlwt.easyxf('font: bold on, height 350;')
        header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
        base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
        base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
        base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')

        worksheet.col(0).width = 2000
        worksheet.col(1).width = 6000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 6000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 3000
        worksheet.col(6).width = 12000
        worksheet.col(7).width = 3000
        worksheet.col(8).width = 5000
        worksheet.col(9).width = 5000
        worksheet.col(10).width = 3000


        header_fields = [
                'Sr No.',
                'Client',
                'Org',
                'Date Account',
                'DocumentNo',
                'Code',
                'Beneficiary',
                'Total',
                'Allocated Amt',
                'Unallocated Amt',
                'Due Days',
                ]


     
        for index, value in enumerate(header_fields):
            worksheet.write(row_index, index, value, header_style)
        row_index += 1

        count = 0

        invoice_filter = self.invoice_filter_one2many

        if  len(invoice_filter) < 1:
            raise ValidationError(_('No Records Selected'))

        for res in invoice_filter:
            if res :
                count +=1

                worksheet.write(row_index, 0,count, base_style )
                worksheet.write(row_index, 1,self.company_id.name, base_style )
                worksheet.write(row_index, 2,res.ad_org, base_style )
                worksheet.write(row_index, 3, res.value_date , base_style )
                worksheet.write(row_index, 4,res.documentno, base_style )
                worksheet.write(row_index, 5, res.customercode, base_style )
                worksheet.write(row_index, 6, res.beneficiary_name, base_style )
                worksheet.write(row_index, 7, str(abs(res.totalamt)), base_style )
                worksheet.write(row_index, 8, str(abs(res.allocatedamt)), base_style )
                worksheet.write(row_index, 9, str(abs(res.unallocated)), base_style )
                worksheet.write(row_index, 10, res.duedays, base_style )

                row_index += 1


        row_index +=1
        workbook.save(fp)


        out = base64.encodestring(fp.getvalue())

        self.write({'output_file': out,'export_file':name+'.xls'})

        if self.state != 'erp_posted':
            self.state = 'generated_invoice_template'

        self.filter_rep_bool = True


    @api.multi
    def generate_invoice_report(self):

        file = StringIO()
        
        self.ensure_one()
        status = payment_no = ''
        self.name = 'Due Invoices' + '(' + str(date.today()) + ')'

        order_list = []
        second_heading = approval_status = ''
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('DUE INVOICE')
        fp = StringIO()
        row_index = 0

        main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
        sp_style = xlwt.easyxf('font: bold on, height 350;')
        header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
        base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
        base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
        base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')

        worksheet.col(0).width = 2000
        worksheet.col(1).width = 6000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 6000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 3000
        worksheet.col(6).width = 12000
        worksheet.col(7).width = 3000
        worksheet.col(8).width = 5000
        worksheet.col(9).width = 5000
        worksheet.col(10).width = 3000


        header_fields = [
                'Sr No.',
                'Client',
                'Org',
                'Date Account',
                'DocumentNo',
                'Code',
                'Beneficiary',
                'Total',
                'Allocated Amt',
                'Unallocated Amt',
                'Due Days',
                ]
     
        for index, value in enumerate(header_fields):
            worksheet.write(row_index, index, value, header_style)
        row_index += 1

        count = 0

        for res in self.invoice_lines_one2many:
            if res :
                count +=1

                worksheet.write(row_index, 0,count, base_style )
                worksheet.write(row_index, 1,self.company_id.name, base_style )
                worksheet.write(row_index, 2,res.ad_org, base_style )
                worksheet.write(row_index, 3, res.value_date , base_style )
                worksheet.write(row_index, 4,res.documentno, base_style )
                worksheet.write(row_index, 5, res.customercode, base_style )
                worksheet.write(row_index, 6, res.beneficiary_name, base_style )
                worksheet.write(row_index, 7, str(abs(res.totalamt)), base_style )
                worksheet.write(row_index, 8, str(abs(res.allocatedamt)), base_style )
                worksheet.write(row_index, 9, str(abs(res.unallocated)), base_style )
                worksheet.write(row_index, 10, res.duedays, base_style )

                row_index += 1


        row_index +=1
        workbook.save(fp)


        out = base64.encodestring(fp.getvalue())

        self.write({'file_name2': out,'hr_payment_data2':self.name+'.xls'})
        self.inv_rep_bool = True



    @api.multi
    def generate_payment_report(self):

        filtered_list = []
        filter_dict = {}
        total_amount = 0
        vals = []
        documentno = status = payment_no = ''

        file = StringIO()
        self.ensure_one()

        order_list = []
        second_heading = approval_status = ''
        # file_name = self.name + '.xls'
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Expense Report')
        fp = StringIO()
        row_index = 0

        main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
        sp_style = xlwt.easyxf('font: bold on, height 350;')
        header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
        base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
        base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
        base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')

        worksheet.col(0).width = 6000
        worksheet.col(1).width = 12000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 12000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 12000
        worksheet.col(6).width = 6000
        worksheet.col(7).width = 6000
        worksheet.col(8).width = 6000
        worksheet.col(9).width = 6000
        worksheet.col(10).width = 6000
        worksheet.col(11).width = 6000
        worksheet.col(12).width = 6000
        worksheet.col(13).width = 6001
        worksheet.col(14).width = 6002
        worksheet.col(15).width = 6003
        worksheet.col(16).width = 6004
        worksheet.col(17).width = 6005
        worksheet.col(18).width = 6006
        worksheet.col(19).width = 6007
        worksheet.col(20).width = 6008
     
        for index, value in enumerate(header_fields2):
            worksheet.write(row_index, index, value, base_style)
        row_index += 1


        for rec in self.invoice_filter_one2many:
            # filtered_list.append((rec.beneficiary_name,(rec.id, rec.unallocated)))
            filtered_list.append(rec.beneficiary_name)
        
        filtered_list3 = dict(Counter(filtered_list))
        
        org_id = self.ad_org_id

        daymonth = datetime.strptime(self.date, "%Y-%m-%d")
        month = daymonth.strftime("%m")
        year = daymonth.strftime("%y")

        if month <= 3:
            pre_year = int(year) - 1
            pre_year_1 = year
        elif month > 3:
            pre_year = year
            pre_year_1 = int(year) + 1


        for beneficiary_name, value in filtered_list3.iteritems():
       
            for record in self.invoice_filter_one2many:
                if beneficiary_name == record.beneficiary_name:
                    if value > 1:
                        total_amount += record.unallocated
                        documentno = ''
                    else:
                        total_amount = record.unallocated
                        documentno = record.documentno

                    ad_org = record.ad_org
                    date_filter = record.invoice_filter_id.date
                    customercode = record.customercode

            new_list = (ad_org, customercode , documentno, abs(total_amount))

            vals.append(new_list)

        for res in vals:
            
            seq = self.env['ir.sequence'].sudo().next_by_code('bank.invoice.lines') or '/'
            payment_no = 'PMT/' + str(org_id.value)+'/' + str(pre_year)+ str(pre_year_1) + '/' + str(org_id.prefix) + str(seq)

            worksheet.write(row_index,0, org_id.name, base_style )
            worksheet.write(row_index,1,'HDFC Turbhe', base_style )
            worksheet.write(row_index,2, payment_no, base_style )
            worksheet.write(row_index,3,'N', base_style )
            worksheet.write(row_index,4,'AP Payment', base_style )
            worksheet.write(row_index,5, self.date, base_style )
            worksheet.write(row_index,6, res[1], base_style )
            worksheet.write(row_index,7,'', base_style )
            worksheet.write(row_index,8, res[2], base_style )
            worksheet.write(row_index,9,304, base_style )
            worksheet.write(row_index,10, res[3], base_style )
            worksheet.write(row_index,11,0, base_style )
            worksheet.write(row_index,12,0, base_style )
            worksheet.write(row_index,13,'N', base_style )
            worksheet.write(row_index,14,0, base_style )
            worksheet.write(row_index,15,'K', base_style )
            worksheet.write(row_index,16,'S', base_style )
            worksheet.write(row_index,17,0, base_style )
            worksheet.write(row_index,18,0, base_style )
            worksheet.write(row_index,19,'', base_style )
            worksheet.write(row_index,20,'N', base_style )
       
            row_index += 1


        row_index +=1
        workbook.save(fp)


        out = base64.encodestring(fp.getvalue())

        self.write({'file_name': out,'hr_payment_data':str(self.name_creation())+'.xls'})
        self.state = 'generated_invoice_template'

    @api.multi
    def generate_payment_webservice(self):
        filtered_list = []
        filter_dict = {}
        
        vals = []
        documentno = ''

        invoice_filter = self.invoice_filter_one2many.search([("invoice_filter_id","=",self.id)])

        if  len(invoice_filter) < 1:
            raise ValidationError(_('No Records Selected'))

        user_ids = self.env['wp.erp.credentials'].search([("wp_user_id","=",self.env.uid),("company_id","=",self.company_id.id)])

        if len(user_ids) < 1:
            raise ValidationError(_("User's ERP Credentials not found. Kindly Contact IT Helpdesk"))

        # user_ids = self.env['res.users'].search([("id","=",self.env.uid)])

        for rec in self.invoice_filter_one2many:
            # filtered_list.append((rec.beneficiary_name,(rec.id, rec.unallocated)))
            filtered_list.append(rec.beneficiary_name)
        
        filtered_list3 = dict(Counter(filtered_list))
        
        org_id = self.ad_org_id

        for beneficiary_name, value in filtered_list3.iteritems():
            total_amount = 0
            payment_description = ''
       
            for record in self.invoice_filter_one2many:
                if beneficiary_name == record.beneficiary_name:
                    if value > 1:
                        total_amount += record.unallocated
                        documentno = ''
                        payment_description += record.invoiceno + ', '
                        # payment_description += record.documentno + ', '

                    else:
                        total_amount = record.unallocated
                        documentno = record.documentno
                        payment_description = record.invoiceno
                        # payment_description = record.documentno


                    ad_org = record.ad_org_id.ad_org_id
                    date_filter = record.invoice_filter_id.date
                    customercode = record.customercode
                    c_bpartner_id = (str(record.c_bpartner_id).split('.'))[0]
                    filter_id = record.id

            new_list = (ad_org, customercode , documentno, abs(total_amount), c_bpartner_id, filter_id, payment_description)

            vals.append(new_list)

        for res in vals:
            line_body = """ """
            body = """ """
            upper_body  = """ """
            payment_body = """ """
            lower_body = """ """
            documentno_log = ''

            daymonth = datetime.today().strftime( "%Y-%m-%d 00:00:00")


            C_BankAccount_ID = self.erp_bank_id.c_bankaccount_id

            paymt_description = "Payment Against - " + res[6] if res[6] else ''


            print "hhhhhhhhhhhhhhhhhhhh" , paymt_description

            if self.company_id.ad_client_id == '1000000':
                C_DocType_ID = 1000009
            elif self.company_id.ad_client_id == '1000001':
                C_DocType_ID = 1000056
            elif self.company_id.ad_client_id == '1000002':
                C_DocType_ID = 1000103
            elif self.company_id.ad_client_id == '1000003':
                C_DocType_ID = 1000150
            else:
                raise UserError(" Select proper company " )
   
            
            upper_body = """<?xml version="1.0" encoding="UTF-8"?>
                 <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:_0="http://idempiere.org/ADInterface/1_0">
                   <soapenv:Header/>
                   <soapenv:Body>
                      <_0:compositeOperation>
                         <!--Optional:-->
                         <_0:CompositeRequest>
                            <_0:ADLoginRequest>
                               <_0:user>%s</_0:user>
                               <_0:pass>%s</_0:pass>
                               <_0:ClientID>%s</_0:ClientID>
                               <_0:RoleID>%s</_0:RoleID>
                               <_0:OrgID>0</_0:OrgID>
                               <_0:WarehouseID>0</_0:WarehouseID>
                               <_0:stage>0</_0:stage>
                            </_0:ADLoginRequest>
                            <_0:serviceType>CreateCompletePayment</_0:serviceType>
                            """ % (user_ids.erp_user, user_ids.erp_pass, self.company_id.ad_client_id, user_ids.erp_roleid )


            payment_body = """<_0:operations>
                               <_0:operation preCommit="false" postCommit="false">
                                  <_0:TargetPort>createData</_0:TargetPort>
                                  <_0:ModelCRUD>
                                     <_0:serviceType>CreatePayment</_0:serviceType>
                                     <_0:TableName>C_Payment</_0:TableName>
                                     <_0:DataRow>
                                        <!--Zero or more repetitions:-->
                                        <_0:field column="AD_Org_ID">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="C_BankAccount_ID">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="C_DocType_ID">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="DateTrx">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="DateAcct">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="C_Invoice_ID">
                                           <_0:val/>
                                        </_0:field>
                                        <_0:field column="C_BPartner_ID">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="PayAmt">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="Description">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="ByWebservice">
                                           <_0:val>Y</_0:val>
                                        </_0:field>
                                        <_0:field column="C_Currency_ID">
                                           <_0:val>304</_0:val>
                                        </_0:field>
                                     </_0:DataRow>
                                  </_0:ModelCRUD>
                               </_0:operation>"""  % ( self.ad_org_id.ad_org_id ,C_BankAccount_ID, C_DocType_ID, daymonth, daymonth, res[4], res[3], paymt_description)


            for line_rec in invoice_filter:
                if line_rec.customercode == res[1]:

                    line_body += """<_0:operation preCommit="false" postCommit="false">
                                  <_0:TargetPort>createData</_0:TargetPort>
                                  <_0:ModelCRUD>
                                     <_0:serviceType>PaymentAllocationLines</_0:serviceType>
                                     <_0:TableName>C_PaymentAllocate</_0:TableName>
                                     <RecordID>0</RecordID>
                                     <Action>createData</Action>
                                     <_0:DataRow>
                                        <!--Zero or more repetitions:-->
                                        <_0:field column="AD_Org_ID">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="C_Invoice_ID">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="Amount">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="InvoiceAmt">
                                           <_0:val>%s</_0:val>
                                        </_0:field>
                                        <_0:field column="C_Charge_ID">
                                            <_0:val/>
                                           
                                        </_0:field>
                                         <_0:field column="C_Payment_ID">
                                           <_0:val>@C_Payment.C_Payment_ID</_0:val>
                                        </_0:field>
                                       <!-- <field column="C_Payment_ID">
                                           <val>@C_Payment.C_Payment_ID</val>
                                        </field> -->
                                     </_0:DataRow>
                                  </_0:ModelCRUD>
                               </_0:operation>"""  % ( self.ad_org_id.ad_org_id, (str(line_rec.c_invoice_id).split('.'))[0] , abs(line_rec.unallocated), abs(line_rec.unallocated) )


            lower_body = """<_0:operation preCommit="true" postCommit="true">
                                  <_0:TargetPort>setDocAction</_0:TargetPort>
                                  <_0:ModelSetDocAction>
                                     <_0:serviceType>CompletePayment</_0:serviceType>
                                     <_0:tableName>C_Payment</_0:tableName>
                                     <_0:recordID>0</_0:recordID>
                                     <!--Optional:-->
                                     <_0:recordIDVariable>@C_Payment.C_Payment_ID</_0:recordIDVariable>
                                     <_0:docAction>CO</_0:docAction>
                                  </_0:ModelSetDocAction>
                                  <!--Optional:-->
                               </_0:operation>
                            </_0:operations>
                         </_0:CompositeRequest>
                      </_0:compositeOperation>
                   </soapenv:Body>
                </soapenv:Envelope>"""

# <_0:val>1001816</_0:val>

            body = upper_body + payment_body + line_body + lower_body

            # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , body

            response = requests.post(idempiere_url,data=body,headers=headers)
            print response.content , type(response.content)
            
            log = str(response.content)
            if log.find('DocumentNo') is not -1:
                self.state = 'erp_posted'
                documentno_log = log.split('column="DocumentNo" value="')[1].split('"></outputField>')[0]
                print "ssssssssssssssssssssssssss" , documentno_log , self.state
                

            if log.find('IsRolledBack') is not -1:
                # documentno_log = 'error'
                documentno_log = log.split('<Error>')[1].split('</Error>')[0]
                raise ValidationError("Error Occured %s" % (documentno_log))


            if log.find('Invalid') is not -1:
                documentno_log = log.split('<faultstring>')[1].split('</faultstring>')[0]
                raise ValidationError("Error Occured %s" % (documentno_log))


            write_data = self.invoice_filter_one2many.search([('id', '=', res[5])]).write(
            {'log': documentno_log,'state': 'approved'})

            self.invoice_lines_one2many.unlink()


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
                        (select a_name  from adempiere.C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select a_email  from adempiere.C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select x_ifc_code  from adempiere.C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select x_drawee_location  from adempiere.C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select X_BeneBankBranchName  from adempiere.C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select accountno  from adempiere.C_BP_BankAccount cba where cba.C_BPartner_ID = cb.C_BPartner_ID ) , \
                        (select name from adempiere.AD_User au where au.AD_User_ID = cb.SalesRep_ID ),\
                        (select EMail from adempiere.C_BPartner_Location cbl where cbl.C_BPartner_ID = cb.C_BPartner_ID ), \
                        (select EMail from adempiere.AD_User au where au.AD_User_ID = cb.SalesRep_ID ), \
                        (Select Name from adempiere.AD_Org where AD_Org_ID=cp.AD_Org_ID) as Org, \
                        cb.value \
                    from adempiere.c_payment cp \
                    JOIN adempiere.C_BPartner cb ON cb.C_BPartner_ID = cp.C_BPartner_ID \
                    WHERE \
                        cp.docstatus in ('CO') and \
                        ( cp.dateacct::date = %s::date  ) and \
                        cp.isreceipt = 'N'  and \
                        cp.ad_client_id = %s"  ,(self.date,ad_client_id))
                            # and ci.C_PaymentTerm_id != 1000000
                


                entry_id = pg_cursor.fetchall()

                if entry_id == []:
                    print " No Records Found   iiiiiiiiiiiiiiiiiiiiiiiiiii"
                    raise UserError(" No Records Found " )


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
                            'ad_org':record[15],
                            'customer_reference_number' : record[16]
                            
                        }
                    self.env['bank.payment.lines'].sudo().create(vals_line)


            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#" ,  'Error %s' % e 
                    conn_pg.rollback()
         
                print 'Error %s' % e        
                # sys.exit(1)

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#"
                    conn_pg.close()



    @api.multi
    def payment_report(self):

        file = StringIO()
        
        self.ensure_one()
        status = payment_no = ''
        name = 'Filtered Payments' + '(' + str(date.today()) + ')'

        order_list = []
        second_heading = approval_status = ''
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Filtered Payments')
        fp = StringIO()
        row_index = 0

        main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
        sp_style = xlwt.easyxf('font: bold on, height 350;')
        header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
        base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
        base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
        base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')

        worksheet.col(0).width = 2000
        worksheet.col(1).width = 6000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 6000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 3000
        worksheet.col(6).width = 12000
        worksheet.col(7).width = 3000
        worksheet.col(8).width = 5000
        worksheet.col(9).width = 5000
        worksheet.col(10).width = 3000
        worksheet.col(11).width = 5000
        worksheet.col(12).width = 5000
        worksheet.col(13).width = 3000


        header_fields = [
                'Sr No.',
                'Client',
                'Org',
                'Date Account',
                'DocumentNo',
                'Description',
                'Code',
                'Beneficiary',
                'Total',
                'Beneficiary Account Number',
                'IFSC Code',
                'Bank',
                'Beneficiary Email'
                ]


     
        for index, value in enumerate(header_fields):
            worksheet.write(row_index, index, value, header_style)
        row_index += 1

        count = 0

        payment_filter = self.payment_lines_one2many

        if  len(payment_filter) < 1:
            raise ValidationError(_('No Records Found'))

        for res in payment_filter:
            if res :
                count +=1

                worksheet.write(row_index, 0,count, base_style )
                worksheet.write(row_index, 1,self.company_id.name, base_style )
                worksheet.write(row_index, 2,res.ad_org, base_style )
                worksheet.write(row_index, 3, res.value_date , base_style )
                worksheet.write(row_index, 4,res.documentno, base_style )
                worksheet.write(row_index, 5,res.description, base_style )
                worksheet.write(row_index, 6, res.customer_reference_number, base_style )
                worksheet.write(row_index, 7, res.beneficiary_name, base_style )
                worksheet.write(row_index, 8, str(abs(res.transaction_amount)), base_style )
                worksheet.write(row_index, 9, res.beneficiary_account_number or '', base_style )
                worksheet.write(row_index, 10, res.ifsc_code or '', base_style )
                worksheet.write(row_index, 11, res.bank_name or '', base_style )
                worksheet.write(row_index, 12, res.beneficiary_email_id or '', base_style )

                row_index += 1


        row_index +=1
        workbook.save(fp)


        out = base64.encodestring(fp.getvalue())

        self.write({'pmt_output_file': out,'pmt_export_file':name+'.xls'})



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

            file_extension =  self.env['bank.payment'].search([("date","=",self.date)])
            ext = str(len(file_extension)+1).zfill(3)

            payment_lines = self.payment_lines_one2many

            if  len(payment_lines) < 1:
                raise ValidationError(_('No Records Selected'))

            for rec in payment_lines:
                # print "kkkkkkkkkkkkkkkkkkkkkkkk" , rec.beneficiary_account_number , rec.ifsc_code

                if not (rec.beneficiary_account_number and rec.ifsc_code):
                    raise ValidationError(" Kindly Enter Bank Account No / IFSC Code or Delete the Payment Line" )

                if not (rec.beneficiary_account_number or rec.ifsc_code):
                    raise ValidationError(" Kindly Enter Bank Account No / IFSC Code or Delete the Payment Line" )


                if rec.beneficiary_account_number > 2500000:
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
            print "Mount Not Found" , mount

            #os.system('sudo  umount -f -a -t cifs -l /media/BACKUP')

            destination = '/media/BACKUP/'


            # p = Popen(['cp','-p','--preserve',fileName,destination])
            # p.wait()

            # shutil.copy(fileName, destination+realfilename)
            # shutil.copyfile(fileName, '/media/BACKUP/', *, follow_symlinks=True)
            if mount == True:
                print "#----------------------------Mount -Connected--Successfully -------------------------------"
                # os.system('sudo mount -t cifs -o username=bankuser,password=Bank@2004 //192.168.40.7/users/Public/BankPayments/tobank /media/BACKUP/' )
                os.system('sudo mount -t cifs -o username=bankuser,password=Bank@2004,domain=miraj //192.168.40.7/f/bankautomation/tobank /media/BACKUP/' )
                # os.system('sudo mount -t cifs -o username=bankuser,password=Bank@2004,domain=miraj //192.168.40.7/f /media/BACKUP/' )

            try:
                os.system('sudo cp -f ' + fileName +  ' /media/BACKUP/ ' )
                print "File Transfering......................................."

            except:
                print "This is an error message!"
                raise UserError(" File Not Copied. Contact IT Dept" )
                
            finally:
                # print error
                print "File Transfered Successfully"

   


class bank_payment_lines(models.Model):
    _name = "bank.payment.lines"
    _description="Payment lines"

    name = fields.Char('Name')
    payment_id = fields.Many2one('bank.payment', string='Payment', track_visibility='onchange')
    transaction_type = fields.Selection([
                                    ('R', 'RTGS'),
                                    ('N', 'NEFT'),
                                    ('I', 'Funds Transfer'),
                                    ('D', 'Demand Draft')], 
                                    string='Transaction Type',track_visibility='onchange')
    beneficiary_code = fields.Char('Beneficiary Code')
    beneficiary_account_number = fields.Char('Beneficiary Account Number')
    transaction_amount = fields.Float('Transaction Amount')
    beneficiary_name = fields.Char('Beneficiary Name')
    customer_reference_number = fields.Char('Customer Reference Number')
    value_date = fields.Char('Value Date')
    ifsc_code = fields.Char('IFSC Code')
    beneficiary_email_id = fields.Char('Beneficiary Email Id')
    payment_term = fields.Char('Payment Term')
    owner = fields.Char('Owner')
    owner_email = fields.Char('Owner Email')
    description = fields.Char('Description')
    documentno = fields.Char('Document No')
    check_invoice = fields.Boolean('Check')
    user_id = fields.Many2one('res.users', string='Owner')
    bank_name = fields.Char('Bank')
    ad_org = fields.Char(string="Org")



class bank_invoice_selected(models.Model):
    _name = "bank.invoice.selected"
    _description="Invoice selected"

    name = fields.Char('Name')
    invoice_selected_id = fields.Many2one('bank.payment', string='Selected Invoices', track_visibility='onchange')
    transaction_type = fields.Selection([
                                    ('R', 'RTGS'),
                                    ('N', 'NEFT'),
                                    ('I', 'Funds Transfer'),
                                    ('D', 'Demand Draft')], 
                                    string='Transaction Type',track_visibility='onchange')
    beneficiary_code = fields.Char('Beneficiary Code')
    beneficiary_account_number = fields.Char('Beneficiary Account Number')
    transaction_amount = fields.Float('Transaction Amount')
    beneficiary_name = fields.Char('Beneficiary Name')
    customer_reference_number = fields.Char('Customer Reference Number')
    value_date = fields.Char('Value Date')
    ifsc_code = fields.Char('IFSC Code')
    beneficiary_email_id = fields.Char('Beneficiary Email Id')
    payment_term = fields.Char('Payment Term')
    owner = fields.Char('Owner')
    owner_email = fields.Char('Owner Email')
    description = fields.Char('Description')
    documentno = fields.Char('Document No')
    check_invoice = fields.Boolean(string = "", nolabel="1")
    user_id = fields.Many2one('res.users', string='Owner')
    state = fields.Selection([
                                ('draft', 'Draft'),
                                ('approved', 'Approved'),
                                ('rejected', 'Rejected'),
                                ('hold', 'Holded')], 
                                string='Status',track_visibility='onchange')

    delegate_user_id = fields.Many2many('res.users', 'bank_invoice_selected_res_users_rel',  string='Delegate To')
    delay_date = fields.Date('Delay Date')
    customercode = fields.Char(string="Code")
    totalamt = fields.Float(string="Total")
    allocatedamt = fields.Float(string="Allocated Amt")
    unallocated = fields.Float(string="Unallocated Amt")
    duedays = fields.Integer(string="Due Days")
    invoiceno = fields.Char(string="Inv No")
    ad_org = fields.Char(string="Org")
    c_bpartner_id = fields.Char("Partner ID")
    c_invoice_id = fields.Char("ERP Invoice ID")
    ad_org_id = fields.Many2one('org.master', string='Organisation' )


    @api.multi
    def approve_invoice(self):
        condition= ''
        unallocated = abs(self.unallocated)

        if self.state == 'approved':
            self.state = 'draft'
            self.env['bank.invoice.filter'].sudo().search([("selected_id","=",self.id)]).unlink()
            self.env['bank.invoice.filter'].sudo().search([("documentno","=",self.documentno)]).unlink()
            condition = 'deduct'
            self.invoice_selected_id._amount_calc(condition,unallocated)
        else:
            condition = 'add'
            self.invoice_selected_id._amount_calc(condition,unallocated)

            if len(self.env['bank.invoice.filter'].search([("invoice_filter_id","=",self.invoice_selected_id.id)])) < 1:
                vals_line = {
                    'invoice_filter_id':self.invoice_selected_id.id,
                    'documentno':self.documentno,
                    'value_date':self.value_date,
                    'transaction_amount':self.transaction_amount,
                    'beneficiary_name':self.beneficiary_name,
                    'invoiceno' :self.invoiceno,
                    'totalamt' : abs(self.totalamt),
                    'allocatedamt' : abs(self.allocatedamt),
                    'unallocated' : abs(self.unallocated),
                    'unallocated2' : abs(self.unallocated),
                    'duedays' : self.duedays,
                    'customercode': self.customercode,
                    'ad_org': self.ad_org,
                    'selected_id' : self.id,
                    'c_bpartner_id': self.c_bpartner_id,
                    'ad_org_id': self.invoice_selected_id.ad_org_id.id,
                    'c_invoice_id': self.c_invoice_id,

                                
                    }

            else:

                for res in self.env['bank.invoice.filter'].search([("invoice_filter_id","=",self.invoice_selected_id.id)]):
                    if res.documentno != self.documentno:
               
                        vals_line = {
                            'invoice_filter_id':self.invoice_selected_id.id,
                            'documentno':self.documentno,
                            'value_date':self.value_date,
                            'transaction_amount':self.transaction_amount,
                            'beneficiary_name':self.beneficiary_name,
                            'invoiceno' :self.invoiceno,
                            'totalamt' : abs(self.totalamt),
                            'allocatedamt' :abs(self.allocatedamt),
                            'unallocated' : abs(self.unallocated),
                            'unallocated2' :abs(self.unallocated),
                            'duedays' : self.duedays,
                            'customercode': self.customercode,
                            'ad_org': self.ad_org,
                            'lines_id' : self.id,
                            'c_bpartner_id': self.c_bpartner_id,
                            'ad_org_id': self.invoice_selected_id.ad_org_id.id,
                            'c_invoice_id': self.c_invoice_id,

                                        
                            }
                    else:
                        raise ValidationError("Invoice Already Present in 'Filtered Invoices' ")
        
            self.invoice_selected_id.invoice_filter_one2many.create(vals_line)
            self.state = 'approved'



    # @api.multi
    # def sync_selected_invoices(self):

    #     if self.partner_name:

    #         if len(self.env['bank.invoice.filter']) < 1:
    #             vals_line = {
    #                         'invoice_selected_id':self.id,
    #                         'documentno':res.documentno,
    #                         'value_date':res.value_date,
    #                         'transaction_amount':res.transaction_amount,
    #                         'beneficiary_name':res.beneficiary_name,
    #                         'invoiceno' :res.invoiceno,
    #                         'totalamt' :res.totalamt,
    #                         'allocatedamt' :res.allocatedamt,
    #                         'unallocated' :res.unallocated,
    #                         'duedays' : res.duedays,
    #                         'customercode': res.customercode,
    #                         'ad_org': res.ad_org,
    #                         'c_bpartner_id': res.c_bpartner_id,
    #                         'c_invoice_id': res.c_invoice_id,
                            
    #                     }
    #         else:

    #             for res in self.env['bank.invoice.filter']:
    #                 if res.documentno != self.documentno:
    #                     for res in self.invoice_lines_one2many:
    #                         if self.partner_name == res.beneficiary_name:
    #                             vals_line = {
    #                                     'invoice_selected_id':self.id,
    #                                     'documentno':res.documentno,
    #                                     'value_date':res.value_date,
    #                                     'transaction_amount':res.transaction_amount,
    #                                     'beneficiary_name':res.beneficiary_name,
    #                                     'invoiceno' :res.invoiceno,
    #                                     'totalamt' :res.totalamt,
    #                                     'allocatedamt' :res.allocatedamt,
    #                                     'unallocated' :res.unallocated,
    #                                     'duedays' : res.duedays,
    #                                     'customercode': res.customercode,
    #                                     'ad_org': res.ad_org,
    #                                     'c_bpartner_id': res.c_bpartner_id,
    #                                     'c_invoice_id': res.c_invoice_id,
                                        
    #                                 }
    #         self.invoice_selected_one2many.create(vals_line)


    #     self.partner_name = ''



class bank_invoice_filter(models.Model):
    _name = "bank.invoice.filter"
    _description="Filtered Invoice"

    name = fields.Char('Name')
    invoice_filter_id = fields.Many2one('bank.payment', string='Filter Invoices', track_visibility='onchange')
    transaction_type = fields.Selection([
                                    ('R', 'RTGS'),
                                    ('N', 'NEFT'),
                                    ('I', 'Funds Transfer'),
                                    ('D', 'Demand Draft')], 
                                    string='Transaction Type',track_visibility='onchange')
    beneficiary_code = fields.Char('Beneficiary Code')
    beneficiary_account_number = fields.Char('Beneficiary Account Number')
    transaction_amount = fields.Float('Transaction Amount')
    beneficiary_name = fields.Char('Beneficiary Name')
    customer_reference_number = fields.Char('Customer Reference Number')
    value_date = fields.Char('Value Date')
    ifsc_code = fields.Char('IFSC Code')
    beneficiary_email_id = fields.Char('Beneficiary Email Id')
    payment_term = fields.Char('Payment Term')
    owner = fields.Char('Owner')
    owner_email = fields.Char('Owner Email')
    description = fields.Char('Description')
    documentno = fields.Char('Document No')
    check_invoice = fields.Boolean(string = "", nolabel="1")
    user_id = fields.Many2one('res.users', string='Owner')
    state = fields.Selection([
                                ('draft', 'Draft'),
                                ('approved', 'Approved'),
                                ('rejected', 'Rejected'),
                                ('hold', 'Holded')], 
                                string='Status',track_visibility='onchange')

    delegate_user_id = fields.Many2many('res.users', 'bank_invoice_filter_res_users_rel',  string='Delegate To')
    delay_date = fields.Date('Delay Date')
    customercode = fields.Char(string="Code")
    totalamt = fields.Float(string="Total")
    allocatedamt = fields.Float(string="Allocated Amt")
    unallocated = fields.Float(string="Unallocated Amt")
    duedays = fields.Integer(string="Due Days")
    invoiceno = fields.Char(string="Inv No")
    ad_org = fields.Char(string="Org")
    selected_id = fields.Integer(string="Selected ID")
    lines_id = fields.Integer(string="Lines ID")
    company_id = fields.Many2one('res.company')
    ad_org_id = fields.Many2one('org.master', string='Organisation' )
    c_bpartner_id = fields.Char("Partner ID")
    log = fields.Text("Log")
    c_invoice_id = fields.Char("ERP Invoice ID")
    unallocated2 = fields.Float(string="Unallocated")


    @api.onchange('unallocated')
    def onchange_unallocated(self):
        if self.unallocated :
            if self.unallocated > self.unallocated2:

                raise ValidationError(" Unallocated Amount cannot be greater" )



class bank_invoice_lines(models.Model):
    _name = "bank.invoice.lines"
    _description="Invoice lines"

    name = fields.Char('Name')
    invoice_id = fields.Many2one('bank.payment', string='Invoices', track_visibility='onchange')
    # invoice_icici_id = fields.Many2one('bank.payment.icici', string='Invoices', track_visibility='onchange')
    transaction_type = fields.Selection([
                                    ('R', 'RTGS'),
                                    ('N', 'NEFT'),
                                    ('I', 'Funds Transfer'),
                                    ('D', 'Demand Draft')], 
                                    string='Transaction Type',track_visibility='onchange')
    beneficiary_code = fields.Char('Beneficiary Code')
    beneficiary_account_number = fields.Char('Beneficiary Account Number')
    transaction_amount = fields.Float('Transaction Amount')
    beneficiary_name = fields.Char('Beneficiary Name')
    customer_reference_number = fields.Char('Customer Reference Number')
    value_date = fields.Char('Value Date')
    ifsc_code = fields.Char('IFSC Code')
    beneficiary_email_id = fields.Char('Beneficiary Email Id')
    payment_term = fields.Char('Payment Term')
    owner = fields.Char('Owner')
    owner_email = fields.Char('Owner Email')
    description = fields.Char('Description')
    documentno = fields.Char('Document No')
    check_invoice = fields.Boolean(string = "", nolabel="1")
    user_id = fields.Many2one('res.users', string='Owner')
    state = fields.Selection([
                                ('draft', 'Draft'),
                                ('approved', 'Approved'),
                                ('rejected', 'Rejected'),
                                ('hold', 'Holded')], 
                                string='Status',track_visibility='onchange')

    delegate_user_id = fields.Many2many('res.users', 'bank_invoice_lines_res_users_rel',  string='Delegate To')
    delay_date = fields.Date('Delay Date')
    customercode = fields.Char(string="Code")
    totalamt = fields.Float(string="Total")
    allocatedamt = fields.Float(string="Allocated Amt")
    unallocated = fields.Float(string="Unallocated Amt")
    duedays = fields.Integer(string="Due Days")
    invoiceno = fields.Char(string="Inv No")
    ad_org = fields.Char(string="Org")
    c_bpartner_id = fields.Char("Partner ID")
    c_invoice_id = fields.Char("ERP Invoice ID")
    ad_org_id = fields.Many2one('org.master', string='Organisation' )


    @api.multi
    def submit_manager_line(self):

        for records in self:
            if records.owner_email:
                template_id = self.env['ir.model.data'].get_object_reference('external_db_connect','confirm_invoice_action')[1]
                email_template_obj = self.env['mail.template'].browse(template_id)
                if template_id:
                    values = email_template_obj.generate_email(self.id, fields=None)
                    values['email_from'] = records.invoice_id.user_id.login
                    values['email_to'] = records.owner_email
                    values['res_id'] = False
                    mail_mail_obj = self.env['mail.mail']
                    msg_id = mail_mail_obj.sudo().create(values)
                    self.mail_date = datetime.now()
                    if msg_id:
                        msg_id.sudo().send()

        return True


    @api.multi
    def approve_invoice(self):

        if self.state == 'approved':
            self.state = 'draft'
            self.env['bank.invoice.filter'].sudo().search([("lines_id","=",self.id)]).unlink()
            self.env['bank.invoice.filter'].sudo().search([("documentno","=",self.documentno)]).unlink()

        else:

            if len(self.env['bank.invoice.filter'].search([("invoice_filter_id","=",self.invoice_id.id)])) < 1:
                vals_line = {
                        'invoice_filter_id':self.invoice_id.id,
                        'documentno':self.documentno,
                        'value_date':self.value_date,
                        'transaction_amount':self.transaction_amount,
                        'beneficiary_name':self.beneficiary_name,
                        'invoiceno' :self.invoiceno,
                        'totalamt' : abs(self.totalamt),
                        'allocatedamt' :abs(self.allocatedamt),
                        'unallocated' : abs(self.unallocated),
                        'unallocated2' :abs(self.unallocated),
                        'duedays' : self.duedays,
                        'customercode': self.customercode,
                        'ad_org': self.ad_org,
                        'lines_id' : self.id,
                        'c_bpartner_id': self.c_bpartner_id,
                        'ad_org_id': self.invoice_id.ad_org_id.id,
                        'c_invoice_id': self.c_invoice_id,

                                    
                        }


            else:

                for res in self.env['bank.invoice.filter'].search([("invoice_filter_id","=",self.invoice_id.id)]):
                    if res.documentno != self.documentno:
                
                        vals_line = {
                            'invoice_filter_id':self.invoice_id.id,
                            'documentno':self.documentno,
                            'value_date':self.value_date,
                            'transaction_amount':self.transaction_amount,
                            'beneficiary_name':self.beneficiary_name,
                            'invoiceno' :self.invoiceno,
                            'totalamt' : abs(self.totalamt),
                            'allocatedamt' :abs(self.allocatedamt),
                            'unallocated' : abs(self.unallocated),
                            'unallocated2' :abs(self.unallocated),
                            'duedays' : self.duedays,
                            'customercode': self.customercode,
                            'ad_org': self.ad_org,
                            'lines_id' : self.id,
                            'c_bpartner_id': self.c_bpartner_id,
                            'ad_org_id': self.invoice_id.ad_org_id.id,
                            'c_invoice_id': self.c_invoice_id,

                                        
                            }
                    else:
                        raise ValidationError("Invoice Already Present in 'Filtered Invoices' ")
            self.invoice_id.invoice_filter_one2many.create(vals_line)
            self.state = 'approved'


class wizard_reject(models.TransientModel):
    _name = 'wizard.reject'

    @api.model
    def _default_invoice_id(self):
        if 'default_invoice_id' in self._context:
            return self._context['default_invoice_id']
        if self._context.get('active_model') == 'bank.invoice.lines':
            return self._context.get('active_id')
        return False

    @api.multi
    def delay_invoice(self):

        create_date = dateutil.parser.parse(self.create_date).date()
        delay_days = int(self.delay_days)
        delay_date = create_date + timedelta(days=delay_days )
        if self.invoice_id.user_id.id == self.env.uid or self.invoice_id.user_id.employee_id.parent_id.user_id.id == self.env.uid \
                                                                or  self.env.uid in [x.id for x in self.invoice_id.delegate_user_id] :
            if self.invoice_id:
                self.invoice_id.delay_date = delay_date
                self.invoice_id.state = 'rejected'

        else:
            raise UserError("Not Authorised" )


    delay_days = fields.Char('Delay By Days')
    invoice_id= fields.Many2one('bank.invoice.lines', default=_default_invoice_id)



class ErpBankMaster(models.Model):
    _name = "erp.bank.master"
    _description="Bank Master"

    c_bankaccount_id= fields.Char('Bankaccount Id')
    ad_client_id= fields.Char('Client Id')
    ad_org_id= fields.Char('Org Id')
    active= fields.Boolean('Active')
    c_bank_id= fields.Char('C_Bank_Id')
    bankaccounttype= fields.Selection([
                                    ('D', 'Card'),
                                    ('B', 'Cash'),
                                    ('C', 'Checking'),
                                    ('S', 'Savings')], 
                                    string='Bankaccounttype')
    accountno= fields.Char('Accountno')
    currentbalance= fields.Float('Currentbalance')
    creditlimit= fields.Float('Creditlimit')
    default= fields.Boolean('Default')
    name= fields.Char('Name')
    value= fields.Char('Value')
    company_id = fields.Many2one('res.company', string='Company')
    ad_org = fields.Many2one('org.master', string='Organisation',  domain="[('company_id','=',company_id)]" )