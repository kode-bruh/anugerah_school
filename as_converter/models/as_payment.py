from odoo import models, api, fields

class Payment(models.Model):
	_name = "as.payment"
	_inherit = "as.payment"

	paid_by_autodebit = fields.Boolean(readonly=True)
	autodebit_id = fields.Many2one("as.import", ondelete="cascade", readonly=True)