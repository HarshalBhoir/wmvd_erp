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

# idempiere_url="http://35.200.227.4/ADInterface/services/compositeInterface"
# idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
idempiere_url="https://erpnew.wmvd.live/ADInterface/services/compositeInterface?wsdl"
headers = {'content-type': 'text/xml'}


class bank_receipt(models.Model):
    _name = "bank.receipt"
    _description=" Receipt to Bank"
    _inherit = 'mail.thread'
    _order    = 'id desc'

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


    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_('You can only delete Draft Entries'))
        return super(bank_receipt, self).unlink()


    name = fields.Char('Name', store=True)
    config_id = fields.Many2one('external.db.configuration', string='Database', track_visibility='onchange' , default=_get_config)
    note = fields.Text('Text', track_visibility='onchange')
    state = fields.Selection([('draft', 'Draft'),
                             ('generated_invoice_template', 'Template Generated'), 
                             ('synced', 'Synced'),
                             ('erp_posted', 'Posted'), 
                             ], string='Status',track_visibility='onchange', default='draft')


    import_invoice_lines_one2many = fields.One2many('wp.invoice.lines','invoice_id',string="Invoice Details" )
        
    date = fields.Date(string="Date", default=lambda self: fields.Datetime.now())
    employee_id = fields.Many2one('hr.employee', string="Employee")
    completed = fields.Boolean("Completed")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    ad_org_id = fields.Many2one('org.master', string='Organisation',  domain="[('company_id','=',company_id)]" )
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)

    output_file = fields.Binary('Prepared file', filters='.xls', attachment=True)
    export_file = fields.Char(string="Export")

    partner_name = fields.Char('Partner Name')
    bank_referenceno = fields.Char('Bank Reference No')
    partner_id = fields.Many2one('res.partner', string="Partner" ,domain="[('company_id','=',company_id)]")

    condition = fields.Selection([
        ('invoice', 'Invoice'),
        ('receipt', 'receipt')], string='Condition')
    erp_bank_id = fields.Many2one('erp.bank.master', string='Bank Account',  domain="[('company_id','=',company_id)]" )
    filter_rep_bool = fields.Boolean('Filter Rep Generated' , default=False)

    amount_total = fields.Float(string='Total', store=True)
    can_edit_name = fields.Boolean(compute='_compute_can_edit_name')


    @api.multi
    def add_lines(self):
        todaydate = "{:%Y-%m-%d}".format(datetime.now())

        receipt_name = self.partner_id.name + ' (' + todaydate + ')'

        # Decode the file data
        if self.state == 'draft':
            wb = open_workbook(file_contents = base64.decodestring(self.output_file))

            sheet = wb.sheets()[0]
            for s in wb.sheets():
                values = []
                for row in range(1,s.nrows):
                    val = {}
                    col_value = []
                    for col in range(s.ncols):
                        value  = (s.cell(row,col).value)
                        col_value.append(value)


                    print "kkkkkkkkkdddddddddddddddddddddddddd" , col_value[2]

                    inv_date = dateutil.parser.parse(col_value[2]).strftime("%Y-%m-%d")
                    posting_date = dateutil.parser.parse(col_value[4]).strftime("%Y-%m-%d")
                    due_date = dateutil.parser.parse(col_value[5]).strftime("%Y-%m-%d")
                  
                    # val['particlulars'] = values['documentno']
                    val['reference'] = col_value[1]
                    val['invoice_date'] = inv_date
                    val['business_place'] = col_value[3]
                    val['posting_date'] = posting_date
                    val['due_date'] = due_date
                    val['amount'] = abs(float(col_value[6]))
                    val['invoice_id'] = self.id

                    self.name = receipt_name
                    self.state = 'generated_invoice_template'
                    
                    invoice_lines = self.import_invoice_lines_one2many.sudo().create(val)


    @api.multi
    def sync_invoices(self):
        conn_pg = None
        
        if not self.config_id:
            print " No Records Found   iiiiiiiiiiiiiiiiiiiiiiiiiii"
            raise UserError(" DB Connection not set / Disconnected " )

        else:
            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, password=self.config_id.password, 
                    host= self.config_id.ip_address, port=self.config_id.port)
                pg_cursor = conn_pg.cursor()
                if self.company_id:
                    for res in self.import_invoice_lines_one2many:

                        pg_cursor.execute("select description, documentno,c_invoice_id from adempiere.c_invoice \
                    where poreference = %s and ad_client_id = %s and issotrx = 'Y' " ,(res.reference,self.company_id.ad_client_id))

                        entry_id = pg_cursor.fetchall()

                        if entry_id == []:
                            # raise UserError(" No Records Found " )
                            # pass
                            res.documentno = 'Invoice Not Found'
                            res.notfound_bool= True

                        for record in entry_id:
                            res.description = record[0]
                            res.documentno = record[1]
                            res.c_invoice_id = record[2]

                self.state = 'synced'
                    
            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '#-------------------Except ---Error %s' % e        

            finally:
                if conn_pg: conn_pg.close()
                print "#--------------Select ----Finally----------------------#"


                    

    @api.multi
    def generate_filter_invoice_report(self):

        file = StringIO()
        
        self.ensure_one()
        status = receipt_no = ''
        name = 'Filtered Invoices' + '(' + str(date.today()) + ')'

        order_list = []
        second_heading = approval_status = ''
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Filtered INVOICE')
        fp = StringIO()
        row_index = 0

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
            if res and not res.notfound_bool :
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
    def generate_receipt_webservice(self):
        totalamt = 0.0
        vals = []
        documentno = documentno_log = ''
        line_body = body = upper_body  = receipt_body = lower_body = """ """

        import_invoice_lines = self.import_invoice_lines_one2many.search([("invoice_id","=",self.id),("notfound_bool","=",False)])

        if  len(import_invoice_lines) < 1:
            raise ValidationError(_('No Records Selected'))

        user_ids = self.env['wp.erp.credentials'].search([("wp_user_id","=",self.env.uid),("company_id","=",self.company_id.id)])

        if len(user_ids) < 1:
            raise ValidationError(_("User's ERP Credentials not found. Kindly Contact IT Helpdesk"))

        for res in import_invoice_lines:
            totalamt += res.amount

        # daymonth = datetime.today().strftime( "%Y-%m-%d 00:00:00")
        daymonth = self.date + ' 00:00:00'

        C_BankAccount_ID = self.erp_bank_id.c_bankaccount_id
        C_BPartner_ID = self.partner_id.c_bpartner_id

        paymt_description = "AMOUNT RECEIVED FROM "+ self.partner_id.name + " Ref no " + self.bank_referenceno
        
        if self.company_id.ad_client_id == '1000000':
            C_DocType_ID = 1000008
        elif self.company_id.ad_client_id == '1000001':
            C_DocType_ID = 1000055
        elif self.company_id.ad_client_id == '1000002':
            C_DocType_ID = 1000102
        elif self.company_id.ad_client_id == '1000003':
            C_DocType_ID = 1000149
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
                        <_0:serviceType>CreateCompleteReceipt</_0:serviceType>
                        """ % (user_ids.erp_user, user_ids.erp_pass, self.company_id.ad_client_id, user_ids.erp_roleid )


        receipt_body = """<_0:operations>
                           <_0:operation preCommit="false" postCommit="false">
                              <_0:TargetPort>createData</_0:TargetPort>
                              <_0:ModelCRUD>
                                 <_0:serviceType>CreateReceipt</_0:serviceType>
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
                                    <_0:field column="IsReceipt">
                                       <_0:val>Y</_0:val>
                                    </_0:field>
                                    <_0:field column="C_Currency_ID">
                                       <_0:val>304</_0:val>
                                    </_0:field>
                                 </_0:DataRow>
                              </_0:ModelCRUD>
                           </_0:operation>"""  % ( self.ad_org_id.ad_org_id ,C_BankAccount_ID, C_DocType_ID, 
                            daymonth, daymonth, C_BPartner_ID, totalamt, paymt_description)


        for line_rec in import_invoice_lines:

            line_body += """<_0:operation preCommit="false" postCommit="false">
                          <_0:TargetPort>createData</_0:TargetPort>
                          <_0:ModelCRUD>
                             <_0:serviceType>ReceiptAllocationLines</_0:serviceType>
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
                        abs(line_rec.amount), abs(line_rec.amount) )


        lower_body = """<_0:operation preCommit="true" postCommit="true">
                              <_0:TargetPort>setDocAction</_0:TargetPort>
                              <_0:ModelSetDocAction>
                                 <_0:serviceType>CompleteReceipt</_0:serviceType>
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

        body = upper_body + receipt_body + line_body + lower_body

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


        write_data = import_invoice_lines.write({'log': documentno_log})

                       

class bank_payment_lines(models.Model):
    _name = "wp.invoice.lines"
    _description="Invoice lines"

    name = fields.Char('Name')
    invoice_id = fields.Many2one('bank.receipt', string='Receipt', track_visibility='onchange')

    description = fields.Char('Description')
    documentno = fields.Char('Document No')
    check_invoice = fields.Boolean('Check')
    user_id = fields.Many2one('res.users', string='Owner')
    c_invoice_id = fields.Char('Invoice ID')

    particlulars = fields.Char('Particlulars')
    reference = fields.Char('Invoice/reference')
    invoice_date = fields.Date('Invoice date')
    business_place = fields.Char('Business place')
    posting_date = fields.Date('Posting date')
    due_date = fields.Date('Due date')
    amount = fields.Float('Amount')
    currency = fields.Char('Currency')
    log = fields.Char('Log')
    notfound_bool =  fields.Boolean('Not Found', default=False)