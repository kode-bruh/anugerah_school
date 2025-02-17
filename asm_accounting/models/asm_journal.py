from odoo import api, fields, models, exceptions
from datetime import date, datetime, timedelta

class Account(models.Model):
	_name = "asm.account"
	_description = "Akun Keuangan"

	name = fields.Char(string="Nama", required=True)
	journal_ids = fields.One2many("asm.journal", "account_id", string="Jurnal Keuangan")
	balance = fields.Float(string="Saldo", compute="_get_balance", store=True)
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)

	@api.depends("journal_ids", "journal_ids.active")
	def _get_balance(self):
		for i in self:
			total = 0
			for journal in i.journal_ids:
				total += journal.total
			i.balance = total

class Journal(models.Model):
	_name = "asm.journal"
	_description = "Jurnal Keuangan"

	active = fields.Boolean(default=True)
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)
	account_id = fields.Many2one("asm.account", ondelete="restrict", string="Akun", readonly=True)
	payment_method = fields.Many2one("as.selection", ondelete="restrict", string="Metode Bayar", domain="[('is_payment_channel', '=', True)]")
	name = fields.Char(string="Kode Jurnal", readonly=True)
	date = fields.Datetime(string="Tanggal")
	debit = fields.Float(string="Debit", readonly=True)
	credit = fields.Float(string="Kredit", readonly=True)
	total = fields.Float(string="Total", readonly=True)
	balance = fields.Float(string="Saldo")
	note = fields.Char(string="Keterangan")
	change_ids = fields.One2many("as.change_journal.line", "journal_id", string="Perubahan", readonly=True)
	change_count = fields.Integer(string="Jumlah Perubahan", compute="_get_total_changes", store=True)

	reference = fields.Reference([
		('asm.transaction', 'asm.transaction'),
		('as.payment','as.payment'),
		('as.refund.payment', 'as.refund.payment'),
		('as.account.adjustment', 'as.account.adjustment'),
	], string="Asal Transaksi")

	@api.model
	def create(self, values):
		res = super(Journal, self).create(values)
		prev_journal = self.env['asm.journal'].search([('date', '<', res['date']), ('account_id', '=', res['account_id'].id)], limit=1, order='date desc')
		if prev_journal:
			res['balance'] = prev_journal.balance + res['debit'] + res['credit']
		else:
			res['balance'] += res['debit'] + res['credit']
		return res

	def recalculate_journal_balance(self):
		active_ids = self.env.context.get('active_ids', [])
		journals = self.env['asm.journal'].search([('id', 'in', active_ids)], order="id asc")
		for journal in journals:
			if journal.active:
				prev_journal = self.env['asm.journal'].search([('id', '<', journal.id), ('active', '=', True)], limit=1, order="id desc")
				balance = 0
				if prev_journal:
					balance = prev_journal.balance
				balance += journal.debit + journal.credit
				journal.balance = balance

	@api.depends("change_ids.approved_date")
	def _get_total_changes(self):
		for journal in self:
			journal.change_count = len([change for change in journal.change_ids if change.approved_date])

	def view_journal_changes(self):
		for journal in self:
			return {
				'type': 'ir.actions.act_window',
				'name': 'Perubahan Jurnal',
				'res_model': 'as.change_journal.line',
				'view_mode': 'tree',
				'target': 'current',
				'domain': [('journal_id', '=', journal.id), ('approved_date', '!=', False)]
			}

class AccountAdjustment(models.Model):
	_name = "as.account.adjustment"
	_description = "Penyesuaian Akun"

	name = fields.Char(string="Kode Penyesuaian", default="New", readonly=True)
	desc = fields.Char(string="Deskripsi", required=True)
	account_id = fields.Many2one("asm.account", ondelete="restrict", string="Akun", required=True, help="Akun yang saldo nnya akan disesuaikan.")
	current_balance = fields.Float(string="Saldo", compute="_get_current_balance", store=True)
	adjust_date = fields.Datetime(string="Tanggal Disahkan", readonly=True)
	value = fields.Float(string="Saldo Akhir", required=True, help="Jumlah saldo akhir yang diberlakukan setelah validasi penyesuaian.")
	state = fields.Selection([
		('Draft', 'Draft'),
		('Validated', 'Validated')
	], string="Status", default='Draft')
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)

	@api.depends("account_id")
	def _get_current_balance(self):
		for i in self:
			if i.account_id:
				i.current_balance = i.account_id.balance
			else:
				i.current_balance = 0

	def action_validate(self):
		if self.value == self.current_balance:
			raise exceptions.UserError("Saldo akhir tidak boleh sama dengan saldo saat ini.")
		else:
			self.state = 'Validated'
			self.adjust_date = datetime.now()
			self.name = "AS/J/ADJ/%s" % str(self.id).zfill(4)
			deviation = self.value - self.current_balance
			journal = self.env['asm.journal'].sudo().create({
				'account_id': self.account_id.id,
				'name': self.name,
				'date': datetime.now(),
				'debit': deviation if deviation < 0 else 0,
				'credit': deviation if deviation > 0 else 0,
				'total': deviation,
				'note': self.desc,
				'reference': "%s,%s" % (self._name, self.id),
			})
			journal.balance = self.value