# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<http://www.cybrosys.com>).
#    Author: Jesni Banu(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import datetime
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx


class MeetingReportXls(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, lines):
        print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

        
        print error
        get_warehouse = self.get_warehouse(data)
        count = len(get_warehouse[0]) * 11 + 6
        sheet = workbook.add_worksheet('Meeting Details')
        format1 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'vcenter', 'bold': True})
        format11 = workbook.add_format({'font_size': 12, 'align': 'center', 'right': True, 'left': True, 'bottom': True, 'top': True, 'bold': True})
        format21 = workbook.add_format({'font_size': 10, 'align': 'center', 'right': True, 'left': True,'bottom': True, 'top': True, 'bold': True})
        format3 = workbook.add_format({'bottom': True, 'top': True, 'font_size': 12})
        font_size_8 = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 8})
        red_mark = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 8,
                                        'bg_color': 'red'})
        justify = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 12})
        format3.set_align('center')
        font_size_8.set_align('center')
        justify.set_align('justify')
        format1.set_align('center')
        red_mark.set_align('center')
        sheet.merge_range('A3:G3', 'Report Date: ' + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M %p")), format1)
        sheet.merge_range(2, 7, 2, count, 'Warehouses', format1)
        sheet.merge_range('A4:G4', 'Product Information', format11)
        w_col_no = 6
        w_col_no1 = 7
        for i in get_warehouse[0]:
            w_col_no = w_col_no + 11
            sheet.merge_range(3, w_col_no1, 3, w_col_no, i, format11)
            w_col_no1 = w_col_no1 + 11
        sheet.write(4, 0, 'SKU', format21)
        sheet.merge_range(4, 1, 4, 3, 'Name', format21)
        sheet.merge_range(4, 4, 4, 5, 'Category', format21)
        sheet.write(4, 6, 'Cost Price', format21)
        p_col_no1 = 7
        for i in get_warehouse[0]:
            sheet.write(4, p_col_no1, 'Available', format21)
            sheet.write(4, p_col_no1 + 1, 'Virtual', format21)
            sheet.write(4, p_col_no1 + 2, 'Incoming', format21)
            sheet.write(4, p_col_no1 + 3, 'Outgoing', format21)
            sheet.merge_range(4, p_col_no1 + 4, 4, p_col_no1 + 5, 'Net On Hand', format21)
            sheet.merge_range(4, p_col_no1 + 6, 4, p_col_no1 + 7, 'Total Sold', format21)
            sheet.merge_range(4, p_col_no1 + 8, 4, p_col_no1 + 9, 'Total Purchased', format21)
            sheet.write(4, p_col_no1 + 10, 'Valuation', format21)
            p_col_no1 = p_col_no1 + 11
        prod_row = 5
        prod_col = 0
        for i in get_warehouse[1]:
            get_line = self.get_lines(data, i)
            for each in get_line:
                sheet.write(prod_row, prod_col, each['sku'], font_size_8)
                sheet.merge_range(prod_row, prod_col + 1, prod_row, prod_col + 3, each['name'], font_size_8)
                sheet.merge_range(prod_row, prod_col + 4, prod_row, prod_col + 5, each['category'], font_size_8)
                sheet.write(prod_row, prod_col + 6, each['cost_price'], font_size_8)
                prod_row = prod_row + 1
            break
        prod_row = 5
        prod_col = 7
        for i in get_warehouse[1]:
            get_line = self.get_lines(data, i)
            for each in get_line:
                if each['available'] < 0:
                    sheet.write(prod_row, prod_col, each['available'], red_mark)
                else:
                    sheet.write(prod_row, prod_col, each['available'], font_size_8)
                if each['virtual'] < 0:
                    sheet.write(prod_row, prod_col + 1, each['virtual'], red_mark)
                else:
                    sheet.write(prod_row, prod_col + 1, each['virtual'], font_size_8)
                if each['incoming'] < 0:
                    sheet.write(prod_row, prod_col + 2, each['incoming'], red_mark)
                else:
                    sheet.write(prod_row, prod_col + 2, each['incoming'], font_size_8)
                if each['outgoing'] < 0:
                    sheet.write(prod_row, prod_col + 3, each['outgoing'], red_mark)
                else:
                    sheet.write(prod_row, prod_col + 3, each['outgoing'], font_size_8)
                if each['net_on_hand'] < 0:
                    sheet.merge_range(prod_row, prod_col + 4, prod_row, prod_col + 5, each['net_on_hand'], red_mark)
                else:
                    sheet.merge_range(prod_row, prod_col + 4, prod_row, prod_col + 5, each['net_on_hand'], font_size_8)
                if each['sale_value'] < 0:
                    sheet.merge_range(prod_row, prod_col + 6, prod_row, prod_col + 7, each['sale_value'], red_mark)
                else:
                    sheet.merge_range(prod_row, prod_col + 6, prod_row, prod_col + 7, each['sale_value'], font_size_8)
                if each['purchase_value'] < 0:
                    sheet.merge_range(prod_row, prod_col + 8, prod_row, prod_col + 9, each['purchase_value'], red_mark)
                else:
                    sheet.merge_range(prod_row, prod_col + 8, prod_row, prod_col + 9, each['purchase_value'], font_size_8)
                if each['total_value'] < 0:
                    sheet.write(prod_row, prod_col + 10, each['total_value'], red_mark)
                else:
                    sheet.write(prod_row, prod_col + 10, each['total_value'], font_size_8)
                prod_row = prod_row + 1
            prod_row = 5
            prod_col = prod_col + 11

MeetingReportXls('report.sales_meet.meeting_report_xls.xlsx', 'calendar.event')
