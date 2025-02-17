from odoo import api, fields, models, exceptions
from datetime import date, datetime, timedelta

class Transaction(models.Model):
	_name = "asm.transaction"
	_description = "Transactions"

	def _get_default_account(self):
		return int(self.env['ir.config_parameter'].sudo().get_param('asm_accounting.account_id'))

	name = fields.Char(string="Kode Transaksi", readonly=True)
	account_id = fields.Many2one("asm.account", ondelete="restrict", string="Akun", required=True, default=_get_default_account)
	partner = fields.Char(string="Kepada")
	payment_method = fields.Many2one("as.selection", ondelete="restrict", required=True, string="Metode Pembayaran", domain="[('is_payment_channel', '=', True)]")
	type = fields.Selection([
		('OUT', 'OUT'),
		('IN', 'IN')
	], string="Tipe Transaksi", required=True)
	date = fields.Date(string="Tanggal", required=True, default=lambda *a: date.today())
	approved_by = fields.Many2one("res.users", ondelete="set null", string="Disetujui oleh", readonly=True)
	approved_date = fields.Datetime(string="Waktu Persetujuan", readonly=True)
	transaction_line_ids = fields.One2many("as.transaction.lines", "transaction_id", string="Daftar Barang")
	amount_total = fields.Float(string="Total", compute="_get_total", store=True)
	file = fields.Binary("Attachment")
	filename = fields.Char("File Name")
	state = fields.Selection([
		('Draft', 'Draft'),
		('Approved', 'Approved'),
		('Posted', 'Posted'),
		('Cancelled', 'Cancelled')
	], string="Status", default="Draft")
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)

	@api.model
	def create(self, values):
		res = super(Transaction, self).create(values)
		res['name'] = "AS/T/%s/%s" % (res['type'], str(res['id']).zfill(4))
		return res

	@api.depends("transaction_line_ids.subtotal")
	def _get_total(self):
		for i in self:
			total = 0
			for item in i.transaction_line_ids:
				total += item.subtotal
			i.amount_total = total

	def action_post(self):
		for i in self:
			if i.account_id:
				i.state = "Posted"
				timestamp = datetime.now()
				for item in i.transaction_line_ids:
					item.journal_id = self.env['asm.journal'].sudo().create({
						'account_id': i.account_id.id,
						'payment_method': i.payment_method.id,
						'name': "AS/J/IN/" if i.type == 'IN' else "AS/J/OUT/",
						'note': item.item,
						'date': timestamp,
						'debit': -(item.subtotal) if i.type == 'OUT' else 0,
						'credit': item.subtotal if i.type == 'IN' else 0,
						'total': item.subtotal if i.type == 'IN' else -(item.subtotal),
						'reference': "%s,%s" % (self._name, i.id),
					})
					item.journal_id.name += str(item.journal_id.id).zfill(4)

				# Create log
				timestamp = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%d %B %Y %H:%M")
				self.env['mail.message'].create({
					'subject': 'Transaction Registered',
					'date': datetime.now(),
					'author_id': self.env.user.partner_id.id,
					'model': 'asm.transaction',
					'res_id': i.id,
					'message_type': 'notification',
					'subtype_id': self.env.ref('mail.mt_note').id,
					'body': '<p>Pembayaran dilakukan untuk transaksi ini pada <b>%s</b> dan dilakukan oleh <b>%s</b></p>' % (timestamp, self.env.user.partner_id.name)
	 			})
			else:
				raise exceptions.UserError("Tidak bisa posting jurnal tanpa memilih akun.")

	def action_unpost(self):
		self.state = "Approved"
		for item in self.transaction_line_ids:
			next_journal = self.env['asm.journal'].search_count([('date', '>', item.journal_id.date), ('account_id', '=', item.journal_id.account_id.id)])
			if next_journal > 0:
				raise exceptions.UserError("Tidak dapat menghapus journal lama.")
			else:
				item.journal_id.sudo().unlink();

	def action_approve(self):
		self.state = "Approved"
		self.approved_by = self.env.uid
		self.approved_date = datetime.now()

	def action_cancel(self):
		valid_cancellation = True
		for i in self.transaction_line_ids:
			if i.journal_id:
				valid_cancellation = False
				break
		if valid_cancellation:
			self.state = "Cancelled"
			self.approved_by = None
			self.approved_date = None
		else:
			raise exceptions.UserError("Tidak bisa membatalkan transaksi yang sudah di-post.\nBatalkan post jurnal terlebih dahulu.")

	def action_draft(self):
		self.state = "Draft"

	def unlink(self):
		for i in self:
			if i.state not in ("Draft", "Cancelled"):
				raise exceptions.UserError("Harap batalkan transaksi ini sebelum menghapus.")
		super(Transaction, self).unlink()

class TransactionLine(models.Model):
	_name = "as.transaction.lines"
	_description = "Transaction Lines"
	_rec_name = "transaction_id"

	journal_id = fields.Many2one("asm.journal", ondelete="set null", string="Jurnal")
	transaction_id = fields.Many2one("asm.transaction", ondelete="cascade", string="Nota Transaksi")
	item = fields.Char(string="Nama Item")
	quantity = fields.Integer(string="Jumlah", required=True, default=1)
	price = fields.Float(string="Harga", required=True)
	tax = fields.Float(string="Pajak(%)")
	subtotal = fields.Float(string="Subtotal", compute="_get_subtotal", store=True)
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)

	@api.depends("quantity", "price", "tax")
	def _get_subtotal(self):
		for i in self:
			i.subtotal = (i.quantity * i.price) * ((100 + i.tax) / 100)

	@api.onchange("quantity")
	def _validate_quantity(self):
		for i in self:
			if i.quantity <= 0:
				raise exceptions.UserError("Jumlah barang minimal 1")

	@api.onchange("tax")
	def _validate_tax(self):
		for i in self:
			if i.tax < 0:
				raise exceptions.UserError("Pajak tidak dapat berupa angka negatif")

	@api.onchange("price")
	def _validate_price(self):
		for i in self:
			if i.price < 0:
				raise exceptions.UserError("Harga barang tidak dapat berupa angka negatif")