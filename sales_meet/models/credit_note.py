#!/usr/bin/env bash

from odoo import _, models, fields, api, tools, registry, SUPERUSER_ID
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _
from odoo.exceptions import UserError, Warning, ValidationError
import time
import psycopg2
import csv
from cStringIO import StringIO
import xlwt
import re
import base64
from odoo import http
from werkzeug import url_encode
from collections import Counter
import requests
import cStringIO
from time import gmtime, strftime

# idempiere_url="http://35.200.227.4/ADInterface/services/compositeInterface"
# idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
idempiere_url="https://erpnew.wmvd.live/ADInterface/services/compositeInterface?wsdl"
headers = {'content-type': 'text/xml'}

# http://192.168.1.183:8080/jasperserver/flow.html?_flowId=viewReportFlow&_flowId=viewReportFlow&
# ParentFolderUri=%2Freports%2Finteractive&reportUnit=%2Freports%2Finteractive%2FInvoice_Report&standAlone=true
# &j_username=jasperadmin&j_password=jasperadmin

CN_TYPE = [
        ('Annual Scheme','Annual Scheme'),
        ('Cash Discount','Cash Discount'),
        ('Damage Discount','Damage Discount'),
        ('Damage Discount Against Quality Issue','Damage Discount Against Quality Issue'),
        ('Half Yearly Scheme','Half Yearly Scheme'),
        ('Others','Others'),
        ('Quantity Discount','Quantity Discount'),
        ('Quarterly Scheme','Quarterly Scheme'),
        ('Retailer Scheme','Retailer Scheme'),
        ('Special Support Scheme','Special Support Scheme'),
        ('Spot Offer','Spot Offer'),
        ('Tokens / Scratch Card','Tokens / Scratch Card'),
        ('Transportation Charges','Transportation Charges'),
    ]

todaydate = "{:%d-%b-%y}".format(datetime.now())

