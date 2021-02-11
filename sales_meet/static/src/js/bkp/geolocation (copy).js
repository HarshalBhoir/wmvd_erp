odoo.define('sales_meet.currentlatlong', function (require) {
    "use strict";

var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
// var Model = require('web.DataModel');
var Model = require('web.Model');
var QWeb = core.qweb;
var web_client = require('web.web_client');
var WebClient = require('web.WebClient');
var _t = core._t;
var sales_meet = new Model('sales.meet');


var options = {
  enableHighAccuracy: true,
  timeout: 5000,
  maximumAge: 0
};

function success(pos) {
  var crd = pos.coords;

  console.log('Your current position is:');
  console.log(`Latitude : ${crd.latitude}`);
  console.log(`Longitude: ${crd.longitude}`);
  console.log(`More or less ${crd.accuracy} meters.`);
  console.log(self);
  

  var checkin_lattitude = crd.latitude;
  var checkin_longitude = crd.longitude;

  console.log('AAAAAAAAAAAAAA' + checkin_lattitude + checkin_longitude);



   // self.view.fields.checkin_lattitude.set_value(checkin_lattitude);
    // this.field_manager.get_field_value('checkin_lattitude');


};

function error(err) {
  console.warn(`ERROR(${err.code}): ${err.message}`);
};



navigator.geolocation.getCurrentPosition(success, error, options);



});

