from odoo import fields, models, api

class SelectionData(models.Model):
	_name = "as.selection"
	_inherit = "as.selection"

	is_custom_transaction = fields.Boolean(string="Sebuah tagihan custom?")