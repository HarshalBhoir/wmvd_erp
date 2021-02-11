# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2014-Today BrowseInfo (<http://www.browseinfo.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
from odoo.tools.translate import _
from odoo import tools, api
from odoo import api, fields, models, _ , registry, SUPERUSER_ID
from odoo.osv import  osv
# import erppeek
import logging
import xmlrpclib

_logger = logging.getLogger(__name__)

import shutil
import os
import time
import psycopg2
import urllib
import tarfile


class db_connect(models.Model):
	_name = "db.connect"

	# portal_user = fields.Boolean("Portal User" , default=False)
	name = fields.Char('Name')
	db_name = fields.Char('DB Name')

	@api.multi
	def get_data_from_database(self):

	    # with registry('odoo10manishademo') as new_cr:

		password = "admin"
		server = "http://localhost:2000"
		user = "admin"
		host = 'localhost'
		dbname = "odoo10manishademo"

		conn_pg = psycopg2.connect("dbname= 'odoo10manishademo' user=postgres password=postgres host= 'localhost' ")
		pg_cursor = conn_pg.cursor()
		pg_cursor.execute("select * from sale_order")
		sale_order = pg_cursor.fetchall()

		print "KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK" , sale_order
		# for sale


		# db_model = self.env['base.external.dbsource'].search([])

		# print "KKKKKKKKKKKKKKKKKKKKK" , db_model

		# conn = pg.DB(host="localhost", user="USERNAME", passwd="PASSWORD", dbname="DBNAME")

		# result = conn.query("SELECT fname, lname FROM employee")

		# for firstname, lastname in result.getresult() :
		#     print firstname, lastname

		# conn.close()

		# https://www.cybrosys.com/blog/document-management-system



    

