from odoo import api, models, fields, exceptions
from datetime import datetime, date, timedelta

YEARS = [
	('2023', '2023'),
	('2024', '2024'),
	('2025', '2025'),
	('2026', '2026'),
	('2027', '2027'),
	('2028', '2028'),
	('2029', '2029'),
	('2030', '2030'),
	('2031', '2031'),
	('2032', '2032'),
	('2033', '2033'),
	('2034', '2034'),
	('2035', '2035'),
	('2036', '2036'),
	('2037', '2037'),
	('2038', '2038'),
	('2039', '2039'),
	('2040', '2040'),
	('2041', '2041'),
	('2042', '2042'),
	('2043', '2043'),
]

class CreateInvoiceWizard(models.TransientModel):
	_name = "as.create_invoice.wiz"
	_description = "Pembuatan Tagihan"

	is_custom = fields.Boolean()
	student_id = fields.Many2one("asm.student", ondelete="set null", string="Siswa")
	invoice_ids = fields.One2many("as.create_invoice.line", "wizard_id", string="Tagihan Yang Dibuat")
	alternate_invoice_ids = fields.One2many("as.alt_create_invoice.line", "wizard_id", string="Tagihan Yang Dibuat")
	custom_invoice_ids = fields.One2many("as.create_custom_invoice.line", "wizard_id", string="Tagihan Yang Dibuat")
	use_next_payment_template = fields.Boolean(string="Template Pembayaran Berikutnya")
	next_payment_debug = fields.Text(string="Keterangan", compute="_get_next_payment_template", store=True)
	next_payment_template_id = fields.Many2one("as.payment.template", ondelete="cascade", string="Template Tagihan Berikutnya", compute="_get_next_payment_template", store=True)

	@api.depends("use_next_payment_template")
	def _get_next_payment_template(self):
		for i in self:
			text = "Template Pembayaran Berikutnya tidak ditemukan:\n"
			valid = True
			if i.use_next_payment_template:
				if len(i.student_id.student_class_ids) <= 0:
					raise exceptions.UserError("Tidak dapat menggunakan Template Pembayaran Berikutnya. Siswa '%s' belum memiliki kelas." % i.student_id.display_name)
				current_stage = sorted(i.student_id.student_class_ids, key=lambda i: i['class_id']['priority'])[-1].class_id.priority
				next_class = self.env['asm.class'].search([('priority', '>', current_stage), ('class_stage_id.payment_template_ids', '!=', [])], limit=1, order="priority asc")
				next_stage = next_class.class_stage_id

				starting_month = self.env['ir.config_parameter'].sudo().get_param('asm_student_payment.new_term_month')
				next_term_year_in = datetime.now().year + 1 if datetime.now().month >= int(starting_month) else datetime.now().year
				next_term_year_out = datetime.now().year + 2 if datetime.now().month >= int(starting_month) else datetime.now().year + 1
				next_term = self.env['asm.term'].search([('year_in', '=', next_term_year_in), ('year_out', '=', next_term_year_out)])
				if not next_class:
					valid = False
					text += "- Tidak ditemukan KELAS dengan jenjang yang lebih tinggi dari jenjang saat ini dan memiliki template pembayaran.\n"
				if not next_term:
					valid = False
					text += "- Tidak ditemukan TAHUN AJARAN berikutnya.\n"

				if next_class and next_stage and next_term:
					next_payment_template = self.env['as.payment.template'].search([('term_id', '=', next_term.id), ('stage_id', '=', next_stage.id)], limit=1)
					if next_payment_template:
						i.next_payment_template_id = next_payment_template.id
					else:
						i.next_payment_template_id = False
						valid = False
						text += "- Tidak ditemukan TEMPLATE PEMBAYARAN dengan tahun ajaran %s dan jenjang %s\n" % (next_term.display_name, next_stage.display_name)
				else:
					i.next_payment_template_id = False
			else:
				i.next_payment_template_id = False			

			if not valid:
				i.next_payment_debug = text
			else:
				i.next_payment_debug = ""

	def action_confirm(self):
		for i in self:
			if not i.student_id:
				raise exceptions.UserError("Tidak bisa membuat tagihan. 'SISWA' belum dipilih.")
			if not i.is_custom:
				if len(i.invoice_ids) == 0 and not i.use_next_payment_template:
					raise exceptions.UserError("Tidak bisa membuat tagihan. 'TAGIHAN YANG DIBUAT' kosong.")
				if len(i.alternate_invoice_ids) == 0 and i.use_next_payment_template:
					raise exceptions.UserError("Tidak bisa membuat tagihan. 'TAGIHAN YANG DIBUAT' kosong.")
			if len(i.custom_invoice_ids) == 0 and i.is_custom:
				raise exceptions.UserError("Tidak bisa membuat tagihan. 'TAGIHAN YANG DIBUAT' kosong.")

			# Standard invoices
			if not i.is_custom:
				# Standard current class invoice
				if not i.use_next_payment_template:
					for item in i.invoice_ids:
						if not item.invoice_id:
							raise exceptions.UserError("Tidak bisa membuat tagihan. 'TAGIHAN' belum dipilih.")
						
						invoice_name = item.invoice_id.payment_category_id.name
						existing_invoice = False
						if item.month:
							invoice_name += " %s %s" % (item.month, item.year)

							existing_invoice = self.env['as.due.payment'].search([('student_id', '=', i.student_id.id), ('reference', '=', invoice_name)], limit=1)
							if existing_invoice:
								raise exceptions.UserError("Tagihan '%s' sudah terbentuk. Tidak dapat membentuk tagihan duplikat." % invoice_name)

						invoice = self.env['as.due.payment'].sudo().create({
							'reference': invoice_name,
							'student_id': i.student_id.id,
							'due_date': item.due_date,
							'amount_total': item.invoice_id.amount_total,
							'balance_payment': item.balance_payment,
							'note': item.note,
						})
						# Create log
						timestamp = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%d %B %Y %H:%M")
						self.env['mail.message'].create({
							'subject': 'Invoice Created',
							'date': datetime.now(),
							'author_id': self.env.user.partner_id.id,
							'model': 'asm.student',
							'res_id': i.student_id.id,
							'message_type': 'notification',
							'subtype_id': self.env.ref('mail.mt_note').id,
							'body': '<p>Tagihan <b>%s</b> telah dibuat pada <b>%s</b> oleh <b>%s</b></p>' % (invoice.name, timestamp, self.env.user.partner_id.name),
						})
				# Standard next class invoice
				else:
					for item in i.alternate_invoice_ids:
						if not item.invoice_id:
							raise exceptions.UserError("Tidak bisa membuat tagihan. 'TAGIHAN' belum dipilih.")
						
						invoice_name = item.invoice_id.name
						existing_invoice = False

						if item.month:
							invoice_name += " %s %s" % (item.month, item.year)

							existing_invoice = self.env['as.due.payment'].search([('student_id', '=', i.student_id.id), ('reference', '=', invoice_name)], limit=1)

							if existing_invoice:
								raise exceptions.UserError("Tagihan '%s' sudah terbentuk. Tidak dapat membentuk tagihan duplikat." % invoice_name)

						invoice = self.env['as.due.payment'].sudo().create({
							'reference': invoice_name,
							'student_id': i.student_id.id,
							'due_date': item.due_date,
							'amount_total': item.amount_total,
							'balance_payment': item.balance_payment,
							'note': item.note,
						})
						# Create log
						timestamp = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%d %B %Y %H:%M")
						self.env['mail.message'].create({
							'subject': 'Invoice Created',
							'date': datetime.now(),
							'author_id': self.env.user.partner_id.id,
							'model': 'asm.student',
							'res_id': i.student_id.id,
							'message_type': 'notification',
							'subtype_id': self.env.ref('mail.mt_note').id,
							'body': '<p>Tagihan <b>%s</b> telah dibuat pada <b>%s</b> oleh <b>%s</b></p>' % (invoice.name, timestamp, self.env.user.partner_id.name),
						})
			# Custom invoices
			else:
				for item in i.custom_invoice_ids:
					if not item.invoice_id:
						raise exceptions.UserError("Tidak bisa membuat tagihan. 'TAGIHAN' belum dipilih.")
					
					invoice_name = item.invoice_id.name
					existing_invoice = False

					if item.month:
						invoice_name += " %s %s" % (item.month, item.year)

						existing_invoice = self.env['as.due.payment'].search([('student_id', '=', i.student_id.id), ('reference', '=', invoice_name)], limit=1)
						if existing_invoice:
							raise exceptions.UserError("Tagihan '%s' sudah terbentuk. Tidak dapat membentuk tagihan duplikat." % invoice_name)
					invoice = self.env['as.due.payment'].sudo().create({
						'reference': invoice_name,
						'student_id': i.student_id.id,
						'due_date': item.due_date,
						'amount_total': item.amount_total,
						'balance_payment': item.balance_payment,
						'note': item.note,
					})
					# Create log
					timestamp = datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()), "%d %B %Y %H:%M")
					self.env['mail.message'].create({
						'subject': 'Invoice Created',
						'date': datetime.now(),
						'author_id': self.env.user.partner_id.id,
						'model': 'asm.student',
						'res_id': i.student_id.id,
						'message_type': 'notification',
						'subtype_id': self.env.ref('mail.mt_note').id,
						'body': '<p>Tagihan <b>%s</b> telah dibuat pada <b>%s</b> oleh <b>%s</b></p>' % (invoice.name, timestamp, self.env.user.partner_id.name),
		 			})

