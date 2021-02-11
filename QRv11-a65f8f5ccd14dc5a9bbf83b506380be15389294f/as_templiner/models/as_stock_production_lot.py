# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import time
import datetime
from time import mktime
from dateutil import parser
from datetime import datetime, timedelta, date
#QR
import qrcode
from bs4 import BeautifulSoup
import tempfile
import base64
from io import StringIO
import io
import logging
_logger = logging.getLogger(__name__)
FILETYPE_BASE64_MAGICWORD = {
    b'/': 'jpg',
    b'R': 'gif',
    b'i': 'png',
    b'P': 'svg+xml',
}

class astockproductionlot(models.Model):
    _inherit = "stock.production.lot"

    origin = fields.Char(string='Origen')
 
    def get_qrcode(self,cadena_qr): 
        try:
            qr_img = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,box_size=10,border=0)
            qr_img.add_data(cadena_qr)
            qr_img.make(fit=True)
            img = qr_img.make_image()
            # buffer = StringIO()
            buffer = io.BytesIO()
            img.save(buffer)
            qr_img = base64.b64encode(buffer.getvalue())
            return qr_img
        except:
            raise UserError(_('No se puedo generar el codigo QR'))
    @api.multi
    def image_data_uri(self,base64_source):
        """This returns data URL scheme according RFC 2397
        (https://tools.ietf.org/html/rfc2397) for all kind of supported images
        (PNG, GIF, JPG and SVG), defaulting on PNG type if not mimetype detected.
        """
        return 'data:image/%s;base64,%s' % (
            FILETYPE_BASE64_MAGICWORD.get(base64_source[:1], 'png'),
            base64_source.decode(),
        )

    def get_codqr_url(self, cadena):
        qr= self.get_qrcode(cadena)
        return self.image_data_uri(qr)

