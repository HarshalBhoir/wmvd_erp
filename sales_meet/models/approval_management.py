
from datetime import datetime, timedelta, date
from odoo.tools.translate import _
from odoo import api, fields, tools, models, _ , registry, SUPERUSER_ID
from odoo.exceptions import UserError , ValidationError, Warning
import time
import psycopg2
from werkzeug import url_encode
import logging

_logger = logging.getLogger(__name__)

STATE = [('draft', 'Draft'),
         ('select', 'Generated'), 
         ('update', 'Sent For Approval'), 
         ('update2', 'Approved'), 
         ('select2', 'Posted')]

todaydate = "{:%d-%b-%y}".format(datetime.now())

class approval_management(models.Model):
    _name = "approval.management"
    _description=" External DB Connect"
    _inherit = 'mail.thread'
    _order    = 'id desc'


    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_('You can only delete Draft Entries'))
        return super(approval_management, self).unlink()


    @api.multi
    def _get_config(self):
        config = self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1)
        if config:
            config_id = config.id
        else:
            config = self.env['external.db.configuration'].search([('id', '!=',0)], limit=1)
            config_id = config.id
        return config_id

    name = fields.Char('Name', store=True)
    config_id = fields.Many2one('external.db.configuration', string='Database',
        track_visibility='onchange' , default=_get_config)
    state = fields.Selection(STATE, string='Status',track_visibility='onchange', default='draft')
    entry_type = fields.Selection([('invoice', 'Invoice'),
                                    ('payment', 'Payment/Receipt'),
                                    ('production', 'Production'),
                                    ('shipment', 'Shipment / Material Receipt')], 
                                    string='Entry Type',track_visibility='onchange')
    documentno = fields.Char('Document No', track_visibility='onchange')
    connect_lines_one2many = fields.One2many('approval.management.lines','connect_id',string="Line Details")
    date = fields.Date(string="Date From", default=lambda self: fields.Datetime.now())
    c_bpartner_id = fields.Char("Partner ID",default='Standard')
    approval_config_id = fields.Many2one('approval.management.configuration', string='Document Type' )
    docstatus = fields.Selection([('DR', 'DRAFT'),
                                ('CO', 'COMPLETE'),
                                ('CL', 'CLOSE'),], 
                                string='DocStatus',track_visibility='onchange')
    changed_date = fields.Date(string="Changed Date")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('approval.management'))
    customercode  = fields.Char('Code') 
    customername  = fields.Char('Customer')
    approver_config_id = fields.Many2one('approval.mgmt.config', string="Approver Group", 
        domain="[('company_id','=',company_id),('active','=',True)]")
    remarks = fields.Text('Remark')

    user_id = fields.Many2one('res.users', string='User' , copy=False , index=True,
        track_visibility='onchange', default=lambda self: self.env.user)
    approver_id = fields.Many2one('res.users', string='Approver' , copy=False , index=True)


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('approval.management')
        result = super(approval_management, self).create(vals)
        return result


    @api.multi
    def select_all(self):
        for record in self.connect_lines_one2many:
            if record.selection == True:
                record.selection = False
            elif record.selection == False:
                record.selection = True

    
    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and self.env.uid != 1:
                raise UserError(_('You can only delete Draft Entries'))
        return super(approval_management, self).unlink()

    def report_check(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_check = base_url + '/web#%s' % (url_encode({
                'model': self._name,
                'view_type': 'form',
                'id': self.id,
            }))
        rep_check = """ <br/>
            <td>
                <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                    font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                    text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                    text-align: center; vertical-align: middle; cursor: pointer; 
                    white-space: nowrap; background-image: none; background-color: #337ab7; 
                    border: 1px solid #337ab7; margin-right: 10px;">Check Distributor</a>
            </td> 
            """  % ( report_check)
        return rep_check


    @api.multi
    def get_partner_id(self):
        order_lines= []
        conn_pg = None
        if self.documentno and self.company_id:

            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username,
                    password=self.config_id.password, 
                    host= self.config_id.ip_address,port=self.config_id.port)
                pg_cursor = conn_pg.cursor()

                # pg_cursor.execute("select * from adempiere.due_invoice_from_shipment where \
                #   documentno= %s and ad_client_id =  %s ",(self.documentno,self.company_id.ad_client_id))

                if self.company_id.ad_client_id == 1000001:
                    pg_cursor.execute("select * from adempiere.due_invoice_detail_from_shipment where \
                        documentno= %s and ad_client_id =  %s and \
                        date > '2019-09-01' ",(self.documentno,self.company_id.ad_client_id))
                else:

                    pg_cursor.execute("select * from adempiere.due_invoice_detail_from_shipment where \
                      documentno= %s and ad_client_id =  %s ",(self.documentno,self.company_id.ad_client_id))

                records = pg_cursor.fetchall()

                if len(records) == 0:
                    raise UserError("No records Found")
                    (str(record[4]).split('.'))[0]

                for record in records:
                    order_lines.append((0, 0, {
                            'connect_id':self.id,
                            'documentno':record[1],
                            'processowner':record[2],
                            'customerpaymenttermmin':record[3],
                            'inrrate':record[4],
                            'org':record[5],
                            'entryno':record[6],
                            'dateacct':record[7],
                            'invno':record[8],
                            'custgroup':record[9],
                            'customerid':(str(record[10]).split('.'))[0],# record[10],
                            'customername':record[11],
                            'customercode':record[12],
                            'customercreditlimit':record[13],
                            'customerpaymentterm':record[14],
                            'state':'select',
                            'grandtotal':record[15],
                            'remarks' : record[16],
                            'amount' : record[17],
                            'overunderamt' : record[18],
                            'duedate' : record[19],                          
                        } ))
                    
                    self.customername = record[11]
                    self.c_bpartner_id = record[10]
                    self.customercode = record[12]

                # self.env['approval.management.lines'].create(vals_line)
                self.connect_lines_one2many = order_lines
                self.state = 'select'

            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '-----------------------------Error %s' % e    

            finally:
                if conn_pg: conn_pg.close()
                print "#---------------Update ----Finally----------------------#"


    @api.multi
    def send_approval_mail(self):
        body = """ """
        subject = line_html = ""
        main_id = self.id

        approval_mgmt_line = self.connect_lines_one2many.search([('connect_id', '=', self.id),
                                                                 ('selection', '=', True)])

        if  len(approval_mgmt_line) < 1:
            raise ValidationError(_('No Records Selected'))
            
        for l in approval_mgmt_line:
            if l.selection:
                start_date = datetime.strptime(str(((l.dateacct).split())[0]), 
                    tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

                line_html += """
                <tr>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                </tr>
                """ % (start_date, l.entryno, l.invno, l.customerpaymentterm, l.grandtotal, l.remarks or '')


        body = """
            <h3>Hi Team,</h3>
            <h3>The following Invoices are outstanding / unallocated and due to which the below given
             shipment is requesting an approval from your end.</h3>
            <h3>Kindly take necessary action by clicking the buttons below:</h3>

            <table>
              <tr><th style=" text-align: left;padding: 8px;">Document No</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Customer</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Cust Code</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Company</td><td> : %s</td></tr>
            </table>
            <br/>

            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Date</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Entry No</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Invoice No</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">PMT Term</th>             
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Total Amt</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Remarks</th>
                    </tr>
                    %s
                </tbody>
            </table>
            <br/><br/>

        """ % (self.documentno,self.customername, self.customercode, self.company_id.name, line_html)

        subject = "Request for Due Invoice Approval - ( %s )"  % (todaydate)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        approver = self.env['approval.mgmt.approver'].sudo().search([("config_id","=",self.approver_config_id.id)])

        if len(approver) < 1:
            raise ValidationError("Approver Config doesnot have any Approver. Configure the Approvers and Users ")

        email_from = self.env.user.email
     
        for rec in approver:
            email_to = rec.approver.email

            approve_url = base_url + '/approvals?%s' % (url_encode({
                    'model': self._name,
                    'approval_id': main_id,
                    'res_id': rec.id,
                    'user_id': rec.approver.id,
                    'action': 'approve_approval_request',
                }))
            reject_url = base_url + '/approvals?%s' % (url_encode({
                    'model': self._name,
                    'approval_id': main_id,
                    'res_id': rec.id,
                    'user_id': rec.approver.id,
                    'action': 'refuse_approval_request',
                }))

            full_body = body + """<br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; 
                        line-height: 18px; color: #FFFFFF; border-color:#337ab7; text-decoration: none; display: inline-block;
                        margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; cursor: pointer; 
                        white-space: nowrap; background-image: none; background-color: #337ab7; 
                          border: 1px solid #337ab7; margin-right: 10px;">Approve</a>
                        </td>
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; 
                        line-height: 18px; color: #FFFFFF; border-color:#337ab7; text-decoration: none; display: inline-block;
                        margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; cursor: pointer; 
                        white-space: nowrap; background-image: none; background-color: #337ab7; 
                          border: 1px solid #337ab7; margin-right: 10px;">Reject</a>
                        </td>

                    </tr>
                </tbody>
            </table>
            """ % (approve_url, reject_url)

            self.send_generic_mail(subject, full_body, email_from, email_to)

        self.state='update'



    @api.multi
    def approve_approval_request(self, remarks, user_id=False):

        if user_id:
            approver_id = self.env['res.users'].sudo().search([("id","=",user_id)])
        else:
            approver_id = self.env['res.users'].sudo().search([("id","=",self.env.uid)])

        self.sudo().write({'write_uid':1088,'state': 'select2','remarks':remarks, 'approver_id':approver_id.id})

        if self.config_id:
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
                    password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
                pg_cursor = conn_pg.cursor()

                for res in self.connect_lines_one2many:
                    if res.selection:
                        remarks_invoice = "Validated on %s by %s - %s" %(self.date,approver_id.name,remarks)
                        pg_cursor.execute("update adempiere.C_Invoice set remarks = %s where ad_client_id=%s and \
                            documentno=%s",(remarks_invoice,self.company_id.ad_client_id,res.entryno))

                        res.remarks = remarks
                        res.state = 'select2'
                        print "==============Update Invoice ====================="

                entry_id = conn_pg.commit()
                self.update_shipment()
                self.send_user_mail()

            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '-----------------------------Error %s' % e    

            finally:
                if conn_pg: conn_pg.close()
                print "#---------------Update ----Finally----------------------#"


    @api.multi
    def update_shipment(self):
        if self.config_id:
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
                    password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
                pg_cursor = conn_pg.cursor()

                pg_cursor.execute("update adempiere.ChuBoe_Validation \
                    set isChuBoe_ValidationApproved = 'Y' , email = %s , Approve_Notes = %s \
            where  record_id in (select M_InOut_ID from adempiere.M_InOut where documentno = %s and \
            ad_client_id =  %s )",(self.approver_id.login , self.remarks,self.documentno,self.company_id.ad_client_id))

                entry_id = conn_pg.commit()
                print "==============Update Shipment====================="

            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '-----------------------------Error %s' % e    

            finally:
                if conn_pg: conn_pg.close()
                print "#---------------Update ----Finally----------------------#"


    @api.multi
    def send_user_mail(self):
        line_html = ""
        main_id = self.id
        self.changed_date = datetime.now()
        email_from = self.approver_id.email
        approval_mgmt_line = self.connect_lines_one2many.search([('connect_id', '=', self.id),('selection', '=', True)])

        for l in approval_mgmt_line:
            if l.selection:
                start_date = datetime.strptime(str(((l.dateacct).split())[0]), 
                    tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

                line_html += """
                <tr>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                </tr>
                """ % (start_date, l.entryno, l.invno, l.customerpaymentterm, l.grandtotal, l.remarks)

        main_body = """
            <h2>Hi Team,</h2>
            <br/><br/>

            <h2>The request for document %s is approved by %s dated %s</h2>
            <h2>%s can Complete the %s document and Post. </h2>

            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Date</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Entry No</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Invoice No</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">PMT Term</th>             
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Total Amt</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Remarks</th>
                    </tr>
                    %s
                </tbody>
            </table>
            <br/>

        """  % (self.documentno, self.approver_id.name, self.changed_date, self.user_id.name , 
            self.approval_config_id.name , line_html)

        link_body = main_body + self.report_check()

        subject = "[Approved] Request for %s -(%s)"  % (self.name,todaydate)
        approver = self.env['approval.mgmt.approver'].search([("config_id","=",self.approver_config_id.id)])

        if len(approver) < 1:
            raise ValidationError("Approver Config doesnot have any Approver. Configure the Approvers and Users ")

        full_body = link_body
        email_to = self.user_id.email
      
        self.send_generic_mail(subject, full_body, email_from, email_to)


    @api.multi
    def refuse_approval_request(self,remarks, user_id):

        approver_id = self.env['res.users'].sudo().search([("id","=",user_id)])
        subject = "Approval on %s - Refused" % (self.approval_config_id.name)
        email_from = approver_id.email
        body = (_("Approval on Document %s has been refused by \
            %s.<br/><ul class=o_timeline_tracking_value_list></ul>") % (self.name, self.approver_id.name))
        full_body = body

        approver = self.env['approval.mgmt.approver'].sudo().search([("config_id","=",self.approver_config_id.id)])
        if len(approver) < 1:
            raise ValidationError("Approver Config doesnot have any Approver. Configure the Approvers and Users ")
      
        for rec in approver:
            email_to =  rec.approver.email
            self.send_generic_mail(subject, full_body, email_from, email_to)

        self.sudo().write({'state': 'refused','remarks':remarks, 'approver_id':approver_id.id})


    @api.model
    @api.multi
    def update_invoice(self):
        conn_pg = None
        if self.config_id:
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
                    password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
                pg_cursor = conn_pg.cursor()

                for record in self.sudo().search([('state', '=','select2')]) :
                    remarks_invoice = "Validated on %s by %s - %s" %(record.date,record.approver_id.name,record.remarks)

                    entryno = tuple([(res.entryno).encode('utf-8') for res in record.connect_lines_one2many])

                    pg_cursor.execute("update adempiere.C_Invoice \
                        set remarks = %s where ad_client_id=%s and documentno in %s",(remarks_invoice,
                                record.company_id.ad_client_id,entryno))

                    print "==============Update Invoice ====================="

                entry_id = conn_pg.commit()

            except psycopg2.DatabaseError, e:
                if conn_pg: conn_pg.rollback()
                print '----------------------Error %s' % e    

            finally:
                if conn_pg: conn_pg.close()
                print "#---------------update_invoice ----Finally----------------------#"


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
        print "--- Mail Sent to ---" , email_to, "---- Mail Sent From ---" , email_from


class approval_management_lines(models.Model):
    _name = "approval.management.lines"
    _description=" External DB lines"

    name = fields.Char('Name')
    selection = fields.Boolean(string = "", nolabel="1")
    connect_id = fields.Many2one('approval.management', string='connect', track_visibility='onchange')
    c_bpartner_id = fields.Char('Partner / Client')
    documentno = fields.Char('Document No')
    c_invoice_id = fields.Char('Invoice/Payment')
    totallines = fields.Char('Total')
    grandtotal = fields.Char('Grand Total')
    docstatus = fields.Char('Status')
    processed = fields.Char('Processed')
    posted = fields.Char('Posted')
    dateacct = fields.Date('Account Date')
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('approval.management.lines'))

    processowner = fields.Char('Owner')
    customerpaymenttermmin = fields.Char('Pmt Term Min')
    inrrate = fields.Float('MultiplyRate')
    org = fields.Char('Org')
    entryno  = fields.Char('Entry No')
    invno  = fields.Char('Invoice No')
    custgroup  = fields.Char('Cust Group')
    customerid  = fields.Char('Cust ID')
    customername  = fields.Char('Customer')
    customercode  = fields.Char('Code') 
    customercreditlimit  = fields.Char('Credit Limit')
    customerpaymentterm  = fields.Char('Pmt Term')
    remarks = fields.Text('Remark')
    state = fields.Selection(STATE, string='Status',track_visibility='onchange', default='draft')
    grandtotal = fields.Float('Grand Total')
    amount = fields.Float('Allocated')
    overunderamt = fields.Float('Difference')
    duedate = fields.Date('Due Date')

    @api.multi
    def approve_line(self):
        if self.connect_id.state != 'posted':
            if self.state == 'select': self.selection = True
        else:
            raise ValidationError(_("Expense cannot be approved in 'Post' State"))


class approval_management_configuration(models.Model):
    _name = "approval.management.configuration"
    _description=" Approval Configuration"

    name= fields.Char('Name')

class ApprovalMgmt(models.Model):
    _name = "approval.mgmt.config"

    @api.model
    def create(self, vals):
        result = super(ApprovalMgmt, self).create(vals)

        if result.group_id and result.company_id  and result.owner:
            result.name = result.company_id.short_name  + '_' + result.group_id.name +  '_'  + result.owner.name
        return result


    name = fields.Char(string = "Config No.")
    am_approver_one2many = fields.One2many('approval.mgmt.approver','config_id',string="Credit Note Approver" )
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('approval.mgmt.config'))
    group_id = fields.Many2one('res.partner.group', string='Group', required=True)
    org_id = fields.Many2one('org.master', string='Organisation')
    active = fields.Boolean('Active', default=True)
    owner = fields.Many2one('res.users', string='Owner')


class ApprovalMgmtApprover(models.Model):
    _name = "approval.mgmt.approver"
    _order= "sequence"

    config_id = fields.Many2one('approval.mgmt.config', string='Config', ondelete='cascade')
    approver = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Approver sequence')