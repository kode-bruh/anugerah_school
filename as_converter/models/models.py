# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import date, datetime
import base64
from xlrd import open_workbook
from datetime import date
import io
import xlsxwriter

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

class ExcelImport(models.Model):
	_name = "as.import"

	name = fields.Char(string="Referensi", compute="_get_import_data", store=True)
	account_id = fields.Many2one("asm.account", ondelete="restrict", string="Akun Keuangan", required=True, default=lambda self: int(self.env['ir.config_parameter'].sudo().get_param('asm_accounting.account_id')))
	file = fields.Binary(required=True)
	date = fields.Date(compute="_get_import_data", store=True, string="Tanggal")
	import_by = fields.Many2one('res.users', ondelete="restrict", string="Diimport oleh")
	import_date = fields.Datetime(string="Proses Import Mulai", readonly=True)
	import_end_date = fields.Datetime(string="Proses Import Selesai", readonly=True)
	item_ids = fields.One2many("as.import.line", "import_id", string="Daftar Autodebit")
	ready = fields.Boolean(compute="_get_ready_state", store=True)
	done = fields.Boolean(readonly=True)
	amount_total = fields.Float(string="Total Nominal", compute="_get_total_amount", store=True)
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
	], string="Bulan", default=lambda *a: datetime.now().strftime("%B"), required=True)
	year = fields.Selection(YEARS, string="Tahun", default=lambda *a: datetime.now().strftime("%Y"), required=True)

	_sql_constraints = [('unique_name', 'unique(name, month, year)', 'Import autodebit hanya dapat dilakukan 1x per bulan.')]

	@api.depends("item_ids")
	def _get_total_amount(self):
		for i in self:
			i.amount_total = sum([x.amount_total for x in i.item_ids])

	@api.depends("file", "month", "year")
	def _get_import_data(self):
		for i in self:
			i.name = "Import Autodebit - %s %s" % (i.month, i.year)
			i.date = datetime.strptime("%s %s 01" % (i.year, i.month), "%Y %B %d").date()	

	@api.depends("item_ids.state")
	def _get_ready_state(self):
		for i in self:
			ready = True
			for item in i.item_ids:
				if item.state == 'Error' and item.to_import:
					ready = False
					break
			if len(i.item_ids) == 0:
				ready = False
			i.ready = ready

	def _recheck_all_items(self):
		for i in self:
			for item in i.item_ids:
				item.action_refresh()

	def recheck_all_items(self, raise_exception=False):
		for i in self:
			i._recheck_all_items()
			if not i.ready and raise_exception:
				raise exceptions.UserError("Terdapat beberapa error pada daftar import autodebit ini. Klik 'Cek Ulang' untuk melihat error yang ditemukan.")

	def action_import(self):
		for i in self:
			i.recheck_all_items(raise_exception=True)
			i.import_date = datetime.now()
			for item in i.item_ids:
				if item.to_import:
					amount = item.amount_total
					for invoice in item.invoice_ids:
						to_pay = amount if amount <= invoice.unpaid else invoice.unpaid
						amount -= to_pay
						if to_pay > 0:
							payment = self.env['as.payment'].create({
								'student_id': item.student_id.id,
								'account_id': i.account_id.id,
								'payment_id': invoice.id,
								'payment_method': self.env['as.selection'].search([('name', '=', 'Autodebit')], limit=1).id,
								'value': to_pay,
								'paid_by_autodebit': True,
								'autodebit_id': i.id,
							})
							payment.action_post(autodebit=True)
			i.done = True
			i.import_end_date = datetime.now()
			i.import_by = self.env.user.id

	def action_undo_import(self):
		for i in self:
			posted_payments = self.env['as.payment'].search([
				('autodebit_id', '=', i.id), 
				('paid_by_autodebit', '=', True), 
				('state', '=', 'Posted')])
			for payment in posted_payments:
				payment.action_cancel()
				payment.unlink()
			i.import_date = False
			i.import_end_date = False
			i.import_by = False
			i.done = False

	def action_load(self):
		for i in self:
			read = io.BytesIO()
			read.write(base64.decodestring(i.file)) #decode binary from field, then write (set) it into read variable
			book = open_workbook(file_contents=read.getvalue())
			sheet = book.sheets()[0]

			#SET COLUMN NUMBER FOR EACH VALUE
			nias_col = 14
			name_col = 12
			value_col = 9

			#READ FILE
			import_line = [(5, 0, 0)] # Always reset the lines
			for x in range(11, sheet.nrows): # Change the 12 inside range() according to the row number of the first table content minus 1 in uploaded Excel
				if x == 0:
					continue
				if x >= 1:
					nias = sheet.cell_value(x, nias_col)
					nias = repr(nias).split(".")[0]
					name = sheet.cell_value(x, name_col)
					value = sheet.cell_value(x, value_col)

					if not sheet.cell_value(x, nias_col) and not sheet.cell_value(x, name_col) and not sheet.cell_value(x, value_col):
						break

					if nias:
						nias = str(nias).replace("'", "").replace('"',"")
						student = self.env['asm.student'].search([('nias', '=', nias), ('active', '=', True)], limit=1, order="id desc")
						if student:
							invoices = self.env['as.due.payment'].search([('student_id', '=', student.id), ('status', '=', 'Belum Lunas'), ('balance_payment', '=', True)], order="id asc")
							invoice_list = []
							for_paying = value
							for invoice in invoices:
								if for_paying > 0:
									invoice_list.append(invoice.id)
									for_paying -= invoice.unpaid
								else: 
									break
							import_line.append((0, 0, {
								'name': name,
								'nias': nias,
								'student_id': student.id,
								'amount_total': value,
								'invoice_ids': invoice_list,
							}))
						else:
							import_line.append((0, 0, {
								'name': name,
								'nias': nias,
								'amount_total': value,
							}))
			i.item_ids = import_line

