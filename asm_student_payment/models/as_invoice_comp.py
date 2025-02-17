from odoo import api, models, fields, exceptions
from datetime import datetime

class InvoiceCompensation(models.Model):
	_name = "as.invoice.comp"
	_inherit = 'mail.thread'
	_description = "Kompensasi Tagihan"
	_order = "id desc"

	name = fields.Char(string="Kode Kompensasi", readonly=True, copy=False)
	invoice_id = fields.Many2one("as.due.payment", ondelete="cascade", string="Tagihan", required=True)
	currency_id = fields.Many2one('res.currency', related="invoice_id.currency_id", store=True)
	student_id = fields.Many2one("asm.student", related="invoice_id.student_id", store=True, string="Siswa")
	description = fields.Char(string="Keterangan", required=True, copy=False)
	amount = fields.Float(string="Nilai Kompensasi", required=True)
	state = fields.Selection([
		('inactive', 'Tidak Aktif'),
		('active', 'Aktif')
	], default="inactive")
	validated_by = fields.Many2one("res.users", ondelete="restrict", readonly=True, copy=False)
	validated_on = fields.Datetime(readonly=True, copy=False)

	@api.model
	def create(self, values):
		rec = super(InvoiceCompensation, self).create(values)
		rec.name = 'AS/INV-COMP/%s/%s' % (str(rec.student_id.id).zfill(5), str(rec.id).zfill(5))
		return rec

	@api.constrains("amount")
	def _check_amount(self):
		for i in self:
			if i.amount <= 0:
				raise exceptions.UserError("Nilai kompensasi harus lebih dari 0.")

	def validate_comp(self):
		for i in self:
			i.write({
				'state': 'active',
				'validated_by': self.env.uid,
				'validated_on': datetime.now(),
			})