# -*- coding: utf-8 -*-

import random
from odoo.exceptions import UserError, Warning, ValidationError
from odoo import models, fields, tools, api,  _ , registry, SUPERUSER_ID
from datetime import datetime, timedelta, date
import pandas as pd
import time
from cStringIO import StringIO
import xlwt
import re
import base64
from odoo.http import request
from werkzeug import url_encode
import ast
from xlrd import open_workbook

# import cv2
# from PIL import Image
# from pyzbar.pyzbar import decode
# from iteration_utilities import duplicates

list_barcode= []
rejected_barcode = []
todaydate = "{:%d-%b-%y}".format(datetime.now())

STATE = [('draft', 'Draft'), 
		  ('generated', 'Generated'), 
		  ('create', 'Created'), 
		  ('update', 'Updated'), 
		  ('reject', 'Rejected')]

class barcode_marketing(models.Model):
	_name = "barcode.marketing"
	_inherit = 'mail.thread'
	_description= "QR Code Generate"
	_order = 'id desc'

	name = fields.Char('Sequence No')
	date = fields.Date('Date', default=lambda self: fields.datetime.now())
	barcode = fields.Integer('No Of Sequence')
	attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
	datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
	report = fields.Binary('Prepared file', filters='.xls', readonly=True)
	state = fields.Selection([('draft', 'Draft'), ('generated', 'Generated'), ('print', 'Printed')], default='draft')
	amount= fields.Float('Coupon Worth')
	product_name = fields.Char('Product')
	lines_one2many = fields.One2many('barcode.marketing.line', 'barcode_marketing_id', string='Barcode Lines')

	@api.depends('date','barcode')
	@api.multi
	def _get_name(self):
		rep_name = "Barcode_Report"
		for res in self:
			# if not res.name:
				if res.date and res.barcode and not res.name:
					rep_name = "QRcode Sequences (%s)(%s Rupees) - %s.xls" % (res.date,res.amount,res.id)
				res.name = rep_name

	@api.multi
	def generate_barcode(self):
		start = time.time()
		order_lines = []
		count = self.barcode
		if self.date and self.amount:
			self.name = "QRcode Sequences (%s)(%s Rupees) - %s.xls" % (self.date,self.amount,self.id)

		count_no = 0
		# self.env.cr.execute("SELECT name FROM barcode_marketing_line ")
		# sequence_name = [int(x[0]) for x in self.env.cr.fetchall()]

		while len(order_lines) < count:
			random_numbers = random.randint(1000000000000,9999999999999)

			# if sequence_name.count(random_numbers) == 0:
			# 	print "aaaaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbb"


			order_lines.append((0, 0, {
											'name': random_numbers, 
											'date': self.date,
											'amount': self.amount,
											'barcode_marketing_id': self.id,
											'product_name': self.product_name

											}))
			count_no += 1
			print "----------------Line count_no" , count_no

			
		self.lines_one2many = order_lines
		self.state = 'generated'
		end = time.time()
		print "-------------------------------- generate_barcode TIME" , end-start



	@api.multi
	def print_report(self):
		start = time.time()
		self.ensure_one()
		if self.date and self.barcode:
			if not self.attachment_id:
				workbook = xlwt.Workbook(encoding='utf-8')
				worksheet = workbook.add_sheet('Qrcode Details')
				fp = StringIO()

				header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; \
					borders: bottom thin, top thin, left thin, right thin')
				base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')

				row_index = 0
				worksheet.col(0).width = 12000
				header_fields = ['Sequence No']
				row_index += 1
				
				for index, value in enumerate(header_fields):
					worksheet.write(row_index, index, value, header_style)
				row_index += 1

				barcode_marketing_ids = [x.name for x in self.env['barcode.marketing.line'].sudo().search([('date','=',self.date),
					('barcode_marketing_id','=',self.id)])]
				
				if (not barcode_marketing_ids):
					raise Warning(_('Record Not Found'))

				for barcode_marketing_id in barcode_marketing_ids:
					worksheet.write(row_index, 0,int(barcode_marketing_id), base_style)
					row_index += 1

				row_index +=1
				workbook.save(fp)

			out = base64.encodestring(fp.getvalue())
			self.write({'report': out,'state':'print'})
		end = time.time()
		print "---------------print_report TIME --------" , end-start