class credit_note(models.Model):
    _name = 'credit.note'
    _description = "Credit Note"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    # _inherit = 'mail.thread'
    _order    = 'id desc'

    @api.multi
    def _get_config(self):
        config = self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1)
        if config:
            config_id = config.id
        else:
            config = self.env['external.db.configuration'].search([('id', '!=',0)], limit=1)
            config_id = config.id
        return config_id

    
    name = fields.Char(string = "CN No.")
    partner_id = fields.Many2one('res.partner',string="Customer" )
    date_start = fields.Date(string="From Date" , default=lambda self: fields.datetime.now())
    date_end = fields.Date(string="To Date" , default=lambda self: fields.datetime.now())
    config_id = fields.Many2one('external.db.configuration', string='Database', default=_get_config )
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid, track_visibility='always')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Generated'),
        ('import_template', 'Template Imported'),
        ('approval_sent', 'Approval Sent'),
        ('approved', 'Approved'),
        ('cancel', 'Rejected'),
        ('posted', 'Posted'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('credit.note'))
    credit_note_id = fields.Integer('CN Id')    
    credit_note_line_one2many = fields.One2many('credit.note.line','credit_note_id',string="Credit Note Line")
    cn_data = fields.Char('Name', size=256)
    file_name = fields.Binary('CN Export', readonly=True)
    condition = fields.Selection([
        ('normal', 'Normal'),
        ('token', 'Token')], string='Condition')
    report_generated = fields.Boolean("Report", default=False)
    check_lines = fields.Boolean(string = "", nolabel="1" , default=False)
    clubbed_bool = fields.Boolean(string = "Clubbed ?", default=False)
    new_year_bool = fields.Boolean('New Server' , default=False)
    dateordered2 = fields.Date(string='Exp Period From', default=lambda self: fields.datetime.now())
    dateordered3 = fields.Date(string='Exp Period To', default=lambda self: fields.datetime.now())
    user2_id = fields.Many2one('wp.c.elementvalue', string='Functions' ,  
        domain="[('company_id','=',company_id),('c_element_id','=','1000013')]")
    cn_type= fields.Selection(CN_TYPE, string='CN Type',track_visibility='onchange',
                                default='Tokens / Scratch Card')

    cn_csv_data = fields.Char('Name', size=256)
    cn_file_name = fields.Binary('CN Import', readonly=True)
    delimeter = fields.Char('Delimeter', default=',')
    scan_type = fields.Selection([
        ('Mobile', 'Mobile'),
        ('Token Scanner', 'Token Scanner')], string='Scan Type')

    @api.multi
    def approve_credit_note_manager(self):
        self.sudo().send_user_mail()
        self.state = 'approved'

    @api.constrains('date_start','date_end')
    def constraints_check(self):
        if not self.date_start and  not self.date_end or self.date_start > self.date_end:
            raise UserError("Please select a valid date range")

    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and self.env.uid != 1:
                raise UserError(_('You can only delete Draft Entries'))
        return super(credit_note, self).unlink()


    @api.multi
    def _sales_unset(self):
        self.env['credit.note.line'].search([('credit_note_id', 'in', self.ids)]).unlink()
        
        
    @api.multi
    def select_all(self):
        for record in self.credit_note_line_one2many:
            if record.state == 'approved':
                record.state = 'draft'
                record.check_invoice = False
            else:
                record.state = 'approved'
                record.check_invoice = True

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


    @api.multi
    def refuse_credit_note(self):
        subject = "Credit Note - Refused"
        full_body = (_("Credit Note %s has been refused.<br/><ul class=o_timeline_tracking_value_list></ul>") % (self.name))

        cn_user = self.env['credit.note.user'].search([("id","!=",0)])
        if len(cn_user) < 1:
            raise ValidationError("CN Config doesnot have any User. Configure the Approvers and Users ")

        support_email = [x.user.email for x in cn_user]
        email_to = ",".join(support_email)
        email_from = self.env.user.email

        self.send_generic_mail(subject, full_body, email_from, email_to)
        self.state='cancel'


    @api.multi
    def add_lines(self):
        # """Load credit_note Line data from the CSV file."""
        charge_obj = self.env['credit.note.charge']
        org_obj = self.env['org.master']
        partner_ids = self.env['res.partner']
        cn_name = 'Normal Credit Note (' + todaydate + ')'

        # Decode the file data
        if self.state == 'draft':
            data = base64.b64decode(self.cn_file_name)
            file_input = cStringIO.StringIO(data)
            file_input.seek(0)
            reader_info = []
            if self.delimeter:
                delimeter = str(self.delimeter)
            else:
                delimeter = ','
            reader = csv.reader(file_input, delimiter=delimeter,lineterminator='\r\n')
            try:
                reader_info.extend(reader)
            except Exception:
                reader_info.extend(reader)
                raise Warning(_("Not a valid file!"))
            keys = reader_info[0]
            # check if keys exist
            if not isinstance(keys, list) or ('Organisation' not in keys or
                                              'Code' not in keys or
                                              'Charge' not in keys or
                                              'Description' not in keys or
                                              'Amount' not in keys ):
                raise Warning(
                    _("'Organisation' or 'Code' or 'Charge' or 'Description'  keys not found"))
            del reader_info[0]
            values = {}
            
            for i in range(len(reader_info)):
                val = {}
                field = reader_info[i]
                values = dict(zip(keys, field))
    
                charge_list = charge_obj.search([('name', '=',values['Charge'])], limit= 1)
                if charge_list:
                    val['charge_id'] = charge_list[0].id
                    val['charge_name'] = charge_list[0].name
                

                org_list = org_obj.search([('name', '=',values['Organisation'])], limit= 1)
                if org_list:
                    val['ad_org_id'] = org_list[0].id
                    val['ad_org'] = org_list[0].name

                partner_list = partner_ids.search([('bp_code', '=',values['Code'])], limit= 1)
                if partner_list:
                    val['partner_id'] = partner_list[0].id
                    val['beneficiary_name'] = partner_list[0].name

                
                val['beneficiary_code'] = values['Code']
                val['description'] = values['Description']
                val['totalamt'] = values['Amount']
                val['value_date'] = date.today()
                val['company_id'] = self.company_id.id
                # val['check_lines'] = True
     
                val['credit_note_id'] = self.id

                val['dateordered2'] = self.dateordered2
                val['dateordered3'] = self.dateordered3
                val['cn_type'] = self.cn_type
                val['user2_id'] = self.user2_id.id

                self.name = cn_name
                self.check_lines = True

                credit_lines = self.credit_note_line_one2many.sudo().create(val)
                
        else:
            raise Warning(_("Credit Note can be imported only in 'Draft' Stage"))
    

    @api.multi
    def send_user_mail(self):
        amnt = totalcn = 0.0
        body = """ """
        line_html = subject = ""
        main_id = self.id
        config_mail = self.env['credit.note.config'].search([("id","!=",0)])
        email_from =  config_mail.sales_support_mail

        for l in self.credit_note_line_one2many:
            if l.check_invoice:
                start_date = datetime.strptime(str(((l.value_date).split())[0]), 
                    tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

                line_html += """
                <tr>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                </tr>
                """ % (start_date , l.beneficiary_name, l.charge_name, l.description, l.totalamt)

                totalcn += l.totalamt

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <h3>Following are the details as Below Listed. </h3>

            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Date</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Beneficiary</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Charge</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Description</th>             
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Total Amt</th>
                    </tr>
                    %s
                </tbody>
            </table>
            <br/>

            <h2>Total Credit Amount : %s </h2>
            <br/>

        """ % (line_html, totalcn)

        subject = "[Approval] Credit Note - ( %s )"  % (todaydate)
        full_body = body

        cn_user = self.env['credit.note.user'].search([("id","!=",0)])

        if len(cn_user) < 1:
            raise ValidationError("Approval Config doesnot have any User. Configure the Approvers and Users ")

        support_email = [x.user.email for x in cn_user]
        email_to = ",".join(support_email)

        self.send_generic_mail(subject, full_body, email_from, email_to)


    @api.multi
    def send_approval(self):
        amnt = totalcn = 0.0
        body = """ """
        line_html = subject = ""
        main_id = self.id
        email_from = self.env.user.email

        credit_note_line = self.credit_note_line_one2many.search([('credit_note_id', '=', self.id),
                                                                    ('check_invoice', '=', True)])

        if  len(credit_note_line) < 1:
            raise ValidationError(_('No Records Selected'))

        for l in credit_note_line:
            if l.check_invoice:
                start_date = datetime.strptime(str(((l.value_date).split())[0]), 
                    tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

                line_html += """
                <tr>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                </tr>
                """ % (start_date, l.beneficiary_name, l.charge_name, l.description, l.totalamt)

                totalcn += l.totalamt

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <h3>Following are the details as Below Listed. </h3>

            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                         <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Date</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Beneficiary</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Charge</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Description</th>             
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Total Amt</th>
                    </tr>                      
                    %s
                </tbody>
            </table>
            <br/>

            <h2>Total Credit Amount : %s </h2>

            <br/>

        """ % (line_html, totalcn)

        subject = "Request for Credit Note Approval - ( %s )"  % (todaydate)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        approver = self.env['credit.note.approver'].search([("id","!=",0)])

        if len(approver) < 1:
            raise ValidationError("CN Config doesnot have any Approver. Configure the Approvers and Users ")

        approve_url = base_url + '/creditnote?%s' % (url_encode({
                'model': self._name,
                'credit_note_id': self,
                'res_id': self.id,
                'action': 'approve_credit_note_manager',
            }))
        reject_url = base_url + '/creditnote?%s' % (url_encode({
                'model': self._name,
                'credit_note_id': self,
                'res_id': self.id,
                'action': 'refuse_credit_note',
            }))

        report_check = base_url + '/web#%s' % (url_encode({
            'model': self._name,
            'view_type': 'form',
            'id': main_id,
        }))

        approver_email = [x.approver.email for x in approver]
        email_to = ",".join(approver_email)
      

        full_body = body + """<br/>
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
                            border: 1px solid #337ab7; margin-right: 10px;">Selective Approve/Reject</a>
                    </td>

                </tr>
            </tbody>
        </table>
        """ % (approve_url, reject_url, report_check)

        self.send_generic_mail(subject, full_body, email_from, email_to)
        self.state='approval_sent'
            
            
    @api.multi
    def update_values(self):
        conn_pg = None

        if not self.config_id:
            raise UserError(" DB Connection not set / Disconnected " )

        else:

            ad_client_id=self.company_id.ad_client_id

            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
                    password=self.config_id.password, host= self.config_id.ip_address,port= self.config_id.port)
                pg_cursor = conn_pg.cursor()

                if self.company_id:
                    for record in self.credit_note_line_one2many:
                        query = " select c_bpartner_id from adempiere.C_BPartner where  value = '%s' \
                        and ad_client_id= %s " % (record.beneficiary_code,self.company_id.ad_client_id)

                        pg_cursor.execute(query)
                        record_query = pg_cursor.fetchall()

                        if record_query != []:
                            for rec in record_query:
                                record.c_bpartner_id2 = (str(rec[0]).split('.'))[0]
                                self.state = 'done'

                        else:
                            raise ValidationError(_('Customer Code Not Found %s' % (record.beneficiary_code)))


            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print '#-------------------Except----------------------#Error %s' % e
                    conn_pg.rollback()

            finally:
                if conn_pg:
                    conn_pg.close()
                    print "#--------------Select --44444444--Finally----------------------#" , pg_cursor




    @api.multi
    def search_qr_invoices(self):
        order_lines = []
        if self.scan_type == 'Mobile':

            qr_records =self.env['barcode.marketing.check'].sudo().search([
                                                            ("date","<=",self.date_end),
                                                            ("date",">=",self.date_start),
                                                            ("mobile_bool","=", True),
                                                            ("imported","=", False),
                                                            ("state","=", "update")])
        else:

            qr_records =self.env['barcode.marketing.check'].sudo().search([
                                                            ("date","<=",self.date_end),
                                                            ("date",">=",self.date_start),
                                                            ("imported","=", False),
                                                            ("mobile_bool","=", False),
                                                            ("state","=", "update")])

        if  len(qr_records) < 1:
            raise ValidationError(_('No Records Found for below dates'))

        todaydate = "{:%Y-%m-%d}".format(datetime.now())

        self.name = 'Coupon Credit Note (' + todaydate + ')'

        for rec in qr_records:
            desc = str(rec.amount) + ' x ' + \
                        str((rec.count_accepted if rec.count_accepted else 0) + \
                        (rec.manual_count if rec.manual_count else 0) )   +' = ' + \
                        str(rec.total_amount) + ' /- '

            if rec.charge == 'tr':
                description = 'Token ' + desc
                charge_name =  'Token Reimbursment'

            elif rec.charge == 'scd':
                description = 'Scratch Coupon ' + desc
                charge_name =  'Scratch Card Discount'
            else:
                description = charge_name = ''

            order_lines.append((0, 0, {
                        'credit_note_id':self.id,
                        'value_date':todaydate,
                        'description':description,
                        'transaction_amount':rec.total_amount,
                        'partner_id':rec.partner_id.id,
                        'beneficiary_name':rec.partner_id.name,
                        'totalamt' : rec.total_amount,
                        'customercode':rec.partner_id.bp_code if rec.partner_id.bp_code else '',
                        'charge_name' : charge_name,
                        'company_id':self.company_id.id,
                        'dateordered2': self.dateordered2,
                        'dateordered3': self.dateordered3,
                        'cn_type': self.cn_type,
                        'user2_id': self.user2_id.id,
                        'barcode_check_id': rec.id,
                        'barcode_scan_id': rec.id,
                        
                    }))

        self.credit_note_line_one2many = order_lines

        if self.scan_type == 'Mobile':
            self.state='approved'
        else:
            self.state='done'

    @api.multi
    def cn_raised_mail(self,email_to=False):
        body = """ """
        line_html = subject = ""
        main_id = self.id

        config_mail = self.env['credit.note.config'].search([("id","!=",0)])
        email_from =  config_mail.sales_support_mail

        credit_note_line_filter = self.credit_note_line_one2many.sudo().search([("credit_note_id","=",self.id),
                                                                                ("check_invoice","=",True)])

        if  len(credit_note_line_filter) < 1:
            raise ValidationError(_('No Records Selected or No approved expense detected'))

        for rec in credit_note_line_filter:
            email_to = rec.barcode_scan_id.user_id.email
            subject = "CN Raised against Coupon Codes Scanned - %s"  % (rec.partner_id.name)

            main_body = """
                    <p>Hi Team,</p><br/>                    
                    <p>Credit Note is raised against the Coupon  <b>%s</b> which is worth Rs. <b>%s</b></p><br/>
                """ % ( rec.barcode_scan_id.name, rec.totalamt )

            full_body = main_body
          
            self.send_generic_mail(subject, full_body, email_from, email_to)

            if rec.barcode_scan_id.state == 'update':
                rec.barcode_scan_id.state = 'cn_raised'
            print "------------------ credit.note ----------- Mail Sent to" , email_to
            
    @api.multi
    def credit_note_report(self):

        file = StringIO()
        today_date = str(date.today())
        self.ensure_one()

        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Credit Note Report')
        fp = StringIO()
        row_index = 0

        base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')

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

        # Headers
        header_fields = ['AD_Org_ID[Name]',
                        'C_DocType_ID[Name]',
                        'IsSOTrx',
                        'Description',
                        'SalesRep_ID[Name]',
                        'C_Currency_ID',
                        'M_PriceList_ID[Name]',
                        'C_PaymentTerm_ID[Value]',
                        'C_BPartner_ID[Value]',
                        'C_Region_ID[Name]',
                        'CountryCode',
                        'C_Country_ID[Name]',
                        'DateInvoiced',
                        'DateAcct',
                        'C_Charge_ID[Name]',
                        'QtyOrdered',
                        'PriceActual',
                        'LineDescription',
                        'C_Tax_ID[Name]',
                        ]
        # row_index += 1
     
        for index, value in enumerate(header_fields):
            worksheet.write(row_index, index, value, base_style)
        row_index += 1

        credit_note_line = self.credit_note_line_one2many.search([('credit_note_id', '=', self.id),
                                                                    ('check_invoice', '=', True)])

        if  len(credit_note_line) < 1:
            raise ValidationError(_('No Records Selected'))


        for res in credit_note_line:
            if not res.ad_org_id :
                raise ValidationError(_('Organisation not Selected for approved CN'))
            if not res.charge_name:
                raise ValidationError(_('Charge not Selected for approved CN'))


            worksheet.write(row_index,0,res.ad_org_id.name or '', base_style )
            worksheet.write(row_index,1,'AR Credit Memo', base_style )
            worksheet.write(row_index,2,'Y', base_style )
            worksheet.write(row_index,3,res.description or '', base_style )
            worksheet.write(row_index,4,'Raju Ghagare', base_style )
            worksheet.write(row_index,5,'304', base_style )
            worksheet.write(row_index,6,'Purchase PL', base_style )
            worksheet.write(row_index,7,'Immediate', base_style )
            worksheet.write(row_index,8,res.customercode or '', base_style )
            worksheet.write(row_index,9,'OR', base_style )
            worksheet.write(row_index,10,'N', base_style )
            worksheet.write(row_index,11,'India', base_style )
            worksheet.write(row_index,12,today_date or '', base_style )
            worksheet.write(row_index,13,today_date or '', base_style )
            worksheet.write(row_index,14,res.charge_name or '', base_style )
            worksheet.write(row_index,15,'1', base_style )
            worksheet.write(row_index,16,res.totalamt or '', base_style )
            worksheet.write(row_index,17,res.description or '', base_style )
            worksheet.write(row_index,18,'Tax Exempt', base_style )

        
            row_index += 1

        row_index +=1
        workbook.save(fp)

        out = base64.encodestring(fp.getvalue())
        self.report_generated = True

        self.write({'file_name': out,'cn_data':self.name+'.xls'})


    @api.multi
    def db_configuration(self):
        conn_pg = None
        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
        if config_id:

            print "#-------------Select --TRY----------------------#"
            conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, 
                password=config_id.password, host= config_id.ip_address,port=config_id.port)
            pg_cursor = conn_pg.cursor()

        return pg_cursor

    # Normal CN Webservice

    @api.multi
    def generate_csv_cn_webservice(self):
        filtered_list = []
        filter_dict = {}
        upper_body  = """ """
        vals = []
        documentno = crm_description = C_Tax_ID = documentno_log = crm_description2 = ''
        commit_bool = False

        credit_note_line_filter = self.credit_note_line_one2many.sudo().search([("credit_note_id","=",self.id),
                                                                                ("check_invoice","=",True)])

        if  len(credit_note_line_filter) < 1:
            raise ValidationError(_('No Records Selected or No approved expense detected'))

        partner_ids = list(set([ x.partner_id.c_bpartner_id for x in credit_note_line_filter if x.partner_id.c_bpartner_id]))

        pg_cursor = self.db_configuration()

        user_ids = self.env['wp.erp.credentials'].sudo().search([("wp_user_id","=",self.env.uid),
                                                                 ("company_id","=",self.company_id.id)])

        if len(user_ids) < 1:
            raise ValidationError(_("User's ERP Credentials not found. Kindly Contact IT Helpdesk"))


        upper_body = """<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:_0="http://idempiere.org/ADInterface/1_0">
                    <soapenv:Header />
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
                                <_0:serviceType>CreateCompleteCreditNote</_0:serviceType>
                """ % (user_ids.erp_user, user_ids.erp_pass, self.company_id.ad_client_id, user_ids.erp_roleid )

        # if self.clubbed_bool:
        for rec in credit_note_line_filter:

            total_amount = rec.totalamt
            crm_description =  (rec.description).encode('ascii', 'ignore').decode('ascii')
            C_Charge_ID = rec.charge_id.c_charge_id
            cn_on_product = rec.cn_on_product.m_product_id

            if rec.c_bpartner_id2:
                partner = c_bpartner_id = rec.c_bpartner_id2 
            else:
                raise ValidationError(_("Employee ID not found. Kindly Contact IT Helpdesk"))
            filter_id = rec.id
            org_id = rec.ad_org_id.ad_org_id
            CN_Type = rec.cn_type
            CNToPeriod = rec.c_period_id.c_period_id
            CNFromPeriod = rec.cnfromperiod.c_period_id
            User1_ID = rec.user1_id.c_elementvalue_id
            User2_ID = rec.user2_id.c_elementvalue_id

            commit_bool = False
            
            query = "select LCO_TaxPayerType_ID from adempiere.C_BPartner where  C_BPartner_ID = %s and \
            ad_client_id= %s  " % (c_bpartner_id,self.company_id.ad_client_id)

            pg_cursor.execute(query)
            record_query = pg_cursor.fetchall()

            if record_query[0][0] == None:
                print "------------------------------ commit_bool ----------------------" , record_query
                commit_bool = True


            line_body = body = payment_body = lower_body = """ """      
            
            # daymonth = datetime.today().strftime( "%Y-%m-%d 00:00:00")
            # daynow = datetime.now()
            daynow  = datetime.now().strftime( "%y%m%d%H%M%S")
            daymonth = self.date_start + ' 00:00:00'
            dateordered2 = self.dateordered2 + ' 00:00:00'
            dateordered3 = self.dateordered3 + ' 00:00:00'

            if self.company_id.ad_client_id == '1000000':
                C_DocType_ID = C_DocTypeTarget_ID = 1000004
                C_Tax_ID = 1000193
                M_PriceList_ID = 1000014
                
            elif self.company_id.ad_client_id == '1000001':
                C_DocType_ID = 1000056
            elif self.company_id.ad_client_id == '1000002':
                C_DocType_ID = 1000103
            elif self.company_id.ad_client_id == '1000003':
                C_DocType_ID = 1000150
            else:
                raise UserError(" Select proper company " )


            payment_body = """<_0:serviceType>CreateCompleteCreditNote</_0:serviceType>
                <_0:operations>
                    <_0:operation preCommit="false" postCommit="false">
                        <_0:TargetPort>createData</_0:TargetPort>
                        <_0:ModelCRUD>
                            <_0:serviceType>CreateCreditNote</_0:serviceType>
                            <_0:TableName>C_Invoice</_0:TableName>
                            <_0:DataRow>
                                <!--Zero or more repetitions:-->
                                <_0:field column="AD_Org_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_DocTypeTarget_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_DocType_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="DateInvoiced">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="DateAcct">
                                    <_0:val>%s</_0:val>
                                </_0:field>

                                <_0:field column="CN_Type">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="DateOrdered2">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="DateOrdered3">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="User1_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="User2_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_BPartner_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>

                                <_0:field column="Description">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_Currency_ID">
                                    <_0:val>304</_0:val>
                                </_0:field>
                                <_0:field column="IsSOTrx">
                                    <_0:val>Y</_0:val>
                                </_0:field>
                                <_0:field column="POReference">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                            </_0:DataRow>
                        </_0:ModelCRUD>
                    </_0:operation>"""  % ( org_id ,C_DocTypeTarget_ID, C_DocType_ID, daymonth, daymonth, 
                        CN_Type, dateordered2,dateordered3, User1_ID, User2_ID , c_bpartner_id,crm_description,daynow)


            line_body += """<_0:operation preCommit="false" postCommit="false">
                        <_0:TargetPort>createData</_0:TargetPort>
                        <_0:ModelCRUD>
                            <_0:serviceType>CreditNoteLines</_0:serviceType>
                            <_0:TableName>C_InvoiceLine</_0:TableName>
                            <RecordID>0</RecordID>
                            <Action>createData</Action>
                            <_0:DataRow>
                                <!--Zero or more repetitions:-->
                                <_0:field column="AD_Org_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_Tax_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="PriceList">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="PriceActual">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="PriceEntered">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_Charge_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="CN_On_Product">
                                    <_0:val></_0:val>
                                </_0:field>
                                <_0:field column="QtyEntered">
                                    <_0:val>1.0000</_0:val>
                                </_0:field>
                                
                                <_0:field column="C_Invoice_ID">
                                    <_0:val>@C_Invoice.C_Invoice_ID</_0:val>
                                </_0:field>
                            </_0:DataRow>
                        </_0:ModelCRUD>
                    </_0:operation>"""  % ( org_id, C_Tax_ID,total_amount,total_amount,total_amount, C_Charge_ID)


            if commit_bool == True:
                lower_body = """
                                <_0:operation preCommit="true" postCommit="true">
                                        <_0:TargetPort>setDocAction</_0:TargetPort>
                                        <_0:ModelSetDocAction>
                                            <_0:serviceType>CompleteCreditNote</_0:serviceType>
                                            <_0:tableName>C_Invoice</_0:tableName>
                                            <_0:recordID>0</_0:recordID>
                                            <!--Optional:-->
                                            <_0:recordIDVariable>@C_Invoice.C_Invoice_ID</_0:recordIDVariable>
                                            <_0:docAction>CO</_0:docAction>
                                        </_0:ModelSetDocAction>
                                        <!--Optional:-->
                                    </_0:operation>
                                </_0:operations>
                            </_0:CompositeRequest>
                        </_0:compositeOperation>
                    </soapenv:Body>
                </soapenv:Envelope>"""

            else:
                print "#################### Generate Withdrawn Found ##### partner "
                lower_body = """
                                </_0:operations>
                            </_0:CompositeRequest>
                        </_0:compositeOperation>
                    </soapenv:Body>
                </soapenv:Envelope>"""

            body = upper_body + payment_body + line_body  + lower_body
            # print "ffffffffffffffffffffffffffffffffffffffffff" , body


            # if self.new_year_bool:
            #     idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
                
            # else:
            #     idempiere_url="http://35.200.227.4/ADInterface/services/compositeInterface"

            # idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
            idempiere_url="https://erpnew.wmvd.live/ADInterface/services/compositeInterface?wsdl"

            response = requests.post(idempiere_url,data=body,headers=headers)
            print response.content
            
            log = str(response.content)
            if log.find('DocumentNo') is not -1:
                documentno_log = log.split('column="DocumentNo" value="')[1].split('"></outputField>')[0]
                print "ssssssssssssssssssssssssss" , documentno_log , self.state
                self.state = 'posted'
                write_data = self.credit_note_line_one2many.search([('id', '=', filter_id)]).sudo().write(
                                        {'log': documentno_log})


            if log.find('UNMARSHAL_ERROR') is not -1:
                write_data = self.credit_note_line_one2many.search([('id', '=', filter_id)]).sudo().write(
                                        {'log': 'Manual Entry'})

            if log.find('IsRolledBack') is not -1:
                # documentno_log = 'error'
                # documentno_log = log.split('<Error>')[1].split('</Error>')[0]
                raise ValidationError("Error Occured is %s" % (log))


            if log.find('Invalid') is not -1:
                # documentno_log = log.split('<faultstring>')[1].split('</faultstring>')[0]
                raise ValidationError("Error Occured is %s" % (log))

       


    # Coupon Webservice
    @api.multi
    def generate_invoice_webservice(self):
        filtered_list = []
        filter_dict = {}
        vals = []
        documentno = C_Tax_ID = crm_description = crm_description2 = documentno_log =''
        commit_bool = False

        credit_note_line_filter = self.credit_note_line_one2many.sudo().search([
            ("credit_note_id","=",self.id),("check_invoice","=",True)])

        if  len(credit_note_line_filter) < 1:
            raise ValidationError(_('No Records Selected or No approved expense detected'))

        partner_ids = list(set([ x.partner_id.c_bpartner_id for x in credit_note_line_filter if x.partner_id.c_bpartner_id]))

        pg_cursor = self.db_configuration()

        user_ids = self.env['wp.erp.credentials'].sudo().search([
            ("wp_user_id","=",self.env.uid),("company_id","=",self.company_id.id)])

        if len(user_ids) < 1:
            raise ValidationError(_("User's ERP Credentials not found. Kindly Contact IT Helpdesk"))

        for rec in credit_note_line_filter:
            filtered_list.append((rec.partner_id,rec.charge_name))


        filtered_list3 = dict(Counter(filtered_list))

        # print "ffffffffffffffffff" , filtered_list3

        for beneficiary_name, value in filtered_list3.iteritems():
            crm_description = ''
            # print "lllllllllllllllllllllllll" , beneficiary_name, value
            total_amount = 0
            c_charge_id = beneficiary_name[1]
            partner_id = beneficiary_name[0].id
            for record in credit_note_line_filter :
                # if beneficiary_name[0].id == record.partner_id.id and c_charge_id == record.charge_name :
                if beneficiary_name[0].id == record.partner_id.id :
                    crm_description += record.description + ',  '
                    if c_charge_id == record.charge_name :
                
                        if value > 1:
                            total_amount += record.totalamt
                            
                        else:
                            total_amount = record.totalamt
                            # crm_description = record.description

                        if record.partner_id and record.partner_id.c_bpartner_id:
                            c_bpartner_id = record.partner_id.c_bpartner_id #(str(record.partner_id.c_bpartner_id).split('.'))[0]
                        else:
                            raise ValidationError(_("Partner ID not found. Kindly Contact IT Helpdesk"))
                        filter_id = record.id
                        org_id = record.ad_org_id.ad_org_id
                        CN_Type = record.cn_type
                        CNFromPeriod = record.cnfromperiod.c_period_id
                        CNToPeriod = record.c_period_id.c_period_id
                        User1_ID = record.user1_id.c_elementvalue_id
                        User2_ID = record.user2_id.c_elementvalue_id
                        cn_on_product = record.cn_on_product.m_product_id

            print "99999999999999999999999999999" , crm_description , total_amount

            new_list = (c_bpartner_id, abs(total_amount), c_charge_id, filter_id,crm_description,  org_id, CN_Type, 
                CNToPeriod, User1_ID, User2_ID,CNFromPeriod, cn_on_product)
            vals.append(new_list)


        for partner in partner_ids:
            commit_bool = False
            crm_description2 = ''

            query = " select LCO_TaxPayerType_ID from adempiere.C_BPartner where  C_BPartner_ID = %s " % (partner)

            pg_cursor.execute(query)
            record_query = pg_cursor.fetchall()

            if not record_query:
                partner_not_found = self.env['res.partner'].sudo().search([("c_bpartner_id","=",partner)])
                raise ValidationError("Partner %s - %s Not found in ERP. \
                    Contact Sales Support or IT for help." % (partner_not_found.bp_code or '',partner_not_found.name))

            if record_query[0][0] == None:
                # print "------------------------------ commit_bool ----------------------" , partner , record_query
                commit_bool = True

            for records in vals:
                if partner == records[0]:
                    crm_description2 = records[4]
                    org = records[5]
                    CN_Type = records[6]
                    CNToPeriod = records[7]
                    User1_ID = records[8]
                    User2_ID = records[9]
                    CNFromPeriod = records[10]


            line_body = body = upper_body  = payment_body = lower_body = """ """   

            daynow =  datetime.now().strftime( "%y%m%d%H%M%S")
            if self.scan_type == 'Mobile':
                daymonth = datetime.now() #"{:%Y-%M-%d}".format(datetime.now())
            else:
                daymonth = self.date_start + ' 00:00:00'
            dateordered2 = self.dateordered2 + ' 00:00:00'
            dateordered3 = self.dateordered3 + ' 00:00:00'

            if self.company_id.ad_client_id == '1000000':
                C_DocType_ID = C_DocTypeTarget_ID = 1000004
                C_Tax_ID = 1000193
                M_PriceList_ID = 1000014
                
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
                                <soapenv:Header />
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
                                            <_0:serviceType>CreateCompleteCreditNote</_0:serviceType>
                            """ % (user_ids.erp_user, user_ids.erp_pass, self.company_id.ad_client_id, user_ids.erp_roleid )


            payment_body = """<_0:serviceType>CreateCompleteCreditNote</_0:serviceType>
                <_0:operations>
                    <_0:operation preCommit="false" postCommit="false">
                        <_0:TargetPort>createData</_0:TargetPort>
                        <_0:ModelCRUD>
                            <_0:serviceType>CreateCreditNote</_0:serviceType>
                            <_0:TableName>C_Invoice</_0:TableName>
                            <_0:DataRow>
                                <!--Zero or more repetitions:-->
                                <_0:field column="AD_Org_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_DocTypeTarget_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_DocType_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="DateInvoiced">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="DateAcct">
                                    <_0:val>%s</_0:val>
                                </_0:field>

                                <_0:field column="CN_Type">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="DateOrdered2">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="DateOrdered3">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="User1_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="User2_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_BPartner_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>

                                <_0:field column="Description">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_Currency_ID">
                                    <_0:val>304</_0:val>
                                </_0:field>
                                <_0:field column="IsSOTrx">
                                    <_0:val>Y</_0:val>
                                </_0:field>
                                <_0:field column="POReference">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                            </_0:DataRow>
                        </_0:ModelCRUD>
                    </_0:operation>"""  % ( org ,C_DocTypeTarget_ID, C_DocType_ID, daymonth, daymonth, 
                        CN_Type, dateordered2,dateordered3,
                        User1_ID, User2_ID,  partner,crm_description2,daynow)


            for line_rec in vals:
                if partner == line_rec[0]:
                    PriceList = line_rec[1]
                    filter_id = line_rec[3]
                    cn_on_product = line_rec[11]

                    if line_rec[2] == 'Token Reimbursment':
                        C_Charge_ID=1000087
                    if line_rec[2] == 'Scratch Card Discount':
                        C_Charge_ID=1001726


                    line_body += """<_0:operation preCommit="false" postCommit="false">
                        <_0:TargetPort>createData</_0:TargetPort>
                        <_0:ModelCRUD>
                            <_0:serviceType>CreditNoteLines</_0:serviceType>
                            <_0:TableName>C_InvoiceLine</_0:TableName>
                            <RecordID>0</RecordID>
                            <Action>createData</Action>
                            <_0:DataRow>
                                <!--Zero or more repetitions:-->
                                <_0:field column="AD_Org_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_Tax_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="PriceList">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="PriceActual">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="PriceEntered">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="C_Charge_ID">
                                    <_0:val>%s</_0:val>
                                </_0:field>
                                <_0:field column="CN_On_Product">
                                    <_0:val></_0:val>
                                </_0:field>
                                
                                <_0:field column="QtyEntered">
                                    <_0:val>1.0000</_0:val>
                                </_0:field>
                                
                                <_0:field column="C_Invoice_ID">
                                    <_0:val>@C_Invoice.C_Invoice_ID</_0:val>
                                </_0:field>
                            </_0:DataRow>
                        </_0:ModelCRUD>
                    </_0:operation>"""  % ( org, C_Tax_ID,PriceList,PriceList,PriceList, C_Charge_ID) #, cn_on_product

                    # <_0:field column="CN_On_Product">
                    #     <_0:val>%s</_0:val>
                    # </_0:field>


            if commit_bool == True:
                lower_body = """
                                <_0:operation preCommit="true" postCommit="true">
                                        <_0:TargetPort>setDocAction</_0:TargetPort>
                                        <_0:ModelSetDocAction>
                                            <_0:serviceType>CompleteCreditNote</_0:serviceType>
                                            <_0:tableName>C_Invoice</_0:tableName>
                                            <_0:recordID>0</_0:recordID>
                                            <!--Optional:-->
                                            <_0:recordIDVariable>@C_Invoice.C_Invoice_ID</_0:recordIDVariable>
                                            <_0:docAction>CO</_0:docAction>
                                        </_0:ModelSetDocAction>
                                        <!--Optional:-->
                                    </_0:operation>
                                </_0:operations>
                            </_0:CompositeRequest>
                        </_0:compositeOperation>
                    </soapenv:Body>
                </soapenv:Envelope>"""

            else:
                print "#################### Generate Withdrawn Found ##### partner " , partner
                lower_body = """
                                </_0:operations>
                            </_0:CompositeRequest>
                        </_0:compositeOperation>
                    </soapenv:Body>
                </soapenv:Envelope>"""

            # <_0:val>1001816</_0:val>

            body = upper_body + payment_body + line_body  + lower_body
            # print "ffffffffffffffffffffffffffffffffffffffffff" , body

            # if self.new_year_bool:
            #     idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
                
            # else:
            #     idempiere_url="http://35.200.227.4/ADInterface/services/compositeInterface"


            # idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
            idempiere_url="https://erpnew.wmvd.live/ADInterface/services/compositeInterface?wsdl"

            response = requests.post(idempiere_url,data=body,headers=headers)
            print response.content
            
            log = str(response.content)

            
            if log.find('GenerateDocumentNoError') is not -1:
                # documentno_log = 'error'
                # documentno_log = log.split('<Error>')[1].split('</Error>')[0]
                raise ValidationError("Error Occured for partner %s  and the error is %s" % (partner, log))
                
            if log.find('DocumentNo') is not -1:
                print "llllllllllllllllllllllllllllllllllll" , log
                documentno_log = log.split('column="DocumentNo" value="')[1].split('"></outputField>')[0]
                print "ssssssssssssssssssssssssss" , documentno_log , self.state
                self.state = 'posted'
                write_data = self.credit_note_line_one2many.search([('id', '=', filter_id)]).sudo().write(
                                        {'log': documentno_log})


            if log.find('UNMARSHAL_ERROR') is not -1:
                write_data = self.credit_note_line_one2many.search([('id', '=', filter_id)]).sudo().write(
                                        {'log': 'Manual Entry'})

            if log.find('IsRolledBack') is not -1:
                # documentno_log = 'error'
                # documentno_log = log.split('<Error>')[1].split('</Error>')[0]
                raise ValidationError("Error Occured for partner %s  and the error is %s" % (partner, log))


            if log.find('Invalid') is not -1:
                # documentno_log = log.split('<faultstring>')[1].split('</faultstring>')[0]
                raise ValidationError("Error Occured for partner %s  and the error is %s" % (partner, log))


        for l in credit_note_line_filter:
            qr_records =self.env['barcode.marketing.check'].sudo().search([("id","=", l.barcode_check_id)]).sudo().write(
                                {'imported': True})

        
class credit_note_line(models.Model):
    _name = 'credit.note.line'
    _description = "Credit Note Line"

    credit_note_id  = fields.Many2one('credit.note', ondelete='cascade')
    name = fields.Char('Name')
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
    value_date = fields.Char('Date')
    ifsc_code = fields.Char('IFSC Code')
    beneficiary_email_id = fields.Char('Beneficiary Email Id')
    payment_term = fields.Char('Payment Term')
    owner = fields.Char('Owner')
    owner_email = fields.Char('Owner Email')
    description = fields.Char('Description')
    documentno = fields.Char('Document No')
    check_invoice = fields.Boolean(string = "", nolabel="1" , default=False)
    user_id = fields.Many2one('res.users', string='Owner')
    state = fields.Selection([
                                ('draft', 'Draft'),
                                ('approved', 'Approved'),
                                ('rejected', 'Rejected'),
                                ('hold', 'Holded')], 
                                string='Status',track_visibility='onchange')

    delegate_user_id = fields.Many2many('res.users', 'credit_note_lines_res_users_rel',  string='Delegate To')
    delay_date = fields.Date('Delay Date')
    partner_id = fields.Many2one('res.partner',string="Beneficiary" )
    customercode = fields.Char(string="Code" ,related='partner_id.bp_code' )
    c_bpartner_id = fields.Char(string="Partner ID" ,related='partner_id.c_bpartner_id')
    totalamt = fields.Float(string="Total")
    allocatedamt = fields.Float(string="Allocated Amt")
    unallocated = fields.Float(string="Unallocated Amt")
    duedays = fields.Integer(string="Due Days")
    invoiceno = fields.Char(string="Inv No")
    ad_org = fields.Char(string="Org")
    charge_name = fields.Char(string="Charge")
    company_id = fields.Many2one('res.company')
    ad_org_id = fields.Many2one('org.master', string='Org',  domain="[('company_id','=',company_id)]" )
    barcode_check_id = fields.Integer('Barcode Check ID')
    barcode_scan_id = fields.Many2one('barcode.marketing.check', string='Barcode Scan ID')
    log = fields.Text("Log")
    log2 = fields.Text("Log2")
    cn_type= fields.Selection(CN_TYPE, string='CN Type',track_visibility='onchange')
    poreference = fields.Char(string="POReference")
    c_period_id = fields.Many2one('wp.c.period', string='CN To' ,
      domain="[('company_id','=',company_id)]")
    c_elementvalue_id = fields.Many2one('wp.c.elementvalue', string='Cost Center' ,
      domain="[('company_id','=',company_id)]")
    charge_id = fields.Many2one('credit.note.charge', string='Charge')
    c_bpartner_id2 = fields.Char(string="Partner ID")
    cnfromperiod = fields.Many2one('wp.c.period', string='CN From' ,
      domain="[('company_id','=',company_id)]")
    cn_on_product = fields.Many2one('product.product', string='CN On Product' ,
      domain="[('company_id','=',company_id),('type','in',('product','consu'))]")
    user1_id = fields.Many2one('wp.c.elementvalue', string='Business Division' ,
      domain="[('company_id','=',company_id),('c_element_id','=','1000005')]")
    user2_id = fields.Many2one('wp.c.elementvalue', string='Functions' ,
      domain="[('company_id','=',company_id),('c_element_id','=','1000013')]")
    dateordered2 = fields.Date(string='Exp Period From')
    dateordered3 = fields.Date(string='Exp Period To')
    
    @api.onchange('charge_id')
    def _onchange_charge_id(self):
        if self.charge_id:
            self.charge_name = self.charge_id.name
   
    @api.multi
    def approve_invoice(self):
        if self.credit_note_id.state not in ('posted', 'cancel'):
            if self.state == 'approved':
                self.state = 'draft'
                self.check_invoice = False
            else:
                self.state = 'approved'
                self.check_invoice = True


class CreditNoteCharge(models.Model):
    _name = "credit.note.charge"
    _description = "Credit Note Charge"

    c_charge_id = fields.Char('Charge ID')
    company_id = fields.Many2one('res.company')
    active = fields.Boolean('Active')
    name = fields.Char('Name')
    description = fields.Char('Description')


class CreditNoteConfig(models.Model):
    _name = "credit.note.config"
    _description = "Credit Note Config"

    @api.model
    def create(self, vals):
        result = super(CreditNoteConfig, self).create(vals)

        a = self.search([("id","!=",0)])
        if len(a) >1:
            raise UserError(_('You can only create 1 Config Record'))

        return result

    @api.multi
    def _get_name(self):
        return "CN Config"

    name = fields.Char(string = "Config No.", default=_get_name)
    cn_approver_one2many = fields.One2many('credit.note.approver','config_id',string="Credit Note Approver")
    cn_user_one2many = fields.One2many('credit.note.user','config_user_id',string="Credit Note User")
    confirmation_mail = fields.Char(string = "Confirmation Mail")
    sales_support_mail = fields.Char(string = "Sales Support Mail")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('credit.note.config'))
    

class creditnoteApprover(models.Model):
    _name = "credit.note.approver"
    _description = "Credit Note Approver"
    _order= "sequence"

    config_id = fields.Many2one('credit.note.config', string='Config', ondelete='cascade')
    approver = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Approver sequence')


class CreditNoteUser(models.Model):
    _name = "credit.note.user"
    _description = "Credit Note User"

    config_user_id = fields.Many2one('credit.note.config', string='Config', ondelete='cascade')
    user = fields.Many2one('res.users', string='User', required=True)
    sequence = fields.Integer(string='User sequence')