class CreateInvoiceLine(models.TransientModel):
	_name = "as.create_invoice.line"
	_description = "Baris Pembuatan Tagihan"

	wizard_id = fields.Many2one("as.create_invoice.wiz", ondelete="cascade")
	student_id = fields.Many2one("asm.student", ondelete="set null", string="Siswa", related="wizard_id.student_id", store=True)
	invoice_id = fields.Many2one("as.invoice.rule", ondelete="set null", string="Tagihan", domain="[('student_id', '=', student_id), ('invoiced', '=', True)]")
	balance_payment = fields.Boolean("Pembayaran dari Autodebit")
	due_date = fields.Date(string="Batas Bayar")
	month = fields.Selection([
		('January', 'Januari'),
		('February', 'Februari'),
		('March', 'Maret'),
		('April', 'April'),
		('May', 'Mei'),
		('June', 'Juni'),
		('July', 'Juli'),
		('August', 'Agustus'),
		('September', 'September'),
		('October', 'Oktober'),
		('November', 'November'),
		('December', 'Desember'),
	], string="Bulan")
	year = fields.Selection(YEARS, string="Tahun")
	amount_total = fields.Float(string="Nominal")
	note = fields.Char(string="Keterangan")

	@api.onchange("invoice_id")
	def _get_initial_value(self):
		for i in self:
			if i.invoice_id:
				i.balance_payment = i.invoice_id.payment_category_id.balance_payment
				i.due_date = date.today() + timedelta(days=i.invoice_id.payment_category_id.due)

	@api.onchange("month")
	def _get_initial_year(self):
		for i in self:
			if not i.year:
				if i.month:
					i.year = datetime.now().strftime("%Y")
				else:
					i.year = False

	@api.onchange("invoice_id")
	def _get_initial_amount(self):
		for i in self:
			if i.invoice_id:
				i.amount_total = i.invoice_id.amount_total