class barcode_marketing_line(models.Model):
	_name = "barcode.marketing.line"
	_description= "QR Code Lines"

	name = fields.Char('Sequence No' )
	sequence_no = fields.Integer('Sequence')
	date = fields.Date('Date')
	updated_date = fields.Date('Updated Date')
	barcode_marketing_id = fields.Many2one('barcode.marketing', string="Barcode", ondelete='cascade')
	barcode_check_id = fields.Many2one('barcode.marketing.check', string="Scan ID")
	barcode_check2_id = fields.Many2one('barcode.marketing.check', string="Scan ID 2")
	partner_id = fields.Many2one('res.partner',  string="Partner")
	flag = fields.Boolean('Flag')
	second_flag = fields.Boolean('Second Flag')
	amount= fields.Float('Coupon Worth')
	product_name = fields.Char('Product')
	state = fields.Selection(STATE, default='draft')
	recheck_bool = fields.Boolean('Coupon Recheck Bool')
	rechecked_date = fields.Date('Rechecked Date')
	barcode_recheck_id = fields.Many2one('barcode.marketing.check', string="ReCheck ID")


class barcode_marketing_check(models.Model):
	_name = "barcode.marketing.check"
	_inherit = 'mail.thread'
	_description= "QR Code Scan"
	_order = 'id desc'

	name = fields.Char('Name')
	barcode = fields.Char('Barcode')
	accepted = fields.Text('Accepted', copy=False)
	rejected = fields.Text('Rejected', copy=False)
	duplicated = fields.Text('Duplicated', copy=False)
	previously_scanned = fields.Text('Previously Scanned', copy=False)
	old_scanned = fields.Text('Old Scanned', copy=False)
	flag = fields.Boolean('Flag', copy=False)
	date = fields.Date('Date', default=lambda self: fields.datetime.today())
	partner_id = fields.Many2one('res.partner',  string="Partner")
	bp_code = fields.Char(string="Partner Code" , compute="onchange_partner_id", copy=False)
	accepted_count = fields.Char('Accepted Count', compute="onchange_accepted_data", copy=False)
	rejected_count = fields.Char('Rejected Count', compute="onchange_rejected_data", copy=False)
	duplicated_count = fields.Char('Duplicated Count', compute="onchange_duplicated_data", copy=False)
	previously_scanned_count = fields.Char('Previously Scanned Count', compute="onchange_previously_scanned_data", copy=False)
	old_scanned_count = fields.Char('Old Scanned Count', compute="onchange_old_scanned_data", copy=False)
	state = fields.Selection([('draft', 'Draft'), 
								('recheck', 'Rechecked'), 
								('create', 'Created'), 
								('update', 'Updated'), 
								('reject', 'Rejected'),
								('cn_raised', 'CN Raised'),], default='draft')
	amount= fields.Float('Coupon Worth', copy=False)
	net_amount= fields.Float('Net Coupon Worth', copy=False)
	total_amount= fields.Float('Total Coupon Worth', copy=False)
	manual_count = fields.Integer('Manual Count')
	count_accepted = fields.Integer('Accepted')
	count_rejected = fields.Char('Rejected' , related='rejected_count')
	count_duplicated = fields.Char('Duplicated' , related='duplicated_count')
	count_previously_scanned = fields.Char('Previously Scanned' , related='previously_scanned_count')
	count_old_scanned = fields.Char('Old Scanned' , related='old_scanned_count')

	charge = fields.Selection([('tr', 'Token Reimbursment'), ('scd', 'Scratch Card Discount')])
	imported = fields.Boolean('Imported', default=False)
	qrcode_image = fields.Binary("Qr Image", attachment=True)

	output_file = fields.Binary('Prepared file', filters='.xls', attachment=True, copy=False)
	export_file = fields.Char(string="Export")

	user_id = fields.Many2one('res.users', string='User', index=True, track_visibility='onchange',
	 default=lambda self: self.env.user)
	lines_one2many = fields.One2many('barcode.scan.lines', 'check_line_id', string='Check Lines')
	mobile_bool = fields.Boolean('Mobile Bool')
	recheck_bool = fields.Boolean('Coupon Recheck')


	@api.multi
	def unlink(self):
		for order in self:
			if order.state not in  ('draft','create') and self.env.uid != 1:
				raise UserError(_('You can only delete Draft / Created Entries'))
		return super(barcode_marketing_check, self).unlink()

	@api.multi
	def set_to_draft(self): #Set To Draft
		if self.state in ('create','recheck'):
			self.state = 'draft'
		else:
			raise Warning("Record can be set to draft only in 'Created' State")

	@api.multi
	@api.onchange('partner_id')
	def onchange_partner_id(self):
		if self.partner_id:
			self.bp_code = self.partner_id.bp_code
		else:
			self.bp_code = False


	@api.multi
	def add_lines(self):
		start = time.time()
		todaydate = "{:%Y-%m-%d}".format(datetime.now())
		total_amount_list = []
		net_amount_list = []
		list_barcode_scan = []
		rejected_barcode_scan = []
		duplicated_barcode_scan = []
		previously_scanned_barcode = []
		old_scanned_barcode = []
		barcode_found = []
		net_amount_total = net_amount_new = net_amount_old = 0
		amount_commission_total = amount_commission_new = amount_commission_old = 0

		receipt_name = self.partner_id.name + ' (' + todaydate + ')'

		if not self.output_file:
			raise Warning('Attach the Qrcode file')

		if self.state == 'draft':
			wb = open_workbook(file_contents = base64.decodestring(self.output_file))
			sheet = wb.sheets()[0]
			arrayofvalues = sheet.col_values(0, 1)

			try:
				all_barcodes = [barcode.encode('utf-8').strip() for barcode in arrayofvalues]
			except:
				all_barcodes = [str(barcode).encode('utf-8').strip() for barcode in arrayofvalues]

			barcode_accepted_list = [ x for x in all_barcodes  if x.isdigit()  ]
			# barcode_duplicated_list = list(duplicates(all_barcodes))
			# barcode_duplicated_list = [all_barcodes if arrayofvalues.count(barcode) > 1]
			barcode_duplicated_list = list(pd.Series(all_barcodes)[pd.Series(all_barcodes).duplicated()].values)
			barcode_rejected_list = [ x for x in  all_barcodes if not x.isdigit()  ]

			barcode_ids = self.env['barcode.marketing.line'].sudo().search([('name','in', barcode_accepted_list)])
			barcode_found = [x.name for x in barcode_ids]

			barcode_rejected = ','.join(map(str, [i for i in barcode_accepted_list if i not in barcode_found]  ))
			if len(barcode_rejected) != 0:
				barcode_rejected_list.append(barcode_rejected)


			if not barcode_ids:
				raise Warning('No Records Found. \n Check the Sheet')

			for rec in barcode_ids:
				barcode = rec.name.encode('utf-8').strip()

				if rec.flag == False:
					list_barcode_scan.append(barcode)
					
					# amount_commission = float(rec.amount) + (float(rec.amount)*10/100)
					# net_amount_list.append(rec.amount)
					# total_amount_list.append(amount_commission)
					amount_commission_new = float(rec.amount) + (float(rec.amount)*10/100)
					net_amount_new = float(rec.amount)
					net_amount_list.append(net_amount_new)
					total_amount_list.append(amount_commission_new)

				elif rec.flag == True:
					if rec.barcode_marketing_id.id in (10,11) and rec.second_flag == False:
						old_scanned_barcode.append(barcode)
						amount_commission_old = float(rec.amount) + (float(rec.amount)*10/100)
						net_amount_old = float(rec.amount)
						net_amount_list.append(net_amount_old)
						total_amount_list.append(amount_commission_old)
					else:
						previously_scanned_barcode.append(barcode)

			if len(barcode_rejected_list) != 0: 
				self.count_rejected = len(barcode_rejected_list)
				self.rejected = barcode_rejected_list

			if len(old_scanned_barcode) != 0: 
				self.count_old_scanned = len(old_scanned_barcode)
				self.old_scanned = old_scanned_barcode
			
			if len(barcode_duplicated_list) != 0: 
				self.count_duplicated = len(barcode_duplicated_list)
				self.duplicated = barcode_duplicated_list

			if len(previously_scanned_barcode) != 0: 
				self.count_previously_scanned = len(previously_scanned_barcode)
				self.previously_scanned = previously_scanned_barcode

			if len(list_barcode_scan) != 0: 
				self.count_accepted = len(list_barcode_scan)
				self.accepted = list_barcode_scan
			
			self.total_amount = sum(total_amount_list)
			self.net_amount = sum(net_amount_list)
			self.state = 'create'
			self.name = receipt_name
			self.charge = 'scd'
			# self.update_records()

		if sum(total_amount_list) > 0 :
			self.send_for_approval()
			print "---------------- Mail Sent to Aprrover - Coupon" 
		else:
			raise Warning("Total Amount is 0.0. \n Check Whether you have uploaded the same file twice. \n \
				Click on 'SUBMIT' Button once again. ")
			
		end = time.time()
		print "------------------add_lines --- TIME---------" , end - start

	@api.multi
	def recheck_records(self):
		start = time.time()
		accepted  = []
		warning_list = []
		if self.state in ('recheck','update', 'cn_raised'):
			raise Warning('You Cannot Update an already Updated/CN Raised Record.')

		if self.accepted :
			accepted = ast.literal_eval(self.accepted)
			accepted_list = [str(n).strip() for n in accepted]
			line_ids = self.env['barcode.marketing.line']

			warning_list = [x.name for x in line_ids.sudo().search([('name','in',accepted_list), ('recheck_bool','=', True)]) ]
			self.warning_already_scanned(warning_list, self.accepted_count)

			line_ids.sudo().search([('name','in',accepted_list), ('recheck_bool','=', False)]).write({
						'recheck_bool': True,
						'barcode_recheck_id': self.id,
						'rechecked_date': self.date,
						})

			# rechecked_date = date.today()
			# tuple_accepted_list = tuple([str(n).strip() for n in accepted])
			# self.env.cr.execute("""UPDATE barcode_marketing_line SET recheck_bool= True, \
			#  barcode_recheck_id = %s , rechecked_date='%s' WHERE name in %s """ % (self.id, rechecked_date, tuple_accepted_list))


			self.state = 'recheck'
			self.name = "Recheck Qrcode - (%s)" % (self.date)

		elif not self.rejected and not self.manual_count:
			raise Warning('No Qrcode Scanned')

		end = time.time()
		print "----------------------------recheck_records TIME------------------------" , end - start



	@api.multi
	def update_records(self):
		start = time.time()
		accepted  = []
		warning_list = []
		line_ids = self.env['barcode.marketing.line']
		if self.state in ('update', 'cn_raised'):
			raise Warning('You Cannot Update an already Updated/CN Raised Record.')

		if not self.mobile_bool:
			if not self.partner_id: raise Warning('Select a partner to link the QRcodes')
			
			if not self.charge: raise Warning('Select a Charge to the record For CN Automation')

			if not self.amount: raise Warning('Enter Coupon Worth amount')

			self.name = "Qrcode Check - %s - (%s)" % (self.partner_id.name,self.date)
			self.total_amount = ( float(self.count_accepted) + float(self.manual_count)) * float(self.amount)

			if self.manual_count and not self.accepted:
				self.state = 'update'

		if self.accepted or self.old_scanned or self.manual_count:
			if self.accepted :
				accepted = ast.literal_eval(self.accepted)
				accepted_list = [str(n).strip() for n in accepted]

				warning_list = [x.name for x in line_ids.sudo().search([('name','in', accepted_list), ('flag','=', True)]) ]
				if warning_list: self.warning_already_scanned(warning_list, self.accepted_count)

				barcode_ids = line_ids.sudo().search([('name','in',accepted_list), ('flag','=', False)]).write({
							'flag': True,
							'partner_id': self.partner_id.id,
							'state': 'update',
							'barcode_check_id': self.id,
							'updated_date': self.date,
							})

			if self.old_scanned :
				old_scanned = ast.literal_eval(self.old_scanned)
				old_scanned_list = [str(n).strip() for n in old_scanned]

				warning_list = [x.name for x in line_ids.sudo().search([('name','in', old_scanned_list), ('second_flag','=', True)]) ]
				if warning_list: self.warning_already_scanned(warning_list, self.old_scanned_count)

				old_scanned_barcode_ids = line_ids.sudo().search([('name','in',old_scanned_list), ('second_flag','=', False)]).write({
							'second_flag': True, 'barcode_check2_id': self.id,})

			self.state = 'update'
				
		else:
			raise Warning('No Qrcode Scanned')

		if self.mobile_bool: self.approval_mail()

		end = time.time()
		print "--------------------- update_records TIME-----------------" , end - start


	@api.multi
	def reject_records(self): #Rollover
		if self.accepted or self.old_scanned or self.manual_count:
			if self.accepted :
				barcode_ids = self.env['barcode.marketing.line'].sudo().search([('barcode_check_id','=',self.id)]).write({
						'flag': False,
						'partner_id': False,
						'state': 'create',
						'barcode_check_id': False,
						'updated_date': False,
						})

			if self.old_scanned :
				old_barcode_ids = self.env['barcode.marketing.line'].sudo().search([('barcode_check2_id','=',self.id)]).write({
						'second_flag': False, 'barcode_check2_id': False, })

			self.state = 'create'
		else:
			raise Warning('No Qrcode Scanned or Found to Rollover')


	@api.multi
	def refuse_records(self):
		accepted  = []
		if self.accepted :
			accepted = ast.literal_eval(self.accepted)
			accepted_list = [str(n).strip() for n in accepted]
			barcode_ids = self.env['barcode.marketing.line'].sudo().search([('name','in',accepted_list)]).write({
					'flag': True,
					'partner_id': self.partner_id.id,
					'state': 'reject',
					'barcode_check_id': self.id,
					'updated_date': self.date,
					})
			self.state = 'reject'

		elif not self.rejected and not self.manual_count:
			raise Warning('No Qrcode Scanned')

	def warning_already_scanned(self, warning_list, accepted_count):
		if warning_list:
			a= '\n'.join(map(str, warning_list))
			raise Warning("Some Coupons are already Scanned and Updated. \n \
				Total Coupons Repeated : %s \n \
				Total Coupons Scanned : %s \n \n \
				Following Coupons are Repeated : \n %s " % (len(warning_list), accepted_count, a))


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
			if res.recheck_bool:
				if res.barcode :
					barcode = int(res.barcode.encode('utf-8').strip())
					barcode_ids = res.env['barcode.marketing.line'].sudo().search([('name','=',res.barcode),('recheck_bool','=',False)])
					if barcode_ids:
						if barcode in list_barcode:
							raise Warning('Same barcode scanned twice')
						list_barcode.append(barcode)
					else:
						raise Warning('Coupon already Rechecked. Keep it seperate and submit to Sales Support Team')

					res.accepted = list_barcode
					res.barcode = ''
			else:
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
	@api.onchange('accepted')
	def onchange_accepted_data(self):
		accepted  = []
		accepted_rec_list =[]
		accepted_ting = []
		
		for res in self:
			if res.accepted :
				a = res.accepted.strip('[')
				c = a.strip(']')
				accepted.append(c.encode('utf-8').strip())
				for rec in accepted:
					count_accepted = 0
					accepted_ting = rec.split(',')
					accepted_rec_list.append(rec)
					for record in accepted_ting:
						record1 = record.lstrip()
						count_accepted += 1
						res.accepted_count = count_accepted
						res.count_accepted = count_accepted
				print "---------- count_accepted " , count_accepted


	@api.multi
	@api.onchange('rejected')
	def onchange_rejected_data(self):
		rejected  = []
		rejected_rec_list =[]
		
		for res in self:
			if res.rejected :
				a = res.rejected.strip('[')
				c = a.strip(']')
				rejected.append(c.encode('utf-8').strip())
				for rec in rejected:
					count_rejected = 0
					rejected_ting = rec.split(',')
					rejected_rec_list.append(rec)
					for record in rejected_ting:
						count_rejected += 1
						res.rejected_count = count_rejected

				print "---------- Rejected" , count_rejected


	@api.multi
	@api.onchange('duplicated')
	def onchange_duplicated_data(self):
		duplicated  = []
		duplicated_rec_list =[]
		duplicated_ting = []
		
		for res in self:
			if res.duplicated :
				a = res.duplicated.strip('[')
				c = a.strip(']')
				duplicated.append(c.encode('utf-8').strip())
				for rec in duplicated:
					count_duplicated = 0
					duplicated_ting = rec.split(',')
					duplicated_rec_list.append(rec)
					for record in duplicated_ting:
						count_duplicated += 1
						res.duplicated_count = count_duplicated

				print "---------- Duplicated" , count_duplicated


	@api.multi
	@api.onchange('previously_scanned')
	def onchange_previously_scanned_data(self):
		previously_scanned  = []
		previously_scanned_rec_list =[]
		previously_scanned_ting = []
		
		for res in self:
			if res.previously_scanned:
				a = res.previously_scanned.strip('[')
				c = a.strip(']')
				previously_scanned.append(c.encode('utf-8').strip())
				for rec in previously_scanned:
					count_previously_scanned = 0
					previously_scanned_ting = rec.split(',')
					previously_scanned_rec_list.append(rec)
					for record in previously_scanned_ting:
						count_previously_scanned += 1
						res.previously_scanned_count = count_previously_scanned

				print "---------- Previously Scanned" , count_previously_scanned

	@api.multi
	@api.onchange('old_scanned')
	def onchange_old_scanned_data(self):
		old_scanned  = []
		old_scanned_rec_list =[]
		old_scanned_ting = []
		
		for res in self:
			if res.old_scanned:
				a = res.old_scanned.strip('[')
				c = a.strip(']')
				old_scanned.append(c.encode('utf-8').strip())
				for rec in old_scanned:
					count_old_scanned = 0
					old_scanned_ting = rec.split(',')
					old_scanned_rec_list.append(rec)
					for record in old_scanned_ting:
						count_old_scanned += 1
						res.old_scanned_count = count_old_scanned

				print "---------- OLD Scanned" , count_old_scanned

				
	@api.multi
	def send_for_approval(self):
		subject = "Coupon Codes Scanned - %s ( %s )"  % (self.partner_id.name, todaydate)
		approver = self.env['credit.note.approver'].search([("id","!=",0)])

		if len(approver) < 1:
			raise ValidationError("Approval Config doesnot have any Approver. Configure the Approvers and Users ")

		support_email = [x.approver.email for x in approver]
		email_to = ",".join(support_email)

		greeting_body = """
				<p>Hi Team,</p><br/>
				<p>I have submitted the Coupons from <b>%s</b> which are worth Rs. <b>%s</b>.</p><br/>
			""" % ( self.partner_id.name, self.total_amount)

		self.send_generic_mail(subject, email_to, greeting_body)


	@api.multi
	def approval_mail(self):
		subject = "[Approved] Coupon Codes Scanned - %s ( %s )"  % (self.partner_id.name, todaydate)
		cn_user = self.env['credit.note.user'].search([("id","!=",0)])

		if len(cn_user) < 1:
			raise ValidationError("User Config doesnot have any user. Configure the Approvers and Users from CN Config")

		support_email = [x.user.email for x in cn_user]
		email_to = ",".join(support_email)

		greeting_body = """
				<p>Hi Team,</p><br/>
				<p>I have Approved the Coupons from <b>%s</b> which are worth Rs. <b>%s</b> scanned by <b>%s</b>.</p><br/>
			""" % ( self.partner_id.name, self.total_amount, self.user_id.name)

		self.send_generic_mail(subject, email_to, greeting_body)


	@api.multi
	def send_generic_mail(self,subject, email_to, greeting_body):
		main_id = self.id
		email_from = self.env.user.email

		imd = self.env['ir.model.data']
		action = imd.xmlid_to_object('sales_meet.action_barcode_marketing_check_mobile')
		form_view_id = imd.xmlid_to_res_id('sales_meet.view_barcode_marketing_check_form_mobile')
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

		report_check = base_url + '/web#%s' % (url_encode({
				'model': self._name,
				'view_type': 'form',
				'id': main_id,
				'action' : action.id
			}))

		main_body = """
				<td>
					<a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
					font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
					text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
					text-align: center; vertical-align: middle; cursor: pointer; 
					white-space: nowrap; background-image: none; background-color: #337ab7; 
					border: 1px solid #337ab7; margin-right: 10px;">Check Request</a>
				</td>
			""" % (report_check)

		full_body = greeting_body + main_body
		composed_mail = self.env['mail.mail'].sudo().create({
				'model': self._name,
				'res_id': main_id,
				'email_from': email_from,
				'email_to': email_to,
				'subject': subject,
				'body_html': full_body,
			})

		composed_mail.sudo().send()
		print "---------------------------------- Mail Sent to" , email_to


	@api.model
	def get_scan_details(self):
		uid = request.session.uid
		cr = self.env.cr

		user_id = self.env['res.users'].sudo().search_read([('id', '=', uid)], limit=1)
		draft_scan_count = self.env['barcode.marketing.check'].sudo().search_count([('user_id', '=', uid),('state', '=', 'draft')])
		create_scan_count = self.env['barcode.marketing.check'].sudo().search_count([('user_id', '=', uid),('state', '=', 'create')])
		done_scan_count = self.env['barcode.marketing.check'].sudo().search_count([('user_id', '=', uid),('state', '=', 'update')])
		cn_raised_scan_count = self.env['barcode.marketing.check'].sudo().search_count([('user_id', '=', uid),('state', '=', 'cn_raised')])
		scan_view_id = self.env.ref('sales_meet.view_barcode_marketing_check_form_mobile')
		
		if user_id:
			data = {
				'draft_scan_count': draft_scan_count,
				'create_scan_count': create_scan_count,	
				'done_scan_count': done_scan_count,	
				'cn_raised_scan_count': cn_raised_scan_count,	
				'scan_view_id': scan_view_id.id,		  
			}
			user_id[0].update(data)

		return user_id

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

	# @api.multi
	# def qr_code_check(self):
	# 	data = decode(Image.open(self.qrcode_image))
	# 	print(data)
	# 	print(data[0][0])


class barcode_scan_lines(models.Model):
	_name = "barcode.scan.lines"
	_description= "QR Scan Lines"
	_order = 'id desc'

	name = fields.Char('Sequence No' )
	sequence_no = fields.Integer('Sequence')
	date = fields.Date('Date')
	check_line_id = fields.Many2one('barcode.marketing.check', string="Barcode Check", ondelete='cascade')
	partner_id = fields.Many2one('res.partner',  string="Partner")
	flag = fields.Boolean('Flag')
	amount= fields.Float('Coupon Worth')
	product_name = fields.Char('Product')
	state = fields.Selection(STATE, default='draft')