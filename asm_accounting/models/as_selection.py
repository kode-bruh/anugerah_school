from odoo import fields, models, api

class SelectionData(models.Model):
	_name = "as.selection"
	_inherit = "as.selection"

	is_payment_channel = fields.Boolean(string="Sebuah Metode Pembayaran?")
	payment_extra_fee = fields.Integer(string="Denda (Rp)", default=0, help="Untuk mengenakan biaya tambahan jika ada yang memakai metode pembayaran ini.")
	payment_cut_fee = fields.Float(string="Potongan (%)", default=0, help="Untuk mengabaikan biaya potongan jika ada yang memakai metode pembayaran ini.")