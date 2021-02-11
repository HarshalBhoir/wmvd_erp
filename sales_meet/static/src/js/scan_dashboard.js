odoo.define('sales_meet.ScanDashboard', function (require) {
"use strict";

var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
var _t = core._t;
var QWeb = core.qweb;

var scan_view_id = 0.0;

var ScanDashboard = Widget.extend(ControlPanelMixin, {
    template: "sales_meet.ScanDashboardMain",
    events: {
        'click .go_to_scan':'go_to_scan',
        'click .draft_scan_count':'draft_scan_count',
        'click .create_scan_count':'create_scan_count',
        'click .updated_scan_count':'updated_scan_count',
        'click .cn_raised_scan_count':'cn_raised_scan_count',
    },

    init: function(parent, context) {
        this._super(parent, context);
        var self = this;
        this.login_user = true;
        this.view_id = true;
        this._super(parent,context);

    },

    start: function() {
        var self = this;
        var model_obj = new Model('ir.model.data');

        var model  = new Model('barcode.marketing.check').call('get_scan_details').then(function(result){
            this.login_user =  result[0];

            $('.o_scan_dashboard').html(QWeb.render('ScanManagerDashboard', {widget: this}));

        });
        
        model_obj.call('get_object_reference',['sales_meet','view_barcode_marketing_check_form_mobile']).then( function(result){
            var t = result[1];
            scan_view_id = t;
            // console.log('------------------------------------ is:', result[1], scan_view_id);
        });

    },


    go_to_scan: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        
        this.do_action({
            name: 'action_barcode_marketing_check_mobile',
            type: 'ir.actions.act_window',
            res_model: "barcode.marketing.check",
            view_mode: 'form',
            views: [[scan_view_id, 'form']],
            context: {
                    'search_default_mobile_bool': true,
                    'default_mobile_bool': true,
                    },
         
        });
    },



    draft_scan_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Draft Scans"),
            type: 'ir.actions.act_window',
            res_model: 'barcode.marketing.check',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[scan_view_id, 'form']],
            domain: [['state','=', 'draft']],
            context: {
                    'search_default_mobile_bool': true,
                    'default_mobile_bool': true,
                    },
            target: 'current'
        })
    },


    create_scan_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Create Scans"),
            type: 'ir.actions.act_window',
            res_model: 'barcode.marketing.check',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[scan_view_id, 'form']],
            domain: [['state','=', 'create']],
            context: {
                    'search_default_mobile_bool': true,
                    'default_mobile_bool': true,
                    },
            target: 'current'
        })
    },

    updated_scan_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Updated Scans"),
            type: 'ir.actions.act_window',
            res_model: 'barcode.marketing.check',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[scan_view_id, 'form']],
            domain: [['state','=', 'update']],
            context: {
                    'search_default_mobile_bool': true,
                    'default_mobile_bool': true,
                    },
            target: 'current'
        })
    },

    cn_raised_scan_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("CN Raised Scans"),
            type: 'ir.actions.act_window',
            res_model: 'barcode.marketing.check',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[scan_view_id, 'form']],
            domain: [['state','=', 'cn_raised']],
            context: {
                    'search_default_mobile_bool': true,
                    'default_mobile_bool': true,
                    },
            target: 'current'
        })
    },


    

});

core.action_registry.add('scan_dashboard', ScanDashboard);

return ScanDashboard;

});