class CreateAlternateInvoiceLine(models.TransientModel):
	_name = "as.alt_create_invoice.line"
	_description = "Baris Pembuatan Tagihan Alternatif"

	wizard_id = fields.Many2one("as.create_invoice.wiz", ondelete="cascade")
	payment_template_id = fields.Many2one("as.payment.template", ondelete="cascade", related="wizard_id.next_payment_template_id", store=True)
	student_id = fields.Many2one("asm.student", ondelete="set null", string="Siswa", related="wizard_id.student_id", store=True)
	invoice_id = fields.Many2one("asm.payment.category", ondelete="set null", string="Tagihan", domain="[('template_id', '=', payment_template_id)]")
	balance_payment = fields.Boolean("Pembayaran dari Autodebit")
	due_date = fields.Date(string="Batas Bayar")
	month = fields.Selection([
		('January', 'Januari'),
		('February', 'Februari'),
		('March', 'Maret'),
		('April', 'April'),
		('May', 'Mei'),
		('June', 'Juni'),
		('July', 'Juli'),
		('August', 'Agustus'),
		('September', 'September'),
		('October', 'Oktober'),
		('November', 'November'),
		('December', 'Desember'),
	], string="Bulan")
	year = fields.Selection(YEARS, string="Tahun")
	discount_amount = fields.Float(string="Diskon(Rp.)", default=0)
	amount_total = fields.Float(string="Nominal Akhir", compute="_get_amount_total", store=True)
	note = fields.Char(string="Keterangan")

	@api.onchange("invoice_id")
	def _get_initial_value(self):
		for i in self:
			if i.invoice_id:
				i.balance_payment = i.invoice_id.balance_payment
				i.due_date = date.today() + timedelta(days=i.invoice_id.due)

	@api.onchange("month")
	def _get_initial_year(self):
		for i in self:
			if not i.year:
				if i.month:
					i.year = datetime.now().strftime("%Y")
				else:
					i.year = False

	@api.depends("invoice_id", "discount_amount")
	def _get_amount_total(self):
		for i in self:
			if i.invoice_id:
				amount = i.invoice_id.value - i.discount_amount if i.invoice_id.value > 0 else i.invoice_id.value
				if amount < 0:
					raise exceptions.UserError("Nominal tagihan akhir tidak boleh negatif.")
				i.amount_total = i.invoice_id.value - i.discount_amount
			else:
				i.amount_total = 0

