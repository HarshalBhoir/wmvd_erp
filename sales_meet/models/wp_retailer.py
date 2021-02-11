# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from datetime import datetime, timedelta, date , time
from odoo import api, fields, models, _ , SUPERUSER_ID, tools
from odoo.exceptions import UserError , ValidationError , Warning
from odoo.http import request
import time
import string
import calendar
from odoo import http
from werkzeug import url_encode
import csv
from cStringIO import StringIO
import re
import base64
import cStringIO

todaydate = "{:%d-%b-%y}".format(datetime.now())

ZONE = [('north', 'North'),
        ('east', 'East'),
        ('central', 'Central'),
        ('Gujarat', 'Gujarat'),
        ('west', 'West'),
        ('south', 'South'),
        ('export', 'Export')]

class WpRetailer(models.Model):
    _name = "wp.retailer"
    _description = 'Retailer Form'
    _inherit = 'mail.thread'
    _order = 'id desc'


    code = fields.Char('Code')
    pan_no = fields.Char('Pan No')
    taxid = fields.Char('Tax ID')
    aadhar_no = fields.Char('Aadhar No')
    tin_no = fields.Char('Tin No')
    vat_no = fields.Char('Vat No')
    cst_no = fields.Char('Cst No')
    gst_no = fields.Char('Gst No')

    so_creditlimit=fields.Float(string="Credit limit" )
    totalopenbalance=fields.Float(string="Open Balance" )
    contact_name = fields.Char('Contact Name')
    bank_name = fields.Char('Bank Name')
    account_no = fields.Char('Account No')
    ifsc_code = fields.Char('IFSC Code')
    branch_name = fields.Char('Branch Name')
    cheque_no = fields.Char('Blank Cheque No')
    contact_name = fields.Char('Contact Name')
    address = fields.Char('Bank Address')
    bank_country = fields.Many2one("res.country", string='Country')
    district_id = fields.Many2one("res.state.district", string='District')
    name = fields.Char(index=True)
    date = fields.Date(index=True)
    title = fields.Many2one('res.partner.title')
    distributer_id = fields.Many2one('res.partner', string='Distributer', index=True)
    lead_id = fields.Many2one('crm.lead', string='Lead', index=True)
    ref = fields.Char(string='Internal Reference', index=True)
    user_id = fields.Many2one('res.users', string='User', copy=False , index=True, track_visibility='onchange',
     default=lambda self: self.env.user)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', copy=False , index=True,
     track_visibility='onchange')

    vat = fields.Char(string='TIN', help="Tax Identification Number. "
                                         "Fill it if the company is subjected to taxes. "
                                         "Used by the some of the legal statements.")
    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks')
    website = fields.Char(help="Website of Partner or Company")
    comment = fields.Text(string='Notes')
    barcode = fields.Char(oldname='ean13')
    active = fields.Boolean(default=True)
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    email = fields.Char()
    email_formatted = fields.Char(
        'Formatted Email', compute='_compute_email_formatted',
        help='Format email address "Name <email@domain>"')
    phone = fields.Char()
    fax = fields.Char()
    mobile = fields.Char(size = 10)
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('wp.retailer'))
    color = fields.Integer(string='Color Index', default=0)
    user_ids = fields.One2many('res.users', 'partner_id', string='Users', auto_join=True)
    
    image = fields.Binary("Image", attachment=True,
        help="This field holds the image used as avatar for this contact, limited to 1024x1024px",)
    image_medium = fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized image of this contact. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized image", attachment=True,
        help="Small-sized image of this contact. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    zone = fields.Selection(ZONE, string='Zone', copy=False, index=True, store=True)


    @api.model
    def create(self, vals):

        vals['code'] = self.env['ir.sequence'].next_by_code('wp.retailer')
        result = super(WpRetailer, self).create(vals)

        print "111111111111 Retailer Details Create 1111111111111"
        if result.mobile :
            phone = self.env['wp.retailer'].search([('mobile','=',result.mobile)])
            if len(phone) > 1 :
                phname = phone[1].name 
                raise UserError("Mobile Number already present in the Retailer ' " + phname + " '")

            if len(result.mobile) != 10:
                raise UserError(" Kindly enter 10 digit Mobile number")

        return result

    @api.multi
    def write(self, vals):
        result = super(WpRetailer, self).write(vals)

        if self.mobile :
            mobile = self.env['wp.retailer'].search([('mobile','=',self.mobile)])
            if len(mobile) > 1 :
                mbname = mobile[1].name 
                raise UserError("Mobile Number already present in the Retailer ' " + mbname + " '")

            if len(self.mobile) != 10:
                raise UserError(" Kindly enter 10 digit phone number")

        return result

