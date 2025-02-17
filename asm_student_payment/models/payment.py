from odoo import api, fields, models, exceptions
from datetime import date, datetime, timedelta
import pytz
import math
import logging
_logger = logging.getLogger(__name__)

class DuePayment(models.Model):
	_name = "as.due.payment"
	_description = "Due Payment"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	active = fields.Boolean(default=True)
	name = fields.Char(string="Kode Tagihan")
	current_class = fields.Char(string="Kelas Siswa", related="student_id.current_class", store=True)
	reference = fields.Char(string="Referensi")
	student_id = fields.Many2one("asm.student", ondelete="cascade", string="Siswa")
	payment_ids = fields.One2many("as.payment", "payment_id", string="Histori Bayar", readonly=True)
	due_date = fields.Date(string="Batas Bayar")
	amount_total = fields.Float(string="Nominal")
	paid = fields.Float(string="Terbayar", compute="_get_total_paid", store=True)
	unpaid = fields.Float(string="Belum Bayar", compute="_get_total_paid", store=True)
	status = fields.Selection([
		('Belum Lunas', 'Belum Lunas'),
		('Lunas', 'Lunas')
	], string="Status", compute="_get_total_paid", store=True)
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)
	balance_payment = fields.Boolean(string="Pembayaran Autodebit")
	note = fields.Char(string="Keterangan")
	compensation_ids = fields.One2many("as.invoice.comp", "invoice_id", readonly=True, copy=False)
	created_automatically_on = fields.Datetime(string="Tanggal Terbuat Otomatis", readonly=True)
	refund_ids = fields.One2many("as.refund.payment", "invoice_id", string="Refund")

	def action_create_comp(self):
		for i in self:
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'as.invoice.comp',
				'view_mode': 'form',
				'view_type': 'form',
				'target': 'new',
				'context': {
					'default_invoice_id': i.id,
				}
			}

	def action_open_refund(self):
		for i in self:
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'as.refund.payment',
				'view_mode': 'form',
				'view_type': 'form',
				'target': 'new',
				'context': {
					'default_student_id': i.student_id.id,
					'default_invoice_id': i.id,
				}
			}

	def action_change_amount(self):
		for i in self:
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'as.edit_invoice.wiz',
				'view_mode': 'form',
				'target': 'new',
				'context': {
					'default_student_id': i.student_id.id,
					'default_invoice_id': i.id,
					'default_currency_id': i.currency_id.id,
					'default_amount_total': i.amount_total,
				}
			}

	def toggle_active(self):
		for i in self:
			active = not i.active
			for payment in i.payment_ids:
				if payment.active == i.active:
					payment.journal_id.active = active
					if payment.fee_journal_id:
						payment.fee_journal_id.active = active
					if payment.cut_journal_id:
						payment.cut_journal_id.active = active
					payment.active = active
			i.active = active

	def print_report(self):
		return self.env.ref("asm_student_payment.student_invoice").report_action(self)

	@api.model
	def create(self, values):
		res = super(DuePayment, self).create(values)
		res['name'] = "AS/INV/%s/%s" % (datetime.today().strftime("00%Y%m"), str(res['id']).zfill(4))
		self.env['mail.activity'].create({
			'res_model_id': self.env['ir.model'].search([('model', '=', 'as.due.payment')]).id,
			'res_id': res['id'],
			'user_id': self.env.uid,
			'date_deadline': res['due_date'],
			'note': 'Harap melakukan penagihan kepada orang tua / wali siswa untuk tagihan ini.',
			'summary': 'Tagihan Belum Lunas',
		})
		return res

	def unlink(self):
		for rec in self:
			if len(rec.payment_ids) > 0:
				raise exceptions.UserError("Tidak bisa menghapus tagihan yang sudah terbayarkan.")
		return super(DuePayment, self).unlink()

	def name_get(self):
		res = []
		for rec in self:
			res.append((rec.id, "%s (%s)" % (rec.name, rec.reference)))
		return res

	@api.depends("amount_total", "payment_ids.state", "payment_ids.active", "compensation_ids.state")
	def _get_total_paid(self):
		for i in self:
			total = 0
			for payment in i.payment_ids:
				if payment.state == 'Posted' and payment.active:
					total += math.ceil(payment.value)
			for comp in i.compensation_ids:
				if comp.state == 'active':
					total += math.ceil(comp.amount)
			i.paid = total
			i.unpaid = i.amount_total - i.paid
			if total >= i.amount_total:
				i.status = "Lunas"
			else:
				i.status = "Belum Lunas"

	@api.model
	def manual_daily_run(self):
		localTZ = pytz.timezone("Asia/Jakarta") 
		states = self.env['asm.state'].search([('is_invoiced', '=', True)])
		invoiced_students = self.env['asm.student'].search([('invoiced', '=', True), ('state_id', 'in', states.ids), ('active', '=', True)], order="id desc")
		text = "TOTAL INVOICED %s | " % len(invoiced_students)
		current_date = datetime.now(localTZ)
		automatic_create_date = datetime.now()
		starting_month = self.env['ir.config_parameter'].sudo().get_param('asm_student_payment.new_term_month', default=7)
		for student in invoiced_students:
			for personal_rule in student.invoice_rules:
				# Checks and create invoice if invoice date is today
				if personal_rule.category_type == 'Perulangan':
					if personal_rule.invoiced:
						invoice_name = personal_rule.name
						if personal_rule.balance_payment:
							invoice_name += " %s" % current_date.strftime("%B %Y")

						# Check if term
						term_id = personal_rule.term_id
						current_term_year_in = current_date.year if current_date.month >= int(starting_month) else current_date.year - 1
						current_term_year_out = current_date.year + 1 if current_date.month >= int(starting_month) else current_date.year
						in_term = True
						if term_id:
							if str(term_id.year_in) != str(current_term_year_in) or str(term_id.year_out) != str(current_term_year_out):
								in_term = False

						existing_invoice = self.env['as.due.payment'].search([('student_id', '=', student.id), ('reference', '=', invoice_name)], limit=1)
						if in_term:
							text += "This month is in term for: %s : %s | " % (invoice_name, student.full_name) 
							if not existing_invoice:
								self.env['as.due.payment'].create({
									'reference': invoice_name,
									'student_id': student.id,
									'due_date': (current_date + timedelta(days=personal_rule.due)).date(),
									'amount_total': personal_rule.amount_total,
									'balance_payment': personal_rule.balance_payment,
									'created_automatically_on': automatic_create_date,
								})
								text += 'Today is the invoice date: %s | ' % student.full_name
							else:
								text += 'Existing invoice detected for %s : %s | ' % (invoice_name, student.full_name) 
						else:
							text += "This month is not in term for: %s : %s | " % (invoice_name, student.full_name) 
					else:
						text += 'Invoice rule is not detected for %s : %s | ' % (personal_rule, student.full_name)
		_logger.warning(text)

	@api.model
	def daily_run(self, force_date=False):
		localTZ = pytz.timezone("Asia/Jakarta") 
		states = self.env['asm.state'].search([('is_invoiced', '=', True)])
		invoiced_students = self.env['asm.student'].search([('invoiced', '=', True), ('state_id', 'in', states.ids), ('active', '=', True)], order="id desc")
		text = "TOTAL INVOICED %s | " % len(invoiced_students)
		current_date = datetime.now(localTZ) if not force_date else datetime.strptime("%s 01:00:00 +0700" % force_date, "%Y-%m-%d %H:%M:%S %z")
		automatic_create_date = datetime.now()
		starting_month = self.env['ir.config_parameter'].sudo().get_param('asm_student_payment.new_term_month', default=7)
		for student in invoiced_students:
			for personal_rule in student.invoice_rules:
				# Checks and create invoice if invoice date is today
				if personal_rule.category_type == 'Perulangan':
					if personal_rule.invoiced:
						invoice_name = personal_rule.name
						if personal_rule.balance_payment:
							invoice_name += " %s" % current_date.strftime("%B %Y")

						# Check if term
						term_id = personal_rule.term_id
						current_term_year_in = current_date.year if current_date.month >= int(starting_month) else current_date.year - 1
						current_term_year_out = current_date.year + 1 if current_date.month >= int(starting_month) else current_date.year
						in_term = True
						if term_id:
							if str(term_id.year_in) != str(current_term_year_in) or str(term_id.year_out) != str(current_term_year_out):
								in_term = False

						existing_invoice = self.env['as.due.payment'].search([('student_id', '=', student.id), ('reference', '=', invoice_name)], limit=1)
						if in_term:
							text += "This month is in term for: %s : %s | " % (invoice_name, student.full_name) 
							if not existing_invoice:
								if int(current_date.strftime("%d")) == personal_rule.invoiced_date and personal_rule.amount_total > 0:
									self.env['as.due.payment'].create({
										'reference': invoice_name,
										'student_id': student.id,
										'due_date': (current_date + timedelta(days=personal_rule.due)).date(),
										'amount_total': personal_rule.amount_total,
										'balance_payment': personal_rule.balance_payment,
										'created_automatically_on': automatic_create_date,
									})
									text += 'Today is the invoice date: %s | ' % student.full_name
								else:
									text += 'Today is not the invoice date : %s | ' % student.full_name
							else:
								text += 'Existing invoice detected for %s : %s | ' % (invoice_name, student.full_name) 
						else:
							text += "This month is not in term for: %s : %s | " % (invoice_name, student.full_name) 
					else:
						text += 'Invoice rule is not detected for %s : %s | ' % (personal_rule, student.full_name)
		_logger.warning(text)

