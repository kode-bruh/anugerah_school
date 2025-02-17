from odoo import api, models, fields, exceptions
from datetime import datetime, date, timedelta

class EditInvoiceWizard(models.TransientModel):
	_name = "as.edit_invoice.wiz"
	_description = "Pengubahan Tagihan"

	student_id = fields.Many2one("asm.student", ondelete="cascade", string="Siswa")
	invoice_id = fields.Many2one("as.due.payment", ondelete="cascade", string="Tagihan", domain="[('student_id', '=', student_id)]")
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)
	amount_total = fields.Float(string="Nominal Tagihan")
	balance_payment = fields.Boolean(string="Pembayaran Autodebit")
	reference = fields.Char(string="Referensi")
	due_date = fields.Date(string="Batas Bayar")
	note = fields.Char(string="Keterangan")

	@api.onchange("invoice_id")
	def _get_initial_value(self):
		for wiz in self:
			if wiz.invoice_id:
				wiz.amount_total = wiz.invoice_id.amount_total
				wiz.reference = wiz.invoice_id.reference
				wiz.due_date = wiz.invoice_id.due_date
				wiz.note = wiz.invoice_id.note
				wiz.balance_payment = wiz.invoice_id.balance_payment

	def validate_changes(self):
		for wiz in self:
			if not wiz.student_id:
				raise exceptions.UserError("Siswa harus dipilih sebelum melakukan perubahan tagihan.")
			if not wiz.invoice_id:
				raise exceptions.UserError("Tagihan harus dipilih sebelum melakukan perubahan.")

			timestamp = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%d %B %Y %H:%M")
			log = False
			text = "<p>Perubahan tagihan <b>%s</b> dilakukan oleh <b>%s</b> pada <b>%s</b><ul>" % (wiz.invoice_id.display_name, self.env.user.partner_id.name, timestamp)

			if wiz.amount_total != wiz.invoice_id.amount_total:
				if wiz.amount_total < wiz.invoice_id.paid:
					raise exceptions.UserError("Tidak dapat merubah Nominal Tagihan kurang dari yang telah dibayar siswa.")
				log = True	
				text += "<li>%s <i class='fa fa-long-arrow-right'></i> %s</li>" % (wiz.invoice_id.amount_total, wiz.amount_total)
				wiz.invoice_id.amount_total = wiz.amount_total

			if wiz.due_date != wiz.invoice_id.due_date:
				if not wiz.due_date:
					raise exceptions.UserError("Batas Bayar tagihan tidak boleh kosong.")
				log = True	
				text += "<li>%s <i class='fa fa-long-arrow-right'></i> %s</li>" % (wiz.invoice_id.due_date, wiz.due_date)
				wiz.invoice_id.due_date = wiz.due_date

			if wiz.reference != wiz.invoice_id.reference:
				if wiz.reference == '':
					raise exceptions.UserError("Referensi tagihan tidak boleh kosong.")
				log = True	
				text += "<li>%s <i class='fa fa-long-arrow-right'></i> %s</li>" % (wiz.invoice_id.reference, wiz.reference)
				wiz.invoice_id.reference = wiz.reference

			if wiz.note != wiz.invoice_id.note:
				log = True	
				text += "<li>%s <i class='fa fa-long-arrow-right'></i> %s</li>" % (wiz.invoice_id.note, wiz.note)
				wiz.invoice_id.note = wiz.note

			if wiz.balance_payment != wiz.invoice_id.balance_payment:
				log = True	
				text += "<li>Pembayaran Autodebit <i class='fa fa-long-arrow-right'></i> %s</li>" % (wiz.balance_payment)
				wiz.invoice_id.balance_payment = wiz.balance_payment

			if log:
				text += "</ul>"
				self.env['mail.message'].create({
					'subject': 'Nominal Tagihan Diubah',
					'date': datetime.now(),
					'author_id': self.env.user.partner_id.id,
					'model': 'asm.student',
					'res_id': wiz.student_id.id,
					'message_type': 'notification',
					'subtype_id': self.env.ref('mail.mt_note').id,
					'body': text
				})
			else:
				raise exceptions.UserError("Tidak ada perubahan dalam tagihan.")