class ExcelImportLine(models.Model):
	_name = "as.import.line"

	import_id = fields.Many2one("as.import", ondelete="cascade")
	name = fields.Char(string="Nama Siswa", readonly=True)
	nias = fields.Char(string="NIAS", readonly=True)
	student_id = fields.Many2one("asm.student", ondelete="set null", string="Siswa")
	amount_total = fields.Float(string="Nominal")
	invoice_ids = fields.Many2many("as.due.payment", string="Tagihan yang Dibayar", readonly=True)
	state = fields.Selection([
		('Ready', 'Ready'),
		('Error', 'Error')
	], string="Status", compute="_get_state", store=True)
	note = fields.Text(compute="_get_state", store=True)
	to_import = fields.Boolean(default=True, readonly=True, copy=False)
	done = fields.Boolean(related="import_id.done", store=True)

	@api.depends("student_id", "amount_total", "invoice_ids")
	def _get_state(self):
		for i in self:
			valid = True
			text = ""
			if not i.student_id:
				valid = False
				text += "- Siswa tidak ditemukan, harap memperbaiki NIAS di data siswa yang dimaksud\n"
			if i.amount_total <= 0:
				valid = False
				text += "- Nominal tidak boleh negatif maupun nol, harap mengubah nominal sesuai nominal autodebit\n"
			if len(i.invoice_ids) == 0:
				valid = False
				text += "- Tidak ada tagihan yang dapat dibayarkan menggunakan nominal autodebit ini, harap membuat tagihan yang dapat dibayarkan\n"
			else:
				balance_left = i.amount_total
				for invoice in i.invoice_ids:
					balance_left -= invoice.unpaid
				if balance_left > 0:
					valid = False
					text += "- Nominal autodebit belum terpakai penuh, harap membuat tagihan yang dapat dibayarkan\n"
			i.note = "Terdapat beberapa kesalahan data dalam autodebit siswa ini: \n%s" % text if not valid else ""
			i.state = 'Ready' if valid else 'Error'

	def action_refresh(self):
		for i in self:
			if not i.student_id:
				student = self.env['asm.student'].search([('nias', '=', i.nias), ('active', '=', True)], limit=1, order="id desc")
				i.student_id = student.id if student else False
			else:
				# Recheck NIAS
				student = self.env['asm.student'].search([('nias', '=', i.nias), ('active', '=', True)], limit=1, order="id desc")
				if not student:
					i.student_id = False
				else:
					if student != i.student_id:
						i.student_id = student.id

			if i.student_id:
				invoices = self.env['as.due.payment'].search([('student_id', '=', i.student_id.id), ('status', '=', 'Belum Lunas'), ('balance_payment', '=', True)], order="id asc")

				invoice_list = []
				for_paying = i.amount_total
				for invoice in invoices:
					if for_paying > 0:
						invoice_list.append(invoice.id)
						for_paying -= invoice.unpaid
					else: 
						break
				i.invoice_ids = [(6, 0, invoice_list)]

	def action_toggle_import(self):
		for i in self:
			i.to_import = not i.to_import