class InvoiceRules(models.Model):
	_name = "as.invoice.rule"
	_description = "Invoice Rule"
	_rec_name = "payment_category_id"

	payment_category_id = fields.Many2one("asm.payment.category", ondelete="set null", string="Tunggakan")
	student_id = fields.Many2one("asm.student", ondelete="cascade", string="Siswa")
	discount = fields.Float(string="Diskon(%)", default=0) # No longer used, hidden in view
	discount_amount = fields.Float(string="Diskon(Rp.)", default=0)
	invoiced = fields.Boolean(string="Tertagih", default=True)
	value = fields.Float(string="Harga")
	amount_total = fields.Float(string="Total", compute="_get_total", store=True)
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)

	name = fields.Char(string="Tunggakan", readonly=True)
	category_type = fields.Selection([
		("1x Bayar", "1x Bayar"),
		("Perulangan", "Perulangan")
	], string="Tipe Pembayaran", readonly=True)
	balance_payment = fields.Boolean(string="Bayar dari Autodebit", readonly=True)
	invoiced_date = fields.Integer(string="Tanggal Tertagih", readonly=True)
	due = fields.Integer(string="Batas Pembayaran", readonly=True)
	term_id = fields.Many2one("asm.term", ondelete="restrict", string="Tahun Ajaran", readonly=True)

	@api.model
	def create(self, values):
		res = super(InvoiceRules, self).create(values)
		res.value = res.payment_category_id.value
		res.name = res.payment_category_id.name
		res.category_type = res.payment_category_id.category_type
		res.balance_payment = res.payment_category_id.balance_payment
		res.invoiced_date = res.payment_category_id.invoiced_date
		res.due = res.payment_category_id.due
		res.term_id = res.payment_category_id.template_id.term_id.id
		return res

	def write(self, values):
		log = False
		for rec in self:
			text = "<p>Terdapat perubahan pada aturan tagihan <b>%s</b> yang dilakukan oleh <b>%s</b></p><ul>" % (rec.name, self.env.user.partner_id.name)
			if 'value' in values and values['value'] != rec.value:
				log = True
				text += "<li>Harga: %s <i class='fa fa-long-arrow-right'></i> %s</li>" % (rec.value, values['value'])
			if 'discount_amount' in values and values['discount_amount'] != rec.discount_amount:
				log = True
				text += "<li>Diskon (Rp.): %s <i class='fa fa-long-arrow-right'></i> %s</li>" % (rec.discount_amount, values['discount_amount'])
			if 'invoiced' in values and values['invoiced'] != rec.invoiced:
				log = True
				text += "<li>Tertagih: %s <i class='fa fa-long-arrow-right'></i> Tertagih %s</li>" % (rec.invoiced, values['invoiced'])
			if log:
				self.env['mail.message'].sudo().create({
					'subject': 'Invoice Rules Changed',
					'date': datetime.now(),
					'author_id': self.env.user.partner_id.id,
					'model': 'asm.student',
					'res_id': rec.student_id.id,
					'message_type': 'notification',
					'subtype_id': self.env.ref('mail.mt_note').id,
					'body': text
	 			})
		return super(InvoiceRules, self).write(values)

	@api.depends("invoiced", "discount_amount", "value")
	def _get_total(self):
		for i in self:
			if i.invoiced:
				i.amount_total = i.value - i.discount_amount
			else:
				i.amount_total = 0

