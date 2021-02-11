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


// form_widget.WidgetButton.include({
//     on_click: function() {

// 	console.log('111111111111111111111111111111111');
//          if(this.node.attrs.custom === "click"){
// 	    console.log('22222222222222222222222222222');

//             $('input.checkin_lattitude').val(latitude);
//             $('input.checkin_longitude').val(longitude);

//             return;
//          }
// 	console.log('333333333333333333333333333333333');
//          this._super();
//     },
// });
// });


instance.web.FormView.include({
    init: function(parent, dataset, view_id, options) {
        var self = this;
        this._super(parent, dataset, view_id, options);
    },
    
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        // console.log("__INIT__" + latitude + longitude);
        // $('input.checkin_lattitude').val(latitude);
        // $('input.checkin_longitude').val(longitude);

        $('input.checkin_lattitude').val(latitude);
        $('input.checkin_longitude').val(longitude);
        
        this.$el.delegate('.geo_checkin', 'click', self.get_location);



    },
    
    get_location: function(){
        $('input.checkin_lattitude').val(latitude);
        $('input.checkin_longitude').val(longitude);
    },


//     onclick: {

// "click .txt_js": "updatetxt",

// },

// updatetxt: function () {

// console.log('Button Clicked')

// },
    
});


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
};

function error(err) {
  console.warn(`ERROR(${err.code}): ${err.message}`);
};


// var latLong;
//     $.getJSON("http://ipinfo.io", function(ipinfo){
//         console.log("Found location ["+ipinfo.loc+"] by ipinfo.io");
//         latLong = ipinfo.loc.split(",");
//         console.log("__INIT__" + latLong);


//     });



// function do_something(coords) {
//     // Do something with the coords here
// }

// navigator.geolocation.getCurrentPosition(function(position) { 
//     do_something(position.coords);
//     },
//     function(failure) {
//         $.getJSON('https://ipinfo.io/geo', function(response) { 
//         var loc = response.loc.split(',');
//         var coords = {
//             latitude: loc[0],
//             longitude: loc[1]
//         };
//         do_something(coords);
//         });  
//     };
// });

navigator.geolocation.getCurrentPosition(success, error, options);


//This is the "Offline page" service worker

//Add this below content to your HTML page, or add the js file to your page at the very top to register sercie worker
// if (navigator.serviceWorker.controller) {
//   console.log('[PWA Builder] active service worker found, no need to register')
// } else {
//   //Register the ServiceWorker
//   navigator.serviceWorker.register('pwabuilder-sw.js', {
//     scope: './'
//   }).then(function(reg) {
//     console.log('Service worker has been registered for scope:'+ reg.scope);
//   });
// }



// function success(position) {
// alert(position.coords.latitude);
// alert(position.coords.longitude);
// }

// function error(msg) {
// alert('error');
// }

// if (navigator.geolocation) {
// navigator.geolocation.getCurrentPosition(success, error);
// } else {error('not supported');
// }



});

