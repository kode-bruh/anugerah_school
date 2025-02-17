from odoo import api, models, fields, exceptions
from datetime import datetime, date

class RefundPayment(models.Model):
	_name = "as.refund.payment"
	_description = "Refund Payment"

	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)
	approved_date = fields.Datetime(string="Tanggal Refund", readonly=True)
	user_id = fields.Many2one("res.users", ondelete="restrict", string="Refund oleh", readonly=True)

	name = fields.Char(string="Kode Refund", readonly=True)
	student_id = fields.Many2one("asm.student", ondelete="restrict", string="Siswa", required=True)
	invoice_id = fields.Many2one("as.due.payment", ondelete="set null", string="Tagihan", domain="[('student_id', '=', student_id)]")
	account_id = fields.Many2one("asm.account", ondelete="restrict", required=True, string="Akun Keuangan")
	payment_method = fields.Many2one("as.selection", ondelete='restrict', string="Metode Pembayaran", required=True, domain="[('is_payment_channel', '=', True)]")
	journal_id = fields.Many2one("asm.journal", ondelete="set null", string="Jurnal", readonly=True)
	amount = fields.Float(string="Nominal", required=True)
	note = fields.Text(string="Keterangan")

	@api.model
	def create(self, values):
		res = super(RefundPayment, self).create(values)
		res.name = "AS/RE/%s" % str(res.id).zfill(4)
		return res

	def unlink(self):
		for rec in self:
			if rec.journal_id:
				raise exceptions.UserError("Tidak bisa menghapus refund yang sudah dipost.")
		return super(RefundPayment, self).unlink()

	def unpost_refund(self):
		for refund in self:
			refund.write({
				'approved_date': False,
				'user_id': False,
			})

			refund.journal_id.unlink()

			# Create log
			self.env['mail.message'].create({
				'subject': 'Refund Registered',
				'date': datetime.now(),
				'author_id': self.env.user.partner_id.id,
				'model': 'asm.student',
				'res_id': refund.student_id.id,
				'message_type': 'notification',
				'subtype_id': self.env.ref('mail.mt_note').id,
				'body': "Refund <b>%s</b> dibatalkan oleh <b>%s</b> pada <b>%s</b>." % (refund.name, self.env.user.partner_id.name, datetime.now().strftime("%d %B %Y %H:%M"))
 			})

	def post_refund(self):
		for refund in self:
			refund.write({
				'approved_date': datetime.now(),
				'user_id': self.env.user.id,
			})

			refund.journal_id = self.env['asm.journal'].sudo().create({
				'account_id': refund.account_id.id,
				'payment_method': refund.payment_method.id,
				'name': "AS/J/RE/%s" % str(refund.id).zfill(4),
				'note': "Refund untuk siswa %s" % refund.student_id.full_name,
				'date': datetime.now(),
				'debit': -(refund.amount),
				'credit': 0,
				'total': refund.amount,
				'reference': "%s,%s" % (self._name, refund.id),
			})

			# Create log
			self.env['mail.message'].create({
				'subject': 'Refund Registered',
				'date': datetime.now(),
				'author_id': self.env.user.partner_id.id,
				'model': 'asm.student',
				'res_id': refund.student_id.id,
				'message_type': 'notification',
				'subtype_id': self.env.ref('mail.mt_note').id,
				'body': "Refund <b>%s</b> dilakukan oleh <b>%s</b> dengan nominal <b>%s %s</b> pada <b>%s</b>." % (refund.name, self.env.user.partner_id.name, refund.currency_id.symbol, refund.amount, datetime.now().strftime("%d %B %Y %H:%M"))
 			})