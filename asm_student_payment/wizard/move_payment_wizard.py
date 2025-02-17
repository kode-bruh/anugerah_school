from odoo import api, models, fields, exceptions
from datetime import datetime, date, timedelta

class MovePaymentWizard(models.TransientModel):
	_name = "as.move_payment.wiz"
	_description = "Pemindahan Pembayaran"

	student_id = fields.Many2one("asm.student", ondelete="cascade")
	invoice_from_id = fields.Many2one("as.due.payment", ondelete="cascade", string="Tagihan", required=True, domain="[('student_id', '=', student_id)]")
	invoice_to_id = fields.Many2one("as.due.payment", ondelete="cascade", string="Tujuan Tagihan", required=True, domain="[('student_id', '=', student_id), ('status', '=', 'Belum Lunas'), ('id', '!=' , invoice_from_id)]")
	payment_id = fields.Many2one("as.payment", ondelete="cascade", string="Pembayaran", required=True, domain="[('payment_id', '=', invoice_from_id)]")

	@api.onchange("student_id", "payment_id")
	def _set_invoice_to_domain(self):
		for wiz in self:
			if wiz.payment_id and wiz.student_id:
				return {
					'domain': {
						'invoice_to_id': [('unpaid', '>=', wiz.payment_id.value), ('student_id', '=', wiz.student_id.id), ('status', '=', 'Belum Lunas'), ('id', '!=' , wiz.invoice_from_id.id)]
					}
				}
			else:
				return {
					'domain': {
						'invoice_to_id': [('student_id', '=', wiz.student_id.id), ('status', '=', 'Belum Lunas'), ('id', '!=' , wiz.invoice_from_id.id)]
					}
				}

	def action_move(self):
		for wiz in self:
			text = "<ul><li>Pembayaran %s dipindah dari tagihan %s <i class='fa fa-long-arrow-right'></i> <b>%s</b> oleh %s</li></ul>" % (wiz.payment_id.display_name, wiz.invoice_from_id.display_name, wiz.invoice_to_id.display_name, self.env.user.partner_id.display_name)
			wiz.payment_id.write({
				'payment_id': wiz.invoice_to_id.id
			})

			self.env['mail.message'].create({
				'subject': 'Pembayaran Dipindah',
				'date': datetime.now(),
				'author_id': self.env.user.partner_id.id,
				'model': 'asm.student',
				'res_id': wiz.invoice_from_id.student_id.id,
				'message_type': 'notification',
				'subtype_id': self.env.ref('mail.mt_note').id,
				'body': text
			})