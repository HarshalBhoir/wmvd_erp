#!/usr/bin/env bash

from datetime import datetime, timedelta, date
import dateutil.parser
from odoo.tools.translate import _
from odoo import tools, api, fields, models, _ , registry, SUPERUSER_ID
import logging
from odoo.exceptions import UserError , ValidationError
import shutil
import os
import time
import psycopg2
import csv
from cStringIO import StringIO
import xlwt
import re
import base64
from subprocess import Popen
from odoo import http
from collections import Counter
import requests
from werkzeug import url_encode

_logger = logging.getLogger(__name__)

idempiere_url="https://erpnew.wmvd.live/ADInterface/services/compositeInterface?wsdl"
headers = {'content-type': 'text/xml'}

todaydate = "{:%d-%b-%y}".format(datetime.now())

DATE_FORMAT = "%Y-%m-%d"

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

header_fields3 = [
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

TRANSACTION_TYPE = [('R', 'RTGS'),
                    ('N', 'NEFT'),
                    ('I', 'Funds Transfer'),
                    ('D', 'Demand Draft')]

STATE = [('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('hold', 'Holded')]


main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; \
        borders: bottom thick, top thick, left thick, right thick')
sp_style = xlwt.easyxf('font: bold on, height 350;')
header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center, vertical center; \
    borders: bottom thin, top thin, left thin, right thin; \
    pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
    pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
    pattern: pattern fine_dots, fore_color white, back_color yellow;')

class bank_payment(models.Model):
    _name = "bank.payment"
    _description=" Payment to Bank"
    _inherit = 'mail.thread'
    _order    = 'id desc'


    @api.multi
    def _compute_can_edit_name(self):
        self.can_edit_name = self.env.user.has_group('sales_meet.group_sales_meet_hidden')
        print "1111111111111111111111111111111111111111 _compute_can_edit_name bank_payment"

    @api.multi
    def _get_config(self):
        config = self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1)
        if config:
            config_id = config.id
        else:
            config = self.env['external.db.configuration'].search([('id', '!=',0)], limit=1)
            config_id = config.id
        return config_id


    @api.multi
    def _amount_calc(self,condition=False,amount=False):
        if condition == 'deduct':
            self.amount_total -= amount
        elif condition == 'add':
            self.amount_total += amount

    @api.depends('invoice_filter_one2many.unallocated')
    @api.onchange('invoice_filter_one2many.unallocated')
    def _calculate_all(self):
        for order in self:
            total_unallocated = 0.0
            for line in order.invoice_filter_one2many:
                total_unallocated += line.unallocated
            order.update({'amount_filtered_total': total_unallocated,})


    def _default_ad_org_id(self):
        org = self.env['org.master'].sudo().search([('company_id','=',self.env.user.company_id.id),
            ('default', '=',True)], limit=1)
        if not org:
            return False
        else:
            org_id = org.id
            return org_id


    name = fields.Char('Name', store=True)
    db_name = fields.Char('DB Name')
    config_id = fields.Many2one('external.db.configuration', string='Database' , default=_get_config)
    note = fields.Text('Text', copy=False)
    state = fields.Selection([('draft', 'Draft'),
                             ('generated_invoice', 'Invoice Generated'), 
                             ('generated_invoice_template', 'Template Generated'), 
                             ('submitted_to_manager', 'Submitted to Manager'), 
                             ('approved', 'Approved'), 
                             ('refused', 'Refused'), 
                             ('erp_posted', 'Posted'), 
                             ('generated_payment', 'Payment Generated'), 
                             ('submitted_to_bank', 'Submitted to Bank') 
                             ], string='Status',track_visibility='onchange', default='draft')

    transaction_type = fields.Selection(TRANSACTION_TYPE, string='Transaction Type')
    requester = fields.Char('Requester')
    payment_lines_one2many = fields.One2many('bank.payment.lines','payment_id',string="Payments Details")
    invoice_lines_one2many = fields.One2many('bank.invoice.lines','invoice_id',string="Invoice Details" )
    invoice_selected_one2many = fields.One2many('bank.invoice.selected','invoice_selected_id',
        string="Selected Invoice" )
    invoice_filter_one2many = fields.One2many('bank.invoice.filter','invoice_filter_id',
        string="Selected Invoice" )
    
    date = fields.Date(string="Date", default=lambda self: fields.Datetime.now())
    employee_id = fields.Many2one('hr.employee', string="Employee")
    completed = fields.Boolean("Completed", copy=False)
    company_id = fields.Many2one('res.company', string='Company', index=True, 
        default=lambda self: self.env.user.company_id.id)
    ad_org_id = fields.Many2one('org.master', string='Organisation',  
        domain="[('company_id','=',company_id)]", default=_default_ad_org_id)
    c_bpartner_id = fields.Char("Partner ID")
    ad_client_id = fields.Char('Client ID')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, default=lambda self: self.env.user)
    
    delegate_user_id = fields.Many2many('res.users',  string='Delegate To')
    custgroup = fields.Char(string="Group")
    hr_payment_data = fields.Char('Rep Name')
    file_name = fields.Binary('Expense Report', readonly=True, copy=False)

    output_file = fields.Binary('Prepared file', filters='.xls', attachment=True, copy=False)
    export_file = fields.Char(string="Export", copy=False)

    pmt_output_file = fields.Binary('Prepared file', filters='.xls', attachment=True, copy=False)
    pmt_export_file = fields.Char(string="Export", copy=False)

    partner_name = fields.Char('Partner')
    hr_payment_data2 = fields.Char('Rep Name2')
    file_name2 = fields.Binary('Due Invoices Report', copy=False)
    inv_rep_bool = fields.Boolean('Inv Rep Generated' , default=False, copy=False)
    condition = fields.Selection([
        ('invoice', 'Invoice'),
        ('payment', 'Payment')], string='Condition')
    erp_bank_id = fields.Many2one('erp.bank.master', string='Bank Account', 
        domain="[('company_id','=',company_id)]" )
    filter_rep_bool = fields.Boolean('Filter Rep Generated' , default=False, copy=False)

    amount_total = fields.Float(string='Total', store=True)
    amount_filtered_total = fields.Float(string='Filtered Total', readonly=True, 
        compute='_calculate_all', digits=(16,3), store=True)

    can_edit_name = fields.Boolean(compute='_compute_can_edit_name')
    owner_id = fields.Many2one('erp.representative.approver', string='Owner', 
        domain="[('company_id','=',company_id)]" )
    server_instance = fields.Selection([
        ('Demo', 'Demo'),
        ('Live', 'Live')], string='Server Instance')

    @api.multi
    def unlink(self):
        for order in self:
            if self.env.uid != 1 or order.state in ('erp_posted','refused') :
                raise UserError(_('Records in Approved/ Rejected/ Posted state cannot be deleted'))
        return super(bank_payment, self).unlink()


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
    def refresh_form(self):
        return True


    @api.multi
    def name_creation(self):
        name =''
        daymonth = datetime.strptime(self.date, DATE_FORMAT)
        month2 = daymonth.strftime("%b")
        day = daymonth.strftime("%d")
        week_day = daymonth.strftime("%A")
        year = daymonth.strftime("%Y")
        self.name = name = 'Bank Statement for ' + str(day) + ' ' + str(month2) + ' ' + str(week_day) + ' ' + str(year)
        return name

    @api.multi
    def select_all(self):
        filter_lines = []
        filtered_lines = [x.documentno for x in self.invoice_filter_one2many]

        for res in self.invoice_selected_one2many:
            if res.documentno not in filtered_lines:

                filter_lines.append((0, 0, {
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
                    }))


        self.invoice_filter_one2many = filter_lines
        self.invoice_selected_one2many.unlink()


    @api.multi
    def sync_selected_invoices(self):
        self.invoice_selected_one2many.unlink()
        selected_lines = []

        if self.partner_name:
            for rec in self.invoice_selected_one2many:
                if self.partner_name == rec.beneficiary_name:
                    raise UserError(" Partner already selected" )
                else:
                    continue

            for res in self.invoice_lines_one2many:
                if self.partner_name == res.beneficiary_name:

                    selected_lines.append((0, 0, {
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
                        }))

            self.invoice_selected_one2many = selected_lines

        else:
            raise UserError(" Partner Not Selected" )

        self.partner_name = ''
        self.amount_total = 0.0


    @api.multi
    def sync_invoices(self):
        conn_pg = None
        invoice_lines = []

        if not self.config_id:
            raise UserError(" DB Connection not set / Disconnected " )

        else:
            try:
                print "#-------------Select --TRY----------------------#"
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
                password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
                pg_cursor = conn_pg.cursor()

                ad_client_id=self.company_id.ad_client_id
                salesrep_id = self.owner_id.salesrep_id

                if self.owner_id:
                    pg_cursor.execute("select * from adempiere.due_sync_vendor_invoice where \
                        ad_client_id=%s and SalesRep_ID=%s" ,[ad_client_id, salesrep_id])

                else:
                    pg_cursor.execute("select * from adempiere.due_sync_vendor_invoice where \
                        ad_client_id=%s " ,[ad_client_id])
                     
                entry_id = pg_cursor.fetchall()

                if entry_id == []:
                    raise UserError(" No Records Found " )

                for record in entry_id:
                    user_ids = self.env['res.users'].sudo().search([("login","=",record[11])])

                    invoice_lines.append((0, 0, {
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
                        }))

                self.invoice_lines_one2many = invoice_lines
                self.state='generated_invoice'
                self.name = 'Due Invoices' + '(' + str(date.today()) + ')'
                seq = self.env['ir.sequence'].sudo().next_by_code('bank.payment.invoice') or '/'
                self.name = 'DI/' + str(self.company_id.short_name)+'/' + str(seq)

            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '#-------------------Except ---Error %s' % e        

            finally:
                if conn_pg: conn_pg.close()
                print "#--------------Select ----Finally----------------------#"


    @api.multi
    def update_payschedule_boolean(self,condition=False):
        if self.config_id:
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
                    password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
                pg_cursor = conn_pg.cursor()

                doc_number = tuple([(res.documentno).encode('utf-8') for res in self.invoice_filter_one2many])

                if condition == 1:
                    pg_cursor.execute("update adempiere.C_Invoice set IsPayScheduleValid = 'Y' where ad_client_id=%s and \
                        documentno in %s",(self.company_id.ad_client_id, doc_number))
                elif condition == 0:
                    pg_cursor.execute("update adempiere.C_Invoice set IsPayScheduleValid = 'N' where ad_client_id=%s and \
                        documentno in %s",(self.company_id.ad_client_id, doc_number))
                else:
                    pg_cursor.execute("update adempiere.C_Invoice set IsPayScheduleValid = 'N' where ad_client_id=%s and \
                        documentno in %s",(self.company_id.ad_client_id, doc_number))

                print "==============Update Invoice =====================", condition

                entry_id = conn_pg.commit()

            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '-----------------------------Error %s' % e    

            finally:
                if conn_pg: conn_pg.close()
                print "#---------------Update ----Finally----------------------#"


    @api.multi
    def generate_filter_invoice_report(self):
        filter_invoice_report = 1
        self.general_invoice_report(filter_invoice_report)

        if self.state in  ('generated_invoice','draft'):
            self.state = 'generated_invoice_template'

        self.filter_rep_bool = True


    @api.multi
    def generate_invoice_report(self):
        self.general_invoice_report()
        self.inv_rep_bool = True
                  

    @api.multi
    def general_invoice_report(self,filter_invoice_report=False):      
        self.ensure_one()

        if filter_invoice_report == 1:
            name = 'Filter Invoices Report' + '(' + str(date.today()) + ')'
            invoice_filter = self.invoice_filter_one2many
        else:
            name = 'Invoices Report' + '(' + str(date.today()) + ')'
            invoice_filter = self.invoice_lines_one2many

        status = payment_no = second_heading = approval_status = ''
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet(name)
        fp = StringIO()
        row_index = 0

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

     
        for index, value in enumerate(header_fields3):
            worksheet.write(row_index, index, value, header_style)
        row_index += 1

        count = 0

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

        if filter_invoice_report == 1:
            self.write({'output_file': out,'export_file':name+'.xls'})
        else:
            self.write({'file_name2': out,'hr_payment_data2':name+'.xls'})


    @api.multi
    def refuse_approval_request(self,remarks=False, user_id=False):
        owner_refuse = self.env['res.users'].sudo().search([("id","=",self.owner_id.owner_id.id)])

        if self.env.uid == owner_refuse.id or self.env.uid ==1 or \
        self.user_has_groups('sales_meet.group_bank_payment_manager'):

            if not (remarks or self.note):
                raise ValidationError(_('Kindly Update the Remarks and then Reject'))

            if self.note:
                self.sudo().write({'state': 'refused'})
            else:
                self.sudo().write({'state': 'refused','note':remarks or self.note})

            subject = "[Refused] Approval on %s" % (self.name)
            full_body = (_("Approval on Document %s has been refused by \
                %s.<br/><ul class=o_timeline_tracking_value_list></ul>") % (self.name, owner_refuse.name))

            email_from = owner_refuse.email
            payment_mail = "payments@walplast.com"
            email_to_user = self.user_id.email
            email_to = email_to_user + ',' + payment_mail
            condition = 0
            self.send_generic_mail(subject, full_body, email_from, email_to)
            self.update_payschedule_boolean(condition)
        else:
            raise ValidationError(_('Only Owner / Bank Payment Manager can Reject the Due Invoices'))


    @api.multi
    def approve_approval_request(self, remarks=False, user_id=False):
        owner_approval = self.env['res.users'].sudo().search([("id","=",self.owner_id.owner_id.id)])
        user_mail = self.env['res.users'].sudo().search([("id","=",self.user_id.id)])
        if self.env.uid == owner_approval.id or self.env.uid ==1 or \
        self.user_has_groups('sales_meet.group_bank_payment_manager'):

            if not (remarks or self.note):
                raise ValidationError(_('Kindly Update the Remarks and then Approve'))

            if self.note:
                self.sudo().write({'state': 'approved'})
            else:
                self.sudo().write({'state': 'approved','note':remarks or self.note})

            approver = 0
            condition = 1
            email_from = owner_approval.email
            payment_mail = "payments@walplast.com"
            email_to_user = user_mail.email
            email_to = email_to_user + ',' + payment_mail
            subject = "[Approved] Request for %s"  % (self.name)
            initial_body = """ 
                <h3>Hi %s,</h3>
                <h3>The request for document %s is approved by %s dated %s</h3>
                <h3>You can Post the Invoices to create Payment in ERP. </h3>
            """  % (user_mail.name , self.name, owner_approval.name, todaydate)

            self.send_general_mail(initial_body, subject, approver, email_from, email_to)          
            self.update_payschedule_boolean(condition)
            print "------------------- Approved----------------------",  self.state , self.note
        else:
            raise ValidationError(_('Only Owner / Bank Payment Manager can Approve the Due Invoices'))


    @api.multi
    def send_approval_mail(self):
        if not self.owner_id:
            raise ValidationError(_('Kindly Select Owner for requesting Approval for the Due Invoices'))

        approver = 1
        email_from = self.user_id.email

        if self.owner_id.hierarchy_bool:
            email_to_list = [owner.user_id.email for owner in self.env['erp.representative.matrix'].sudo().search([
                                                                ("approver_id","=",self.owner_id.id),
                                                                ("min_amt","<=",self.amount_filtered_total),
                                                                ("max_amt",">=",self.amount_filtered_total)], limit=1)]

            email_to = ",".join(email_to_list)
        else:
            owner = self.env['res.users'].sudo().search([("id","=",self.owner_id.owner_id.id)])
            email_to = owner.email

        subject = "Request for Due Invoices Approval - %s "  % (todaydate)
        initial_body = """ 
        <h3>Hi %s,</h3>
            <h3>The following Invoices are outstanding / unallocated and requires an approval from your end.</h3>
            <h3>Kindly take necessary action by clicking the buttons below:</h3>
        """ % (owner.name)
        self.send_general_mail(initial_body, subject, approver, email_from, email_to)
        self.state='submitted_to_manager'

   
    @api.multi
    def send_general_mail(self, initial_body=False, subject=False, approver=False, email_from=False, email_to=False):
        second_body = body = """ """
        line_html = ""
        main_id = self.id
        owner_general = self.env['res.users'].sudo().search([("id","=",self.owner_id.owner_id.id)])

        print "---------------Start ---------------" , email_from, email_to, approver

        invoice_filter_line = self.invoice_filter_one2many.search([("invoice_filter_id","=",self.id)])

        if  len(invoice_filter_line) < 1:
            raise ValidationError(_('No Records Selected'))

            
        for l in invoice_filter_line:

            start_date = datetime.strptime(str(((l.value_date).split())[0]), 
                tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

            line_html += """
            <tr>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
            </tr>
            """ % (start_date, l.invoiceno, l.documentno, l.customercode, l.beneficiary_name, \
                l.totalamt, l.allocatedamt, l.unallocated, l.duedays)

            # totalcn += l.totalamt

        main_date = datetime.strptime(str(((self.date).split())[0]), 
                tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

        body = """
            <table >
                <tr>  <th style=" text-align: left;padding: 8px;">Date</td><td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Bank Account</td>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Organisation</td>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Owner</td>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Company</td>  <td> : %s</td></tr>
            </table>
            <br/>

            <table border="1">
                <tbody>
                    <tr class="text-center table_mail">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Date</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Invoice No</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Document No</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Code</th>             
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Partner</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Total Amt</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Allocated Amt</th>             
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Unallocated Amt</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Due Days</th>
                    </tr>
                    %s
                </tbody>
            </table>
            <br/><br/>

        """ % (main_date,self.erp_bank_id.name or '', self.ad_org_id.name or '',  
            owner_general.name, self.company_id.name, line_html)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        imd = self.env['ir.model.data']

        approve_url = base_url + '/approvals?%s' % (url_encode({
                'model': self._name,
                'approval_id': main_id,
                'res_id': main_id,
                'user_id': owner_general.id,
                'action': 'approve_approval_request',
            }))
        reject_url = base_url + '/approvals?%s' % (url_encode({
                'model': self._name,
                'approval_id': main_id,
                'res_id': main_id,
                'user_id': owner_general.id,
                'action': 'refuse_approval_request',
            }))

        report_check = base_url + '/web#%s' % (url_encode({
            'model': self._name,
            'view_type': 'form',
            'id': main_id,
            'view_id' : imd.xmlid_to_res_id('sales_meet.view_invoice_payment_form')
        }))

        if approver == 1:

            second_body =  """<br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Approve All</a>
                        </td>
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Reject All</a>
                        </td>

                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Check All</a>
                        </td>

                    </tr>
                </tbody>
            </table>
            """ % (approve_url, reject_url, report_check)

        else:

            second_body = """<br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Check Approval</a>
                        </td>
                    </tr>
                </tbody>
            </table>
            """ % (report_check)

        full_body =  initial_body + body + second_body

        self.send_generic_mail(subject, full_body, email_from, email_to)

    @api.multi
    def send_generic_mail(self,subject=False, full_body=False, email_from=False, email_to=False):
        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': self.id,
                'email_from': email_from,
                'email_to': email_to,
                'subject': subject,
                'body_html': full_body,
            })

        composed_mail.send()
        print "---------Mail Sent to ---------" , email_to, "---------Mail Sent From ---------" , email_from
        


    @api.multi
    def generate_payment_webservice(self):
        filtered_list = []
        filter_dict = {}
        vals = []
        documentno = ''

        org_id = self.ad_org_id
        daymonth = datetime.today().strftime( "%Y-%m-%d 00:00:00")
        C_BankAccount_ID = self.erp_bank_id.c_bankaccount_id

        invoice_filter = self.invoice_filter_one2many.search([("invoice_filter_id","=",self.id)])

        if  len(invoice_filter) < 1:
            raise ValidationError(_('No Records Selected'))

        user_ids = self.env['wp.erp.credentials'].search([("wp_user_id","=",self.env.uid),("company_id","=",self.company_id.id)])

        if len(user_ids) < 1:
            raise ValidationError(_("User's ERP Credentials not found. Kindly Contact IT Helpdesk"))

        for rec in self.invoice_filter_one2many:
            # filtered_list.append((rec.beneficiary_name,(rec.id, rec.unallocated)))
            filtered_list.append(rec.beneficiary_name)
        
        filtered_list3 = dict(Counter(filtered_list))       

        for beneficiary_name, value in filtered_list3.iteritems():
            total_amount = 0
            payment_description = ''
       
            for record in self.invoice_filter_one2many:
                if beneficiary_name == record.beneficiary_name:
                    if value > 1:
                        total_amount += record.unallocated
                        documentno = ''
                        payment_description += record.invoiceno + ', '

                    else:
                        total_amount = record.unallocated
                        documentno = record.documentno
                        payment_description = record.invoiceno

                    ad_org = record.ad_org_id.ad_org_id
                    date_filter = record.invoice_filter_id.date
                    customercode = record.customercode
                    c_bpartner_id = (str(record.c_bpartner_id).split('.'))[0]
                    filter_id = record.id

            new_list = (ad_org, customercode , documentno, abs(total_amount), c_bpartner_id, filter_id, payment_description)

            vals.append(new_list)

        for res in vals:
            line_body = body = upper_body  = payment_body = lower_body = """ """
            documentno_log = ''
        
            paymt_description = "Payment Against - " + res[6] if res[6] else ''

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
                               </_0:operation>"""  % ( self.ad_org_id.ad_org_id ,C_BankAccount_ID, C_DocType_ID,
                                daymonth, daymonth, res[4], res[3], paymt_description)


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
                               </_0:operation>"""  % ( self.ad_org_id.ad_org_id, (str(line_rec.c_invoice_id).split('.'))[0] ,
                                abs(line_rec.unallocated), abs(line_rec.unallocated) )


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

            body = upper_body + payment_body + line_body + lower_body

            # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , body

            response = requests.post(idempiere_url,data=body,headers=headers)
            print response.content , type(response.content)
            
            log = str(response.content)
            if log.find('DocumentNo') is not -1:
                self.state = 'erp_posted'
                print "aaaaaaaaaaaaaaaaaaaaaa" , log
                documentno_log = log.split('column="DocumentNo" value="')[1].split('"></outputField>')[0]
                print "ssssssssssssssssssssssssss" , documentno_log , self.state
                

            if log.find('IsRolledBack') is not -1:
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
        payment_lines = []
        if not self.config_id:
            raise UserError(" DB Connection not set / Disconnected " )

        else:
            try:
                print "#-------------Select --TRY----------------------#"

                ad_client_id=self.company_id.ad_client_id
                c_bankaccount_id=self.erp_bank_id.c_bankaccount_id
                ad_org_id=self.ad_org_id.ad_org_id

                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username,
                 password=self.config_id.password, host= self.config_id.ip_address)
                pg_cursor = conn_pg.cursor()

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
                    cp.c_bankaccount_id = %s and \
                    cp.ad_org_id = %s and \
                    cp.ad_client_id = %s"  ,(self.date,c_bankaccount_id, ad_org_id, ad_client_id))          


                entry_id = pg_cursor.fetchall()
                if entry_id == []:
                    raise UserError(" No Records Found " )


                for record in entry_id:
                    user_ids = self.env['res.users'].search([("login","=",record[10])])
                    if float(record[3]) > 2500000:
                        transaction_type = 'R'
                    else:
                        transaction_type = 'N'

                    payment_lines.append((0, 0, {
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
                            
                        }))
                    # self.env['bank.payment.lines'].sudo().create(vals_line)
                self.payment_lines_one2many = payment_lines
                self.state='generated_payment'
                self.name_creation()


            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '#----------------Error %s' % e        

            finally:
                if conn_pg: conn_pg.close()
                print "#--------------Select ----Finally----------------------#"



    @api.multi
    def payment_report(self):       
        self.ensure_one()
        status = payment_no = second_heading = approval_status = ''
        name = 'Filtered Payments' + '(' + str(date.today()) + ')'

        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet(name)
        fp = StringIO()
        row_index = 0

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
        item_list = []
        today = datetime.now()

        daymonth = datetime.strptime(self.date, DATE_FORMAT)
        month = daymonth.strftime("%m")
        day = daymonth.strftime("%d")
        year = daymonth.strftime("%Y")
        pay_date = datetime.strptime(self.date, DATE_FORMAT).strftime("%d/%m/%Y")

        file_extension =  self.env['bank.payment'].search([("date","=",self.date)])
        ext = str(len(file_extension)+700).zfill(3)

        payment_lines = self.payment_lines_one2many

        if  len(payment_lines) < 1:
            raise ValidationError(_('No Records Selected'))

        for rec in payment_lines:

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
                (rec.beneficiary_name).encode('utf-8') if rec.beneficiary_name else '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                (rec.description).encode('utf-8') if rec.description else '',
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
                (rec.bank_name).encode('utf-8')  if rec.bank_name else '',
                '',
                (rec.beneficiary_email_id).encode('utf-8')  if rec.beneficiary_email_id else '',
                ])


        if self.server_instance == 'Live':

            fileName="/tmp/WALPLAST_W020_W020"+str(day)+str(month)+"." + str(ext)
            realfilename = "/WALPLAST_W020_W020"+str(day)+str(month)+"." + str(ext)

        else:
            fileName="/tmp/TEST_RRBI_RRBI"+str(day)+str(month)+"." + str(ext)
            realfilename = "/TEST_RRBI_RRBI"+str(day)+str(month)+"." + str(ext)

        with open(fileName, 'wb') as f:
            writer = csv.writer(f, delimiter=',')
            for val in item_list:
                writer.writerow(val)

        mount = os.path.isdir("/media/BACKUP/notmounted")
        print "Mount Not Found" , mount

        destination = '/media/BACKUP/'
        #os.system('sudo  umount -f -a -t cifs -l /media/BACKUP')
        # sudo umount /media/BACKUP

        # p = Popen(['cp','-p','--preserve',fileName,destination])
        # p.wait()

        # shutil.copy(fileName, destination+realfilename)
        # shutil.copyfile(fileName, '/media/BACKUP/', *, follow_symlinks=True)
        if mount == True:
            print "#----------------------------Mount -Connected--Successfully -------------------------------"
            # os.system('sudo mount -t cifs -o username=bankuser,password=Bank@2004 //192.168.40.7/users/Public/BankPayments/tobank /media/BACKUP/' )
            # os.system('sudo mount -t cifs -o username=bankuser,password=Bank@2004,domain=miraj //192.168.40.7/f/bankautomation/tobank /media/BACKUP/' )
            # os.system('sudo mount -t cifs -o username=bankuser,password=Bank@2004,domain=miraj //192.168.40.7/f /media/BACKUP/' )
            os.system('sudo mount -t cifs -o username=bankuser,password=Bk@$%4002,domain=drychem //192.168.40.7/HDFC/upload/hdfcforward/Walplast/src /media/BACKUP/' )

            self.state='submitted_to_bank'

        try:
            os.system('sudo cp -f ' + fileName +  ' /media/BACKUP/ ' )
            print "File Transfering......................................."

        except:
            print "This is an error message!"
            raise UserError(" File Not Copied. Contact IT Dept" )
            
        finally:
            print "File Transfered Successfully"

   