class CreateCustomInvoiceLine(models.TransientModel):
	_name = "as.create_custom_invoice.line"
	_description = "Baris Pembuatan Tagihan Custom"

	wizard_id = fields.Many2one("as.create_invoice.wiz", ondelete="cascade")
	invoice_id = fields.Many2one("as.selection", ondelete="cascade", string="Tagihan", domain=[('is_custom_transaction', '=', True)], required=True)
	balance_payment = fields.Boolean("Pembayaran dari Autodebit")
	due_date = fields.Date(string="Batas Bayar", required=True)
	month = fields.Selection([
		('January', 'Januari'),
		('February', 'Februari'),
		('March', 'Maret'),
		('April', 'April'),
		('May', 'Mei'),
		('June', 'Juni'),
		('July', 'Juli'),
		('August', 'Agustus'),
		('September', 'September'),
		('October', 'Oktober'),
		('November', 'November'),
		('December', 'Desember'),
	], string="Bulan")
	year = fields.Selection(YEARS, string="Tahun")
	amount_total = fields.Float(string="Nominal", required=True)
	note = fields.Char(string="Keterangan")

	@api.model
	def create(self, values):
		if values['amount_total'] <= 0:
			raise exceptions.UserError("Nominal harus positif dan tidak boleh 0.")
		return super(CreateCustomInvoiceLine, self).create(values)

	def write(self, values):
		if 'amount_total' in values and values['amount_total'] <= 0:
			raise exceptions.UserError("Nominal harus positif dan tidak boleh 0.")
		return super(CreateCustomInvoiceLine, self).write(values)

	@api.onchange("month")
	def _get_initial_year(self):
		for i in self:
			if not i.year:
				if i.month:
					i.year = datetime.now().strftime("%Y")
				else:
					i.year = False