class WpRetailerOrder(models.Model):
    _name = "wp.retailer.order"
    _description="Retailer Order"
    _inherit = 'mail.thread'
    _order    = 'id desc'


    @api.depends('line_ids.uom_id', 'line_ids.bags')
    def _calculate_all(self):
        """
        Compute the total qty, bags and Tones in orders.
        """
        for order in self:
            total_bags = total_qty = total_tons = 0.0
            for line in order.line_ids:
                total_bags += line.bags
                total_qty += line.qty
                total_tons += line.tons

            order.update({
                'total_qty': total_qty,
                'total_bags': total_bags,
                'total_tons': total_tons,
            })



    name = fields.Char(string="Name")
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default="draft")
    line_ids = fields.One2many('wp.retailer.order.line', 'order_id', string="Lines")
    distributer_id = fields.Many2one('res.partner', string='Distributer', index=True)
    retailer_id = fields.Many2one('wp.retailer', string='Retailer', index=True  ,
      domain="[('distributer_id','=',distributer_id)]")
    date = fields.Date(string="Date", default=lambda self: fields.Datetime.now())
    invoice_no = fields.Char(string="Invoice No")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('wp.retailer.order'))

    total_qty = fields.Float(string='Total Qty', store=True, readonly=True, compute='_calculate_all', digits=(16,3))
    total_bags = fields.Float(string='Total Bags', store=True, readonly=True, compute='_calculate_all', digits=(16,3))
    total_tons = fields.Float(string='Total Tons', store=True, readonly=True, compute='_calculate_all', digits=(16,3))


    @api.multi
    def confirm_order(self):
        self.name = 'RO/' + str(self.id).zfill(4)
        self.state = 'confirmed'
        for res in self.line_ids:
            res.state = 'confirmed'



class WpRetailerOrderLine(models.Model):
    _name = "wp.retailer.order.line"
    _description="Retailer Order Line"
    _order    = 'id desc'

    name = fields.Char(string="Name")
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default="draft")
    date = fields.Date(string="Date", index=True)
    order_id = fields.Many2one('wp.retailer.order', string="Order")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('wp.retailer.order.line'))
    product_id = fields.Many2one("product.product", string="Product")
    category_id = fields.Many2one("product.category", string="Category" , related='product_id.categ_id')
    uom_id = fields.Many2one('product.uom', string='UOM', related='product_id.uom_id')
    qty = fields.Float(string="Qty", digits=(16,3))
    bags = fields.Float(string="Bags", digits=(16,3))
    tons = fields.Float(string="Tons" , digits=(16,3))

    @api.onchange('uom_id', 'bags')
    def onchange_uom(self):
        if self.uom_id  and self.bags:
            self.qty = self.uom_id.uom_code * self.bags
            self.tons  = (self.uom_id.uom_code * self.bags)/1000


class WpRetailerScheme(models.Model):
    _name = "wp.retailer.scheme"
    _description="Retailer Scheme"
    _inherit = 'mail.thread'
    _order    = 'id desc'


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('wp.retailer.scheme')
        result = super(WpRetailerScheme, self).create(vals)
        return result


    name = fields.Char(string="Name")
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')], default="draft")
    quarter = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')])
    line_ids = fields.One2many('wp.retailer.scheme.line', 'scheme_id', string="Lines")
    zone = fields.Selection(ZONE, string='Zone', copy=False, index=True, store=True)
    date = fields.Date(string="Date", default=lambda self: fields.Datetime.now())
    expiry_date = fields.Date(string="Expiry Date")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('wp.retailer.scheme'))
    user_id = fields.Many2one('res.users', string='User', copy=False , index=True, 
        track_visibility='onchange', default=lambda self: self.env.user)