class bank_payment_lines(models.Model):
    _name = "bank.payment.lines"
    _description="Payment lines"

    name = fields.Char('Name')
    payment_id = fields.Many2one('bank.payment', string='Payment')
    transaction_type = fields.Selection(TRANSACTION_TYPE, string='Transaction Type')
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
    invoice_selected_id = fields.Many2one('bank.payment', string='Selected Invoices')
    transaction_type = fields.Selection(TRANSACTION_TYPE, string='Transaction Type')
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
    state = fields.Selection(STATE, string='Status',track_visibility='onchange')

    delegate_user_id = fields.Many2many('res.users', 'bank_invoice_selected_res_users_rel',  
        string='Delegate To')
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
                vals_line={
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
               
                        vals_line={
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
            # self.invoice_selected_id.invoice_filter_one2many = invoice_lines
            self.state = 'approved'


class bank_invoice_filter(models.Model):
    _name = "bank.invoice.filter"
    _description="Filtered Invoice"

    name = fields.Char('Name')
    invoice_filter_id = fields.Many2one('bank.payment', string='Filter Invoices')
    transaction_type = fields.Selection(TRANSACTION_TYPE, string='Transaction Type')
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
    state = fields.Selection(STATE, string='Status',track_visibility='onchange')

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
    invoice_id = fields.Many2one('bank.payment', string='Invoices')
    transaction_type = fields.Selection(TRANSACTION_TYPE, string='Transaction Type')
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
    state = fields.Selection(STATE, string='Status',track_visibility='onchange')

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

                vals_line= {
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

                        vals_line= {
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
        if self.invoice_id.user_id.id == self.env.uid or \
        self.invoice_id.user_id.employee_id.parent_id.user_id.id == self.env.uid or \
        self.env.uid in [x.id for x in self.invoice_id.delegate_user_id] :
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
    hdfc_default= fields.Boolean('HDFC Default')
    hsbc_default= fields.Boolean('HSBC Default')
    name= fields.Char('Name')
    value= fields.Char('Value')
    company_id = fields.Many2one('res.company', string='Company')
    ad_org = fields.Many2one('org.master', string='Organisation',  domain="[('company_id','=',company_id)]" )


    @api.model
    @api.multi
    def process_update_erp_c_bankaccount_queue(self):

        conn_pg = None
        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
        if config_id:

            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
                 password=config_id.password, host= config_id.ip_address,port=config_id.port)
                pg_cursor = conn_pg.cursor()

                query = "select c_bankaccount_id,ad_client_id,ad_org_id,c_bank_id,bankaccounttype,accountno,name,value \
                        from adempiere.C_BankAccount where isactive = 'Y'   " 

                pg_cursor.execute(query)
                records = pg_cursor.fetchall()
               
                if len(records) > 0:
                    portal_c_bankaccount_id = [x.c_bankaccount_id for x in self.env['erp.bank.master'].search([])]

                    for record in records:
                        c_bankaccount_id = (str(record[0]).split('.'))[0]
                        
                        if c_bankaccount_id not in portal_c_bankaccount_id:
                            ad_client_id = (str(record[1]).split('.'))[0]
                            company_id = self.env['res.company'].search([('ad_client_id','=',ad_client_id)], limit=1)

                            vals_line = {
                                'active': True,
                                'c_bankaccount_id':c_bankaccount_id,
                                'ad_client_id':ad_client_id,
                                'ad_org_id':(str(record[2]).split('.'))[0],
                                'c_bank_id':(str(record[3]).split('.'))[0],
                                'bankaccounttype':record[4],
                                'accountno':(str(record[5]).split('.'))[0],
                                'name':record[6],
                                'value':record[7],
                                'company_id': company_id.id,
                            }
                       
                            self.env['erp.bank.master'].create(vals_line)
                            print "----------- Bank Created in CRM  --------" , record[6]


            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '#----------- Error %s' % e        

            finally:
                if conn_pg: conn_pg.close()
                print "#--------------Select --44444444--Finally----------------------#" , pg_cursor



class ErpRepresentativeApprover(models.Model):
    _name = "erp.representative.approver"
    _order= "sequence"

    
    name = fields.Char(string='Name')
    owner_id = fields.Many2one('res.users', string='Representative')
    sequence = fields.Integer(string='Representative Sequence')
    company_id = fields.Many2one('res.company', string='Company', index=True, 
        default=lambda self: self.env.user.company_id.id)
    salesrep_id= fields.Char('Representative ID')
    hierarchy_bool= fields.Boolean(string='Hierarchy Present?')
    line_ids = fields.One2many('erp.representative.matrix', 'approver_id', string="Lines")

    @api.onchange('owner_id')
    def onchange_owner_id(self):
        if self.owner_id : self.name = self.owner_id.name

    @api.model
    def create(self, vals):
        result = super(ErpRepresentativeApprover, self).create(vals)
        result.sequence = self.env['erp.representative.approver'].search([])[-1].sequence + 1
        return result

    @api.multi
    def unlink(self):
        for order in self:
            if self.env.uid != 1 or not self.user_has_groups('sales_meet.group_it_user'):
                raise UserError(_('Only Admin or IT User can delete records'))
        return super(ErpRepresentativeApprover, self).unlink()


class ErpRepresentativeMatrix(models.Model):
    _name = "erp.representative.matrix"
    _description="Representative Matrix"

    name = fields.Char(string='Matrix')
    approver_id = fields.Many2one('erp.representative.approver', string="Approver")
    user_id = fields.Many2one('res.users', string='User', copy=False , index=True)
    min_amt = fields.Float(string="Min", digits=(16,3))
    max_amt = fields.Float(string="Max", digits=(16,3))