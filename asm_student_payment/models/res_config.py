from odoo import api, models, fields

SELECTION_MONTH = [
	('1', 'January'),
	('2', 'February'),
	('3', 'March'),
	('4', 'April'),
	('5', 'May'),
	('6', 'June'),
	('7', 'July'),
	('8', 'August'),
	('9', 'September'),
	('10', 'October'),
	('11', 'November'),
	('12', 'December'),
]

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	new_term_month = fields.Selection(SELECTION_MONTH, string="Awal Tahun Ajaran", default="July")

	def set_values(self):
		res = super(ResConfigSettings, self).set_values()
		self.env['ir.config_parameter'].sudo().set_param('asm_student_payment.new_term_month', self.new_term_month)
		return res

	@api.model
	def get_values(self):
		res = super(ResConfigSettings, self).get_values()
		ICPSudo = self.env['ir.config_parameter'].sudo()
		res.update(
			new_term_month=ICPSudo.get_param('asm_student_payment.new_term_month'),
		)
		return res