# -*- coding: utf-8 -*-

import random
from odoo.exceptions import UserError, Warning, ValidationError
from odoo import models, fields, tools, api,  _ , registry, SUPERUSER_ID
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT

import time
from dateutil import relativedelta
from cStringIO import StringIO
import xlwt
import re
import base64
import pytz
import json
import odoo.http as http
from odoo.http import request

import cv2
from PIL import Image
from pyzbar.pyzbar import decode
from xlrd import open_workbook


class barcode_marketing(models.Model):
	_name = "barcode.marketing"
	_inherit = 'mail.thread'
	_description= "QR Code Generate"

	name = fields.Char('Sequence No', compute="_get_name")
	date = fields.Date('Date', default=lambda self: fields.datetime.now())
	barcode = fields.Integer('No Of Sequence')
	attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
	datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
	report = fields.Binary('Prepared file', filters='.xls', readonly=True)
	state = fields.Selection([('draft', 'Draft'), ('generated', 'Generated'), ('print', 'Printed')], default='draft')
	amount= fields.Float('Coupon Worth')
	product_name = fields.Char('Product')

	@api.depends('date','barcode')
	@api.multi
	def _get_name(self):
		rep_name = "Barcode_Report"
		for res in self:
			# if not res.name:
				if res.date and res.barcode and not res.name:
					rep_name = "Barcode Sequences (%s)(%s Rupees) - %s.xls" % (res.date,res.amount,res.id)
				res.name = rep_name

	@api.multi
	def generate_barcode(self):
		list_no = []
		count = self.barcode
		count_no = 0
		for m in range(count):
			random_numbers = random.randint(1000000000000,9999999999999)
			self.state = 'generated'
			count_no += 1
			print "LLLLLLLLLLLLLLLLl count_no" , count_no
			payment = self.env['barcode.marketing.line'].create({
															'name': random_numbers, 
															'date': self.date,
															'amount': self.amount 
															,'barcode_marketing_id': self.id})



	@api.multi
	def print_report(self):
		
		self.ensure_one()
		if self.date and self.barcode:
			if not self.attachment_id:
				workbook = xlwt.Workbook(encoding='utf-8')
				worksheet = workbook.add_sheet('Meeting Details')
				fp = StringIO()

				header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
				base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')

				row_index = 0
				worksheet.col(0).width = 12000

				header_fields = ['Sequence No']
				row_index += 1
				
				for index, value in enumerate(header_fields):
					worksheet.write(row_index, index, value, header_style)
				row_index += 1

				barcode_marketing_ids = self.env['barcode.marketing.line'].sudo().search([('date','=',self.date),
					('barcode_marketing_id','=',self.id)])
				
				if (not barcode_marketing_ids):
					raise Warning(_('Record Not Found'))

				if barcode_marketing_ids:
					count = 0		
					for barcode_marketing_id in barcode_marketing_ids:
						new_index = row_index
						if barcode_marketing_id:
							count +=1
							worksheet.write(row_index, 0,int(barcode_marketing_id.name), base_style)
							row_index += 1

				row_index +=1
				workbook.save(fp)

			out = base64.encodestring(fp.getvalue())
			self.write({'report': out,'state':'print'})
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'barcode.marketing',
				'view_mode': 'form',
				'view_type': 'form',
				'res_id': self.id,
				'views': [(False, 'form')],
			}


class barcode_marketing_line(models.Model):
	_name = "barcode.marketing.line"
	_description= "QR Code Lines"

	name = fields.Char('Sequence No' )
	sequence_no = fields.Integer('Sequence')
	date = fields.Date('Date')
	barcode_marketing_id = fields.Many2one('barcode.marketing', string="Barcode", ondelete='cascade')
	partner_id = fields.Many2one('res.partner',  string="Partner")
	flag = fields.Boolean('Flag')
	amount= fields.Float('Coupon Worth')
	product_name = fields.Char('Product')


list_barcode= []
rejected_barcode = []

