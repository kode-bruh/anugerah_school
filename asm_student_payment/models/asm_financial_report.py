from odoo import api, models, fields, exceptions
from datetime import date, datetime, timedelta
import pytz

class FinancialReport(models.Model):
	_name = "asm.financial.report"
	_description = "Laporan Estimasi"

	name = fields.Char(string="Deskripsi", compute="_get_name", store=True)
	month = fields.Char(string="Bulan", readonly=True)
	year = fields.Char(string="Tahun", readonly=True)
	item_ids = fields.One2many("asm.financial.report.item", "report_id", string="Tagihan", readonly=True)

	_sql_constraints = [
	    ('report_month_year_unique', 'UNIQUE(month, year)', 'Cannot have a duplicate month and year financial report.')
	]

	@api.depends("month", "year")
	def _get_name(self):
		for i in self:
			if i.month and i.year:
				i.name = 'Laporan Estimasi %s %s' % (i.month, i.year)
			else:
				i.name = 'New'

	def refresh_paid_amount(self):
		for i in self:
			for item in i.item_ids:
				item.calculate_paid_amount()

	def refresh_total_amount(self):
		for i in self:
			for item in i.item_ids:
				item.calculate_total_amount()

	@api.model
	def create(self, values):
		values['month'] = date.today().strftime("%B")
		values['year'] = date.today().strftime("%Y")
		return super(FinancialReport, self).create(values)

	@api.model
	def create_monthly_report(self, force_month=False):
		categories = self.env['as.financial.report.category'].search([])
		localTZ = pytz.timezone("Asia/Jakarta") 
		month = datetime.now(localTZ).strftime("%B") if not force_month else force_month

		values = {
			'month': month,
			'year': datetime.now(localTZ).strftime("%Y"),
			'item_ids': [(0, 0, {
				'category_id': category.id,
				'include_past_receivable': category.include_past_receivable,
				'only_past_receivable': category.only_past_receivable,
			}) for category in categories]
		}
		
		report = self.env['asm.financial.report'].search([('month', '=', month), ('year', '=', datetime.now(localTZ).strftime("%Y"))], limit=1)
		if not report:
			report = self.env['asm.financial.report'].create(values)
			for item in report.item_ids:
				item.calculate_total_amount()
				item.calculate_paid_amount()
		else:
			for item in report.item_ids:
				item.calculate_paid_amount()

class FinancialReportItem(models.Model):
	_name = "asm.financial.report.item"
	_description = "Item Laporan Estimasi"

	report_id = fields.Many2one("asm.financial.report", ondelete="cascade")
	month = fields.Char(string="Bulan", related="report_id.month", store=True)
	year = fields.Char(string="Tahun", related="report_id.year", store=True)
	category_id = fields.Many2one("as.financial.report.category", ondelete="restrict", string="Jenis Tagihan")
	invoice_domain = fields.Char(string="Filter Tagihan", related="category_id.invoice_domain", store=True)
	payment_domain = fields.Char(string="Filter Pembayaran", related="category_id.payment_domain", store=True)
	total = fields.Float(string="Total", readonly=True)
	paid = fields.Float(string="Terbayar", readonly=True)
	include_past_receivable = fields.Boolean(string="Hitung Hutang", readonly=True)
	only_past_receivable = fields.Boolean(string="Hanya Hutang", readonly=True)

	# TOTAL => as.due.payment
	#		- SPP = 	[('reference', 'ilike', 'SPP')]
	#		- FORM = 	[('reference', 'ilike', 'Formulir')]
	#		- DU = 		[('reference', 'ilike', 'Daftar Ulang')]
	#		- PENGEM = 	[('reference', 'ilike', 'Pengembangan')]


	# PAID  => as.payment
	#		- SPP = 	[('approved_date', '>=', create_date(localTZ)), ('payment_id.reference', 'ilike', 'SPP')]
	#		- FORM = 	[('approved_date', '>=', create_date(localTZ)), ('payment_id.reference', 'ilike', 'Formulir')]
	#		- DU = 		[('approved_date', '>=', create_date(localTZ)), ('payment_id.reference', 'ilike', 'Daftar Ulang')]
	#		- PENGEM = 	[('approved_date', '>=', create_date(localTZ)), ('payment_id.reference', 'ilike', 'Pengembangan')]

	def calculate_total_amount(self):
		for i in self:
			localTZ = pytz.timezone("Asia/Jakarta") 
			starting_date = datetime.strptime("01 %s %s" % (i.month, i.year), "%d %B %Y") - timedelta(hours=7)

			# Calculate current month's receivables
			DOMAIN = [('create_date', '>=', starting_date)] + list(eval(i.invoice_domain))
			invoices = self.env['as.due.payment'].search(DOMAIN)
			current_month_total = sum([invoice.amount_total for invoice in invoices])

			# Calculate past months receivables
			DOMAIN = [('create_date', '<', starting_date), ('unpaid', '>', 0)] + list(eval(i.invoice_domain))
			invoices = self.env['as.due.payment'].search(DOMAIN)
			past_month_total = sum([invoice.unpaid for invoice in invoices])

			if i.include_past_receivable:
				if i.only_past_receivable:
					i.total = past_month_total
				else:
					i.total = current_month_total + past_month_total
			else:
				i.total = current_month_total

	def calculate_paid_amount(self):
		for i in self:
			localTZ = pytz.timezone("Asia/Jakarta") 
			starting_date = datetime.strptime("01 %s %s" % (i.month, i.year), "%d %B %Y") - timedelta(hours=7)

			DOMAIN = [('approved_date', '>=', starting_date)] + list(eval(i.payment_domain))

			payments = self.env['as.payment'].search(DOMAIN)
			i.paid = sum([payment.value for payment in payments])

class FinancialReportCategory(models.Model):
	_name = "as.financial.report.category"
	_description = "Pengaturan Laporan Estimasi"

	name = fields.Char(string="Jenis Tagihan", required=True)
	invoice_domain = fields.Char(string="Filter Tagihan", required=True, default="[]")
	payment_domain = fields.Char(string="Filter Pembayaran", required=True, default="[]")
	include_past_receivable = fields.Boolean(string="Hitung Hutang")
	only_past_receivable = fields.Boolean(string="Hanya Hutang")