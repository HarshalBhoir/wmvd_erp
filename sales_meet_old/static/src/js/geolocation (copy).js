odoo.define('sales_meet.currentlatlong', function (require) {
    "use strict";

var instance = openerp;
var core = require('web.core');
var Model = require('web.Model');
var QWeb = core.qweb;
var _t = core._t;
var longitude = 0.0;
var latitude = 0.0;

var form_widget = require('web.form_widgets');


instance.web.FormView.include({
    init: function(parent, dataset, view_id, options) {
        var self = this;
        this._super(parent, dataset, view_id, options);
    },
    
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        // console.log("__INIT__" + latitude + longitude);

        $('input.checkin_lattitude').val(latitude);
        $('input.checkin_longitude').val(longitude);
        
        this.$el.delegate('.geo_checkin', 'click', self.get_location);

    },
    
    get_location: function(){
        $('input.checkin_lattitude').val(latitude);
        $('input.checkin_longitude').val(longitude);
    },

});


// form_widget.WidgetButton.include({
//     on_click: function() {
//          $('input.checkin_lattitude').val(latitude);
//          $('input.checkin_longitude').val(longitude);
//          this._super();
//     },
// });


   var options = {
        enableHighAccuracy: true,
        maximumAge: 3600000
    };


    function success(pos) {
      var crd = pos.coords;

      // console.log('Your current position is:');
      // console.log(`Latitude : ${crd.latitude}`);
      // console.log(`Longitude: ${crd.longitude}`);
      // console.log(`More or less ${crd.accuracy} meters.`);
      
      var checkin_lattitude = crd.latitude;
      var checkin_longitude = crd.longitude;
      longitude = checkin_longitude;
      latitude = checkin_lattitude;

      // console.log(longitude,latitude);
    };

    function error(err) {
      console.warn(`ERROR(${err.code}): ${err.message}`);
    };

    navigator.geolocation.getCurrentPosition(success, error, options);


});

