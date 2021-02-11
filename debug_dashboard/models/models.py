# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

class debug_dashboard(models.Model):
    _name = 'debug.dashboard'

    name = fields.Char(string="Description")
    value = fields.Float(string="Value")
    state = fields.Selection([('new','New'),('opened','Opened'),('closed','Closed')],default="new")

    def to_opened(self):
    	self.state = 'opened'

    def to_closed(self):
    	self.state = 'closed'

class debug_report(models.Model):
	_name = 'fortest.debug.report'
	_auto = False

	value = fields.Float(string="Value")
	state = fields.Selection([('new','New'),('opened','Opened'),('closed','Closed')])
	count_name = fields.Integer(string="Count")

	@api.model_cr
	def init(self):
		tools.drop_view_if_exists(self._cr, 'fortest_debug_report')
		self._cr.execute("""
			CREATE OR REPLACE VIEW fortest_debug_report AS (
				SELECT
					dash.id as id,
					sum(dash.value) as value,
					count(dash.name) as count_name,
					dash.state as state
				FROM
					debug_dashboard dash		
				GROUP BY
					dash.id,
					dash.value,
					dash.name,
					dash.state )""")