class barcode_marketing_check(models.Model):
	_name = "barcode.marketing.check"
	_inherit = 'mail.thread'
	_description= "QR Code Scan"
	_order = 'id desc'


	# @api.multi
	# def _get_name(self):
	# 	rep_name =''
	# 	for res in self:
	# 		if not res.name and res.partner_id:
	# 			rep_name = "Barcode Check - %s" % (res.partner_id.name)
	# 		res.name = rep_name

	name = fields.Char('Name')
	barcode = fields.Char('Barcode')
	accepted = fields.Text('Accepted')
	rejected = fields.Text('Rejected')
	flag = fields.Boolean('Flag')
	date = fields.Date('Date', default=lambda self: fields.datetime.now())
	partner_id = fields.Many2one('res.partner',  string="Partner")
	accepted_count = fields.Char('Accepted Count', compute="onchange_accepted_data")
	rejected_count = fields.Char('Rejected Count', compute="onchange_rejected_data")
	state = fields.Selection([('draft', 'Draft'), ('create', 'Created'), ('update', 'Updated')], default='draft')
	amount= fields.Float('Coupon Worth')
	total_amount= fields.Float('Total Coupon Worth')
	manual_count = fields.Integer('Manual Count')
	count_accepted = fields.Integer('Accepted')
	count_rejected = fields.Char('Rejected' , related='rejected_count')
	charge = fields.Selection([('tr', 'Token Reimbursment'), ('scd', 'Scratch Card Discount')])
	imported = fields.Boolean('Imported', default=False)
	qrcode_image = fields.Binary("Qr Image", attachment=True)

	output_file = fields.Binary('Prepared file', filters='.xls', attachment=True)
	export_file = fields.Char(string="Export")

	user_id = fields.Many2one('res.users', string='User', index=True, track_visibility='onchange', default=lambda self: self.env.user)

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


					# print "kkkkkkkkkdddddddddddddddddddddddddd" , col_value[0]

					barcode = int(col_value[0].encode('utf-8').strip())
					barcode_ids = self.env['barcode.marketing.line'].sudo().search([('name','=',barcode),('flag','=',False)])
					if barcode_ids:
						# if barcode in list_barcode:
						# 	raise Warning('Same barcode scanned twice')
						list_barcode.append(barcode)
					else:
						rejected_barcode.append(barcode)
						self.rejected = rejected_barcode
						# raise Warning('No Coupon is available for this barcode')

					self.accepted = list_barcode
					

					self.name = receipt_name
					# self.state = 'generated_invoice_template'

		print "11111111111111111111111111111111111111111111111111111111111" , self.accepted , self.rejected
						
	

	@api.multi
	@api.onchange('barcode')
	def onchange_name(self):
		list_barcode_temp= []
		rejected_barcode_temp = []
		if not self.accepted:
			list_barcode = list_barcode_temp
		else:
			global list_barcode
		for res in self:
			if res.barcode :
				barcode = int(res.barcode.encode('utf-8').strip())
				barcode_ids = res.env['barcode.marketing.line'].sudo().search([('name','=',res.barcode),('flag','=',False)])
				if barcode_ids:
					if barcode in list_barcode:
						raise Warning('Same barcode scanned twice')
					list_barcode.append(barcode)
				else:
					raise Warning('No Coupon is available for this barcode')

				res.accepted = list_barcode
				res.barcode = ''


	@api.multi
	def clear_records(self):
		rejected_barcode_temp = []
		if not self.rejected:
			rejected_barcode = rejected_barcode_temp
		else:
			global rejected_barcode
		if self.barcode :
			if not self.accepted or self.barcode not in self.accepted :
				barcode = self.barcode
				rejected_barcode.append(int(barcode.encode('utf-8').strip()))
				self.rejected = rejected_barcode
				self.barcode  = ''
			else:
				self.barcode  = ''


	@api.multi
	def update_records(self):
		accepted  = []
		rec_list =[]
		for res in self:
			res.state = 'create'
			if not res.partner_id:
				raise Warning('Select a partner to link the Barcodes')

			if not res.amount:
				raise Warning('Enter Coupon Worth amount')
			if res.accepted :
				a = res.accepted.strip('[')
				c = a.strip(']')
				accepted.append(c.encode('utf-8').strip())
				for rec in accepted:
					ting = rec.split(',')
					rec_list.append(rec)
					for record in ting:
						record1 = record.lstrip()
						barcode_ids = res.env['barcode.marketing.line'].sudo().search([('name','=',record1)])
						if barcode_ids:
							barcode_ids.write({
							'flag': True,
							'partner_id': res.partner_id.id,
							})

			elif not res.rejected and not res.manual_count:
				raise Warning('No Barcode Scanned')


			rep_name = "Barcode Check - %s - (%s)" % (res.partner_id.name,res.date)
			res.name = rep_name

			res.total_amount = ( float(res.count_accepted) + float(res.manual_count)) * float(res.amount)


	@api.multi
	@api.onchange('accepted')
	def onchange_accepted_data(self):
		accepted  = []
		rec_list =[]
		
		for res in self:
			if res.accepted : #and res.state == 'draft'
				a = res.accepted.strip('[')
				c = a.strip(']')
				accepted.append(c.encode('utf-8').strip())
				for rec in accepted:
					count = 0
					ting = rec.split(',')
					rec_list.append(rec)
					for record in ting:
						record1 = record.lstrip()
						count += 1
						res.accepted_count = count
						res.count_accepted = count
						print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , res.count_accepted


			


	@api.multi
	@api.onchange('rejected')
	def onchange_rejected_data(self):
		rejected  = []
		rec_list =[]
		
		for res in self:
			if res.rejected:
			
				a = res.rejected.strip('[')
				c = a.strip(']')
				rejected.append(c.encode('utf-8').strip())
				for rec in rejected:
					count = 0
					ting = rec.split(',')
					rec_list.append(rec)
					for record in ting:
						count += 1
						res.rejected_count = count

						print "ooooooooooooooooooooooooooooooooooooooo"


	# @api.multi
	# def qr_code_check(self):
	# 	rejected_barcode_temp = []
	# 	img='opencv.png'

	# 	camera = cv2.VideoCapture(0)
	# 	for i in range(1):
	# 		return_value, image = camera.read()
	# 		cv2.imwrite(img, image)

	# 		data = decode(Image.open(img))
	# 		print(data)
	# 		print(data[0][0])
	# 	del(camera)

	@api.multi
	def qr_code_check(self):
		data = decode(Image.open(self.qrcode_image))
		print(data)
		print(data[0][0])


	# @api.multi
	# @api.onchange('rejected_count')
	# def onchange_rejected(self):
	# 	if self.count_rejected:
	# 		self.count_rejected = self.rejected_count

					
	@api.multi
	def send_approval(self):
		body = """ """
		subject = ""
		main_id = self.id

		todaydate = "{:%d-%b-%y}".format(datetime.now())
		line_html = ""
		email_from = 'sales.associates@walplast.com'

		working_line = self.line_ids.search([('working_id', '=', self.id)])

		if  len(working_line) < 1:
			raise ValidationError(_('No Records Selected'))

			
		for l in working_line:

			line_html += """
			<tr>
				<td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
				<td style="border: 1px solid black; padding-left: 5px; padding-right: 5px; text-align: center;">%s</td>
				<td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
				<td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
				<td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
				<td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
				<td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
			</tr>
			""" % (l.retailer_id.name, l.gift_item, l.brand, l.cost, l.mrp, l.tons, l.salesperson_id.name)


		body = """
			<style type="text/css">
			* {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
			</style>
			<h3>Hi Team,</h3>
			<br/>
			<h3>Following are the details as Below Listed for distributer %s in %s </h3>

			<table class="table" style="border-collapse: collapse; border-spacing: 0px;">
				<tbody>
					<tr class="text-center">
						<th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
							Retailer
						</th>
						<th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
							Gift Item
						</th>
						<th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
							Brand
						</th>
						<th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
							Cost
						</th>			 
						<th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
							MRP
						</th>
						<th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
							Tons
						</th>
						<th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
							Salesperson
						</th>
					</tr>
					%s
				</tbody>
			</table>
			<br/>


			<br/>

		""" % (self.distributer_id.name, self.company_id.name, line_html)

		subject = "Request for Retailer Working Approval - %s ( %s )"  % (self.distributer_id.name, todaydate)
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		approver = self.env['credit.note.approver'].search([("id","!=",0)])

		if len(approver) < 1:
			raise ValidationError("Approval Config doesnot have any Approver. Configure the Approvers and Users ")
	  
		for rec in approver:

			approve_url = base_url + '/retailerworking?%s' % (url_encode({
					'model': self._name,
					'working_id': main_id,
					'res_id': rec.id,
					'action': 'approve_retailer_working',
				}))
			reject_url = base_url + '/retailerworking?%s' % (url_encode({
					'model': self._name,
					'working_id': main_id,
					'res_id': rec.id,
					'action': 'refuse_retailer_working',
				}))

			report_check = base_url + '/web#%s' % (url_encode({
				'model': self._name,
				'view_type': 'form',
				'id': main_id,
			}))

			full_body = body + """<br/>
			<table class="table" style="border-collapse: collapse; border-spacing: 0px;">
				<tbody>
					<tr class="text-center">
						<td>
							<a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF;
							 border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
							  vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; 
							  border: 1px solid #337ab7; margin-right: 10px;">Approve All</a>
						</td>
						<td>
							<a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF;
							 border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
							  vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
							   margin-right: 10px;">Reject All</a>
						</td>

						<td>
							<a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
							border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
							 vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
							  margin-right: 10px;">Selective Approve/Reject</a>
						</td>

					</tr>
				</tbody>
			</table>
			""" % (approve_url, reject_url, report_check)

			composed_mail = self.env['mail.mail'].sudo().create({
					'model': self._name,
					'res_id': main_id,
					'email_from': email_from,
					'email_to': rec.approver.email,
					'subject': subject,
					'body_html': full_body,
					'auto_delete': False,
				})

			self.state='sent_for_approval'
			composed_mail.sudo().send()
