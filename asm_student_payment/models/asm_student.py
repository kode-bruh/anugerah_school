from odoo import fields, api, models, exceptions
from datetime import datetime, date, timedelta

class BalanceEntry(models.Model):
	_name = "as.balance.entry"
	_description = "Balance Entry"

	student_id = fields.Many2one("asm.student", ondelete="cascade", string="Siswa")
	date = fields.Date(string="Tanggal")
	type = fields.Selection([
		('IN', 'IN'),
		('OUT', 'OUT')
	], string="Jenis")
	value = fields.Float(string="Nominal")
	currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id.id)

class Student(models.Model):
	_name = "asm.student"
	_inherit = "asm.student"

	account_number = fields.Char(string="Rekening Siswa", tracking=True)

	# use_custom_payment_template = fields.Boolean(string="Template Tagihan Custom", tracking=True)
	is_custom_invoice = fields.Boolean(string="Tagihan Khusus", tracking=True)
	is_employee_kid = fields.Boolean(string="Anak Karyawan", tracking=True)
	payment_template = fields.Many2one("as.payment.template", ondelete="set null", compute="_get_payment_template", store=True, string="Template Pembayaran")
	# custom_payment_template = fields.Many2one("as.payment.template", ondelete="restrict", string="Template Pembayaran", tracking=True)
	# final_payment_template = fields.Many2one("as.payment.template", compute="_get_payment_template", store=True, string="Template Pembayaran", tracking=True)
	payment_rule_match = fields.Boolean(compute="_get_rule_match", store=True)
	due_invoice = fields.One2many("as.due.payment", "student_id", string="Tagihan", tracking=True)
	invoiced = fields.Boolean(string="Tertagih", related="state_id.is_invoiced")
	invoice_rules = fields.One2many("as.invoice.rule", "student_id", string="Pengaturan Tagihan", tracking=True)
	is_not_invoiced = fields.Boolean(compute="_get_if_not_invoiced", store=True)
	balance_entry = fields.One2many("as.balance.entry", "student_id", string="Pemasukan Saldo")
	balance = fields.Float(string="Saldo", compute="_compute_balance", store=True)
	payment_note = fields.Text(string="Keterangan")

	refund_ids = fields.One2many("as.refund.payment", "student_id", string="Refund")

	@api.depends("invoice_rules.invoiced")
	def _get_if_not_invoiced(self):
		for i in self:
			result = False
			for rule in i.invoice_rules:
				if not rule.invoiced:
					result = True
					break
			i.is_not_invoiced = result

	def action_open_refund(self):
		for i in self:
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'as.refund.payment',
				'view_mode': 'form',
				'view_type': 'form',
				'target': 'new',
				'context': {
					'default_student_id': i.id,
				}
			}

	@api.depends('student_class_ids', 'student_class_ids.term_id', 'state_id')
	def _get_payment_template(self, bypass=False):
		for i in self:
			invoiced_states = self.env['asm.state'].sudo().search([('is_invoiced', '=', True)]).ids
			if len(i.student_class_ids) > 0 and i.state_id.id in invoiced_states:
				# Reset payment template and reset invoice rules
				if len(i.student_class_ids) > 0:
					class_student = sorted(i.student_class_ids, key=lambda i: i['class_id']['priority'])[-1] 
					class_id = class_student.class_id
					stage_id = class_id.class_stage_id
					term_id = class_student.term_id
					if not stage_id or not term_id:
						raise exceptions.UserError("Kelas saat ini harus memiliki Jenjang dan Tahun Ajaran")

					payment_template = self.env['as.payment.template'].sudo().search([('term_id', '=', term_id.id), ('stage_id', '=', stage_id.id)], limit=1)

					if not payment_template:
						raise exceptions.UserError("Template Pembayaran tidak dapat ditemukan untuk tahun ajaran %s dan jenjang %s." % (term_id.display_name, stage_id.display_name))

					if payment_template:
						if bypass:
							i._reset_template_invoice(payment_template)
						else:
							if not i.is_custom_invoice and not i.is_employee_kid:
								i._reset_template_invoice(payment_template)
					else:
						raise exceptions.UserError("Anda tidak dapat membuat pengaturan tagihan untuk siswa '%s' sebelum memilih template pembayaran." % self.full_name)
				else:
					i.payment_template = False
					i.invoice_rules = [(5, 0, 0)]
			else:
				# Do not reset invoice rules
				i.payment_template = False
				i.invoice_rules = [(5, 0, 0)]

	def _reset_template_invoice(self, payment_template):
		for i in self:
			i.payment_template = payment_template.id
			# Reset invoice rules
			if len(i.invoice_rules) > 0:
				for rule in i.invoice_rules:
					rule.sudo().unlink()
			# Re add invoice rules based on existing template
			if len(payment_template.category_ids) > 0:
				for rule in payment_template.category_ids:
					record = self.env['as.invoice.rule'].create({
						'payment_category_id': rule.id,
						'student_id': i.id,
						'value': rule.value,
					})
			else:
				raise exceptions.UserError("Tidak ada pengaturan invoice yang dapat dibuat untuk Template Tagihan '%s'. \nSilahkan tambahkan jenis tagihan ke dalam template pembayaran." % payment_template.name)

	@api.depends('payment_template.category_ids', 'payment_template.category_ids.value', 'invoice_rules', 'invoice_rules.value', 'invoice_rules.discount_amount', 'student_class_ids')
	def _get_rule_match(self):
		for i in self:
			match = True
			if i.payment_template:
				if len(i.payment_template.category_ids) != len(i.invoice_rules):
					match = False
				else:
					for rule in i.invoice_rules:
						if rule.discount_amount and rule.discount_amount > 0:
							match = False
							break
							
						if not rule.payment_category_id:
							match = False
							break

						if rule.payment_category_id.value != rule.value:
							match = False
							break
				# payment_template_category = sorted(i.payment_template.category_ids.ids)
				# payment_rule_category = sorted([x.payment_category_id.id for x in i.invoice_rules])

				# payment_template_price = sorted([x.value for x in i.payment_template.category_ids])
				# payment_rule_price = sorted([x.payment_category_id.value for x in i.invoice_rules])

				# i.payment_rule_match = (payment_template_category == payment_rule_category) and (payment_template_price == payment_rule_price)
			else:
				match = False

			i.payment_rule_match = match

	@api.depends('balance_entry')
	def _compute_balance(self):
		for i in self:
			total = 0 
			# total variable holds current balance
			# Can be positive if there is unassigned balance
			# And can be 0, if all balance assigned to invoices
			# Never negative.

			for entry in i.balance_entry:
				if entry.type == 'IN':
					total += entry.value
				else:
					total -= entry.value

			i.balance = total

	def print_report(self):
		return self.env.ref("asm_student_payment.student_contract").report_action(self)

	def populate_invoice_rules(self):
		for i in self:
			i._get_payment_template(bypass=True)

	def view_create_invoice(self):
		for i in self:
			return {
				'type': 'ir.actions.act_window',
				'name': 'Create Invoice',
				'res_model': 'as.create_invoice.wiz',
				'view_mode': 'form',
				'view_type': 'form',
				'target': 'new',
				'context': {'default_is_custom': False, 'default_student_id': i.id},
			}

	def view_create_custom_invoice(self):
		for i in self:
			return {
				'type': 'ir.actions.act_window',
				'name': 'Create Custom Invoice',
				'res_model': 'as.create_invoice.wiz',
				'view_mode': 'form',
				'view_type': 'form',
				'target': 'new',
				'context': {'default_is_custom': True, 'default_student_id': i.id},
			}

	### Deprecated
	# def populate_initial_invoices(self):
	# 	if self.invoiced:
	# 		if len(self.invoice_rules) > 0:
	# 			for invoice in self.payment_template.category_ids:
	# 				if invoice.category_type == '1x Bayar':
	# 					personal_rule = False
	# 					for i in self.invoice_rules:
	# 						if i.payment_category_id.id == invoice.id:
	# 							personal_rule = i
	# 							break
	# 					if personal_rule and personal_rule.invoiced:
	# 						self.env['as.due.payment'].sudo().create({
	# 							'reference': invoice.name,
	# 							'student_id': self.id,
	# 							'due_date': datetime.today() + timedelta(days=invoice.due),
	# 							'amount_total': personal_rule.amount_total if personal_rule else invoice.value,
	# 							'balance_payment': personal_rule.payment_category_id.balance_payment
	# 						})
	# 		else:
	# 			raise exceptions.UserError("""
	# 				Anda tidak punya pengaturan invoice. Harap:
	# 				\n- Klik Create Rule, atau jika tidak melihat tombol tersebut, klik Unlock lalu klik Create Rule.
	# 				\n- Definisikan aturan invoice untuk siswa ini.
	# 				""")
	# 	else:
	# 		raise exceptions.UserError("Anda tidak dapat membuat invoice dalam status %s" % self.state_id.name)


### DEPRECATED
# class MassInvoice(models.TransientModel):
# 	_name = "as.mass.invoice"
# 	_description = "Mass Invoicing"

# 	student_ids = fields.Many2many("asm.student", string="Siswa Ditagih")

# 	def create_invoices(self):
# 		for i in self:
# 			if len(i.student_ids) > 0:
# 				for student in i.student_ids:
# 					if student.invoiced:
# 						student.populate_initial_invoices()
# 			else:
# 				raise exceptions.UserError("Sebelum membuat Invoice, masukkan terlebih dahulu nama-nama siswa yang akan ditagih.")