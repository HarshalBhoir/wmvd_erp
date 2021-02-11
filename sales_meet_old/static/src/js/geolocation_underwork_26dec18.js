odoo.define('sales_meet.currentlatlong', function (require) {
    "use strict";

var instance = openerp;
var core = require('web.core');
var Model = require('web.Model');
var QWeb = core.qweb;
var _t = core._t;
var longitude = 0.0;
var latitude = 0.0;
// var checkin_lattitude = ''
// var checkin_longitude = ''
var form_widget = require('web.form_widgets');
// var session = require('web.session');








// instance.web.FormView.include({
//     init: function(parent, dataset, view_id, options) {
//         var self = this;
//         this._super(parent, dataset, view_id, options);
//     },
    
//     start: function() {
//         var self = this;
//         this._super.apply(this, arguments);
//         console.log(" instance.web.FormView __INIT__" + latitude + longitude);

//         $('input.checkin_lattitude').val(latitude);
//         $('input.checkin_longitude').val(longitude);
        
//         this.$el.delegate('.geo_checkin', 'click', self.get_location);

//     },
    
//     get_location: function(){
//         $('input.checkin_lattitude').val(latitude);
//         $('input.checkin_longitude').val(longitude);
//     },

// });






form_widget.WidgetButton.include({
    on_click: function() {


         if(this.node.attrs.custom === "click"){

            console.log('Your current position is:');
            console.log(this.id)

            $('input.checkin_lattitude').val(latitude);
            $('input.checkin_longitude').val(longitude);
            var status = 'open'
            $('input.status').val(status);

            // var user_id = $(this).closest("form").attr('id');

            // var formid = $('form').attr('id');

            console.log("__INIT__" + latitude + longitude + status);




            if (latitude === 0){

              console.log("__IF latitude__" + latitude );

              new instance.web.Model("calendar.event").call("checkin", [[]]); 
            } 

            new instance.web.Model("calendar.event").call("action_save", [[]]); 

            // alert("Checked IN Successfully"); 
            
         

            return;
         }
         this._super();

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

      // console.log(' function success : Your current position is:');
      // console.log(` function success : Latitude : ${crd.latitude}`);
      // console.log(` function success : Longitude: ${crd.longitude}`);
      // console.log(` function success : More or less ${crd.accuracy} meters.`);
      
      var checkin_lattitude = crd.latitude;
      var checkin_longitude = crd.longitude;
      longitude = checkin_longitude;
      latitude = checkin_lattitude;

      // console.log(longitude,latitude);
    };

    function error(err) {
      // console.log('ERRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR');
      console.warn(`ERROR(${err.code}): ${err.message}`);
    };

    navigator.geolocation.getCurrentPosition(success, error, options);


});

