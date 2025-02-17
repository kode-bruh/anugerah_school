from odoo import api, models, fields

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	account_id = fields.Many2one("asm.account", ondelete="set null")

	def set_values(self):
		res = super(ResConfigSettings, self).set_values()
		self.env['ir.config_parameter'].sudo().set_param('asm_accounting.account_id', self.account_id.id)
		return res

	@api.model
	def get_values(self):
		res = super(ResConfigSettings, self).get_values()
		ICPSudo = self.env['ir.config_parameter'].sudo()
		res.update(
			account_id=int(ICPSudo.get_param('asm_accounting.account_id')),
		)
		return res