class PaymentCategories(models.Model):
	_name = "asm.payment.category"
	_description = "Payment Category"

	template_id = fields.Many2one("as.payment.template", ondelete="cascade", string="Template")
	name = fields.Char(string="Jenis Tunggakan", required=True)
	category_type = fields.Selection([
		("1x Bayar", "1x Bayar"),
		("Perulangan", "Perulangan")
	], string="Tipe Pembayaran", default="1x Bayar")
	balance_payment = fields.Boolean(string="Bayar dari Autodebit")
	invoiced_date = fields.Integer(string="Tanggal Tertagih", default=1)
	value = fields.Float(string="Nilai Tunggakan", required=True)
	due = fields.Integer(string="Batas Pembayaran", help="Berapa hari sampai invoice tersebut akan disebut terlambat bayar.")
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)

	def write(self, values):
		for rec in self:
			text = "<ul>Perubahan dilakukan pada tagihan %s:" % rec.name
			log = False
			if 'value' in values:
				log = True
				text += "<li>Nominal: %s <i class='fa fa-long-arrow-right'></i> %s</li>" % (rec.value, values['value'])
			if 'name' in values:
				log = True
				text += "<li>Jenis Tunggakan: %s <i class='fa fa-long-arrow-right'></i> %s</li>" % (rec.name, values['name'])
			if 'category_type' in values:
				log = True
				text += "<li>Tipe Pembayaran: %s <i class='fa fa-long-arrow-right'></i> %s</li>" % (rec.category_type, values['category_type'])
			if 'invoiced_date' in values:
				log = True
				text += "<li>Tanggal Tertagih: %s <i class='fa fa-long-arrow-right'></i> %s</li>" % (rec.invoiced_date, values['invoiced_date'])
			if 'balance_payment' in values:
				log = True
				text += "<li>Bayar dari Autodebit: %s <i class='fa fa-long-arrow-right'></i> %s</li>" % (rec.balance_payment, values['balance_payment'])
			text += "</ul>"
			if log:
				self.env['mail.message'].create({
					'subject': 'Tagihan Diubah',
					'date': datetime.now(),
					'author_id': self.env.user.partner_id.id,
					'model': 'as.payment.template',
					'res_id': rec.template_id.id,
					'message_type': 'notification',
					'subtype_id': self.env.ref('mail.mt_note').id,
					'body': text
	 			})
		return super(PaymentCategories, self).write(values)

	@api.onchange('category_type', 'invoiced_date')
	def _validate_date(self):
		if self.category_type == 'Perulangan':
			if self.invoiced_date <= 0 or self.invoiced_date > 30:
				raise exceptions.UserError("Tanggal tertagih hanya dapat diisi 1-30.")

