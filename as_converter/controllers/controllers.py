# -*- coding: utf-8 -*-
from odoo import http

# class Converter(http.Controller):
#     @http.route('/converter/converter/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/converter/converter/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('converter.listing', {
#             'root': '/converter/converter',
#             'objects': http.request.env['converter.converter'].search([]),
#         })

#     @http.route('/converter/converter/objects/<model("converter.converter"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('converter.object', {
#             'object': obj
#         })