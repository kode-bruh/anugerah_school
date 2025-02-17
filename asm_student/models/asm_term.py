from odoo import api, models, fields, exceptions
from datetime import date, datetime, timedelta

class Terms(models.Model):
	_name = "asm.term"
	_description = "Tahun Ajaran"
	_order = "year_in desc"

	name = fields.Char(string="Nama", compute="_get_name", store=True)
	year_in = fields.Char(string="Tahun Awal", required=True)
	year_out = fields.Char(string="Tahun AKhir", required=True)

	@api.depends("year_in", "year_out")
	def _get_name(self):
		for i in self:
			i.name = "%s - %s" % (i.year_in, i.year_out)

	@api.onchange("year_in", "year_out")
	def _validate_term(self):
		for i in self:
			if i.year_in and i.year_out:
				if i.year_in >= i.year_out:
					raise exceptions.UserError("Tahun Awal tidak bisa sama atau lebih dari Tahun Akhir.")