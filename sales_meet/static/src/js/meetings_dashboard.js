odoo.define('sales_meet.MeetingsDashboard', function (require) {
"use strict";

var ajax = require('web.ajax');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Model = require('web.Model');
var session = require('web.session');
var utils = require('web.utils');
var web_client = require('web.web_client');
var Widget = require('web.Widget');
var _t = core._t;
var QWeb = core.qweb;


var formats = require('web.formats');
var KanbanView = require('web_kanban.KanbanView');
var KanbanRecord = require('web_kanban.Record');
var ActionManager = require('web.ActionManager');

var _lt = core._lt;

var MeetingDashboard = Widget.extend(ControlPanelMixin, {
    template: "sales_meet.MeetingDashboardMain",
    events: {
        'click .meeting_count_month':'meeting_count_month',
        'click .meeting_count':'meeting_count',
        'click .go_to':'go_to',
        'click .go_to_event':'go_to_event',
        'click .go_to_expense':'go_to_expense',
        'click .draft_meeting_count_month':'draft_meeting_count_month',
        // 'click #generate_monthly_meetings_pdf': function(){this.generate_monthly_meetings_pdf("bar");},
        // 'click #generate_attendance_pdf': function(){this.generate_monthly_meetings_pdf("pie")},
    },

    init: function(parent, context) {
        this._super(parent, context);
        var self = this;
        this.login_user = true;
        this._super(parent,context);

    },

    start: function() {
        var self = this;

        var model  = new Model('calendar.event').call('get_user_meeting_details').then(function(result){
            this.login_user =  result[0];
            // self.login_user =  result[0]

            $('.o_meetings_dashboard').html(QWeb.render('MeetingsManagerDashboard', {widget: this}));

        });

    },


    meeting_count_month: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        var firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
        var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
        var fday = firstDay.toJSON().slice(0,10).replace(/-/g,'-');
        var lday = lastDay.toJSON().slice(0,10).replace(/-/g,'-');
        this.do_action({
            name: _t("Meetings For This Month"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            // domain: [['expense_date','>', fday],['expense_date','<', lday]],
            target: 'current'
        })
    },

    draft_meeting_count_month: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        var firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
        var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
        var fday = firstDay.toJSON().slice(0,10).replace(/-/g,'-');
        var lday = lastDay.toJSON().slice(0,10).replace(/-/g,'-');
        console.log('Your current faaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa is:', fday , lday)
        this.do_action({
            name: _t("Draft Meetings For This Month"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['name','=', false]],
            target: 'current'
        })
    },

    meeting_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        console.log('Your current faaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa is:')
        this.do_action({
            name: _t("Meetings"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['expense_date','=', date]],
            target: 'current'
        })
    },


    create_meeting: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        console.log('Your current mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm is:')
        this.do_action({
            name: _t("Meetings"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'form,tree',
            view_type: 'form',
            views: [[false, 'form']],
            // domain: [['expense_date','=', date]],
            target: 'current'
        })
    },

    go_to: function(e) {
        var self = this;
        console.log('Your current mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm is:')
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        // var id = JSON.parse($(calendar.event).data("id"));
        
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "calendar.event",
            // res_id: id,
            views: [[false, 'form']],
        });
    },


    go_to_event: function(e) {
        var self = this;
        console.log('Your current mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm is:')
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        // var id = JSON.parse($(calendar.event).data("id"));
        
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "crm.lead",
            // res_id: id,
            views: [[false, 'form']],
        });
    },


    go_to_expense: function(e) {
        var self = this;
        console.log('Your current mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm is:')
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        // var id = JSON.parse($(calendar.event).data("id"));
        
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "hr.expense",
            // res_id: id,
            views: [[false, 'form']],
        });
    },


    // qty_count: function(e) {
    //     var self = this;
    //     e.stopPropagation();
    //     e.preventDefault();
    //     var date = new Date();
    //     console.log('Your current faaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa is:')
    //     this.do_action({
    //         name: _t("Meetings"),
    //         type: 'ir.actions.act_window',
    //         res_model: 'calendar.event',
    //         view_mode: 'tree,form',
    //         view_type: 'form',
    //         views: [[false, 'list'],[false, 'form']],
    //         // domain: [['expense_date','=', date]],
    //         target: 'current'
    //     })
    // },







    

});

core.action_registry.add('meetings_dashboard', MeetingDashboard);

return MeetingDashboard;

});
