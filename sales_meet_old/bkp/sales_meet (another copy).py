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
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import logging
from odoo.osv import  osv
from odoo import SUPERUSER_ID
import geocoder
from time import gmtime, strftime
import dateutil.parser
from openerp.exceptions import UserError , ValidationError
import requests
import googlemaps
import urllib
import simplejson
from geopy.geocoders import GoogleV3
import time

# googleGeocodeUrl = 'http://maps.googleapis.com/maps/api/geocode/json?'

# gmaps = googlemaps.Client(key='AIzaSyBWGBUR56Byqip7RUel5-EeWzFQygna2Hg')
# google_api_key = 'AIzaSyCt4jsSrJ9C9tIhlAg0hMerzY3lOE1yoq8'
# geocoder = GoogleV3()


datetimeFormat = '%Y-%m-%d %H:%M:%S'
google_key = 'AIzaSyAueXqmASv23IO3NSdPnVA_TNJOWADjEh8'

class sales_meet(models.Model):
    _inherit = "calendar.event"
    _order  = 'start_datetime desc'


    @api.model
    def create(self, vals):
        result = super(sales_meet, self).create(vals)
        return result

    @api.model
    def default_get(self, fields_list):
        res = super(sales_meet, self).default_get(fields_list)

        res['start_datetime'] = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        res['start'] = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        res['stop'] = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        res['expense_date'] =  datetime.now().strftime('%Y-%m-%d')
        return res

    # def _default_stage_id(self):
    #     stage = self.env['crm.stage'].search([('name','=','New')])
    #     return stage.id

    name = fields.Char('Meeting Subject', states={'done': [('readonly', True)]}, required=False, store=True, track_visibility='always') #, states={'done': [('readonly', True)]}, required=False
    checkin_lattitude = fields.Float('Checkin Latitude' , digits=(16, 5) , store=True, track_visibility='onchange') 
    checkin_longitude = fields.Float('Checkin Longitude', digits=(16, 5), store=True, track_visibility='onchange')  
    checkout_lattitude = fields.Char('Checkout Latitude')
    checkout_longitude = fields.Char('Checkout Longitude')
    # distance = fields.Char('Distance')
    timein = fields.Datetime(string="Time IN")
    timeout = fields.Datetime(string="Time OUT")
    islead = fields.Boolean("Lead")
    isopportunity = fields.Boolean("Opportunity")
    iscustomer = fields.Boolean("Customer")
    ischeck = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity'), ('customer', 'Customer')], string='Is Lead/Customer', 
         track_visibility='onchange')
    lead_id = fields.Many2one('crm.lead', string='Lead', track_visibility='always')
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', track_visibility='always')
    status = fields.Selection([('draft', 'Draft'), ('open', 'In Meeting'), ('close', 'Close')], string='Status', 
        readonly=True, track_visibility='onchange', default='draft')
    stage_id = fields.Many2one('crm.stage', string='Stage', track_visibility='onchange', index=True ) # default=lambda self: self._default_stage_id()
    meeting_duration = fields.Char('Meeting Duration' , store=True)
    source = fields.Char('Source Address' , store=True, track_visibility='always')
    source_address = fields.Char('Source Address' , store=True, track_visibility='always')
    destination = fields.Char('Destination Address' , store=True, track_visibility='always')
    destination_address = fields.Char('Destination Address', track_visibility='always')
    partner_latitude = fields.Float(string='Source Geo Latitude', digits=(16, 5) , store=True, track_visibility='always')
    partner_longitude = fields.Float(string='Source Geo Longitude', digits=(16, 5) , store=True, track_visibility='always')
    partner_dest_latitude = fields.Float(string='Dest Geo Latitude', digits=(16, 5) , store=True, track_visibility='always')
    partner_dest_longitude = fields.Float(string='Dest Geo Longitude', digits=(16, 5) , store=True, track_visibility='always')
    date_localization = fields.Date(string='Geolocation Date' , store=True, track_visibility='always')
    next_activity_id = fields.Many2one("crm.activity", string="Next Meeting Reminder", index=True, track_visibility='always')
    date_action = fields.Date('Next Activity Date', index=True, track_visibility='always')
    title_action = fields.Char('Next Activity Summary', track_visibility='always')
    categ_id = fields.Many2one('crm.activity', string="Activity", track_visibility='always')
    partner_id = fields.Many2one('res.partner', string="Customer", track_visibility='always')
    start = fields.Datetime('Start')
    stop = fields.Datetime('Stop')
    start_date = fields.Date('Start Date', compute=False, inverse=False)
    start_datetime = fields.Datetime('Start DateTime', compute=False, inverse=False)
    stop_date = fields.Date('End Date', compute=False, inverse=False)
    stop_datetime = fields.Datetime('End Datetime', compute=False, inverse=False)  # old date_deadline
    display_time = fields.Char('Event Time', compute=False)
    display_start = fields.Char('Date', compute=False)
    reverse_location = fields.Char('Current Location', track_visibility='always')
    next_flag = fields.Boolean("Next Date Flag" ) #, default=False
    expense_date = fields.Date('Expense Date')
    attach_doc_count = fields.Integer(string="Number of documents attached", compute='count_docs')
    company_id = fields.Many2one(related='user_id.company_id', store=True, readonly=True)
    # employee_id = fields.Many2one('hr.employee', string="Employee",  readonly=True,  default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    # manager_id = fields.Many2one('hr.employee', string='Approval',related='employee_id.parent_id' ,  track_visibility='onchange')

    user_name = fields.Char('User Name', related='user_id.name', readonly=True, store=True)
    participants_names = fields.Char('Participants', compute='onchange_partner', store=True)
    ishome = fields.Boolean("Home Location")
    distance = fields.Float(string='Distance',  store=True, track_visibility='always')
    duration = fields.Float(string='Duration',  store=True, track_visibility='always')

    @api.depends('partner_ids')
    def onchange_partner(self):
        for event in self:
            participants = []
            for partner in event.partner_ids:
                participants.append(partner.name)
            participants = ",".join(participants)
            event.participants_names = participants


    @api.multi
    def checkedin(self):
            pass

    @api.multi
    def count_docs(self):
        expense_ids = self.env['hr.expense'].search([("meeting_id","=",self.id)])
        if len(expense_ids):
            self.attach_doc_count = len(expense_ids) or 0


    @api.model
    @api.multi
    def process_delete_meetings_scheduler_queue(self):
        for rec in self.search(['|',('name', '=',False),('stage_id', '=',False)]) :
            rec.sudo().unlink()

    @api.model
    @api.multi
    def process_update_address_scheduler_queue(self):
        for rec in self.search([('status', '!=','draft')]) : #,('checkin_lattitude','=',True),('checkin_longitude','=',True)
            if rec.checkin_lattitude and rec.checkin_longitude and not rec.reverse_location:
                location_list = geocoder.google([rec.checkin_lattitude,rec.checkin_longitude], method='reverse')
                address = location_list.address
                rec.reverse_location = address.encode('utf-8')
                rec.write({'reverse_location': address})
                print "Update Address Schedular - Successfull"

            print "Broke"


    @api.model
    @api.multi
    def process_update_distance_scheduler_queue(self):
        location_dict = {}
        users = []
        location = []

        meeting_ids = self.sudo().search([('status', '!=','draft'),('expense_date', '=','2018-04-14'),('user_id', 'in',(1297,1636))],order="user_id , id asc")
        #,('expense_date', '=','2018-04-14'),('user_id', 'in',(1297,1636))
        for rec in meeting_ids: #self.search([('status', '!=','draft')]) :
            if rec.reverse_location and not rec.distance:
                users.append(rec.user_id.id) 
                location.append(rec.reverse_location) 

                for i, j in zip(users, location):
                    location_dict.setdefault(i, []).append(j)

        for key , values in location_dict.iteritems():
            # print "key: {}, value: {}".format(key, values)
            location_list = list(set(location_dict[key]))

            final_loc_list = [(location_list[i],location_list[i+1]) for i in range(0,len(location_list)-1)]
            count = 0
            for records in final_loc_list:
                li = list(records)
                li.append(google_key)
                lo = tuple(li)

                url_list = []
                url = 'https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins=%s&destinations=%s&key=%s' %lo

                result= simplejson.load(urllib.urlopen(url))
                driving_time = result['rows'][0]['elements'][0]
                distance = result['rows'][0]['elements'][0]['distance']
                duration = result['rows'][0]['elements'][0]['duration']
                meters = float(distance['value'])
                kilometers = float(meters/1000)
                time = duration['text']

                print "OOOOOOOOOOOOOOOOOO" , meters , kilometers , time , key
                count+=1

            print "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP count" , count





                


    @api.multi
    def checkin(self):
        if self.checkin_lattitude and self.checkin_longitude:
            self.status = 'open'
            self.next_flag = False
        else:
            raise UserError("Your location Settings/GPS are not enabled. \
             Contact IT Support for help")



    # @api.onchange('name','checkin_lattitude','checkin_longitude')
    # def _onchange_address(self):
    #     if self.checkin_lattitude and self.checkin_longitude:
    #         try:

    #             location_list = geocoder.reverse((self.checkin_lattitude,self.checkin_longitude))
    #             print "LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL" , location_list
    #             location = location_list[0]
    #             address = location.address

    #             self.reverse_location = address

    #         except UserError:
    #             pass

    @api.multi
    def create_event(self):
        new_stage = self.env['crm.stage'].search([('name', '=','New')])
        calendar_event_vals = {
                'name': self.title_action,
                'start_datetime': self.date_action,
                'stop_datetime': self.date_action,
                'start': self.date_action,
                'stop': self.date_action,
                'allday': False,
                'show_as': 'busy',
                'partner_ids': [(6, 0, [])] or '',
                'partner_id': self.partner_id.id if self.ischeck=='customer' else '',
                'stage_id': new_stage.id or '',
                'categ_id': self.next_activity_id.id,
                'user_id': self.user_id.id,
                'ischeck': self.ischeck,
                'lead_id': self.lead_id.id if self.ischeck=='lead' else '',
                'opportunity_id': self.opportunity_id.id if self.ischeck=='opportunity' else '',
                'next_flag':True,
                'checkin_lattitude':self.checkin_lattitude,
                'checkin_longitude':self.checkin_longitude,
                # 'lead_id': self.lead_id.id if self.ischeck=='opportunity' else '',
                # 'lead_id': self.lead_id.id if self.ischeck=='lead' else '',
            }

        # # if self.name == self.search([('id','in',inv_res)])
        # prod_package = self.env['product.packaging'].search([('name','=',self.title_action)])

        self.status = 'close'
        self.env['calendar.event'].create(calendar_event_vals)
        

    @api.multi
    def get_attached_docs(self):
        expense_ids = self.env['hr.expense'].search([("meeting_id","=",self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('hr_expense.hr_expense_actions_my_unsubmitted')
        list_view_id = imd.xmlid_to_res_id('hr_expense.view_expenses_tree')
        form_view_id = imd.xmlid_to_res_id('hr_expense.hr_expense_form_view')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'],
                [False, 'graph'], [False, 'kanban'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(expense_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % expense_ids.ids
        elif len(expense_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = expense_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.onchange('ischeck')
    def _onchange_date(self):
        if self.ischeck == 'opportunity':
            return {'domain': {
                'opportunity_id': [('user_id', 'in', [self.env.uid])],
            }}
        elif self.ischeck == 'lead':
            return {'domain': {
                'opportunity_id': [('user_id', 'in', (self.env.uid,False))],
            }}


class 