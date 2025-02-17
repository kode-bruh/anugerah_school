from odoo import api, models, fields

class State(models.Model):
	_name = "asm.state"
	_inherit = "asm.state"

	is_invoiced = fields.Boolean(string="Tertagih")