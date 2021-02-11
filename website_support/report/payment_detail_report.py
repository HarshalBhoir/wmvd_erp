from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

import datetime
from datetime import datetime, timedelta , date
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
from odoo.addons.web.controllers.main import ExcelExport


class asset_payment_details_report(models.TransientModel):
	_name = 'asset.payment.details.report'
	_description = "Asset Payment Details Report"


	name = fields.Char(string="PaymentAssetDetailsReport")
	date_from = fields.Date(string="Date From")
	date_to = fields.Date(string="Date To")
	attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
	datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
	repname = fields.Char(string="PaymentAssetDetailsReport")
	report = fields.Binary('Prepared file', filters='.xls', readonly=True)
	state = fields.Selection([('choose', 'choose'), ('get', 'get')],
							 default='choose')

	company_id = fields.Many2one('res.company', string="Company")

  
	@api.constrains('date_from','date_to')
	@api.depends('date_from','date_to')
	def date_range_check(self):
		if self.date_from and self.date_to and self.date_from > self.date_to:
			raise ValidationError(_("Start Date should be before or be the same as End Date."))
		return True
	

	@api.multi
	def print_report(self):
		
		self.ensure_one()
		status = ''
		# self.sudo().unlink()
		if not self.attachment_id:
			order_list = []
			second_heading = ''
			# file_name = self.name + '.xls'
			workbook = xlwt.Workbook(encoding='utf-8')
			worksheet = workbook.add_sheet('Payment Asset Details')
			fp = StringIO()
			
			main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
			sp_style = xlwt.easyxf('font: bold on, height 350;')
			header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
			base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
			base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
			base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')


			if (self.date_from and self.date_to) and not self.company_id  :
				payment_ids = self.env['wp.asset.payment'].sudo().search([
									('date','>=',self.date_from),
									('date','<=',self.date_to)],order="company_id ,date  asc")

			elif self.company_id and (self.date_from and self.date_to):
				# second_heading = self.current_loc_id.name 
				payment_ids = self.env['wp.asset.payment'].sudo().search([
									('company_id','=',self.company_id.id)])
			else:
				# second_heading = 'ALL Data'
				payment_ids = self.env['wp.asset.payment'].sudo().search([],order="company_id , date  asc")

		  
		#	 # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py

			

			rep_name = ''
			if self.date_from:
				date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
			if self.date_to:
				date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
			if self.date_from and self.date_to:
				if self.date_from == self.date_to:
					rep_name = "Payment Assets Details Report(%s) - %s" % (date_from,second_heading)
				else:
					rep_name = "Payment Assets Details Report(%s|%s) - %s"  % (date_from, date_to,second_heading)

			else:
				rep_name = "Payment Assets Details Report"
			self.name = rep_name

			
			worksheet.write_merge(0, 1, 0, 12, self.name ,main_style)
			row_index = 2
			
			worksheet.col(0).width = 2000
			worksheet.col(1).width = 12000
			worksheet.col(2).width = 8000
			worksheet.col(3).width = 8000
			worksheet.col(4).width = 8000
			worksheet.col(5).width = 8000
			worksheet.col(6).width = 6000
			worksheet.col(7).width = 6000
			worksheet.col(8).width = 6000
			worksheet.col(9).width = 4000
			worksheet.col(10).width = 8000
			worksheet.col(11).width = 8000
			worksheet.col(12).width = 4000
			worksheet.col(13).width = 4000
			
			# Headers
			header_fields = ['S.No','Document No','Date','Vendor','Invoice No','Company',
			'Payment Category','Payment Amount','Total Amount','Remarks','Asset','PMT Type','Description','Amount']
			row_index += 1
		 
			for index, value in enumerate(header_fields):
				worksheet.write(row_index, index, value, header_style)
			row_index += 1

		   
			if (not payment_ids):
				raise Warning(_('Record Not Found'))

			if payment_ids:

				count = 0		
				for asset_id in payment_ids:
					if asset_id:
						
						count +=1
						worksheet.write(row_index, 0,count, base_style_yellow )
						# worksheet.write_merge(row_index, row_index+len(asset_id.component_ids), 1, 1, asset_id.asset_name,  base_style_yellow)
						worksheet.write(row_index, 1,asset_id.name,  base_style_yellow )
						worksheet.write(row_index, 2,asset_id.date,  base_style_yellow )
						worksheet.write(row_index, 3,asset_id.partner_id.name or '',  base_style_yellow )
						worksheet.write(row_index, 4,asset_id.vendor_reference or '',  base_style_yellow )
						worksheet.write(row_index, 5,asset_id.company_id.name or '',  base_style_yellow )
						worksheet.write(row_index, 6,asset_id.payment_category or '',  base_style_yellow )
						# worksheet.write_merge(row_index, row_index+len(asset_id.component_ids), 6, 6, asset_id.current_loc_id.name,  base_style_yellow)
						worksheet.write(row_index, 7,asset_id.amount or '',  base_style_yellow )
						worksheet.write(row_index, 8,asset_id.amount_total or '',  base_style_yellow )
						worksheet.write(row_index, 9,asset_id.remarks or '',  base_style_yellow )
						worksheet.write(row_index, 10,'',  base_style_yellow )
						worksheet.write(row_index, 11,'',  base_style_yellow )
						worksheet.write(row_index, 12,'',  base_style_yellow )
						
						row_index += 1

						for line in asset_id.payment_line:
							worksheet.write(row_index, 0,'' )
							worksheet.write(row_index, 10,line.asset_id.asset_name or '', base_style)
							worksheet.write(row_index, 11,line.payment_type, base_style)
							worksheet.write(row_index, 12,line.description, base_style)
							worksheet.write(row_index, 13,line.amount, base_style)

							row_index += 1
						row_index += 1

			row_index +=1
			workbook.save(fp)


		out = base64.encodestring(fp.getvalue())
		self.write({'state': 'get','report': out,'repname':self.name+'.xls'})
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'asset.payment.details.report',
			'view_mode': 'form',
			'view_type': 'form',
			'res_id': self.id,
			'target': 'new',
		}
