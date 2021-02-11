# -*- coding: utf-8 -*-
 
from odoo import models, api, _
from odoo.http import request

import calendar

from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta , date
import time
from dateutil import relativedelta




class CalendarEventExtension(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def get_user_meeting_details(self):
        uid = request.session.uid
        cr = self.env.cr

        user_id = self.env['res.users'].sudo().search_read([('id', '=', uid)], limit=1)
              
        date_today = datetime.today()
        date_from = datetime.today().replace(day=1)
        date_to = datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1])

        meetings_count = self.env['calendar.event'].sudo().search_count([('user_id', '=', uid),('expense_date','=', date_today)])
        meetings_count_month = self.env['calendar.event'].sudo().search_count([('user_id', '=', uid),('expense_date','>', date_from),('expense_date','<', date_to)])
        draft_meetings_count_month = self.env['calendar.event'].sudo().search_count([('user_id', '=', uid),('expense_date','>', date_from),('expense_date','<', date_to),('name', '=', False)])

        if user_id:
            data = {
                'meetings_count': meetings_count,
                'meetings_count_month': meetings_count_month,
                'draft_meetings_count_month': draft_meetings_count_month,
                
            }
            user_id[0].update(data)


        # # payroll Datas for Bar chart
        # query = """
        #     select to_char(expense_date,'Mon') as month , user_id , count(id) as total from calendar_event
        #     where name is not null and user_id = 944 and expense_date is not null
        #     group by month , user_id  order by month
        # """
        # cr.execute(query)
        # monthly_meetings_data = cr.dictfetchall()
        # monthly_meetings_label = []
        # monthly_meetings_dataset = []
        # for data in monthly_meetings_data:
        #     monthly_meetings_label.append(data['month'])
        #     monthly_meetings_dataset.append(float(data['total']))
        #     print "kkkkkkkkkkkkkkkkkkkkkkkkkkkk" , monthly_meetings_label , monthly_meetings_dataset , data['total'] , type(data['total'])


        # # Attendance Chart Pie
        # query = """
        #     select to_char(expense_date,'Mon') as month , user_id , count(id) as total from calendar_event
        #     where name is not null and user_id = 944 and expense_date is not null
        #     group by month , user_id  order by month
        # """
        # cr.execute(query)
        # monthly_meetings_data = cr.dictfetchall()
        # monthly_meetings_label = []
        # monthly_meetings_dataset = []
        # for data in monthly_meetings_data:
        #     monthly_meetings_label.append(data['month'])
        #     monthly_meetings_dataset.append(float(data['total']))
        #     print "kkkkkkkkkkkkkkkkkkkkkkkkkkkk" , monthly_meetings_label , monthly_meetings_dataset , data['total'] , type(data['total'])


        # data = {
        #         'monthly_meetings_label': monthly_meetings_label,
        #         'monthly_meetings_dataset': monthly_meetings_dataset,
        #     }

        # print "jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjffffffffffffffffffffffff" , monthly_meetings_dataset , monthly_meetings_label
        # user_id[0].update(data)



        return user_id