class WpRetailerSchemeLine(models.Model):
    _name = "wp.retailer.scheme.line"
    _description="Retailer Scheme Line"

    name = fields.Char(string="Name")
    scheme_id = fields.Many2one('wp.retailer.scheme', string="Scheme")
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')], default="draft")
    slab = fields.Char(string="Slab")
    sale_mt = fields.Char(string="Sale In MT")
    base = fields.Float(string="Base", digits=(16,3))
    max_tons = fields.Float(string="Max", digits=(16,3))
    scheme_pmt = fields.Float(string="Scheme PMT", digits=(16,3))
    scheme_budget = fields.Float(string="Scheme Budget", digits=(16,3))
    gift_item = fields.Char(string="Gift Item")
    brand = fields.Char(string="Brand")
    cost = fields.Float(string="Cost", digits=(16,3))
    mrp = fields.Float(string="MRP", digits=(16,3))


    @api.model
    def create(self, vals):
        result = super(WpRetailerSchemeLine, self).create(vals)
        result.name = "RSL/"+str(result.id).zfill(2)
        return result



class WpSchemeWorking(models.Model):
    _name = "wp.scheme.working"
    _description="Scheme Working"
    _inherit = 'mail.thread'
    _order    = 'id desc'


    @api.depends('line_ids.retailer_id', 'line_ids.tons')
    def _calculate_all(self):

        for order in self:
            total_tons = 0.0
            for line in order.line_ids:
                total_tons += line.tons

            order.update({'total_tons': total_tons,})

    name = fields.Char(string="Name")
    state = fields.Selection([('draft', 'Draft'), 
                                ('generated', 'Generated'), 
                                ('sent_for_approval', 'Sent For Approval'), 
                                ('approved', 'Approved'),
                                ('rejected', 'Rejected')], default="draft")
    quarter = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')])
    line_ids = fields.One2many('wp.scheme.working.line', 'working_id', string="Lines")
    zone = fields.Selection(ZONE, string='Zone', copy=False, index=True, store=True)

    date = fields.Date(string="Date", default=lambda self: fields.Datetime.now())
    expiry_date = fields.Date(string="Expiry Date")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('wp.scheme.working'))
    user_id = fields.Many2one('res.users', string='User', copy=False , index=True,  default=lambda self: self.env.user)
    distributer_id = fields.Many2one('res.partner', string='Distributer', index=True)
    scheme_id = fields.Many2one('wp.retailer.scheme', string="Scheme")
    total_tons = fields.Float(string='Total Tons', store=True, readonly=True, compute='_calculate_all', digits=(16,3))

    retailer_csv_data = fields.Char('Name', size=256 , copy=False)
    retailer_file_name = fields.Binary('Working Import', readonly=True , copy=False)
    delimeter = fields.Char('Delimeter', default=',')

    @api.onchange('scheme_id')
    def onchange_scheme(self):
        if self.scheme_id:
            self.quarter = self.scheme_id.quarter


    @api.multi
    def action_upload(self):

        retailer_obj = self.env['wp.retailer']
        todaydate = "{:%Y-%m-%d}".format(datetime.now())

        # Decode the file data
        if self.state == 'draft':
            data = base64.b64decode(self.retailer_file_name)
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
            if not isinstance(keys, list) or ('code' not in keys or
                                              'tons' not in keys ):
                raise Warning(_("'Code' or 'tons' keys not found"))
            del reader_info[0]
            values = {}
            
            for i in range(len(reader_info)):
                val = {}
                field = reader_info[i]
                values = dict(zip(keys, field))
    
                retailer_list = retailer_obj.search([('code', '=',values['code'])], limit= 1)
                if retailer_list:
                    print "dddddddddddsssssss" ,  self.distributer_id.id , retailer_list[0].distributer_id.id
                    if self.distributer_id.id == retailer_list[0].distributer_id.id :
                        val['retailer_id'] = retailer_list[0].id
                        val['salesperson_id'] = retailer_list[0].salesperson_id.id
                    else :
                        raise Warning(_( retailer_list[0].name + " is not a retailer of selected Distributer"))
                
                val['tons'] = values['tons']
                val['code'] = values['code']
                val['company_id'] = self.company_id.id
                val['scheme_id']= self.scheme_id.id
                val['distributer_id'] = self.distributer_id.id 
                val['working_id'] = self.id
    
                working_lines = self.line_ids.sudo().create(val)
                print "ffffffffffffffffffffffvvvvvvvvvv" ,working_lines
                working_lines.name = "CWL/"+self.quarter+"/"+str(working_lines.id).zfill(2)
                print "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr" , working_lines.name

            self.name = "CW/"+self.quarter+"/"+str(self.id).zfill(4)
                
        else:
            raise Warning(_("Retailer Working can be imported only in 'Draft' Stage"))


    @api.multi
    def action_update(self):
        self.action_done()
        self.state = 'generated'


    @api.multi
    def action_search(self):

        if self.distributer_id:
            order_id = self.env['wp.retailer.order'].search([('distributer_id','=',self.distributer_id.id)])
            retailer_tons = [(x.retailer_id.id , x.total_tons) for x in order_id]
            dict_retailer_tons = {x:0 for x, _ in retailer_tons}

            for retailer_id , tons in retailer_tons: dict_retailer_tons[retailer_id] += tons

            retailer_tons_output = list(map(tuple, dict_retailer_tons.items())) 

            for res in retailer_tons_output:

                vals_line = {
                    'working_id':self.id,
                    'retailer_id':res[0],
                    'scheme_id':self.scheme_id.id,
                    'distributer_id':self.distributer_id.id,
                    'salesperson_id':self.distributer_id.user_id.id,
                    'tons':res[1],


                }
                self.line_ids.create(vals_line)
                
                self.line_ids[0].name = "CWL/"+self.quarter+"/"+str(self.line_ids[0].id).zfill(2)
                print "dddddddddddddddddddddddddddddd" ,  self.line_ids[0].id , self.line_ids[0].name
            self.name = "CW/"+self.quarter+"/"+str(self.id).zfill(4)

            self.action_done()


    @api.multi
    def action_done(self):
        if self.scheme_id:
            for res in self.line_ids:
                for record in self.scheme_id.line_ids:
                    if res.tons >= record.base and res.tons <= record.max_tons :
                        res.write({'gift_item': record.gift_item, 
                                   'scheme_line_id': record.id,
                                   'cost': record.cost,
                                   'mrp': record.mrp,
                                   'brand': record.brand,})

    @api.multi
    def approve_retailer_working(self):
        self.sudo().send_user_mail()
        self.state = 'approved'
        for res in self.line_ids:
            if res.mail_opt_out:
                res.state = 'submitted'
            else:
                res.state = 'approved'
                res.send_mail_to_salesuser()


    @api.multi
    def send_approval(self):
        approval_mail = 1
        initial_body = """  <h3>Hi Team,</h3><br/>
            <h3>Following are the details as Below Listed for distributer %s in %s </h3>
        """  % (self.distributer_id.name, self.company_id.name)

        email_from = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).salesupport_mail_id

        subject = "Request for Retailer Working Approval - %s ( %s )"  % (self.distributer_id.name, todaydate)
        approver = self.env['credit.note.approver'].search([])
        if len(approver) < 1:
            raise ValidationError("Approval Config doesnot have any Approver. Configure the Approvers and Users ")

        approver_email = [x.approver.email for x in approver]
        email_to = ",".join(approver_email)

        self.send_approval_mail(initial_body, approval_mail, subject, email_from, email_to)
        self.state='sent_for_approval'


    @api.multi
    def send_user_mail(self):
        approval_mail = 0
        subject = "[Approved] Retailer Working - %s ( %s )"  % (self.distributer_id.name, todaydate)
        initial_body = """ <h3>Hi Team,</h3><br/>
            <h3>The Request %s is approved.</h3>
            <h3>Following are the details as Below Listed for distributer %s in %s </h3>
        """  % (self.name, self.distributer_id.name, self.company_id.name)

        cn_user = self.env['credit.note.user'].search([("id","!=",0)])
        if len(cn_user) < 1:
            raise ValidationError("Approval Config doesnot have any User. Configure the Approvers and Users ")

        support_email = [x.user.email for x in cn_user]
        email_to = ",".join(support_email)
        email_from = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).salesupport_mail_id

        self.send_approval_mail(initial_body, approval_mail, subject, email_from, email_to)

    @api.multi
    def send_approval_mail(self,initial_body=False, approval_mail=False, subject=False, email_from=False, email_to=False):
        body = """ """
        line_html = ""
        main_id = self.id
        working_line = self.line_ids.search([('working_id', '=', self.id)])

        if  len(working_line) < 1:
            raise ValidationError(_('No Records Selected'))
            
        for l in working_line:

            line_html += """
            <tr>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
            </tr>
            """ % (l.retailer_id.name, l.gift_item, l.brand, l.cost, l.mrp, l.tons, l.salesperson_id.name)


        body = """
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Retailer</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Gift Item</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Brand</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Cost</th>             
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">MRP</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Tons</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Salesperson</th>
                    </tr>
                    %s
                </tbody>
            </table>
            <br/><br/>

        """ % (line_html)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        approve_url = base_url + '/retailerworking?%s' % (url_encode({
                'model': self._name,
                'working_id': main_id,
                'res_id': main_id,
                'action': 'approve_retailer_working',
            }))
        reject_url = base_url + '/retailerworking?%s' % (url_encode({
                'model': self._name,
                'working_id': main_id,
                'res_id': main_id,
                'action': 'refuse_retailer_working',
            }))

        report_check = base_url + '/web#%s' % (url_encode({
            'model': self._name,
            'view_type': 'form',
            'id': main_id,
        }))

        if approval_mail == 1:
    
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
                                border: 1px solid #337ab7; margin-right: 10px;">Selective Approve/Reject</a>
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
                                <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; 
                            line-height: 18px; color: #FFFFFF; border-color:#337ab7; text-decoration: none; display: inline-block;
                            margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; cursor: pointer; 
                            white-space: nowrap; background-image: none; background-color: #337ab7; 
                              border: 1px solid #337ab7; margin-right: 10px;">Selective Approve/Reject</a>
                            </td>
                        </tr>
                    </tbody>
                </table>
                """ % (report_check)

        full_body = initial_body + body + second_body

        self.send_generic_mail(subject, full_body, email_from, email_to)
        

    @api.multi
    def refuse_retailer_working(self):
        self.state = 'rejected'
        subject = "Retailer Working - Refused"
        full_body = (_("Retailer Working %s has been refused.<br/><ul class=o_timeline_tracking_value_list></ul>") % (self.name))
        email_from = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).salesupport_mail_id

        cn_user = self.env['credit.note.user'].search([("id","!=",0)])

        if len(cn_user) < 1:
            raise ValidationError("Approval Config doesnot have any User. Configure the Approvers and Users ")

        support_email = [x.user.email for x in cn_user]
        email_to = ",".join(support_email)

        self.send_generic_mail(subject, full_body, email_from, email_to)

        self.state = 'rejected'
        for res in self.line_ids:
            res.state = 'rejected'

    
    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and self.env.uid != 1:
                raise UserError(_('You can only delete Draft Entries'))
        return super(retailer_working, self).unlink()

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


class WpSchemeWorkingLine(models.Model):
    _name = "wp.scheme.working.line"
    _description="Scheme Working Line"
    _inherit = 'mail.thread'
    _order    = 'id desc'


    name = fields.Char(string="Name")
    working_id = fields.Many2one('wp.scheme.working', string="Working")
    state = fields.Selection([('draft', 'Draft'),
                             ('approved', 'Approved'), 
                             ('rejected', 'Rejected'), 
                             ('submitted', 'Submitted')], default="draft")
    scheme_line_id = fields.Many2one('wp.retailer.scheme.line',  string="Scheme Line")
    scheme_id = fields.Many2one('wp.retailer.scheme', string="Scheme")
    gift_item = fields.Char(string="Gift Item")
    tons = fields.Float(string="Tons", digits=(16,3))
    distributer_id = fields.Many2one('res.partner', string='Distributer', index=True)
    retailer_id = fields.Many2one('wp.retailer', string='Retailer', index=True  ,
      domain="[('distributer_id','=',distributer_id)]")
    code = fields.Char('Code')
    brand = fields.Char(string="Brand")
    cost = fields.Float(string="Cost", digits=(16,3))
    mrp = fields.Float(string="MRP", digits=(16,3))
    retailer_attachments = fields.Many2many('ir.attachment', 'retailer_attachments_rel' , copy=False, attachment=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', copy=False , index=True, track_visibility='onchange')
    delivered_date = fields.Date(string="Delivered Date")
    company_id = fields.Many2one('res.company', 'Company',
     default=lambda self: self.env['res.company']._company_default_get('wp.scheme.working.line'))
    mail_opt_out = fields.Boolean(string="Opt Out" , default=False)


    @api.multi
    def action_submitted(self):
        if self.retailer_attachments:
            self.send_user_mail()
            self.state = 'submitted'
        else:
            raise UserError("Kindly attach photos or any attachment")

    @api.multi
    def send_mail_to_salesuser(self):
        email_to = self.salesperson_id.email
        email_from = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).confirmation_mail
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_check = base_url + '/web#%s' % (url_encode({
                'model': self._name,
                'view_type': 'form',
                'id': self.id,
            }))

        full_body = """ <p>Hi %s,</p><br/>

            <p>You have been assigned with a gift of %s to be delivered to <b>%s</b> (<b>%s</b>) 
            at its given delivery address</p>
            <br/>
            
            <td>
                <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                    font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                    text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                    text-align: center; vertical-align: middle; cursor: pointer; 
                    white-space: nowrap; background-image: none; background-color: #337ab7; 
                    border: 1px solid #337ab7; margin-right: 10px;">Check Request</a>
            </td>

        """ % ( self.salesperson_id.name , self.gift_item  , self.retailer_id.name, self.distributer_id.name, report_check)
  
        subject = "Gift Delivery to %s ( %s )- ( %s )"  % (self.retailer_id.name, self.distributer_id.name, todaydate)

        self.send_generic_mail(subject, full_body, email_from, email_to)


    @api.multi
    def send_user_mail(self):
        email_from = self.salesperson_id.email
        email_to = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).confirmation_mail

        full_body = """ <p>Hi Team,</p> <br/>
            <p><b>%s</b> has confirmed that Gift of  <b>%s</b> dated <b>%s</b> 
            has been delivered to <b>%s</b> (<b>%s</b>) at its given delivery address.</p> <br/>

        """ % ( self.salesperson_id.name , self.gift_item , todaydate , self.retailer_id.name, self.distributer_id.name)

        subject = "[Confirmation] Gift Delivered to %s  ( %s )- ( %s )"  % (self.retailer_id.name, self.distributer_id.name, todaydate)

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


    @api.model
    def get_user_gift_details(self):
        uid = request.session.uid
        cr = self.env.cr

        user_id = self.env['res.users'].sudo().search_read([('id', '=', uid)], limit=1)
        working_lines = self.env['wp.scheme.working.line']
              
        date_today = datetime.today()
        date_from = datetime.today().replace(day=1)
        date_to = datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1])

        gift_count = working_lines.sudo().search_count([('salesperson_id', '=', uid), ('state', '=', 'approved')])
        gift_count_submitted = working_lines.sudo().search_count([('salesperson_id', '=', uid), ('state', '=', 'submitted')])

        if user_id:
            data = {
                'gift_count': gift_count,
                'gift_count_submitted': gift_count_submitted,             
            }
            user_id[0].update(data)

        return user_id