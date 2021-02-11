# -*- coding: utf-8 -*-
 
from odoo import models, api, _
from odoo.http import request

import calendar

from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta , date
import time
from dateutil import relativedelta

import psycopg2


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

        meetings_count = self.env['calendar.event'].sudo().search_count([('user_id', '=', uid),
                                                                         ('expense_date','=', date_today)])
        meetings_count_month = self.env['calendar.event'].sudo().search_count([('user_id', '=', uid),
                                                                                ('expense_date','>', date_from),
                                                                                ('expense_date','<', date_to)])
        draft_meetings_count_month = self.env['calendar.event'].sudo().search_count([('user_id', '=', uid),
                                                                                    ('expense_date','>', date_from),
                                                                                    ('expense_date','<', date_to),
                                                                                    ('name', '=', False)])

        partner_count = self.env['wp.res.partner'].sudo().search_count([('user_id', '=', uid)])



        partner_view_id = self.env.ref('sales_meet.view_partner_form_extension_all')
        wp_partner_view_id = self.env.ref('sales_meet.view_wp_res_partner_form')

        supplier_view_id = self.env.ref('sales_meet.action_supplier_form_mdm2')
        
        # get_qty_count = self.get_qty_count()

        # print "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh" , get_qty_count

        if user_id:
            data = {
                'meetings_count': meetings_count,
                'meetings_count_month': meetings_count_month,
                'draft_meetings_count_month': draft_meetings_count_month,
                'partner_count': partner_count,
                # 'get_qty_count': get_qty_count,

                # 'create_meetings': create_meetings,
                
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



    # @api.multi
    # def get_qty_count(self):
    #     conn_pg = None

    #     config = self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1)

    #     print "#-------------Select --TRY----------------------#"
    #     try:
    #         conn_pg = psycopg2.connect(dbname= config.database_name, user=config.username, password=config.password, 
    #             host= config.ip_address,port=config.port)
    #         pg_cursor = conn_pg.cursor()


    #         # pg_cursor.execute("select * from adempiere.daily_schedular_query()")
    #         pg_cursor.execute("select  Round(sum(inl.QtyInvoiced)/1000,2) Quantity \
    #                 from adempiere.C_Invoice inv ,adempiere.AD_User ause, \
    #                  adempiere.C_BPartner cbp  ,adempiere.ad_client  cls \
    #                 , adempiere.C_BPartner_Location cbl left join adempiere.C_SalesRegion csa on \
    #                  csa.C_SalesRegion_ID = cbl.C_SalesRegion_ID  ,adempiere.C_Location clo \
    #                 ,  adempiere.AD_Org adg , \
    #                  adempiere.C_InvoiceLine inl left join adempiere.M_Product mpt on mpt.M_Product_ID =inl.M_Product_ID \
    #                  left join  adempiere.C_Charge ch on ch.C_Charge_ID =inl.C_Charge_ID \
    #                  left join adempiere.C_UOM cuom on cuom.C_UOM_ID =inl.C_UOM_ID \
    #                  left join  adempiere.M_Product_Category  mpc on mpt.M_Product_Category_ID = mpc.M_Product_Category_ID \
    #                 where inv.C_Invoice_ID=inl.C_Invoice_ID \
    #                 and  inv.AD_Client_ID=1000000 \
    #                 and cbp.C_BPartner_ID = inv.C_BPartner_ID \
    #                 and cls.AD_Client_ID =inv.AD_Client_ID \
    #                 and inv.docstatus IN ('CO', 'CL') and issotrx='Y' \
    #                 and cbp.C_BP_Group_ID IN (1000001,1000002, 1000014,1000004, 1000005, 1000062) \
    #                 and cbp.C_BPartner_ID = cbl.C_BPartner_ID \
    #                 and clo.c_Location_ID=cbl.c_Location_ID \
    #                 and adg.AD_Org_ID =inv.AD_Org_ID \
    #                 and inv.AD_User_ID =ause.AD_User_ID")


    #         records = pg_cursor.fetchall()

            
    #         if len(records) == 0:
    #             raise UserError("No records Found")

    #         return records

    #     except psycopg2.DatabaseError, e:
    #         print 'Error %s' % e
    #         if conn_pg:
    #             print "#-------------------Except----------------------#"
    #             conn_pg.rollback()
     
    #         print 'Error %s' % e        

    #     finally:
    #         if conn_pg:
    #             print "#--------------Select ----Finally----------------------#"
    #             conn_pg.close()