class PaymentTemplate(models.Model):
	_name = "as.payment.template"
	_inherit = ['mail.thread']
	_description = "Payment Template"

	name = fields.Char(string="Nama Template", required=True)
	term_id = fields.Many2one("asm.term", ondelete="restrict", string="Tahun Ajaran", required=True)
	stage_id = fields.Many2one("asm.class.stage", ondelete="restrict", string="Jenjang", required=True)
	# account_id = fields.Many2one("asm.account", ondelete="restrict", required=True, string="Akun Keuangan") # Moved to as.payment
	category_ids = fields.One2many("asm.payment.category", "template_id", string="Pembayaran", tracking=True)

	def name_get(self):
		res = []
		for rec in self:
			res.append((rec.id, "%s (%s)" % (rec.name, rec.term_id.display_name)))
		return res

class Payment(models.Model):
	_name = "as.payment"
	_description = "Payment"

	active = fields.Boolean(default=True)
	name = fields.Char(string="Kode Transaksi", readonly=True)
	student_id = fields.Many2one("asm.student", ondelete="set null", string="Siswa")
	account_id = fields.Many2one("asm.account", ondelete="restrict", required=True, string="Akun Keuangan")
	payment_id = fields.Many2one("as.due.payment", ondelete="set null", string="Tagihan", domain="[('student_id', '=', student_id), ('status', '=', 'Belum Lunas')]")
	payment_method = fields.Many2one("as.selection", ondelete='restrict', string="Metode Pembayaran", required=True, domain="[('is_payment_channel', '=', True)]")
	journal_id = fields.Many2one("asm.journal", ondelete="set null", string="Jurnal")
	fee_journal_id = fields.Many2one("asm.journal", ondelete="set null", string="Jurnal Denda")
	cut_journal_id = fields.Many2one("asm.journal", ondelete="set null", string="Jurnal Potongan")
	amount_to_pay = fields.Float(string="Total", related="payment_id.unpaid")
	value = fields.Float(string="Nominal Bayar", required=True)
	subtotal = fields.Float(string="Nominal Diterima", compute="_get_total_paid", store=True)
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)
	approved_by = fields.Many2one("res.users", ondelete="restrict", string="Disetujui oleh", readonly=True)
	approved_date = fields.Datetime(string="Tanggal", readonly=True)
	payment_note = fields.Text(string="Catatan Nominal", readonly=True)
	state = fields.Selection([
		('Draft', 'Draft'),
		('Posted', 'Posted')
	], string="Status", default="Draft")
	note = fields.Text(string="Keterangan")

	def toggle_active(self):
		for i in self:
			active = not i.active
			i.active = active
			i.journal_id.active = active
			if i.fee_journal_id:
				i.fee_journal_id.active = active
			if i.cut_journal_id:
				i.cut_journal_id.active = active

	@api.depends("payment_method", "value")
	def _get_total_paid(self):
		for i in self:
			value = i.value
			value_list = []
			if i.payment_method.payment_extra_fee:
				value_list.append(i.payment_method.payment_extra_fee)
			
			if i.payment_method.payment_cut_fee:
				value_list.append(-(i.payment_method.payment_cut_fee * value))
			i.subtotal = i.value + sum(value_list)

	@api.model
	def create(self, values):
		res = super(Payment, self).create(values)
		res['name'] = "AS/P/%s" % str(res['id']).zfill(4)
		return res

	def move_payment_wiz(self):
		for i in self:
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'as.move_payment.wiz',
				'view_mode': 'form',
				'target': 'new',
				'context': {
					'default_student_id': i.student_id.id,
					'default_invoice_from_id': i.payment_id.id,
					'default_payment_id': i.id,
				}
			}

	def action_post(self, autodebit=False):
		for i in self:
			i.state = 'Posted'
			i.approved_by = self.env.uid
			i.approved_date = datetime.now()

			# MAIN JOURNAL (FROM VALUE)
			i.journal_id = self.env['asm.journal'].sudo().create({
				'account_id': i.account_id.id,
				'payment_method': i.payment_method.id,
				'name': "AS/J/SP/%s" % str(i.id).zfill(4),
				'note': "Pembayaran %s %s" % (i.payment_id.reference, i.student_id.full_name),
				'date': datetime.now(),
				'debit': 0,
				'credit': i.value,
				'total': i.value,
				'reference': "%s,%s" % (self._name, i.id),
			})

			# SECONDARY JOURNAL (FROM FEE & CUT)
			text = ""
			if i.payment_method.payment_extra_fee:
				i.fee_journal_id = self.env['asm.journal'].sudo().create({
					'account_id': i.account_id.id,
					'payment_method': i.payment_method.id,
					'name': "AS/J/X/%s" % str(i.id).zfill(4),
					'note': "Denda Pembayaran %s %s" % (i.payment_id.reference, i.student_id.full_name),
					'date': datetime.now(),
					'debit': 0,
					'credit': i.payment_method.payment_extra_fee,
					'total': i.payment_method.payment_extra_fee,
					'reference': "%s,%s" % (self._name, i.id),
				})
				text += "Nominal pembayaran dikenai denda sebesar Rp. %s\n" % i.payment_method.payment_extra_fee
			if i.payment_method.payment_cut_fee:
				i.cut_journal_id = self.env['asm.journal'].sudo().create({
					'account_id': i.account_id.id,
					'payment_method': i.payment_method.id,
					'name': "AS/J/X/%s" % str(i.id).zfill(4),
					'note': "Potongan Pembayaran %s %s" % (i.payment_id.reference, i.student_id.full_name),
					'date': datetime.now(),
					'debit': -(i.payment_method.payment_cut_fee * i.value),
					'credit': 0,
					'total': -(i.payment_method.payment_cut_fee * i.value),
					'reference': "%s,%s" % (self._name, i.id),
				})
				text += "Nominal pembayaran dikenai potongan sebesar %s%% (Rp. %s)\n" % ((i.payment_method.payment_cut_fee * 100), (i.payment_method.payment_cut_fee * i.value))
			i.payment_note = text

			# Create log
			timestamp = datetime.strftime(fields.Datetime.context_timestamp(self, i.approved_date), "%d %B %Y %H:%M")
			message = '<p>Pembayaran dilakukan untuk tagihan <b>%s</b> pada <b>%s</b> dan dilakukan oleh <b>%s</b></p>' % (i.payment_id.name, timestamp, self.env.user.partner_id.name)
			if autodebit:
				message = '<p>Pembayaran Autodebit dilakukan untuk tagihan <b>%s</b> pada <b>%s</b> dan dilakukan oleh <b>%s</b></p>' % (i.payment_id.name, timestamp, self.env.user.partner_id.name)
			self.env['mail.message'].sudo().create({
				'subject': 'Payment Registered',
				'date': datetime.now(),
				'author_id': self.env.user.partner_id.id,
				'model': 'asm.student',
				'res_id': i.student_id.id,
				'message_type': 'notification',
				'subtype_id': self.env.ref('mail.mt_note').id,
				'body': message
 			})

	def action_cancel(self):
		# if self.payment_id.balance_payment:
		# 	raise exceptions.UserError("Cancel post tidak diperbolehkan untuk tagihan autodebit.")
		# else:
		# next_journal = self.env['asm.journal'].search_count([('date', '>', self.journal_id.date), ('account_id', '=', self.account_id.id)])
		# if next_journal > 0:
		# 	raise exceptions.UserError("Tidak dapat menghapus journal lama.")
		# else:
		self.state = 'Draft'
		self.approved_by = None
		self.approved_date = None
		self.journal_id.unlink()
		self.fee_journal_id.unlink()
		self.cut_journal_id.unlink()

	@api.onchange("payment_id", "value")
	def _check_payment_value(self):
		for i in self:
			if i.payment_id.unpaid < i.value:
				raise exceptions.UserError("Tidak bisa membayar melebihi total tagihan.")

	@api.model
	def default_get(self, fields):
		rec = super(Payment, self).default_get(fields)
		if self._context.get('student_id'):
			rec['student_id'] = self._context.get("student_id")
			rec['account_id'] = int(self.env['ir.config_parameter'].sudo().get_param('asm_accounting.account_id'))
		return rec