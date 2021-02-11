odoo.define('sales_meet.RetailerDashboard', function (require) {
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

var RetailerDashboard = Widget.extend(ControlPanelMixin, {
    template: "sales_meet.RetailerDashboardMain",
    events: {
        // 'click .meeting_count_month':'meeting_count_month',
        'click .gift_count':'gift_count',
        'click .gift_count_submitted':'gift_count_submitted',
        // 'click .go_to':'go_to',
        // 'click .go_to_event':'go_to_event',
        // 'click .go_to_expense':'go_to_expense',
        // 'click .draft_meeting_count_month':'draft_meeting_count_month',
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

        var model  = new Model('wp.scheme.working.line').call('get_user_gift_details').then(function(result){
            this.login_user =  result[0];
            // self.login_user =  result[0]

            $('.o_retailer_dashboard').html(QWeb.render('RetailerManagerDashboard', {widget: this}));

        });

    },



    gift_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        var month = date.getMonth();
        console.log('Your current faaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa is:', month)
        this.do_action({
            name: _t("Retailer Acknowledgement"),
            type: 'ir.actions.act_window',
            res_model: 'wp.scheme.working.line',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','=', 'approved']],
            target: 'current'
        })
    },

    gift_count_submitted: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        console.log('Your current ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff is:')
        this.do_action({
            name: _t("Retailer Acknowledgement"),
            type: 'ir.actions.act_window',
            res_model: 'wp.scheme.working.line',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','=', 'submitted']],
            target: 'current'
        })
    },





    // create_meeting: function(e) {
    //     var self = this;
    //     e.stopPropagation();
    //     e.preventDefault();
    //     var date = new Date();
    //     console.log('Your current mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm is:')
    //     this.do_action({
    //         name: _t("Meetings"),
    //         type: 'ir.actions.act_window',
    //         res_model: 'calendar.event',
    //         view_mode: 'form,tree',
    //         view_type: 'form',
    //         views: [[false, 'form']],
    //         // domain: [['expense_date','=', date]],
    //         target: 'current'
    //     })
    // },

    // go_to: function(e) {
    //     var self = this;
    //     console.log('Your current mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm is:')
    //     e.stopPropagation();
    //     e.preventDefault();
    //     var date = new Date();
    //     // var id = JSON.parse($(calendar.event).data("id"));
        
    //     this.do_action({
    //         type: 'ir.actions.act_window',
    //         res_model: "calendar.event",
    //         // res_id: id,
    //         views: [[false, 'form']],
    //     });
    // },


    







    

});

core.action_registry.add('retailer_dashboard', RetailerDashboard);

return RetailerDashboard;

});
